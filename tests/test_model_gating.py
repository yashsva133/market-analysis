"""Unit tests for Model Registry, Quality Gating, and Lifecycle Management."""
import pytest
from packages.scenario_engine.registry.model_registry import ModelRegistry


@pytest.fixture
def registry():
    return ModelRegistry()


def test_model_gating_passes_for_quality_model(registry):
    """Verify a model with low Brier score, low ECE, and sufficient samples is approved for ACTIVE status."""
    registry.register_model(
        model_id="hist-gb-v1",
        model_name="HistGradientBoosting Classifier",
        version="1.0.0",
        family="TABULAR_ML",
        status="EXPERIMENTAL",
        metrics={
            "brier_score": 0.082,
            "prediction_count": 4821,
            "calibration_rating": "GOOD",
        },
    )
    result = registry.evaluate_and_gate("hist-gb-v1")

    assert result["gating_passed"] is True
    assert result["status"] == "ACTIVE"
    assert result["gating_report"]["passed"] is True
    assert "GATING PASSED" in result["gating_report"]["verdict"]


def test_model_gating_rejects_poor_calibration(registry):
    """Verify a model with high Brier score or poor calibration is rejected from ACTIVE status."""
    registry.register_model(
        model_id="poor-cal-v1",
        model_name="Uncalibrated Neural Model",
        version="0.1.0",
        family="DEEP_LEARNING",
        status="EXPERIMENTAL",
        metrics={
            "brier_score": 0.32,  # Too high (> 0.22 threshold)
            "prediction_count": 1200,
            "calibration_rating": "POOR",
        },
    )
    result = registry.evaluate_and_gate("poor-cal-v1")

    assert result["gating_passed"] is False
    assert result["status"] == "VALIDATING"
    assert result["gating_report"]["passed"] is False
    assert "MODEL NOT TRUSTWORTHY FOR PRODUCTION" in result["gating_report"]["verdict"]


def test_model_gating_rejects_insufficient_sample_size(registry):
    """Verify a model with fewer than required validation samples cannot be promoted to ACTIVE."""
    registry.register_model(
        model_id="small-sample-v1",
        model_name="Small Sample Overfitted Model",
        version="0.1.0",
        family="TABULAR_ML",
        status="EXPERIMENTAL",
        metrics={
            "brier_score": 0.05,
            "prediction_count": 10,  # Below 30 threshold!
            "calibration_rating": "GOOD",
        },
    )
    result = registry.evaluate_and_gate("small-sample-v1")

    assert result["gating_passed"] is False
    assert result["gating_report"]["passed"] is False
    assert result["gating_report"]["gates"]["sample_size_gate"]["passed"] is False
