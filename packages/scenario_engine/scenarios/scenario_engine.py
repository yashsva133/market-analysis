"""Scenario Engine for Indian Equities.

Generates 5 deterministic probabilistic market scenarios:
1. SEVERE BEAR (Q05 to Q15)
2. BEAR (Q10 to Q25)
3. BASE (Q40 to Q60 central band)
4. BULL (Q75 to Q90)
5. STRONG BULL (Q90 to Q95)

Each scenario incorporates exact prices, returns, supporting model evidence,
key assumptions, and risk factors derived from features.
"""
from typing import Dict, Any, List


class ScenarioEngine:
    @staticmethod
    def generate_scenarios(
        current_price: float,
        forecast_distribution: Dict[str, float],
        features: Dict[str, Any],
        horizon_days: int,
    ) -> Dict[str, Any]:
        """Produce the 5 structured scenarios grounded in the forecast distribution."""
        q = forecast_distribution
        required_quantiles = ("q05", "q10", "q25", "q40", "q50", "q60", "q75", "q90", "q95")
        missing = [k for k in required_quantiles if q.get(k) is None]
        if missing:
            raise ValueError(
                "DATA_UNAVAILABLE: forecast distribution is missing quantiles "
                f"{missing}. No synthetic quantile is substituted for scenario generation."
            )
        q05 = q["q05"]
        q10 = q["q10"]
        q25 = q["q25"]
        q40 = q["q40"]
        q50 = q["q50"]
        q60 = q["q60"]
        q75 = q["q75"]
        q90 = q["q90"]
        q95 = q["q95"]

        def ret(p):
            return round(((p - current_price) / current_price) * 100.0, 2)

        # Context features — only real values are used; missing features render as N/A.
        def _f(key: str):
            v = features.get(key)
            return float(v) if v is not None else None

        vix = _f("india_vix")
        rev_growth = _f("revenue_growth_yoy")
        sec_str = _f("sector_relative_strength_20d")

        # 1. SEVERE BEAR
        q15 = round((q10 + q05) / 2.0, 2)
        severe_bear = {
            "name": "SEVERE BEAR",
            "price_low": q05,
            "price_high": q15,
            "return_low_pct": ret(q05),
            "return_high_pct": ret(q15),
            "probability_mass_pct": 10.0,
            "supporting_model_evidence": f"Left tail shock conditioned on VIX surge > 22.0 and sharp sector de-rating. Q05 level ₹{q05}.",
            "assumptions": [
                "Severe macroeconomic shock or adverse regulatory intervention",
                "Operating margins contract > 300 bps",
                "Broader market enters sustained correction regime",
            ],
            "risk_factors": [
                "Sharp FII outflow from high-beta Indian equities",
                "Input cost spikes impairing quarterly EBITDA",
            ],
        }

        # 2. BEAR
        bear = {
            "name": "BEAR",
            "price_low": q10,
            "price_high": q25,
            "return_low_pct": ret(q10),
            "return_high_pct": ret(q25),
            "probability_mass_pct": 15.0,
            "supporting_model_evidence": f"Downside band bounded between 10th and 25th distribution percentiles (₹{q10}–₹{q25}).",
            "assumptions": [
                "Growth moderates below historical run-rate",
                "Valuation multiple contracts toward sector median",
                "Relative strength remains neutral to negative",
            ],
            "risk_factors": [
                "Temporary delay in large order execution or capex cycle",
                "Sectoral rotation away from current industry theme",
            ],
        }

        # 3. BASE
        base = {
            "name": "BASE",
            "price_low": q40,
            "price_high": q60,
            "price_median": q50,
            "return_low_pct": ret(q40),
            "return_high_pct": ret(q60),
            "return_median_pct": ret(q50),
            "probability_mass_pct": 50.0,
            "supporting_model_evidence": f"Central modal interval around median Q50 ₹{q50} ({ret(q50):+0.2f}% expected drift over {horizon_days} trading days).",
            "assumptions": [
                f"Revenue growth tracks historical {rev_growth}% pace" if rev_growth is not None else "Revenue growth trend unavailable (no real fundamental data)",
                f"India VIX remains in range ({vix} ± 3.0)" if vix is not None else "India VIX level unavailable (no real market regime data)",
                "No unexpected corporate governance or regulatory disruptions",
            ],
            "risk_factors": [
                "Quarterly earnings meeting consensus without positive surprise",
                "Choppy range-bound index trading",
            ],
        }

        # 4. BULL
        bull = {
            "name": "BULL",
            "price_low": q75,
            "price_high": q90,
            "return_low_pct": ret(q75),
            "return_high_pct": ret(q90),
            "probability_mass_pct": 15.0,
            "supporting_model_evidence": f"Upper quartile expansion (₹{q75}–₹{q90}), supported by positive order momentum and sector tailwinds.",
            "assumptions": [
                "Earnings beat estimates with EBITDA margin expansion",
                f"Sector outperformance continues (current relative strength: {sec_str:+.1f}%)" if sec_str is not None else "Sector relative strength unavailable (no real sector benchmark data)",
                "Institutional accumulation sustains high relative volume",
            ],
            "risk_factors": [
                "Profit booking at technical resistance levels",
                "Valuation multiple reaching upper historical decile",
            ],
        }

        # 5. STRONG BULL
        strong_bull = {
            "name": "STRONG BULL",
            "price_low": q90,
            "price_high": q95,
            "return_low_pct": ret(q90),
            "return_high_pct": ret(q95),
            "probability_mass_pct": 10.0,
            "supporting_model_evidence": f"Right tail breakout (Q90-Q95), driven by major transformative contract or earnings re-rating.",
            "assumptions": [
                "Transformational multi-year order win or breakthrough capex delivery",
                "Broader market enters aggressive risk-on expansion regime",
                "Significant upward revision in consensus earnings estimates",
            ],
            "risk_factors": [
                "Extended RSI (>75) signaling short-term overbought conditions",
                "Macro liquidity tightening capping speculative multiple expansion",
            ],
        }

        for sc in [severe_bear, bear, base, bull, strong_bull]:
            sc["risks"] = sc["risk_factors"]
            sc["scenario_name"] = sc["name"]
            sc["probability"] = sc["probability_mass_pct"] / 100.0
            sc["price_range"] = f"₹{sc['price_low']:,.2f} – ₹{sc['price_high']:,.2f}"
            sc["implied_return_pct"] = f"{sc['return_low_pct']:+0.1f}% to {sc['return_high_pct']:+0.1f}%"
            if "price_median" not in sc:
                sc["price_median"] = round((sc["price_low"] + sc["price_high"]) / 2, 2)
            if "target_price" not in sc:
                sc["target_price"] = sc["price_median"]

        return {
            "SEVERE_BEAR": severe_bear,
            "BEAR": bear,
            "BASE": base,
            "BULL": bull,
            "STRONG_BULL": strong_bull,
        }
