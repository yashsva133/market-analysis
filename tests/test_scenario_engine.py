"""Unit and integration tests for ScenarioEngine, Probabilistic Forecasts, and Whole-Share Execution."""
import pytest
from packages.scenario_engine.scenarios.scenario_engine import ScenarioEngine
from packages.scenario_engine.capital.capital_scenario import CapitalScenarioEngine
from packages.scenario_engine.models.chronos_model import ChronosForecastModel
from packages.scenario_engine.simulation.monte_carlo import MonteCarloSimulator


def test_scenario_generation_five_tiers():
    """Verify 5 distinct scenario tiers are generated with valid price/return/probability structure."""
    scenarios = ScenarioEngine.generate_scenarios(
        current_price=3000.0,
        forecast_distribution={"q05": 2400.0, "q10": 2550.0, "q25": 2800.0, "q40": 2950.0, "q50": 3050.0, "q60": 3150.0, "q75": 3300.0, "q90": 3600.0, "q95": 3850.0},
        features={"india_vix": 13.5, "rsi_14": 55.0},
        horizon_days=63,
    )
    assert len(scenarios) == 5
    assert "SEVERE_BEAR" in scenarios
    assert "BEAR" in scenarios
    assert "BASE" in scenarios
    assert "BULL" in scenarios
    assert "STRONG_BULL" in scenarios

    for key, sc in scenarios.items():
        assert "price_low" in sc
        assert "price_high" in sc
        assert "return_low_pct" in sc
        assert "return_high_pct" in sc
        assert "probability_mass_pct" in sc
        assert len(sc["assumptions"]) > 0
        assert len(sc["risks"]) > 0


def test_insufficient_capital_flag():
    """Verify Indian whole-shares rule flags insufficient capital when capital < share price."""
    cap_engine = CapitalScenarioEngine()
    res = cap_engine.simulate_capital(
        symbol="RELIANCE",
        current_price=3021.23,
        capital=500.0,
        horizon_days=63,
        target_price=1600.0,
        forecast_distribution={"q10": 2800.0, "q25": 2950.0, "q50": 3100.0, "q75": 3300.0, "q90": 3500.0},
        probabilities={"calibrated_p_target_touched": 0.58},
        scenarios={},
    )
    pos = res["execution_position"]
    assert pos["executable_whole_shares"] == 0
    assert pos["is_insufficient_capital"] is True
    assert "INSUFFICIENT CAPITAL FOR ONE SHARE" in pos["insufficient_capital_alert"]
    assert pos["cash_remainder"] == 500.0
    assert pos["entry_notional"] == 0.0
    assert pos["theoretical_fractional_exposure"] > 0
    assert pos["is_fractional_executable"] is False


def test_sufficient_capital_whole_shares():
    """Verify executable quantity is strictly an integer floor of capital minus costs."""
    cap_engine = CapitalScenarioEngine()
    res = cap_engine.simulate_capital(
        symbol="RELIANCE",
        current_price=3000.0,
        capital=10000.0,
        horizon_days=63,
        target_price=3200.0,
        forecast_distribution={"q10": 2800.0, "q25": 2950.0, "q50": 3100.0, "q75": 3300.0, "q90": 3500.0},
        probabilities={"calibrated_p_target_touched": 0.58},
        scenarios={},
    )
    pos = res["execution_position"]
    assert pos["executable_whole_shares"] == 3
    assert pos["is_insufficient_capital"] is False
    assert pos["entry_notional"] == 9000.0
    assert pos["cash_remainder"] > 0


def test_target_touched_vs_finish_above():
    """Verify touching probability is >= finishing above probability across trajectories."""
    res = MonteCarloSimulator.simulate_paths(
        current_price=100.0,
        daily_volatility=0.015,
        horizon_days=20,
        target_price=110.0,
        num_paths=500,
        random_seed=42,
    )
    p_touch = res["p_target_touched"]
    p_finish = res["p_finish_above"]
    assert 0.0 <= p_finish <= p_touch <= 1.0


def test_chronos_forecast_quantiles():
    """Verify Chronos forecast generates monotonic quantiles."""
    model = ChronosForecastModel()
    history = [100.0 * (1 + 0.001 * i) for i in range(100)]
    
    out = model.forecast(history, horizon_days=20)
    q = out["quantiles"]
    assert q["q10"] <= q["q25"] <= q["q50"] <= q["q75"] <= q["q90"]


