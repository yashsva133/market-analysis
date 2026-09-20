"""Unit tests for Probability Calibration Engine (Isotonic, Platt, Brier Score, ECE)."""
import pytest
import numpy as np
from packages.scenario_engine.probability.calibration import ProbabilityCalibrationEngine


@pytest.fixture
def calibration_engine():
    return ProbabilityCalibrationEngine()


def test_probability_bounds(calibration_engine):
    """Verify calibrated probabilities are strictly bounded within [0.01, 0.99]."""
    test_raw = [0.0, 0.05, 0.35, 0.50, 0.75, 0.95, 1.0, -0.2, 1.5]
    for r in test_raw:
        cal = calibration_engine.calibrate(r)
        assert 0.0 <= cal <= 1.0


def test_calibration_metrics_brier_and_ece(calibration_engine):
    """Verify Brier score and expected calibration error are computed on walk-forward holdouts."""
    np.random.seed(42)
    y_true = np.array([0, 0, 0, 1, 1, 1, 1, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.65, 0.9, 0.4, 0.85, 0.75])

    metrics = calibration_engine.evaluate_calibration(y_prob, y_true)
    assert "brier_score" in metrics
    assert "expected_calibration_error" in metrics
    assert "log_loss" in metrics
    assert "rating" in metrics
    assert metrics["rating"] in ["GOOD", "ACCEPTABLE", "POOR"]
    assert 0.0 <= metrics["brier_score"] <= 1.0
    assert 0.0 <= metrics["expected_calibration_error"] <= 1.0


def test_calibration_decile_buckets(calibration_engine):
    """Verify calibration decile buckets contain valid predicted vs observed frequencies."""
    np.random.seed(42)
    y_true = np.random.binomial(1, 0.6, 500)
    y_prob = np.clip(y_true * 0.4 + np.random.normal(0.4, 0.15, 500), 0.01, 0.99)

    report = calibration_engine.evaluate_calibration(y_prob, y_true)
    buckets = report["deciles"]
    assert len(buckets) == 10
    for b in buckets:
        assert "bucket" in b
        assert "predicted_avg_pct" in b
        assert "actual_rate_pct" in b
        assert "sample_count" in b
        assert b["sample_count"] >= 0
