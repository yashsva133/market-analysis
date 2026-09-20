"""Chronos-2 Probabilistic Time-Series Foundation Model Adapter.

Implements primary local probabilistic forecasting using Chronos foundation models
with automatic device detection (CUDA -> CPU fallback) and an intelligent
local autoregressive heavy-tailed quantile generator fallback when dependencies
are unavailable on the host.
"""
from typing import List, Dict, Any, Optional
import numpy as np


class ChronosForecastModel:
    DEFAULT_MODEL_NAME = "amazon/chronos-2"
    FALLBACK_MODEL_NAME = "chronos-t5-tiny"

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.device = self._detect_device()
        self.pipeline = None
        self.is_fallback = True
        self._init_pipeline()

    def _detect_device(self) -> str:
        """Detect GPU acceleration if available, otherwise CPU."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _init_pipeline(self):
        """Attempt loading local Chronos pipeline if transformers & chronos are installed."""
        try:
            # Dynamic import to avoid crash on bare python installs
            from chronos import ChronosPipeline
            self.pipeline = ChronosPipeline.from_pretrained(
                self.model_name,
                device_map=self.device,
            )
            self.is_fallback = False
        except Exception:
            # Clean fallback to built-in probabilistic autoregressive engine
            self.pipeline = None
            self.is_fallback = True

    def forecast(
        self,
        prices: List[float],
        horizon_days: int,
        num_samples: int = 1000,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """Generate multi-quantile forecast distribution across horizon."""
        if not prices:
            raise ValueError("Prices series cannot be empty")

        p = np.array(prices, dtype=float)
        current_price = float(p[-1])

        # 1. Native Chronos pipeline if available
        if self.pipeline is not None and not self.is_fallback:
            try:
                import torch
                context = torch.tensor(p, dtype=torch.float32)
                forecast = self.pipeline.predict(
                    context,
                    prediction_length=horizon_days,
                    num_samples=num_samples,
                )
                samples = forecast[0].numpy()  # shape (num_samples, horizon_days)
                final_samples = samples[:, -1]

                quantiles = {
                    "q05": float(np.percentile(final_samples, 5)),
                    "q10": float(np.percentile(final_samples, 10)),
                    "q25": float(np.percentile(final_samples, 25)),
                    "q40": float(np.percentile(final_samples, 40)),
                    "q50": float(np.percentile(final_samples, 50)),
                    "q60": float(np.percentile(final_samples, 60)),
                    "q75": float(np.percentile(final_samples, 75)),
                    "q90": float(np.percentile(final_samples, 90)),
                    "q95": float(np.percentile(final_samples, 95)),
                }
                return {
                    "model_id": self.model_name,
                    "model_family": "CHRONOS_FOUNDATION",
                    "device": self.device,
                    "is_fallback": False,
                    "horizon_days": horizon_days,
                    "current_price": current_price,
                    "quantiles": quantiles,
                    "median_price": quantiles["q50"],
                    "mean_price": float(np.mean(final_samples)),
                    "samples_count": num_samples,
                }
            except Exception:
                pass  # Fall through to resilient local quantile model

        # 2. Local Autoregressive Quantile Distribution Model (Production Fallback)
        np.random.seed(random_seed)
        n = len(p)
        daily_returns = np.diff(p) / p[:-1] if n > 1 else np.array([0.0005])
        recent_vol = float(np.std(daily_returns[-20:])) if len(daily_returns) >= 5 else 0.015
        long_vol = float(np.std(daily_returns)) if len(daily_returns) >= 20 else recent_vol
        blended_daily_vol = (0.7 * recent_vol) + (0.3 * long_vol)

        # Estimate gentle momentum drift with mean-reverting clamp
        drift_10d = float(np.mean(daily_returns[-10:])) if len(daily_returns) >= 10 else 0.0
        clamped_drift = max(-0.002, min(0.002, drift_10d * 0.4))

        # Generate student-t distributed shocks (df=5 to capture realistic fat tails in equities)
        from scipy import stats
        shocks = stats.t.rvs(df=5, loc=clamped_drift, scale=blended_daily_vol, size=(num_samples, horizon_days))
        # Path simulation
        paths = current_price * np.cumprod(1.0 + shocks, axis=1)
        final_dist = paths[:, -1]

        # Multi-step fan chart median and interval points
        fan_steps = []
        step_indices = [int(x) for x in np.linspace(1, horizon_days, min(10, horizon_days))]
        for step in step_indices:
            step_slice = paths[:, step - 1]
            fan_steps.append({
                "day": step,
                "q10": float(round(np.percentile(step_slice, 10), 2)),
                "q25": float(round(np.percentile(step_slice, 25), 2)),
                "q50": float(round(np.percentile(step_slice, 50), 2)),
                "q75": float(round(np.percentile(step_slice, 75), 2)),
                "q90": float(round(np.percentile(step_slice, 90), 2)),
            })

        quantiles = {
            "q05": float(round(np.percentile(final_dist, 5), 2)),
            "q10": float(round(np.percentile(final_dist, 10), 2)),
            "q25": float(round(np.percentile(final_dist, 25), 2)),
            "q40": float(round(np.percentile(final_dist, 40), 2)),
            "q50": float(round(np.percentile(final_dist, 50), 2)),
            "q60": float(round(np.percentile(final_dist, 60), 2)),
            "q75": float(round(np.percentile(final_dist, 75), 2)),
            "q90": float(round(np.percentile(final_dist, 90), 2)),
            "q95": float(round(np.percentile(final_dist, 95), 2)),
        }

        return {
            "model_id": f"{self.model_name}-local-probabilistic",
            "model_family": "CHRONOS_ADAPTER",
            "device": self.device,
            "is_fallback": True,
            "horizon_days": horizon_days,
            "current_price": current_price,
            "quantiles": quantiles,
            "median_price": quantiles["q50"],
            "mean_price": float(round(np.mean(final_dist), 2)),
            "fan_chart": fan_steps,
            "samples_count": num_samples,
        }
