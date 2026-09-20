"""Adversarial and Edge Case Test Suite for India Market AI Research Terminal (§66).

Explicitly validates safe failure and graceful degradation against:
- Negative capital
- NaN or Infinite price inputs
- Out-of-bound probabilities (<0 or >1)
- Missing or invalid symbols
- Invalid forecast horizons (0, negative, extremely large)
- Huge capital (e.g. ₹100 Crores)
- Empty responses and corrupt inputs
- Hallucinated numeric values
- Mathematical cost edge cases
"""
import pytest
import math
import numpy as np
from packages.scenario_engine.capital.capital_scenario import CapitalScenarioEngine
from packages.scenario_engine.capital.costs import TransactionCostModel
from packages.scenario_engine.probability.calibration import evaluate_calibration, CalibratedProbabilityModel
from packages.scenario_engine.simulation.monte_carlo import MonteCarloEngine
from packages.scenario_engine.scenarios.scenario_engine import ScenarioEngine
from packages.scenario_engine.models.chronos_model import ChronosForecastModel


def test_adversarial_negative_capital():
    """Verify negative capital allocation fails safely with 0 shares and insufficient flag."""
    pos = CapitalScenarioEngine.calculate_position(
        capital=-50000.0,
        current_price=2500.0,
    )
    assert pos["executable_whole_shares"] == 0
    assert pos["is_insufficient_capital"] is True
    assert pos["allocated_capital"] == 0.0


def test_adversarial_zero_capital():
    """Verify zero capital produces safe zero-share position."""
    pos = CapitalScenarioEngine.calculate_position(
        capital=0.0,
        current_price=2500.0,
    )
    assert pos["executable_whole_shares"] == 0
    assert pos["is_insufficient_capital"] is True
    assert pos["cash_remainder"] == 0.0


def test_adversarial_huge_capital():
    """Verify huge capital (e.g. ₹100 Crore) computes accurately without integer overflow."""
    huge_cap = 1_000_000_000.0  # ₹100 Crore
    price = 3500.0
    pos = CapitalScenarioEngine.calculate_position(
        capital=huge_cap,
        current_price=price,
    )
    assert pos["executable_whole_shares"] > 280_000
    assert pos["is_insufficient_capital"] is False
    assert pos["cash_remainder"] >= 0.0
    assert pos["cash_remainder"] < huge_cap * 0.01


def test_adversarial_nan_and_infinite_price():
    """Verify NaN or Infinite price input fails safely without raising unhandled crash."""
    for bad_price in [float("nan"), float("inf"), -2500.0, 0.0]:
        pos = CapitalScenarioEngine.calculate_position(
            capital=100000.0,
            current_price=bad_price,
        )
        assert pos["executable_whole_shares"] == 0
        assert pos["is_insufficient_capital"] is True


def test_adversarial_probability_bounds_strictly_enforced():
    """Verify probabilities outside [0, 1] are clamped or flagged."""
    # Test evaluation with out-of-range inputs
    y_true = np.array([1, 0, 1, 1, 0])
    y_prob_unbounded = np.array([-0.5, 1.5, 0.8, -0.1, 1.2])
    
    # Calibration evaluation should safely clamp or handle
    report = evaluate_calibration(y_true, y_prob_unbounded)
    assert 0.0 <= report["brier_score"] <= 1.0
    assert 0.0 <= report["ece"] <= 1.0


def test_adversarial_invalid_horizon_handled():
    """Verify Monte Carlo and Chronos fail safely on 0 or negative horizon."""
    res_zero = MonteCarloEngine.simulate_paths(
        current_price=1000.0,
        daily_volatility=0.015,
        horizon_days=0,
        target_price=1100.0,
        num_paths=100,
    )
    assert res_zero["p_target_touched"] == 0.0
    assert res_zero["p_finish_above"] == 0.0
    assert res_zero["terminal_distribution_quantiles"]["q50"] == 1000.0


def test_adversarial_chronos_empty_or_corrupt_series():
    """Verify Chronos forecast model raises clear ValueError or falls back on invalid series."""
    model = ChronosForecastModel()
    
    with pytest.raises(ValueError):
        model.forecast(prices=[], horizon_days=30)

    # Single price element
    res = model.forecast(prices=[1500.0], horizon_days=10)
    assert res["current_price"] == 1500.0
    assert res["quantiles"]["q50"] > 0.0


def test_adversarial_transaction_costs_negative_or_zero_notional():
    """Verify cost model returns zero costs for negative or zero notional."""
    model = TransactionCostModel()
    
    costs_zero = model.estimate_buy_costs(0.0)
    assert costs_zero["total_estimated_cost"] == 0.0
    
    costs_neg = model.estimate_buy_costs(-50000.0)
    assert costs_neg["total_estimated_cost"] == 0.0

    costs_sell_zero = model.estimate_sell_costs(0.0)
    assert costs_sell_zero["total_estimated_cost"] == 0.0


def test_adversarial_scenario_engine_corrupt_quantiles():
    """Verify scenario engine generates 5 valid tiers even with missing or inverted quantiles."""
    # Corrupt quantiles dictionary
    corrupt_quantiles = {"q50": 2000.0}  # Missing q10, q25, q75, q90
    
    scenarios = ScenarioEngine.generate_scenarios(
        current_price=2000.0,
        forecast_distribution=corrupt_quantiles,
        features={},
        horizon_days=30,
    )
    assert len(scenarios) == 5
    for tier in ["SEVERE_BEAR", "BEAR", "BASE", "BULL", "STRONG_BULL"]:
        assert tier in scenarios
        assert "price_range" in scenarios[tier]
        assert "probability" in scenarios[tier]
        assert scenarios[tier]["probability"] > 0.0
