"""Fundamental Features Extractor for Scenario & Forecast Engine.

Point-in-time extraction of financial performance indicators:
growth rates, margins, leverage ratios, return on capital, and cash generation.
"""
from typing import Dict, Any, Optional


class FundamentalFeatureExtractor:
    @staticmethod
    def extract(snapshot: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Extract standardized fundamental ratios and metrics from financial snapshot."""
        if not snapshot:
            return {
                "revenue_growth_yoy": 10.0,
                "pat_growth_yoy": 12.0,
                "ebitda_margin_pct": 18.0,
                "pat_margin_pct": 12.0,
                "roe_pct": 16.0,
                "roce_pct": 19.0,
                "debt_to_equity": 0.35,
                "net_debt_to_ebitda": 0.8,
                "fcf_to_pat": 0.85,
                "interest_coverage_ratio": 6.5,
                "is_consolidated": 1.0,
            }

        rev = float(snapshot.get("revenue") or 0.0)
        ebitda = float(snapshot.get("ebitda") or 0.0)
        pat = float(snapshot.get("pat") or 0.0)
        debt = float(snapshot.get("debt") or 0.0)
        cash = float(snapshot.get("cash") or 0.0)
        fcf = float(snapshot.get("free_cash_flow") or 0.0)
        roe = float(snapshot.get("roe") or 15.0)
        roce = float(snapshot.get("roce") or 18.0)

        # Margins
        ebitda_margin = (ebitda / rev * 100.0) if rev > 0 else 18.0
        pat_margin = (pat / rev * 100.0) if rev > 0 else 10.0

        # Leverage
        net_debt = max(0.0, debt - cash)
        net_debt_ebitda = (net_debt / max(ebitda, 1.0)) if ebitda > 0 else 0.5
        d_e = (debt / max(rev * 0.5, 1.0))  # Proxy if equity not explicit

        fcf_pat = (fcf / max(pat, 1.0)) if pat > 0 else 0.8

        return {
            "revenue_growth_yoy": float(round(float(snapshot.get("revenue_growth") or 11.5), 2)),
            "pat_growth_yoy": float(round(float(snapshot.get("pat_growth") or 14.0), 2)),
            "ebitda_margin_pct": float(round(ebitda_margin, 2)),
            "pat_margin_pct": float(round(pat_margin, 2)),
            "roe_pct": float(round(roe, 2)),
            "roce_pct": float(round(roce, 2)),
            "debt_to_equity": float(round(d_e, 2)),
            "net_debt_to_ebitda": float(round(net_debt_ebitda, 2)),
            "fcf_to_pat": float(round(fcf_pat, 2)),
            "interest_coverage_ratio": float(round(float(snapshot.get("interest_coverage") or 7.2), 2)),
            "is_consolidated": 1.0 if snapshot.get("is_consolidated", True) else 0.0,
        }
