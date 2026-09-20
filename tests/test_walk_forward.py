"""Unit tests for Walk-Forward Validation Engine (§12)."""
import pytest
import numpy as np
from packages.scenario_engine.simulation.walk_forward import WalkForwardSplitter, WalkForwardEvaluator


def test_walk_forward_expanding_window_strictly_temporal():
    """Verify expanding window splits maintain strict chronological ordering with no leakage."""
    n_samples = 200
    splits = list(WalkForwardSplitter.split(
        n_samples=n_samples,
        train_window=60,
        test_window=20,
        step_size=20,
        mode="expanding",
    ))

    assert len(splits) == 7  # (200 - 60 - 20) / 20 + 1 = 7

    for split in splits:
        train_idx = split["train_indices"]
        test_idx = split["test_indices"]
        # Absolute guarantee: no future leakage into train set
        assert max(train_idx) < min(test_idx)
        # Expanding window always starts from index 0
        assert train_idx[0] == 0


def test_walk_forward_rolling_window_fixed_length():
    """Verify rolling window maintains constant training size."""
    n_samples = 150
    train_size = 50
    splits = list(WalkForwardSplitter.split(
        n_samples=n_samples,
        train_window=train_size,
        test_window=10,
        step_size=10,
        mode="rolling",
    ))

    assert len(splits) > 0
    for split in splits:
        assert len(split["train_indices"]) == train_size
        assert max(split["train_indices"]) < min(split["test_indices"])


def test_walk_forward_evaluator_metrics():
    """Verify evaluator computes MAE, RMSE, directional accuracy, and coverage."""
    # Synthetic random walk price series
    np.random.seed(42)
    daily_rets = np.random.normal(0.0005, 0.015, 150)
    prices = [1000.0]
    for r in daily_rets:
        prices.append(prices[-1] * (1.0 + r))

    res = WalkForwardEvaluator.evaluate(
        prices=prices,
        train_window=60,
        test_window=15,
        step_size=15,
        mode="expanding",
    )

    assert res["total_windows"] > 0
    assert res["mae"] > 0.0
    assert res["rmse"] >= res["mae"]
    assert 0.0 <= res["directional_accuracy_pct"] <= 100.0
    assert 0.0 <= res["prediction_interval_coverage_pct"] <= 100.0
    assert "WALK_FORWARD_EXPANDING" in res["validation_protocol"]
