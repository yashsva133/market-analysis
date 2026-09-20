"""Tests for RAG Deep Research evidence grounding (FACT, INFERENCE, UNKNOWN)."""
import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from apps.api.routers.research import conduct_deep_research, ResearchQueryRequest
from packages.common.models import Company, Event, FinancialSnapshot, EventFact
from packages.schemas.taxonomy import EventTaxonomy, ImportanceClass


@pytest.mark.asyncio
async def test_deep_research_grounded_evidence():
    """Verify deep research produces evidence-backed findings distinguishing FACT, INFERENCE, and UNKNOWN."""
    company_id = uuid.uuid4()
    company = Company(
        id=company_id,
        isin="INE002A01018",
        legal_name="Reliance Industries Limited",
        sector="Energy & Petrochemicals",
        industry="Refineries",
        status="ACTIVE",
    )
    company.securities = []

    event_id = uuid.uuid4()
    event = Event(
        id=event_id,
        company_id=company_id,
        event_type=EventTaxonomy.ORDER_WIN.value,
        importance=ImportanceClass.CRITICAL.value,
        headline="Reliance wins major deepwater extraction contract worth ₹12,000 Cr",
        announcement_time=datetime.now(timezone.utc),
        status="EXTRACTED",
    )

    fact = EventFact(
        id=uuid.uuid4(),
        event_id=event_id,
        fact_key="contract_amount_inr",
        fact_value={"value": 120000000000.0},
        source_page=3,
        confidence=1.0,
    )

    fin = FinancialSnapshot(
        id=uuid.uuid4(),
        company_id=company_id,
        period="FY2025-26",
        revenue=Decimal("9000000000000"), # 9 Lakh Cr
        pat=Decimal("700000000000"),
        roce=Decimal("12.5"),
    )

    mock_db = AsyncMock()
    
    async def mock_execute(query):
        q_str = str(query)
        res = MagicMock()
        if "companies" in q_str:
            res.scalar_one_or_none.return_value = company
        elif "events" in q_str:
            res.scalars.return_value.all.return_value = [event]
        elif "financial_snapshots" in q_str:
            res.scalars.return_value.all.return_value = [fin]
        elif "event_facts" in q_str:
            res.scalars.return_value.all.return_value = [fact]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalar_one_or_none.return_value = None
        return res

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    request = ResearchQueryRequest(
        company_id=company_id,
        question="Analyze the materiality and execution risks of recent major contract wins.",
    )

    report = await conduct_deep_research(request, db=mock_db)

    assert report.company_name == "Reliance Industries Limited"
    assert report.isin == "INE002A01018"
    assert len(report.grounded_findings) >= 3

    categories = {f["classification"] for f in report.grounded_findings}
    assert "FACT" in categories
    assert "INFERENCE" in categories
    assert "UNKNOWN" in categories

    fact_entry = next(f for f in report.grounded_findings if f["classification"] == "FACT")
    assert fact_entry["evidence_page"] == 3
    assert "120000000000" in fact_entry["statement"]
