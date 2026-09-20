"""Regression tests asserting no fabricated financial data is ever produced.

Each test verifies that a specific fabrication path returns an honest
unavailable state (None / DATA_UNAVAILABLE / INSUFFICIENT_DATA) rather than a
synthetic number.
"""
import pytest

from packages.scenario_engine.features.sector_features import SectorFeatureExtractor
from packages.scenario_engine.comparable.comparable_events import ComparableEventEngine
from packages.scenario_engine.capital.capital_scenario import CapitalScenarioEngine
from packages.scenario_engine.scenarios.scenario_engine import ScenarioEngine


def test_sector_features_no_fabricated_benchmarks():
    """No sector benchmark is invented when sector data is absent."""
    out = SectorFeatureExtractor.extract(
        sector_name="CAPITAL GOODS",
        stock_return_20d=3.5,
        sector_data=None,
    )
    assert out["sector_return_20d"] is None
    assert out["sector_volatility_20d"] is None
    assert out["sector_event_intensity"] is None
    assert out["sector_relative_strength_20d"] is None
    assert out["sector_sentiment_score"] is None


def test_sector_features_uses_real_data_when_provided():
    """Real sector benchmark data flows through unchanged."""
    out = SectorFeatureExtractor.extract(
        sector_name="IT",
        stock_return_20d=3.5,
        sector_data={
            "sector_return_20d": 2.4,
            "sector_volatility_20d": 0.165,
            "sector_event_intensity": 1.2,
            "sector_sentiment": 0.6,
        },
    )
    assert out["sector_return_20d"] == 2.4
    assert out["sector_relative_strength_20d"] == round(3.5 - 2.4, 2)


def test_comparable_events_no_fabricated_database():
    """No fabricated historical event database is substituted when no events exist."""
    out = ComparableEventEngine.find_comparables(
        event_type="ORDER_WIN",
        sector="CAPITAL GOODS",
    )
    assert out["status"] == "DATA_UNAVAILABLE"
    assert out["sample_size"] == 0
    assert out["statistics"] is None
    assert out["comparable_events"] == []


def test_comparable_events_uses_real_events():
    """Real ingested events produce real statistics."""
    events = [
        {
            "event_type": "ORDER_WIN",
            "sector": "CAPITAL GOODS",
            "reaction_1d_pct": 3.0,
            "reaction_5d_pct": 5.0,
            "reaction_20d_pct": 8.0,
            "volume_multiple": 2.0,
        },
        {
            "event_type": "ORDER_WIN",
            "sector": "CAPITAL GOODS",
            "reaction_1d_pct": 4.0,
            "reaction_5d_pct": 6.0,
            "reaction_20d_pct": 9.0,
            "volume_multiple": 2.5,
        },
    ]
    out = ComparableEventEngine.find_comparables(
        event_type="ORDER_WIN",
        sector="CAPITAL GOODS",
        events=events,
    )
    assert out["status"] == "AVAILABLE"
    assert out["sample_size"] == 2
    assert out["statistics"]["median_5d_reaction_pct"] == 5.5


def test_capital_scenario_rejects_missing_quantiles():
    """Capital simulation refuses to fabricate quantiles when they are absent."""
    engine = CapitalScenarioEngine()
    with pytest.raises(ValueError, match="DATA_UNAVAILABLE"):
        engine.simulate_capital(
            symbol="RELIANCE",
            current_price=3000.0,
            capital=10000.0,
            horizon_days=20,
            target_price=3200.0,
            forecast_distribution={"q10": 2800.0},  # missing q25/q50/q75/q90
            probabilities={},
            scenarios={},
        )


def test_scenario_engine_rejects_missing_quantiles():
    """Scenario generation refuses to fabricate quantiles when they are absent."""
    with pytest.raises(ValueError, match="DATA_UNAVAILABLE"):
        ScenarioEngine.generate_scenarios(
            current_price=3000.0,
            forecast_distribution={"q50": 3050.0},  # missing tail quantiles
            features={},
            horizon_days=20,
        )


def test_rule_provider_no_fabricated_confidence():
    """Deterministic rule extraction reports confidence as None, not a fake score."""
    import asyncio
    from packages.ai.rule_provider import RuleProvider

    async def _run():
        provider = RuleProvider()
        resp = await provider.complete("Company bags order worth ₹100 Cr")
        assert resp.parsed_json["confidence"] is None

    asyncio.run(_run())
