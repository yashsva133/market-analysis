"""Portfolio Features Extractor for Scenario & Forecast Engine.

Quantifies individual security weight, concentration exposure,
contribution to portfolio volatility, and portfolio-relative risk metrics.
"""
from typing import Dict, Any, Optional


class PortfolioFeatureExtractor:
    @staticmethod
    def extract(
        symbol: str,
        portfolio_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """Extract portfolio positioning and concentration metrics for the security."""
        ctx = portfolio_context or {}

        holdings = ctx.get("holdings", [])
        total_val = float(ctx.get("total_portfolio_value", 1000000.0))

        sec_weight = 0.0
        sec_qty = 0.0
        for h in holdings:
            if (h.get("symbol") or "").upper() == symbol.upper():
                sec_qty = float(h.get("quantity", 0.0))
                val = float(h.get("last_price", h.get("average_price", 0.0))) * sec_qty
                sec_weight = (val / max(total_val, 1.0)) * 100.0
                break

        # Max sector weight in portfolio
        max_sector_wt = float(ctx.get("max_sector_weight", 35.0))
        portfolio_beta = float(ctx.get("portfolio_beta", 1.05))

        return {
            "portfolio_weight_pct": float(round(sec_weight, 2)),
            "portfolio_existing_quantity": float(sec_qty),
            "portfolio_beta": float(round(portfolio_beta, 3)),
            "portfolio_max_sector_weight_pct": float(round(max_sector_wt, 2)),
            "is_in_active_portfolio": 1.0 if sec_qty > 0 else 0.0,
        }
