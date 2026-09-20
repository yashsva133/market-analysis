"""Capital Scenario Engine for Indian Cash Equities.

Enforces strict Indian market cash-equity mechanics:
- Executable quantities are strictly WHOLE SHARES (floor((capital - costs)/price))
- If quantity == 0: displays "INSUFFICIENT CAPITAL FOR ONE SHARE" and non-executable theoretical fractional exposure
- Computes capital outcome distributions for Bear, Base, Bull, and Q10-Q90 quantiles
- Calculates MODEL-IMPLIED EXPECTED VALUE with clear risk disclosures
"""
import math
from typing import Dict, Any, Optional
from .costs import TransactionCostModel


class CapitalScenarioEngine:
    def __init__(self, cost_model: Optional[TransactionCostModel] = None):
        self.cost_model = cost_model or TransactionCostModel()

    @staticmethod
    def calculate_position(capital: float, current_price: float) -> Dict[str, Any]:
        """Compute execution position safely under all edge conditions."""
        if math.isnan(current_price) or math.isinf(current_price) or current_price <= 0:
            return {
                "executable_whole_shares": 0,
                "is_insufficient_capital": True,
                "allocated_capital": 0.0,
                "cash_remainder": 0.0,
                "insufficient_capital_alert": "INVALID_PRICE",
            }
        if capital <= 0:
            return {
                "executable_whole_shares": 0,
                "is_insufficient_capital": True,
                "allocated_capital": 0.0,
                "cash_remainder": 0.0,
                "insufficient_capital_alert": "INSUFFICIENT_CAPITAL",
            }

        approx_entry_costs = capital * 0.0025
        available_for_shares = max(0.0, capital - approx_entry_costs)
        whole_share_quantity = int(math.floor(available_for_shares / current_price))
        is_insufficient = (whole_share_quantity == 0)

        cost_model = TransactionCostModel()
        if not is_insufficient:
            executable_notional = whole_share_quantity * current_price
            fee_breakdown = cost_model.estimate_buy_costs(executable_notional)
            entry_costs = fee_breakdown["total_estimated_cost"]
            cash_remaining = round(capital - (executable_notional + entry_costs), 2)
        else:
            executable_notional = 0.0
            entry_costs = 0.0
            cash_remaining = round(capital, 2)

        return {
            "executable_whole_shares": whole_share_quantity,
            "is_insufficient_capital": is_insufficient,
            "allocated_capital": capital,
            "cash_remainder": cash_remaining,
            "entry_notional": executable_notional,
            "entry_costs": entry_costs,
        }

    def simulate_capital(
        self,
        symbol: str,
        current_price: float,
        capital: float,
        horizon_days: int,
        target_price: float,
        forecast_distribution: Dict[str, float],
        probabilities: Dict[str, Any],
        scenarios: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate real cash equity positioning and capital outcomes across scenarios."""
        if current_price <= 0:
            raise ValueError("Current price must be positive")
        if capital <= 0:
            raise ValueError("Capital must be positive")

        # 1. Indian Cash-Equity Whole Shares Logic (§23)
        # Estimate approximate entry fee buffer (0.25%)
        approx_entry_costs = capital * 0.0025
        available_for_shares = max(0.0, capital - approx_entry_costs)
        whole_share_quantity = int(math.floor(available_for_shares / current_price))

        is_insufficient_capital = (whole_share_quantity == 0)
        insufficient_capital_reason = (
            f"INSUFFICIENT CAPITAL FOR ONE SHARE (Share price ₹{current_price:,.2f} exceeds available capital ₹{capital:,.2f})"
            if is_insufficient_capital else None
        )

        # Non-executable theoretical fractional exposure (§23)
        theoretical_fractional_shares = round(capital / current_price, 4)

        # Actual executable notional and real entry costs
        if not is_insufficient_capital:
            executable_notional = whole_share_quantity * current_price
            fee_breakdown = self.cost_model.estimate_buy_costs(executable_notional)
            entry_costs = fee_breakdown["total_estimated_cost"]
            cash_remaining = round(capital - (executable_notional + entry_costs), 2)
        else:
            executable_notional = 0.0
            entry_costs = 0.0
            fee_breakdown = {"total_estimated_cost": 0.0, "cost_pct": 0.0}
            cash_remaining = round(capital, 2)

        # 2. Capital Outcome Values Across Quantiles (§24)
        def calc_cap_val(target_p: float) -> Dict[str, float]:
            if not is_insufficient_capital:
                position_val = whole_share_quantity * target_p
                total_val = round(cash_remaining + position_val, 2)
                pnl = round(total_val - capital, 2)
                pnl_pct = round((pnl / capital) * 100.0, 2)
            else:
                # Theoretical calculation for user context
                position_val = theoretical_fractional_shares * target_p
                total_val = round(position_val, 2)
                pnl = round(total_val - capital, 2)
                pnl_pct = round((pnl / capital) * 100.0, 2)

            return {
                "terminal_price": round(target_p, 2),
                "portfolio_value": total_val,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }

        q = forecast_distribution
        q10 = q.get("q10", current_price * 0.92)
        q25 = q.get("q25", q10 * 1.04)
        q50 = q.get("q50", current_price)
        q75 = q.get("q75", q50 * 1.06)
        q90 = q.get("q90", current_price * 1.10)

        cap_q10 = calc_cap_val(q10)
        cap_q25 = calc_cap_val(q25)
        cap_q50 = calc_cap_val(q50)
        cap_q75 = calc_cap_val(q75)
        cap_q90 = calc_cap_val(q90)

        # Scenario values (Bear, Base, Bull)
        sc = scenarios.get("scenarios", scenarios)
        bear_dict = sc.get("BEAR", sc.get("bear", {}))
        base_dict = sc.get("BASE", sc.get("base", {}))
        bull_dict = sc.get("BULL", sc.get("bull", {}))

        bear_p = bear_dict.get("price_low", q10)
        base_p = base_dict.get("price_median", q50)
        bull_p = bull_dict.get("price_high", q90)

        bear_outcome = calc_cap_val(bear_p)
        base_outcome = calc_cap_val(base_p)
        bull_outcome = calc_cap_val(bull_p)

        # Model-Implied Expected Value (§25)
        # E[V] = integral over quantile distribution
        exp_price = (q10 * 0.15) + (q25 * 0.20) + (q50 * 0.30) + (q75 * 0.20) + (q90 * 0.15)
        exp_outcome = calc_cap_val(exp_price)

        exec_dict = {
            "whole_shares": whole_share_quantity,
            "executable_whole_shares": whole_share_quantity,
            "insufficient_capital": is_insufficient_capital,
            "is_insufficient_capital": is_insufficient_capital,
            "insufficient_capital_alert": insufficient_capital_reason,
            "entry_notional": executable_notional,
            "estimated_transaction_costs": entry_costs,
            "transaction_costs_breakdown": fee_breakdown,
            "cash_remaining": cash_remaining,
            "cash_remainder": cash_remaining,
            "theoretical_fractional_exposure": theoretical_fractional_shares,
            "theoretical_fractional_exposure_details": {
                "shares": theoretical_fractional_shares,
                "label": "NON-EXECUTABLE (Informational fractional exposure only; Indian exchanges require whole shares)",
            },
            "is_fractional_executable": False,
        }

        return {
            "symbol": symbol.upper(),
            "capital_inr": capital,
            "current_price": current_price,
            "horizon_days": horizon_days,
            "target_price": target_price,
            "execution": exec_dict,
            "execution_position": exec_dict,
            "scenarios_capital_outcomes": {
                "bear": bear_outcome,
                "base": base_outcome,
                "bull": bull_outcome,
            },
            "quantile_capital_outcomes": {
                "q10": cap_q10,
                "q25": cap_q25,
                "q50": cap_q50,
                "q75": cap_q75,
                "q90": cap_q90,
            },
            "model_implied_expected_value": {
                "label": "MODEL-IMPLIED EXPECTED VALUE",
                "expected_terminal_price": round(exp_price, 2),
                "expected_portfolio_value": exp_outcome["portfolio_value"],
                "expected_pnl": exp_outcome["pnl"],
                "expected_return_pct": exp_outcome["pnl_pct"],
                "disclaimer": "MODEL-IMPLIED ESTIMATE ONLY. DOES NOT CONSTITUTE A GUARANTEED RETURN OR FINANCIAL ADVICE. CAPITAL IS AT RISK.",
            },
            "loss_and_drawdown_risk": probabilities.get("downside_probabilities", {}),
            "target_probabilities": probabilities.get("target_probabilities", {}),
        }
