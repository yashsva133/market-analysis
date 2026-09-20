"""Volume Features Extractor for Scenario & Forecast Engine.

Calculates volume averages, relative volume (RVOL), volume spikes,
and volume-price correlation.
"""
from typing import List, Dict, Any
import numpy as np


class VolumeFeatureExtractor:
    @staticmethod
    def extract(volumes: List[float], closes: List[float] = None) -> Dict[str, float]:
        """Compute standardized volume dynamics and relative activity metrics."""
        if not volumes or len(volumes) < 5:
            return {
                "rvol_20d": 1.0,
                "volume_spike_factor": 1.0,
                "volume_trend_5d": 0.0,
                "volume_price_corr_20d": 0.0,
                "avg_daily_turnover_cr": 25.0,
            }

        v = np.array(volumes, dtype=float)
        n = len(v)
        last_vol = v[-1]

        v_sma20 = float(np.mean(v[-20:])) if n >= 20 else float(np.mean(v))
        rvol = last_vol / max(v_sma20, 1.0)
        spike = last_vol / max(float(np.median(v[-20:])), 1.0)

        # Volume trend 5d
        v_5d = float(np.mean(v[-5:])) if n >= 5 else v_sma20
        vol_trend = (v_5d - v_sma20) / max(v_sma20, 1.0)

        # Volume-price correlation
        corr = 0.0
        if closes and len(closes) == n and n >= 10:
            window = min(n, 20)
            c = np.array(closes[-window:], dtype=float)
            sub_v = v[-window:]
            if np.std(c) > 0 and np.std(sub_v) > 0:
                corr = float(np.corrcoef(c, sub_v)[0, 1])

        # Approximate turnover in Crores assuming average price
        avg_price = closes[-1] if (closes and len(closes) > 0) else 500.0
        turnover_cr = (v_sma20 * avg_price) / 1e7

        return {
            "rvol_20d": float(round(rvol, 2)),
            "volume_spike_factor": float(round(spike, 2)),
            "volume_trend_5d": float(round(vol_trend, 4)),
            "volume_price_corr_20d": float(round(corr, 3)),
            "avg_daily_turnover_cr": float(round(turnover_cr, 2)),
        }
