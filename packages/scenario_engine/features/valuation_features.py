"""Valuation Features Extractor for Scenario & Forecast Engine.

Calculates trailing valuation multiples, enterprise value ratios,
historical valuation percentiles, and sector-relative premiums.
"""
from typing import Dict, Any, Optional


class ValuationFeatureExtractor:
    @staticmethod
    def extract(
        snapshot: Optional[Dict[str, Any]],
        sector_pe_median: float = 24.0,
        sector_pb_median: float = 3.2,
    ) -> Dict[str, float]:
        """Compute standardized valuation metrics and relative multiples."""
        pe = 22.5
        pb = 3.1
        ev_ebitda = 14.2
        val_percentile = 50.0

        if snapshot:
            if snapshot.get("pe"):
                pe = float(snapshot["pe"])
            if snapshot.get("pb"):
                pb = float(snapshot["pb"])
            if snapshot.get("ev_ebitda"):
                ev_ebitda = float(snapshot["ev_ebitda"])
            if snapshot.get("valuation_percentile"):
                val_percentile = float(snapshot["valuation_percentile"])

        # Relative multiples
        pe_rel = pe / max(sector_pe_median, 1.0)
        pb_rel = pb / max(sector_pb_median, 1.0)

        # Earnings yield (1 / PE)
        earnings_yield = (1.0 / max(pe, 1.0)) * 100.0

        return {
            "pe_ratio": float(round(pe, 2)),
            "pb_ratio": float(round(pb, 2)),
            "ev_ebitda_ratio": float(round(ev_ebitda, 2)),
            "pe_relative_to_sector": float(round(pe_rel, 3)),
            "pb_relative_to_sector": float(round(pb_rel, 3)),
            "valuation_percentile_5y": float(round(val_percentile, 1)),
            "earnings_yield_pct": float(round(earnings_yield, 2)),
        }
