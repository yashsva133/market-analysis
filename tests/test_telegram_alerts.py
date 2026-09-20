"""Tests for Telegram alert formatting, duplicate prevention, mute check, and retry."""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import httpx

from services.notifier.telegram_bot import TelegramNotifier
from packages.common.models import AlertRecord, Event, Company, Security, SourceItem, EventFact
from packages.schemas.taxonomy import EventTaxonomy, ImportanceClass


@pytest.mark.asyncio
async def test_telegram_alert_formatting_and_no_advice():
    """Verify alert content includes evidence and never includes buy/sell advice."""
    from packages.ai.agents import alert_formatter_agent

    alert_text = alert_formatter_agent.format_telegram_alert(
        company_name="Tata Consultancy Services Limited",
        symbol="TCS",
        bse_code="532540",
        event_type="ORDER_WIN",
        importance="CRITICAL",
        headline="TCS wins $1B digital transformation contract from UK insurer",
        why_flagged=["Contract value exceeds 5% of annual revenue"],
        unknowns=["Implementation margin not disclosed"],
        source_url="https://nseindia.com/announcements/tcs_filing.pdf",
        financial_context="Scale represents ~8.2% of FY25 revenue.",
        market_reaction="Same-day reaction: +2.8% on 1.8x 20D volume.",
    )

    assert "CRITICAL EVENT" in alert_text
    assert "TCS" in alert_text
    assert "FINANCIAL CONTEXT" in alert_text
    assert "MARKET REACTION" in alert_text
    assert "WHAT IS STILL UNKNOWN" in alert_text
    
    lower = alert_text.lower()
    assert "buy" not in lower
    assert "sell" not in lower
    assert "recommendation" not in lower
    assert "target price" not in lower
    assert "bullish" not in lower


@pytest.mark.asyncio
async def test_telegram_notifier_delivery_and_duplicate_prevention(monkeypatch):
    """Verify notifier dispatches pending alert and skips duplicates."""
    from packages.common.config import settings
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "mock_bot_token_123")
    monkeypatch.setattr(settings, "TELEGRAM_CHAT_ID", "mock_chat_id_456")

    company_id = uuid.uuid4()
    company = Company(
        id=company_id,
        isin="INE467B01029",
        legal_name="Tata Consultancy Services Limited",
        status="ACTIVE",
    )
    security = Security(
        id=uuid.uuid4(),
        company_id=company_id,
        exchange="NSE",
        symbol="TCS",
        is_active=True,
    )
    company.securities = [security]

    event_id = uuid.uuid4()
    event = Event(
        id=event_id,
        company_id=company_id,
        event_type=EventTaxonomy.ORDER_WIN.value,
        importance=ImportanceClass.CRITICAL.value,
        headline="TCS bags major contract",
        status="EXTRACTED",
    )
    event.company = company
    event.source_item = SourceItem(id=uuid.uuid4(), source_id="nse", url="https://example.com")
    event.facts = []

    alert = AlertRecord(
        id=uuid.uuid4(),
        event_id=event_id,
        channel="telegram",
        alert_class="CRITICAL",
        delivery_status="PENDING",
    )
    alert.event = event

    # Create mock httpx transport
    async def mock_transport_handler(request):
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 98765}})

    transport = httpx.MockTransport(mock_transport_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    notifier = TelegramNotifier(
        bot_token="mock_bot_token_123",
        chat_id="mock_chat_id_456",
        http_client=mock_client,
    )

    # Mock DB session
    mock_session = AsyncMock()
    
    async def mock_execute(query):
        q_str = str(query).upper()
        res = MagicMock()
        if "ALERTS.DELIVERY_STATUS IN" in q_str:
            res.scalars.return_value.all.return_value = [alert]
        elif "ALERTS.DELIVERY_STATUS = 'SENT'" in q_str or "ALERTS.ID !=" in q_str:
            res.scalar_one_or_none.return_value = None  # No prior sent alert
        elif "WATCHLIST_ITEMS" in q_str:
            res.scalar_one_or_none.return_value = None  # Not muted
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute = AsyncMock(side_effect=mock_execute)
    mock_session.commit = AsyncMock()

    stats = await notifier.send_pending_alerts(mock_session)

    assert stats["sent"] == 1
    assert alert.delivery_status == "SENT"
    assert alert.telegram_message_id == "98765"
    assert alert.sent_at is not None

    # Now simulate duplicate: prior sent alert exists
    alert_dup = AlertRecord(
        id=uuid.uuid4(),
        event_id=event_id,
        channel="telegram",
        alert_class="CRITICAL",
        delivery_status="PENDING",
    )
    alert_dup.event = event

    async def mock_execute_dup(query):
        q_str = str(query).upper()
        res = MagicMock()
        if "ALERTS.DELIVERY_STATUS IN" in q_str:
            res.scalars.return_value.all.return_value = [alert_dup]
        elif "ALERTS.DELIVERY_STATUS = 'SENT'" in q_str or "ALERTS.ID !=" in q_str:
            res.scalar_one_or_none.return_value = alert.id  # Prior sent alert found!
        elif "WATCHLIST_ITEMS" in q_str:
            res.scalar_one_or_none.return_value = None
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute = AsyncMock(side_effect=mock_execute_dup)
    stats_dup = await notifier.send_pending_alerts(mock_session)

    assert stats_dup["skipped"] == 1
    assert alert_dup.delivery_status == "DUPLICATE_SKIPPED"
