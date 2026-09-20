"""End-to-End Quantitative Integration Test (Section 137, 147, 148)."""
import pytest
from packages.scenario_engine.orchestrator import ScenarioOrchestrator


def test_full_scenario_pipeline_e2e():
    """Verify complete pipeline execution from real price input through forecast to capital simulation."""
    orchestrator = ScenarioOrchestrator()

    # Realistic historical price series (explicit test input — the engine must
    # never fabricate its own price series).
    prices = [3000.0 + i * 2.5 + (i % 7) * 1.2 for i in range(120)]

    # Exact user scenario from prompt: Analyze RELIANCE with ₹500 for 3 months (63 trading days) and target ₹1,600
    res = orchestrator.run_full_scenario_analysis(
        symbol="RELIANCE",
        capital_inr=500.0,
        horizon_days=63,
        target_price=1600.0,
        prices=prices,
    )

    # 1. Pipeline execution status and run identity
    assert "scenario_run_id" in res
    assert res["symbol"] == "RELIANCE"

    # 2. Feature snapshot with hash
    assert "feature_snapshot" in res
    assert "id" in res["feature_snapshot"]
    assert res["feature_snapshot"]["feature_count"] == 89

    # 3. Model metadata and calibration
    assert "model_metadata" in res
    assert len(res["model_metadata"]["ensemble_models"]) >= 2
    assert "calibration_status" in res["model_metadata"]
    # No persisted out-of-sample holdout exists in this deployment, so calibration
    # must be reported as INSUFFICIENT — never fabricated as GOOD.
    assert res["model_metadata"]["calibration_status"] == "INSUFFICIENT"
    assert res["model_metadata"]["brier_score"] is None

    # 4. Indian Whole Shares Execution Position
    pos = res["execution_position"]
    assert pos["executable_whole_shares"] == 0
    assert pos["is_insufficient_capital"] is True
    assert "INSUFFICIENT CAPITAL FOR ONE SHARE" in pos["insufficient_capital_alert"]
    assert pos["cash_remainder"] == 500.0
    assert pos["entry_notional"] == 0.0
    assert pos["theoretical_fractional_exposure"] > 0
    assert pos["is_fractional_executable"] is False

    # 5. Probabilities (calibrated, distinct, bounded)
    probs = res["target_probabilities"]
    assert 0.0 <= probs["calibrated_p_target_touched"] <= 1.0
    assert 0.0 <= probs["calibrated_p_finish_above"] <= 1.0
    downside = res["downside_probabilities"]
    assert 0.0 <= downside["p_loss_overall"] <= 1.0
    assert 0.0 <= downside["p_minus_10pct"] <= 1.0

    # 6. Five Distinct Scenarios
    scenarios = res["scenarios"]
    assert len(scenarios) == 5
    for sc_name in ["SEVERE_BEAR", "BEAR", "BASE", "BULL", "STRONG_BULL"]:
        assert sc_name in scenarios
        sc = scenarios[sc_name]
        assert "price_range" in sc
        assert "implied_return_pct" in sc
        assert "scenario_portfolio_value" in sc
        assert len(sc["assumptions"]) > 0
        assert len(sc["risks"]) > 0

    # 7. Forecast Quantiles
    f_dist = res["forecast_distribution"]
    assert f_dist["q10"] <= f_dist["q25"] <= f_dist["q50"] <= f_dist["q75"] <= f_dist["q90"]

    # 8. Evidence Panel
    evidence = res["evidence_panel"]
    assert len(evidence) >= 5
    types_found = {e["type"] for e in evidence}
    assert "SOURCE-DERIVED" in types_found
    assert "CALCULATED" in types_found
    assert "MODEL-DERIVED" in types_found
    assert "LLM-INTERPRETED" in types_found

    # 9. Mandatory Regulatory & Data Disclaimer
    assert "disclaimer" in res
    assert "non-advisory" in res["disclaimer"].lower() or "not guarantee" in res["disclaimer"].lower()
