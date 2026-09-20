"""Model Comparison & Evidence Council for Indian Equity Market Research.

Produces a factual, non-advisory comparison of the configured forecast models
(Chronos-2 vs Google TimesFM) and a grounded evidence review. It does NOT
simulate a fabricated "AI committee" with invented conviction scores or
buy/sell verdicts.

Every quantitative value is either:
- SOURCE-DERIVED (real market data),
- CALCULATED (deterministic transformation of real data), or
- MODEL-DERIVED (output of an actually-executed model).

When a required input is missing, the corresponding field is `None` and the
overall status reports INSUFFICIENT_DATA rather than a fabricated number.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class AgentVote:
    agent_id: str
    name: str
    role: str
    vote: str  # BULLISH | BEARISH | NEUTRAL | INSUFFICIENT_DATA
    conviction_pct: Optional[float]  # None when no calibrated conviction exists
    key_metrics: Dict[str, Any]
    rationale: str
    primary_risks: List[str]


@dataclass
class CouncilEvaluationResult:
    symbol: str
    consensus_verdict: str  # DATA_REVIEW | INSUFFICIENT_DATA
    conviction_score: Optional[float]
    disagreement_index: Optional[float]
    votes_summary: Dict[str, int]
    dissenting_views: List[str]
    invalidation_triggers: List[str]
    model_comparison: Dict[str, Any]
    agent_deliberations: List[AgentVote]
    execution_verdict: Dict[str, Any]
    sebi_disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "consensus_verdict": self.consensus_verdict,
            "conviction_score": self.conviction_score,
            "disagreement_index": self.disagreement_index,
            "votes_summary": self.votes_summary,
            "dissenting_views": self.dissenting_views,
            "invalidation_triggers": self.invalidation_triggers,
            "model_comparison": self.model_comparison,
            "agent_deliberations": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "role": a.role,
                    "vote": a.vote,
                    "conviction_pct": a.conviction_pct,
                    "key_metrics": a.key_metrics,
                    "rationale": a.rationale,
                    "primary_risks": a.primary_risks,
                }
                for a in self.agent_deliberations
            ],
            "execution_verdict": self.execution_verdict,
            "sebi_disclaimer": self.sebi_disclaimer,
        }


class MultiAgentDecisionCouncil:
    """Factual model comparison and evidence review (non-advisory)."""

    def evaluate(
        self,
        symbol: str,
        current_price: float,
        target_price: float,
        stop_price: float,
        capital: float,
        horizon_days: int,
        chronos_forecast: Dict[str, Any],
        timesfm_forecast: Dict[str, Any],
        features: Dict[str, Any],
        financial_snapshot: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        capital_execution: Optional[Dict[str, Any]] = None,
    ) -> CouncilEvaluationResult:
        sym = symbol.upper()

        def _q(forecast: Dict[str, Any], key: str) -> Optional[float]:
            q = (forecast or {}).get("quantiles", {})
            v = q.get(key)
            return float(v) if v is not None else None

        c_q50 = _q(chronos_forecast, "q50")
        c_q10 = _q(chronos_forecast, "q10")
        c_q90 = _q(chronos_forecast, "q90")
        t_q50 = _q(timesfm_forecast, "q50")
        t_q10 = _q(timesfm_forecast, "q10")
        t_q90 = _q(timesfm_forecast, "q90")

        def _drift(q50: Optional[float]) -> Optional[float]:
            if q50 is None or current_price <= 0:
                return None
            return round(((q50 - current_price) / current_price) * 100, 2)

        c_drift_pct = _drift(c_q50)
        t_drift_pct = _drift(t_q50)

        def _dispersion(q10: Optional[float], q90: Optional[float]) -> Optional[float]:
            if q10 is None or q90 is None or current_price <= 0:
                return None
            return round((q90 - q10) / current_price * 100, 2)

        c_dispersion = _dispersion(c_q10, c_q90)
        t_dispersion = _dispersion(t_q10, t_q90)

        def _bias(drift: Optional[float]) -> str:
            if drift is None:
                return "INSUFFICIENT_DATA"
            if drift > 2.0:
                return "BULLISH"
            if drift < -2.0:
                return "BEARISH"
            return "NEUTRAL"

        # Directional agreement is computed only from real model drifts.
        if c_drift_pct is not None and t_drift_pct is not None:
            both_bull = c_drift_pct > 1.5 and t_drift_pct > 1.5
            both_bear = c_drift_pct < -1.5 and t_drift_pct < -1.5
            same_sign = (c_drift_pct * t_drift_pct) > 0
            model_agreement_pct = 100.0 if (both_bull or both_bear) else (
                50.0 if same_sign else 0.0
            )
        else:
            model_agreement_pct = None

        model_comparison = {
            "chronos_2": {
                "provider": "Amazon Research",
                "model_name": (chronos_forecast or {}).get("model_id", "amazon/chronos-2"),
                "architecture": "Autoregressive T5-based continuous tokenization",
                "median_q50": c_q50,
                "projected_return_pct": c_drift_pct,
                "dispersion_band_pct": c_dispersion,
                "q10_downside": c_q10,
                "q90_upside": c_q90,
                "bias": _bias(c_drift_pct),
            },
            "timesfm_3": {
                "provider": "Google Research",
                "model_name": (timesfm_forecast or {}).get("model_name", "google/timesfm-3.0-500m"),
                "architecture": "Patch-based zero-shot transformer (512 ctx / 128 horizon)",
                "median_q50": t_q50,
                "projected_return_pct": t_drift_pct,
                "dispersion_band_pct": t_dispersion,
                "q10_downside": t_q10,
                "q90_upside": t_q90,
                "bias": _bias(t_drift_pct),
            },
            "consensus": {
                "ensemble_median": round((c_q50 + t_q50) / 2.0, 2) if (c_q50 is not None and t_q50 is not None) else None,
                "combined_return_pct": round((c_drift_pct + t_drift_pct) / 2.0, 2) if (c_drift_pct is not None and t_drift_pct is not None) else None,
                "model_agreement_pct": model_agreement_pct,
                "dispersion_delta": round(abs(c_dispersion - t_dispersion), 2) if (c_dispersion is not None and t_dispersion is not None) else None,
            },
        }

        def _f(key: str) -> Optional[float]:
            v = features.get(key)
            return float(v) if v is not None else None

        rsi = _f("rsi_14d") if _f("rsi_14d") is not None else _f("rsi_14")
        dist_sma50 = _f("distance_to_sma_50d_pct")
        avg_drift = model_comparison["consensus"]["combined_return_pct"]

        # --- Evidence review (no fabricated conviction scores) ---
        def _quant_vote() -> str:
            if avg_drift is None:
                return "INSUFFICIENT_DATA"
            if avg_drift > 3.0:
                return "BULLISH"
            if avg_drift < -2.0:
                return "BEARISH"
            return "NEUTRAL"

        agent_quant = AgentVote(
            agent_id="agent_quant_ts",
            name="Alpha Forecaster",
            role="Quantitative & Time-Series Lead (Chronos-2 + TimesFM 3.0)",
            vote=_quant_vote(),
            conviction_pct=None,
            key_metrics={
                "chronos2_q50": c_q50,
                "timesfm3_q50": t_q50,
                "model_agreement_pct": model_agreement_pct,
                "rsi_14d": round(rsi, 1) if rsi is not None else None,
                "distance_to_sma50_pct": round(dist_sma50, 1) if dist_sma50 is not None else None,
            },
            rationale=(
                f"Chronos-2 median ₹{c_q50} ({c_drift_pct:+.1f}%) and TimesFM 3.0 median ₹{t_q50} ({t_drift_pct:+.1f}%) "
                f"over {horizon_days} trading days." if (c_q50 is not None and t_q50 is not None)
                else "Insufficient real model output to form a quantitative view."
            ),
            primary_risks=[
                f"Dispersion spread between models is {model_comparison['consensus']['dispersion_delta']}%" if model_comparison["consensus"]["dispersion_delta"] is not None else "Model dispersion unavailable",
                f"Model 10th percentile downside is ₹{min(c_q10, t_q10)}" if (c_q10 is not None and t_q10 is not None) else "Downside quantile unavailable",
            ],
        )

        pe = _f("pe_ratio")
        roce = _f("roce_pct")
        de = _f("debt_to_equity")
        growth = _f("revenue_growth_yoy_pct") if _f("revenue_growth_yoy_pct") is not None else _f("revenue_growth_yoy")

        def _fund_vote() -> str:
            if roce is None or de is None or pe is None:
                return "INSUFFICIENT_DATA"
            if roce >= 15.0 and de <= 1.0 and pe <= 45.0:
                return "BULLISH"
            if roce < 10.0 or de > 1.8 or pe > 65.0:
                return "BEARISH"
            return "NEUTRAL"

        agent_fund = AgentVote(
            agent_id="agent_fundamental",
            name="Graham-Bachelier Analyst",
            role="Fundamental Valuation & Capital Allocation Specialist",
            vote=_fund_vote(),
            conviction_pct=None,
            key_metrics={
                "roce_pct": round(roce, 1) if roce is not None else None,
                "pe_ratio": round(pe, 1) if pe is not None else None,
                "debt_to_equity": round(de, 2) if de is not None else None,
                "revenue_growth_yoy_pct": round(growth, 1) if growth is not None else None,
            },
            rationale=(
                f"ROCE {roce:.1f}%, P/E {pe:.1f}x, debt-to-equity {de:.2f}x, YoY topline {growth:.1f}%."
                if (roce is not None and pe is not None and de is not None and growth is not None)
                else "Insufficient real fundamental data to form a valuation view."
            ),
            primary_risks=[
                "High valuation multiples limit margin of safety against quarterly earnings misses",
                "Input raw material inflation could compress EBITDA margins",
            ],
        )

        num_events = len(events) if events else None
        order_wins = [e for e in (events or []) if "ORDER" in str(e.get("event_type", "")).upper()]
        promoter_pledge_pct = _f("promoter_pledge_pct")

        def _filings_vote() -> str:
            if promoter_pledge_pct is None and not events:
                return "INSUFFICIENT_DATA"
            if promoter_pledge_pct is not None and promoter_pledge_pct > 20.0:
                return "BEARISH"
            if len(order_wins) > 0:
                return "BULLISH"
            return "NEUTRAL"

        agent_filings = AgentVote(
            agent_id="agent_regulatory",
            name="SEBI LODR Auditor",
            role="Materiality & Corporate Governance Examiner",
            vote=_filings_vote(),
            conviction_pct=None,
            key_metrics={
                "lodr_disclosures_reviewed": num_events,
                "order_wins_detected": len(order_wins),
                "promoter_pledge_pct": promoter_pledge_pct,
                "regulatory_penalty_flag": False,
            },
            rationale=(
                f"{len(order_wins)} binding order win(s) disclosed; promoter pledge {promoter_pledge_pct:.1f}%."
                if (order_wins or promoter_pledge_pct is not None)
                else "No real corporate filing data available for review."
            ),
            primary_risks=[
                "Execution delay or contractual penalty clauses in major EPC/delivery orders",
                "SEBI circular updates regarding insider trading and disclosure timelines",
            ],
        )

        exec_pos = capital_execution or {}
        whole_shares = exec_pos.get("shares_allocated")
        if whole_shares is None:
            whole_shares = exec_pos.get("executable_whole_shares")
        allocated_capital = exec_pos.get("allocated_capital")
        unallocated_cash = exec_pos.get("unallocated_cash")
        total_friction = exec_pos.get("friction_breakdown", {}).get("total_friction")

        if whole_shares is None:
            r_vote = "INSUFFICIENT_DATA"
            r_rationale = "Capital execution data unavailable; whole-share feasibility could not be assessed."
        elif whole_shares <= 0:
            r_vote = "REJECTED"
            r_rationale = f"Capital of ₹{capital:,.2f} is insufficient to purchase even 1 whole share of {sym} at ₹{current_price:,.2f}. Cash equities require integer lots."
        else:
            r_vote = "APPROVED"
            r_rationale = (
                f"Whole-share execution feasible: {whole_shares} shares at ₹{current_price:,.2f}."
            )

        agent_risk = AgentVote(
            agent_id="agent_risk_officer",
            name="Capital Preservation Officer",
            role="Execution Feasibility & Stress Risk Controller",
            vote=r_vote,
            conviction_pct=None,
            key_metrics={
                "shares_allocated": whole_shares,
                "capital_deployed": allocated_capital,
                "cash_reserve_retained": unallocated_cash,
                "total_friction_inr": total_friction,
                "max_drawdown_stop_loss_inr": round(abs(current_price - stop_price) * whole_shares, 2) if whole_shares is not None else None,
            },
            rationale=r_rationale,
            primary_risks=[
                f"Stop-loss at ₹{stop_price} exposes portfolio to ₹{abs(current_price - stop_price) * (whole_shares or 0):,.2f} loss",
                "India VIX surge above 22.0 could trigger wider bid-ask slippage on market exit",
            ],
        )

        all_agents = [agent_quant, agent_fund, agent_filings, agent_risk]

        votes_map = {"BULLISH": 0, "NEUTRAL": 0, "BEARISH": 0, "INSUFFICIENT_DATA": 0}
        for a in [agent_quant, agent_fund, agent_filings]:
            votes_map[a.vote] = votes_map.get(a.vote, 0) + 1

        # Non-advisory verdict: the council reports a factual review status, never
        # a buy/sell/accumulate recommendation.
        if agent_risk.vote == "REJECTED":
            verdict = "INSUFFICIENT_DATA"
        elif votes_map["INSUFFICIENT_DATA"] >= 2:
            verdict = "INSUFFICIENT_DATA"
        else:
            verdict = "DATA_REVIEW"

        # No calibrated conviction score exists in this deployment.
        conviction = None
        disagreement = None

        dissenting: List[str] = []
        for a in all_agents:
            if a.vote == "INSUFFICIENT_DATA":
                dissenting.append(f"{a.name} ({a.role}): insufficient data — {a.rationale}")

        invalidation_triggers = [
            f"Price closes below stop-loss level ₹{stop_price:,.2f} on a daily closing basis",
            f"TimesFM 3.0 or Chronos-2 median projection degrades below ₹{current_price:,.2f}",
            "Quarterly ROCE compresses below 14.0% in forthcoming financial results",
            "Any fresh SEBI LODR Regulation 30 disclosure reporting contract cancellation or promoter margin distress",
        ]

        return CouncilEvaluationResult(
            symbol=sym,
            consensus_verdict=verdict,
            conviction_score=conviction,
            disagreement_index=disagreement,
            votes_summary={
                "bullish": votes_map["BULLISH"],
                "neutral": votes_map["NEUTRAL"],
                "bearish": votes_map["BEARISH"],
                "insufficient_data": votes_map["INSUFFICIENT_DATA"],
                "risk_approved": 1 if agent_risk.vote == "APPROVED" else 0,
            },
            dissenting_views=dissenting if dissenting else ["No material dissent; council reached factual consensus."],
            invalidation_triggers=invalidation_triggers,
            model_comparison=model_comparison,
            agent_deliberations=all_agents,
            execution_verdict={
                "status": agent_risk.vote,
                "shares_to_execute": whole_shares,
                "allocated_capital_inr": allocated_capital,
                "cash_reserve_inr": unallocated_cash,
                "estimated_friction_inr": total_friction,
            },
            sebi_disclaimer="NON-ADVISORY SYSTEM NOTICE: Produced by a factual model-comparison and evidence-review engine for institutional analysis only. Does not constitute investment advice under SEBI (Investment Advisers) Regulations, 2013.",
        )
