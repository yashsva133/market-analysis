"""Sector Features Extractor for Scenario & Forecast Engine.

Calculates sector-relative performance, sector volatility,
relative strength, and industry thematic momentum.

Sector benchmark values are ONLY derived from supplied `sector_data`
(real ingested sector/benchmark observations). When no sector benchmark
data is available, the corresponding features are returned as `None`
rather than substituted with fabricated benchmark returns or volatilities.
"""
from typing import Dict, Any, Optional


class SectorFeatureExtractor:
    @staticmethod
    def extract(
        sector_name: str,
        stock_return_20d: float,
        sector_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract sector benchmark features and comparative relative strength.

        `sector_data` must supply real sector benchmark observations under the
        keys `sector_return_20d`, `sector_volatility_20d`, and
        `sector_event_intensity`. Any missing key yields `None` for that feature
        (DATA_UNAVAILABLE) — no fabricated sector benchmark is substituted.
        """
        data = sector_data or {}

        sec_ret = data.get("sector_return_20d")
        sec_vol = data.get("sector_volatility_20d")
        sec_intensity = data.get("sector_event_intensity")
        sec_sentiment = data.get("sector_sentiment")

        # Stock vs Sector relative strength is only meaningful when a real
        # sector benchmark return exists.
        relative_strength_20d = (
            stock_return_20d - float(sec_ret)
            if sec_ret is not None
            else None
        )

        return {
            "sector_name": (sector_name or "").upper() or None,
            "sector_return_20d": round(float(sec_ret), 2) if sec_ret is not None else None,
            "sector_volatility_20d": round(float(sec_vol), 4) if sec_vol is not None else None,
            "sector_relative_strength_20d": (
                round(float(relative_strength_20d), 2)
                if relative_strength_20d is not None
                else None
            ),
            "sector_event_intensity": round(float(sec_intensity), 2) if sec_intensity is not None else None,
            "sector_sentiment_score": round(float(sec_sentiment), 3) if sec_sentiment is not None else None,
        }
