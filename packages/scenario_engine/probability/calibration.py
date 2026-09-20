"""Probability Calibration & Reliability Validation Engine.

Implements:
- Isotonic Regression Calibration
- Platt / Logistic Calibration
- Brier Score, Log Loss, and Expected Calibration Error (ECE)
- 10-decile Calibration Curve computation
- Explicit deterministic rating gates: GOOD, ACCEPTABLE, POOR
"""
from typing import Dict, Any, List, Tuple
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


class ProbabilityCalibrationEngine:
    CALIBRATION_MODEL_VERSION = "calib-iso-v1.2"

    # Strict explicit rating thresholds (§13)
    BRIER_GOOD_THRESHOLD = 0.18
    BRIER_ACCEPTABLE_THRESHOLD = 0.25
    ECE_GOOD_THRESHOLD = 0.08
    ECE_ACCEPTABLE_THRESHOLD = 0.15

    def __init__(self, method: str = "isotonic"):
        self.method = method.lower()
        self.calibrator = None
        self.is_fitted = False
        # NOTE: The calibrator intentionally starts UNFITTED. A calibration map must
        # be learned from real out-of-sample walk-forward predictions and their
        # realized outcomes. Fabricating a synthetic seed would produce a meaningless
        # "calibrated" probability, so we refuse to do so. Until real holdout data is
        # supplied via `fit()`, `calibrate()` returns the raw probability unchanged and
        # the engine reports CALIBRATION: INSUFFICIENT.

    def fit(self, raw_probabilities: np.ndarray, outcomes: np.ndarray):
        """Fit calibration model on out-of-sample walk-forward predictions."""
        raw_p = np.clip(np.array(raw_probabilities, dtype=float), 0.001, 0.999)
        y = np.array(outcomes, dtype=int)

        if self.method == "platt":
            # Platt scaling (Logistic Regression on log-odds)
            from scipy.special import logit
            log_odds = logit(raw_p).reshape(-1, 1)
            clf = LogisticRegression(C=1.0, solver="lbfgs")
            clf.fit(log_odds, y)
            self.calibrator = clf
        else:
            # Isotonic Regression (Non-parametric monotonically non-decreasing)
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)
            iso.fit(raw_p, y)
            self.calibrator = iso

        self.is_fitted = True

    def calibrate(self, raw_probability: float) -> float:
        """Transform a raw model probability into an out-of-sample calibrated probability.

        When no real out-of-sample calibration data has been fitted, the raw
        probability is returned unchanged (clamped) — it is NOT silently
        "calibrated" against fabricated data.
        """
        p = float(max(0.001, min(0.999, raw_probability)))
        if not self.is_fitted or self.calibrator is None:
            return round(p, 4)

        if self.method == "platt":
            from scipy.special import logit
            lo = logit(p).reshape(-1, 1)
            calibrated = float(self.calibrator.predict_proba(lo)[0, 1])
        else:
            calibrated = float(self.calibrator.predict([p])[0])

        return float(round(max(0.01, min(0.99, calibrated)), 4))

    def evaluate_calibration(
        self,
        predicted_probs: np.ndarray,
        actual_outcomes: np.ndarray,
    ) -> Dict[str, Any]:
        """Compute Brier score, log loss, ECE, calibration curve deciles, and rating."""
        y_pred = np.clip(np.array(predicted_probs, dtype=float), 0.0001, 0.9999)
        y_true = np.array(actual_outcomes, dtype=int)
        n = len(y_true)

        if n == 0:
            return {
                "brier_score": None,
                "log_loss": None,
                "expected_calibration_error": None,
                "ece": None,
                "rating": "INSUFFICIENT",
                "sample_size": 0,
                "deciles": [],
                "calibration_buckets": [],
                "disclaimer": "No out-of-sample predictions available to evaluate calibration.",
            }

        # 1. Brier Score = 1/N * sum((p - y)^2)
        brier = float(np.mean((y_pred - y_true) ** 2))

        # 2. Log Loss = -1/N * sum(y*log(p) + (1-y)*log(1-p))
        log_loss_val = float(
            -np.mean(y_true * np.log(y_pred) + (1 - y_true) * np.log(1.0 - y_pred))
        )

        # 3. Decile Calibration Buckets (0-10%, 10-20%, ... 90-100%)
        deciles = []
        bin_edges = np.linspace(0.0, 1.0, 11)
        ece = 0.0

        for i in range(10):
            low, high = bin_edges[i], bin_edges[i + 1]
            mask = (y_pred >= low) & (y_pred < high if i < 9 else y_pred <= high)
            bin_size = int(np.sum(mask))

            if bin_size > 0:
                bin_pred_avg = float(np.mean(y_pred[mask]))
                bin_actual_rate = float(np.mean(y_true[mask]))
                abs_diff = abs(bin_pred_avg - bin_actual_rate)
                ece += (bin_size / n) * abs_diff
            else:
                bin_pred_avg = float((low + high) / 2.0)
                bin_actual_rate = bin_pred_avg
                abs_diff = 0.0

            deciles.append({
                "bucket": f"{int(low*100)}–{int(high*100)}%",
                "predicted_avg_pct": round(bin_pred_avg * 100, 1),
                "actual_rate_pct": round(bin_actual_rate * 100, 1),
                "sample_count": bin_size,
                "error_pct": round(abs_diff * 100, 1),
            })

        # 4. Strict Rating Classification (§13)
        if brier <= self.BRIER_GOOD_THRESHOLD and ece <= self.ECE_GOOD_THRESHOLD:
            rating = "GOOD"
        elif brier <= self.BRIER_ACCEPTABLE_THRESHOLD and ece <= self.ECE_ACCEPTABLE_THRESHOLD:
            rating = "ACCEPTABLE"
        else:
            rating = "POOR"

        return {
            "calibration_model_version": self.CALIBRATION_MODEL_VERSION,
            "sample_size": n,
            "brier_score": round(brier, 4),
            "log_loss": round(log_loss_val, 4),
            "expected_calibration_error": round(ece, 4),
            "ece": round(ece, 4),
            "rating": rating,
            "calibration_buckets": deciles,
            "deciles": deciles,
            "disclaimer": "Calibrated against rolling historical walk-forward out-of-sample data. Past calibration does not guarantee future accuracy.",
        }


def evaluate_calibration(actual_outcomes: np.ndarray, predicted_probs: np.ndarray) -> Dict[str, Any]:
    """Module-level calibration evaluation helper."""
    engine = ProbabilityCalibrationEngine()
    return engine.evaluate_calibration(predicted_probs, actual_outcomes)


CalibratedProbabilityModel = ProbabilityCalibrationEngine

