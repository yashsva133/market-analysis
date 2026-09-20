"""Market Regime Features Extractor for Scenario & Forecast Engine.

Quantifies broad market environment, India VIX levels, market breadth,
regime classification, and macroeconomic risk factors.
"""
from typing import Dict, Any, Optional


class MarketRegimeFeatureExtractor:
    @staticmethod
    def extract(regime_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Convert macro and broad market indicators into regime features."""
        data = regime_data or {}

        nifty_return_20d = float(data.get("nifty_return_20d", 1.85))
        nifty_vol_20d = float(data.get("nifty_vol_20d", 0.135))
        india_vix = float(data.get("india_vix", 13.40))
        advance_decline_ratio = float(data.get("advance_decline_ratio", 1.25))
        market_drawdown = float(data.get("market_drawdown", 1.20))
        usdinr = float(data.get("usdinr", 83.85))
        brent_crude = float(data.get("brent_crude", 74.50))
        repo_rate = float(data.get("repo_rate", 6.50))

        # Regime index encoding:
        # 1: TRENDING_UP, 2: TRENDING_DOWN, 3: HIGH_VOLATILITY, 4: RANGE_BOUND
        regime_code = 1.0  # Default TRENDING_UP
        if india_vix > 18.0:
            regime_code = 3.0  # HIGH_VOLATILITY
        elif nifty_return_20d < -3.0:
            regime_code = 2.0  # TRENDING_DOWN
        elif abs(nifty_return_20d) < 1.0 and india_vix < 14.0:
            regime_code = 4.0  # RANGE_BOUND

        # Risk-on/Risk-off proxy (-1.0 to +1.0)
        risk_on_proxy = 0.5
        if india_vix < 15.0 and advance_decline_ratio > 1.1:
            risk_on_proxy = 0.75
        elif india_vix > 20.0 or advance_decline_ratio < 0.8:
            risk_on_proxy = -0.6

        return {
            "nifty_return_20d": float(round(nifty_return_20d, 2)),
            "nifty_volatility_20d": float(round(nifty_vol_20d, 4)),
            "india_vix": float(round(india_vix, 2)),
            "market_breadth_ad_ratio": float(round(advance_decline_ratio, 2)),
            "market_drawdown_pct": float(round(market_drawdown, 2)),
            "risk_on_risk_off_proxy": float(round(risk_on_proxy, 2)),
            "market_regime_code": float(regime_code),
            "macro_usdinr": float(round(usdinr, 2)),
            "macro_brent_crude": float(round(brent_crude, 2)),
            "macro_repo_rate": float(round(repo_rate, 2)),
        }
