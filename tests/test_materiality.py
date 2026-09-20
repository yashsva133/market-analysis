"""Tests for deterministic MaterialityAnalystAgent triage."""
from decimal import Decimal
from packages.ai.agents import materiality_analyst_agent
from packages.schemas.taxonomy import EventTaxonomy, ImportanceClass


def test_critical_event_types():
    analysis = materiality_analyst_agent.analyze(EventTaxonomy.INSOLVENCY)
    assert analysis.importance == ImportanceClass.CRITICAL
    assert len(analysis.why_flagged) > 0

    auditor = materiality_analyst_agent.analyze(EventTaxonomy.AUDITOR_CHANGE)
    assert auditor.importance == ImportanceClass.CRITICAL


def test_order_win_scale_relative_to_revenue():
    # Order of ₹6,000 Cr on revenue of ₹10,000 Cr -> 60% revenue -> CRITICAL
    order_amount = Decimal("60000000000")
    revenue = Decimal("100000000000")

    analysis = materiality_analyst_agent.analyze(
        event_type=EventTaxonomy.ORDER_WIN,
        amount_inr=order_amount,
        annual_revenue_inr=revenue,
    )
    assert analysis.importance == ImportanceClass.CRITICAL
    assert "60.0%" in analysis.financial_scale_summary

    # Order of ₹200 Cr on revenue of ₹10,000 Cr -> 2% -> HIGH (default for order win)
    small_order = Decimal("2000000000")
    analysis_small = materiality_analyst_agent.analyze(
        event_type=EventTaxonomy.ORDER_WIN,
        amount_inr=small_order,
        annual_revenue_inr=revenue,
    )
    assert analysis_small.importance == ImportanceClass.HIGH
