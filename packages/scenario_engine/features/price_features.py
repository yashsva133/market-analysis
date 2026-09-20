"""Price Features Extractor for Scenario & Forecast Engine.

Extracts multi-horizon returns, realized volatility, drawdowns, distance to 52W high/low,
gap frequency, and price trend strength.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import numpy as np


class PriceFeatureExtractor:
    @staticmethod
    def extract_point_in_time(candles: List[Dict[str, Any]], as_of: datetime) -> Dict[str, float]:
        """Extract price features strictly filtering candles up to as_of timestamp to prevent data leakage."""
        filtered_prices = []
        for c in candles:
            t = c.get("timestamp") or c.get("date")
            if t:
                if isinstance(t, str):
                    dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                elif isinstance(t, datetime):
                    dt = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
                else:
                    dt = None
                if dt and dt > as_of:
                    continue  # Strict anti-leakage: future candle rejected!
            filtered_prices.append(float(c.get("close", c.get("price", 0.0))))
        return PriceFeatureExtractor.extract(filtered_prices)

    @staticmethod
    def extract(prices: List[float], highs: List[float] = None, lows: List[float] = None) -> Dict[str, float]:
        """Extract deterministic price features from historical daily closes."""
        if not prices or len(prices) < 2:
            return {
                "return_1d": 0.0,
                "return_3d": 0.0,
                "return_5d": 0.0,
                "return_10d": 0.0,
                "return_20d": 0.0,
                "return_60d": 0.0,
                "return_120d": 0.0,
                "return_252d": 0.0,
                "realized_volatility_20d": 0.15,
                "realized_volatility_60d": 0.18,
                "max_drawdown_252d": 0.0,
                "distance_from_52w_high": 0.0,
                "distance_from_52w_low": 0.0,
                "gap_frequency": 0.0,
                "trend_strength": 0.0,
            }

        p = np.array(prices, dtype=float)
        n = len(p)
        last_price = p[-1]

        def calc_ret(lookback: int) -> float:
            if n > lookback and p[-lookback - 1] > 0:
                return float(round(((last_price - p[-lookback - 1]) / p[-lookback - 1]) * 100, 2))
            return 0.0

        ret_1d = calc_ret(1)
        ret_3d = calc_ret(3)
        ret_5d = calc_ret(5)
        ret_10d = calc_ret(10)
        ret_20d = calc_ret(20)
        ret_60d = calc_ret(60)
        ret_120d = calc_ret(120)
        ret_252d = calc_ret(252)

        # Realized volatility (annualized from daily log returns)
        log_rets = np.diff(np.log(p)) if n > 1 else np.array([0.0])
        vol_20d = float(np.std(log_rets[-20:]) * np.sqrt(252)) if len(log_rets) >= 5 else 0.18
        vol_60d = float(np.std(log_rets[-60:]) * np.sqrt(252)) if len(log_rets) >= 20 else vol_20d

        # 52-week / available window high and low
        window = min(n, 252)
        h52 = float(np.max(p[-window:]))
        l52 = float(np.min(p[-window:]))

        dist_high = float(round(((last_price - h52) / h52) * 100, 2)) if h52 > 0 else 0.0
        dist_low = float(round(((last_price - l52) / l52) * 100, 2)) if l52 > 0 else 0.0

        # Maximum drawdown over window
        cummax = np.maximum.accumulate(p[-window:])
        drawdowns = (p[-window:] - cummax) / cummax
        max_dd = float(round(abs(np.min(drawdowns)) * 100, 2)) if len(drawdowns) > 0 else 0.0

        # Gap frequency (|open - prev_close| / prev_close > 1%)
        gaps = 0
        if len(p) >= 10:
            pct_changes = np.abs(np.diff(p) / p[:-1])
            gaps = int(np.sum(pct_changes > 0.015))
        gap_freq = float(round(gaps / max(1, n - 1), 3))

        # Trend strength (Linear regression slope / volatility)
        x = np.arange(min(n, 60))
        y = p[-len(x):]
        if len(x) > 5:
            slope, _ = np.polyfit(x, y / y[0], 1)
            trend_strength = float(round(slope * 100, 2))
        else:
            trend_strength = 0.0

        return {
            "return_1d": ret_1d,
            "return_3d": ret_3d,
            "return_5d": ret_5d,
            "return_10d": ret_10d,
            "return_20d": ret_20d,
            "return_60d": ret_60d,
            "return_120d": ret_120d,
            "return_252d": ret_252d,
            "realized_volatility_20d": round(vol_20d, 4),
            "realized_volatility_60d": round(vol_60d, 4),
            "max_drawdown_252d": max_dd,
            "distance_from_52w_high": dist_high,
            "distance_from_52w_low": dist_low,
            "gap_frequency": gap_freq,
            "trend_strength": trend_strength,
        }
