"""Tests for Corporate Actions Calendar and Company Comparison APIs."""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from apps.api.routers.calendar import get_corporate_actions, get_actions_summary
from apps.api.routers.compare import compare_companies
from packages.common.models import Company, Event, Security


def _calendar_event(symbol: str, event_type: str, headline: str) -> Event:
    company = Company(
        id=uuid.uuid4(), isin="INE018A01030", legal_name="Larsen & Toubro Limited", sector="Capital Goods"
    )
    company.securities = [Security(company_id=company.id, exchange="NSE", symbol=symbol, is_active=True)]
    event = Event(
        id=uuid.uuid4(),
        company_id=company.id,
        event_type=event_type,
        importance="HIGH",
        headline=headline,
        announcement_time=datetime(2026, 2, 10, tzinfo=timezone.utc),
        status="EXTRACTED",
    )
    event.company = company
    return event


def _calendar_db(events):
    mock_db = AsyncMock()

    async def mock_execute(query):
        res = MagicMock()
        res.scalars.return_value.all.return_value = events
        res.scalar_one_or_none.return_value = None
        return res

    mock_db.execute = AsyncMock(side_effect=mock_execute)
    return mock_db


@pytest.mark.asyncio
async def test_corporate_actions_calendar_filtering():
    """Corporate actions come from ingested events; ex/record dates stay null instead of synthesized."""
    lt_div = _calendar_event("LT", "DIVIDEND", "Interim Dividend - Rs 34.00 per equity share")
    infy_buyback = _calendar_event("INFY", "BUYBACK", "Buyback via tender offer route")
    db = _calendar_db([lt_div, infy_buyback])

    res = await get_corporate_actions(symbol="LT", db=db)
    assert res["status"] == "ok"
    assert len(res["actions"]) == 1
    assert res["actions"][0]["symbol"] == "LT"
    assert res["actions"][0]["action_type"] == "DIVIDEND"
    assert res["actions"][0]["ex_date"] is None
    assert res["actions"][0]["record_date"] is None

    res_div = await get_corporate_actions(action_type="DIVIDEND", db=_calendar_db([lt_div, infy_buyback]))
    assert res_div["status"] == "ok"
    assert all(a["action_type"] == "DIVIDEND" for a in res_div["actions"])


@pytest.mark.asyncio
async def test_corporate_actions_summary():
    lt_div = _calendar_event("LT", "DIVIDEND", "Interim Dividend - Rs 34.00 per equity share")
    infy_buyback = _calendar_event("INFY", "BUYBACK", "Buyback via tender offer route")
    res = await get_actions_summary(db=_calendar_db([lt_div, infy_buyback]))
    assert res["total_actions"] == 2
    assert "DIVIDEND" in res["by_type"]
    # No fabricated forward-looking window counts
    assert res["upcoming_30_days"] == 0


@pytest.mark.asyncio
async def test_company_comparison_multi_equity():
    """Comparison is grounded in ingested snapshots; unknown symbols 404 instead of fabricated metrics."""
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal
    from unittest.mock import AsyncMock, MagicMock
    from fastapi import HTTPException
    from packages.common.models import Company, FinancialSnapshot, Security

    company_a = Company(
        id=uuid.uuid4(), isin="INE018A01030", legal_name="Larsen & Toubro Limited", sector="Capital Goods"
    )
    company_a.securities = [Security(company_id=company_a.id, exchange="NSE", symbol="LT", is_active=True)]
    company_b = Company(
        id=uuid.uuid4(), isin="INE002A01018", legal_name="Reliance Industries Limited", sector="Energy"
    )
    company_b.securities = [Security(company_id=company_b.id, exchange="NSE", symbol="RELIANCE", is_active=True)]
    fin_a = FinancialSnapshot(
        id=uuid.uuid4(), company_id=company_a.id, period="FY2025-26",
        revenue=Decimal("2000000000000"), pat=Decimal("120000000000"),
        ebitda=Decimal("220000000000"), pe=Decimal("34.2"), roce=Decimal("14.2"),
        market_cap=Decimal("4982000000000"),
    )
    fin_b = FinancialSnapshot(
        id=uuid.uuid4(), company_id=company_b.id, period="FY2025-26",
        revenue=Decimal("9000000000000"), pat=Decimal("700000000000"),
        ebitda=Decimal("1500000000000"), pe=Decimal("26.5"), roce=Decimal("10.5"),
        market_cap=Decimal("19800000000000"),
    )

    company_by_symbol = {"LT": (company_a, fin_a), "RELIANCE": (company_b, fin_b)}
    # Symbols are resolved in request order; each symbol triggers a company
    # lookup followed by a financial snapshot lookup.
    call_sequence = ["LT", "RELIANCE", "NOTASTOCK"]
    call_idx = {"i": 0}
    current = {"sym": None}

    mock_db = AsyncMock()

    async def mock_execute(query):
        res = MagicMock()
        q_str = str(query)
        if "financial_snapshots" in q_str:
            # Snapshot lookup for the symbol resolved by the preceding company query
            comp, fin = company_by_symbol.get(current["sym"], (None, None))
            res.scalar_one_or_none.return_value = fin
        else:
            sym = call_sequence[call_idx["i"]] if call_idx["i"] < len(call_sequence) else None
            call_idx["i"] += 1
            current["sym"] = sym
            comp, fin = company_by_symbol.get(sym, (None, None))
            res.scalars.return_value.all.return_value = [comp] if comp else []
        return res

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    res = await compare_companies(symbols="LT,RELIANCE", db=mock_db)
    assert res["status"] == "ok"
    assert res["count"] == 2
    assert "disclaimer" in res

    by_symbol = {item["symbol"]: item for item in res["comparison"]}
    assert by_symbol["LT"]["name"] == "Larsen & Toubro Limited"
    assert by_symbol["LT"]["pe_ratio"] == 34.2
    assert by_symbol["RELIANCE"]["roce_pct"] == 10.5
    # Metrics absent from ingested snapshots are null, never invented
    assert by_symbol["LT"]["pb_ratio"] is None
    assert by_symbol["LT"].get("rsi_14") is None

    # Unknown symbol is rejected with 404
    with pytest.raises(HTTPException) as exc_info:
        await compare_companies(symbols="LT,NOTASTOCK", db=mock_db)
    assert exc_info.value.status_code == 404
