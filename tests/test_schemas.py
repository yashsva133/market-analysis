"""Unit tests for Pydantic core schemas and taxonomy."""
import uuid
from decimal import Decimal
from packages.schemas.taxonomy import EventTaxonomy, ImportanceClass
from packages.schemas.company import CompanyCreate, SecurityCreate
from packages.schemas.event import EventCreate
from packages.schemas.ai import AIClassificationResult, AIMaterialityAnalysis


def test_taxonomy_enums():
    assert EventTaxonomy.ORDER_WIN == "ORDER_WIN"
    assert EventTaxonomy.INSOLVENCY == "INSOLVENCY"
    assert ImportanceClass.CRITICAL == "CRITICAL"


def test_company_security_creation():
    comp = CompanyCreate(
        isin="INE002A01018",
        legal_name="Reliance Industries Limited",
        status="ACTIVE",
    )
    assert comp.isin == "INE002A01018"
    assert comp.legal_name == "Reliance Industries Limited"

    sec = SecurityCreate(
        exchange="NSE",
        symbol="RELIANCE",
        bse_scrip_code="500325",
        security_type="EQUITY",
        series="EQ",
    )
    assert sec.exchange == "NSE"
    assert sec.symbol == "RELIANCE"


def test_ai_classification_result_validation():
    result = AIClassificationResult(
        event_type=EventTaxonomy.ORDER_WIN,
        is_binding=True,
        amount=Decimal("8500000000"),
        counterparty="Ministry of Railways",
        duration="36 months",
        facts=[{"key": "order_value_inr", "value": 8500000000}],
        unknowns=["Operating margin"],
        confidence=0.98,
    )
    assert result.event_type == EventTaxonomy.ORDER_WIN
    assert result.amount == Decimal("8500000000")
    assert result.is_binding is True
