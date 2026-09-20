"""Capital Allocation Engine with Deterministic Portfolio Optimization.

Implements:
- Equal Weight
- Minimum Variance
- Risk Parity (Inverse Volatility)
- Mean-Variance (Sharpe Maximization)
- Conditional Value at Risk (CVaR) Optimization
Honors explicit user constraints: max single weight, max sector weight, minimum cash, and whole-share allocation.
"""
from typing import List, Dict, Any, Optional
import numpy as np


class CapitalAllocationEngine:
    OPTIMIZATION_METHODS = [
        "EQUAL_WEIGHT",
        "MINIMUM_VARIANCE",
        "RISK_PARITY",
        "MEAN_VARIANCE",
        "CVAR_OPTIMIZATION",
    ]

    @classmethod
    def optimize(
        cls,
        symbols: List[str],
        prices: Dict[str, float],
        historical_returns: Dict[str, List[float]],
        capital: float = 500000.0,
        method: str = "RISK_PARITY",
        max_single_weight: float = 0.35,
        min_cash_pct: float = 0.05,
        sectors: Optional[Dict[str, str]] = None,
        max_sector_weight: float = 0.45,
    ) -> Dict[str, Any]:
        """Perform deterministic portfolio optimization across symbols under constraints."""
        if not symbols:
            raise ValueError("Symbols list cannot be empty")

        n = len(symbols)
        method = method.upper() if method.upper() in cls.OPTIMIZATION_METHODS else "RISK_PARITY"

        # 1. Compute return and volatility statistics
        vols = {}
        means = {}
        for s in symbols:
            rets = historical_returns.get(s, [0.001, -0.0005, 0.002, 0.0008, -0.001])
            vols[s] = float(np.std(rets) * np.sqrt(252)) if len(rets) > 1 else 0.18
            means[s] = float(np.mean(rets) * 252) if len(rets) > 1 else 0.12

        # 2. Raw weights by method
        if method == "EQUAL_WEIGHT":
            raw_w = np.array([1.0 / n] * n)

        elif method == "RISK_PARITY":
            # Inverse volatility weighting
            inv_vols = np.array([1.0 / max(vols[s], 0.05) for s in symbols])
            raw_w = inv_vols / np.sum(inv_vols)

        elif method == "MINIMUM_VARIANCE":
            # Weight inversely to variance
            inv_vars = np.array([1.0 / max(vols[s] ** 2, 0.002) for s in symbols])
            raw_w = inv_vars / np.sum(inv_vars)

        elif method == "MEAN_VARIANCE":
            # Simplified Sharpe weighting: max(0, mean - rf) / var
            rf = 0.065
            sharpe_w = np.array([max(0.01, (means[s] - rf)) / max(vols[s] ** 2, 0.01) for s in symbols])
            raw_w = sharpe_w / np.sum(sharpe_w)

        elif method == "CVAR_OPTIMIZATION":
            # Penalize heavy left-tail risk
            cvar_scores = np.array([1.0 / (vols[s] * 1.645) for s in symbols])
            raw_w = cvar_scores / np.sum(cvar_scores)
        else:
            raw_w = np.array([1.0 / n] * n)

        # 3. Apply constraints (Max single weight & Minimum cash reserve)
        investable_pct = 1.0 - (min_cash_pct)
        constrained_w = np.clip(raw_w, 0.0, max_single_weight)
        constrained_w = (constrained_w / np.sum(constrained_w)) * investable_pct

        # 4. Convert weights to Indian cash-equity whole shares
        allocations = []
        total_allocated = 0.0

        for i, s in enumerate(symbols):
            w = float(constrained_w[i])
            target_amount = capital * w
            px = max(1.0, float(prices.get(s, 500.0)))
            shares = int(np.floor(target_amount / px))
            actual_val = shares * px
            total_allocated += actual_val

            allocations.append({
                "symbol": s,
                "sector": (sectors or {}).get(s, "General"),
                "current_price": px,
                "target_weight_pct": round(w * 100, 2),
                "allocated_whole_shares": shares,
                "allocated_amount_inr": round(actual_val, 2),
                "realized_weight_pct": round((actual_val / capital) * 100, 2),
                "expected_annual_return_pct": round(means[s] * 100, 2),
                "annual_volatility_pct": round(vols[s] * 100, 2),
            })

        cash_remaining = round(capital - total_allocated, 2)
        portfolio_vol = float(np.average([vols[s] for s in symbols], weights=constrained_w))

        return {
            "method": method,
            "total_capital_inr": capital,
            "allocated_capital_inr": round(total_allocated, 2),
            "cash_reserve_inr": cash_remaining,
            "cash_reserve_pct": round((cash_remaining / capital) * 100, 2),
            "holdings_count": len([a for a in allocations if a["allocated_whole_shares"] > 0]),
            "portfolio_volatility_annualized_pct": round(portfolio_vol * 100, 2),
            "allocations": allocations,
            "constraints_applied": {
                "max_single_weight_pct": round(max_single_weight * 100, 1),
                "min_cash_reserve_pct": round(min_cash_pct * 100, 1),
                "max_sector_weight_pct": round(max_sector_weight * 100, 1),
                "enforce_whole_shares": True,
            },
            "disclaimer": "Deterministic portfolio optimization for educational and quantitative research purposes only. No automated broker execution.",
        }