def test_timesfm_forecast_quantiles():
    """Verify Google TimesFM forecast generates monotonic quantiles and valid structure."""
    from packages.scenario_engine.models.timesfm_model import TimesFMForecastModel
    model = TimesFMForecastModel()
    history = [100.0 * (1 + 0.001 * i) for i in range(100)]
    
    out = model.forecast(history, horizon_days=20)
    assert "quantiles" in out
    q = out["quantiles"]
    assert q["q10"] <= q["q25"] <= q["q50"] <= q["q75"] <= q["q90"]
    assert "fan_chart" in out
    assert "drift_pct" in out
    assert out["horizon_days"] == 20
    assert out["model_name"] == "google/timesfm-3.0-500m"


def test_multi_agent_decision_council():
    """Verify the council produces a factual, non-advisory review with real model comparison.

    No fabricated conviction score, disagreement index, or buy/sell verdict is emitted.
    """
    from packages.scenario_engine.council.decision_council import MultiAgentDecisionCouncil
    council = MultiAgentDecisionCouncil()

    res = council.evaluate(
        symbol="RELIANCE",
        current_price=3000.0,
        target_price=3300.0,
        stop_price=2800.0,
        capital=50000.0,
        horizon_days=63,
        chronos_forecast={
            "model_id": "amazon/chronos-2",
            "quantiles": {"q10": 2750.0, "q25": 2900.0, "q50": 3150.0, "q75": 3350.0, "q90": 3550.0},
        },
        timesfm_forecast={
            "model_name": "google/timesfm-3.0-500m",
            "quantiles": {"q10": 2780.0, "q25": 2920.0, "q50": 3160.0, "q75": 3340.0, "q90": 3520.0},
        },
        features={
            "rsi_14": 48.5,
            "india_vix": 13.8,
            "pct_above_50dma": 2.1,
            "pe_ratio": 26.5,
            "roce_pct": 15.2,
            "debt_to_equity": 0.4,
            "revenue_growth_yoy": 12.0,
            "promoter_pledge_pct": 0.0,
        },
        events=[{"event_type": "ORDER_WIN", "sector": "CAPITAL GOODS"}],
        capital_execution={"executable_whole_shares": 16, "is_insufficient_capital": False},
    )

    d = res.to_dict()
    assert d["symbol"] == "RELIANCE"
    # Non-advisory verdict only; never a buy/sell/accumulate recommendation.
    assert d["consensus_verdict"] in ["DATA_REVIEW", "INSUFFICIENT_DATA"]
    # No fabricated conviction or disagreement scores.
    assert d["conviction_score"] is None
    assert d["disagreement_index"] is None
    assert len(d["agent_deliberations"]) == 4
    agent_ids = [a["agent_id"] for a in d["agent_deliberations"]]
    assert "agent_quant_ts" in agent_ids
    assert "agent_fundamental" in agent_ids
    assert "agent_regulatory" in agent_ids
    assert "agent_risk_officer" in agent_ids
    # No agent may carry a fabricated conviction percentage.
    for a in d["agent_deliberations"]:
        assert a["conviction_pct"] is None
    assert len(d["invalidation_triggers"]) > 0
    assert "model_comparison" in d
    assert "chronos_2" in d["model_comparison"]
    assert "timesfm_3" in d["model_comparison"]
    assert "consensus" in d["model_comparison"]
    # Real model quantiles flow through unchanged.
    assert d["model_comparison"]["chronos_2"]["median_q50"] == 3150.0
    assert d["model_comparison"]["timesfm_3"]["median_q50"] == 3160.0


def test_decision_council_insufficient_data_when_models_missing():
    """Verify the council reports INSUFFICIENT_DATA rather than fabricating quantiles."""
    from packages.scenario_engine.council.decision_council import MultiAgentDecisionCouncil
    council = MultiAgentDecisionCouncil()

    res = council.evaluate(
        symbol="RELIANCE",
        current_price=3000.0,
        target_price=3300.0,
        stop_price=2800.0,
        capital=50000.0,
        horizon_days=63,
        chronos_forecast={},
        timesfm_forecast={},
        features={},
        events=None,
        capital_execution={},
    )

    d = res.to_dict()
    assert d["consensus_verdict"] == "INSUFFICIENT_DATA"
    assert d["conviction_score"] is None
    # Model comparison must not fabricate medians/drifts when models are absent.
    assert d["model_comparison"]["chronos_2"]["median_q50"] is None
    assert d["model_comparison"]["timesfm_3"]["median_q50"] is None
    assert d["model_comparison"]["consensus"]["model_agreement_pct"] is None

