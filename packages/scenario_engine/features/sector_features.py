"""Sector Features Extractor for Scenario & Forecast Engine.

Calculates sector-relative performance, sector volatility,
relative strength, and industry thematic momentum.
"""
from typing import Dict, Any, Optional


class SectorFeatureExtractor:
    @staticmethod
    def extract(
        sector_name: str,
        stock_return_20d: float,
        sector_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """Extract sector benchmark features and comparative relative strength."""
        data = sector_data or {}

        # Default benchmark returns by sector
        sector_benchmarks = {
            "IT": {"return_20d": 2.40, "vol_20d": 0.165, "event_intensity": 1.2},
            "OIL & GAS": {"return_20d": 1.10, "vol_20d": 0.180, "event_intensity": 1.5},
            "BANKING": {"return_20d": 3.10, "vol_20d": 0.145, "event_intensity": 1.4},
            "CAPITAL GOODS": {"return_20d": 4.20, "vol_20d": 0.210, "event_intensity": 2.1},
            "AUTOMOBILE": {"return_20d": 1.90, "vol_20d": 0.175, "event_intensity": 1.1},
            "PHARMACEUTICALS": {"return_20d": 2.80, "vol_20d": 0.150, "event_intensity": 1.0},
        }

        sec_key = (sector_name or "CAPITAL GOODS").upper()
        sec_info = sector_benchmarks.get(sec_key, {"return_20d": 2.0, "vol_20d": 0.16, "event_intensity": 1.0})

        sec_ret = float(data.get("sector_return_20d", sec_info["return_20d"]))
        sec_vol = float(data.get("sector_volatility_20d", sec_info["vol_20d"]))
        sec_intensity = float(data.get("sector_event_intensity", sec_info["event_intensity"]))

        # Stock vs Sector relative strength
        relative_strength_20d = stock_return_20d - sec_ret

        return {
            "sector_return_20d": float(round(sec_ret, 2)),
            "sector_volatility_20d": float(round(sec_vol, 4)),
            "sector_relative_strength_20d": float(round(relative_strength_20d, 2)),
            "sector_event_intensity": float(round(sec_intensity, 2)),
            "sector_sentiment_score": float(round(float(data.get("sector_sentiment", 0.25)), 3)),
        }
