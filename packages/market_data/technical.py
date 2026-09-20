"""Deterministic Technical Analysis Signal Engine.

Calculates pure mathematical indicators without LLM involvement:
- SMA (20, 50, 200)
- EMA (9, 21, 50)
- RSI (14)
- MACD (12, 26, 9)
- ATR (14)
- ADX (14)
- Bollinger Bands (20, 2)
- VWAP
- Volume Moving Average (20) & Volume Spike multiple
- 52-Week High/Low distance
- Breakout & Support/Resistance candidates
"""
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional


class TechnicalSignalEngine:
    """Calculates factual mathematical signals over OHLCV series."""

    SOURCE_NAME = "DETERMINISTIC_MATH_ENGINE"

    def compute_all_signals(
        self,
        candles: List[Dict[str, Any]],
        timeframe: str = "1D",
    ) -> List[Dict[str, Any]]:
        """Computes comprehensive suite of indicators from an OHLCV candle list (ordered chronologically)."""
        if not candles or len(candles) < 5:
            return []

        closes = [float(c["close"]) for c in candles]
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        volumes = [float(c.get("volume", 0)) for c in candles]
        now_iso = datetime.now(timezone.utc).isoformat()
        current_close = closes[-1]

        signals = []

        # 1. RSI (14)
        rsi_14 = self.compute_rsi(closes, period=14)
        if rsi_14 is not None:
            signals.append({
                "indicator": "RSI_14",
                "timeframe": timeframe,
                "value": round(rsi_14, 2),
                "as_of": now_iso,
                "source": self.SOURCE_NAME,
                "metadata": {
                    "interpretation": "Oversold (<30)" if rsi_14 < 30 else ("Overbought (>70)" if rsi_14 > 70 else "Neutral range (30-70)")
                }
            })

        # 2. Moving Averages (SMA & EMA)
        for p in [20, 50, 200]:
            sma = self.compute_sma(closes, period=p)
            if sma is not None:
                signals.append({
                    "indicator": f"SMA_{p}",
                    "timeframe": timeframe,
                    "value": round(sma, 2),
                    "as_of": now_iso,
                    "source": self.SOURCE_NAME,
                    "metadata": {
                        "price_vs_sma_pct": round((current_close - sma) / sma * 100, 2)
                    }
                })

        for p in [9, 21, 50]:
            ema = self.compute_ema(closes, period=p)
            if ema is not None:
                signals.append({
                    "indicator": f"EMA_{p}",
                    "timeframe": timeframe,
                    "value": round(ema, 2),
                    "as_of": now_iso,
                    "source": self.SOURCE_NAME,
                    "metadata": {
                        "price_vs_ema_pct": round((current_close - ema) / ema * 100, 2)
                    }
                })

        # 3. MACD (12, 26, 9)
        macd = self.compute_macd(closes)
        if macd is not None:
            signals.append({
                "indicator": "MACD",
                "timeframe": timeframe,
                "value": round(macd["macd"], 2),
                "as_of": now_iso,
                "source": self.SOURCE_NAME,
                "metadata": {
                    "signal_line": round(macd["signal"], 2),
                    "histogram": round(macd["histogram"], 2),
                    "cross": "BULLISH_CROSS" if macd["histogram"] > 0 else "BEARISH_CROSS",
                }
            })

        # 4. Bollinger Bands (20, 2)
        bb = self.compute_bollinger_bands(closes, period=20, std_mult=2.0)
        if bb is not None:
            signals.append({
                "indicator": "BOLLINGER_BANDS",
                "timeframe": timeframe,
                "value": round(bb["middle"], 2),
                "as_of": now_iso,
                "source": self.SOURCE_NAME,
                "metadata": {
                    "upper": round(bb["upper"], 2),
                    "lower": round(bb["lower"], 2),
                    "bandwidth": round(bb["bandwidth"], 2),
                    "percent_b": round(bb["percent_b"], 2),
                }
            })

        # 5. ATR (14)
        atr = self.compute_atr(highs, lows, closes, period=14)
        if atr is not None:
            signals.append({
                "indicator": "ATR_14",
                "timeframe": timeframe,
                "value": round(atr, 2),
                "as_of": now_iso,
                "source": self.SOURCE_NAME,
                "metadata": {
                    "atr_pct_of_price": round((atr / current_close) * 100, 2)
                }
            })

        # 6. ADX (14)
        adx = self.compute_adx(highs, lows, closes, period=14)
        if adx is not None:
            signals.append({
                "indicator": "ADX_14",
                "timeframe": timeframe,
                "value": round(adx["adx"], 2),
                "as_of": now_iso,
                "source": self.SOURCE_NAME,
                "metadata": {
                    "plus_di": round(adx["plus_di"], 2),
                    "minus_di": round(adx["minus_di"], 2),
                    "trend_strength": "Strong trend (>25)" if adx["adx"] >= 25 else "Weak/Consolidation (<25)",
                }
            })

        # 7. VWAP
        vwap = self.compute_vwap(highs, lows, closes, volumes)
        if vwap is not None:
            signals.append({
                "indicator": "VWAP",
                "timeframe": timeframe,
                "value": round(vwap, 2),
                "as_of": now_iso,
                "source": self.SOURCE_NAME,
                "metadata": {
                    "price_vs_vwap_pct": round((current_close - vwap) / vwap * 100, 2)
                }
            })

        # 8. Volume Moving Average (20) & Volume Spike
        vol_sma_20 = self.compute_sma(volumes, period=min(20, len(volumes)))
        if vol_sma_20 and vol_sma_20 > 0:
            current_vol = volumes[-1]
            spike_ratio = current_vol / vol_sma_20
            signals.append({
                "indicator": "VOLUME_SPIKE_20D",
                "timeframe": timeframe,
                "value": round(spike_ratio, 2),
                "as_of": now_iso,
                "source": self.SOURCE_NAME,
                "metadata": {
                    "avg_volume_20d": int(vol_sma_20),
                    "current_volume": int(current_vol),
                    "is_spike": spike_ratio >= 2.0,
                }
            })

        # 9. 52-Week High/Low Distance (or max available period)
        lookback = min(len(highs), 252)
        h52 = max(highs[-lookback:])
        l52 = min(lows[-lookback:])
        dist_h = round((current_close - h52) / h52 * 100, 2)
        dist_l = round((current_close - l52) / l52 * 100, 2)
        signals.append({
            "indicator": "HIGH_LOW_52W_DISTANCE",
            "timeframe": timeframe,
            "value": dist_h,
            "as_of": now_iso,
            "source": self.SOURCE_NAME,
            "metadata": {
                "high_52w": h52,
                "low_52w": l52,
                "distance_from_high_pct": dist_h,
                "distance_from_low_pct": dist_l,
            }
        })

        # 10. Breakouts and Support/Resistance Candidates
        sr = self.compute_support_resistance(highs, lows, closes)
        signals.append({
            "indicator": "SUPPORT_RESISTANCE",
            "timeframe": timeframe,
            "value": current_close,
            "as_of": now_iso,
            "source": self.SOURCE_NAME,
            "metadata": sr,
        })

        return signals

    def compute_sma(self, series: List[float], period: int) -> Optional[float]:
        if len(series) < period:
            return None
        return sum(series[-period:]) / period

    def compute_ema(self, series: List[float], period: int) -> Optional[float]:
        if len(series) < period:
            return None
        k = 2 / (period + 1)
        # Seed with SMA of first period items
        ema = sum(series[:period]) / period
        for val in series[period:]:
            ema = (val * k) + (ema * (1 - k))
        return ema

    def compute_rsi(self, closes: List[float], period: int = 14) -> Optional[float]:
        if len(closes) < period + 1:
            return None

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(d, 0.0) for d in deltas]
        losses = [abs(min(d, 0.0)) for d in deltas]

        # Initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Wilder's smoothing
        for i in range(period, len(deltas)):
            avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def compute_macd(self, closes: List[float]) -> Optional[Dict[str, float]]:
        if len(closes) < 26 + 9:
            return None

        ema_12 = self.compute_ema(closes, 12)
        ema_26 = self.compute_ema(closes, 26)
        if ema_12 is None or ema_26 is None:
            return None

        # Calculate MACD line series to get 9-period signal EMA
        macd_series = []
        k12 = 2 / 13
        k26 = 2 / 27
        e12 = sum(closes[:12]) / 12
        for c in closes[12:26]:
            e12 = (c * k12) + (e12 * (1 - k12))
        e26 = sum(closes[:26]) / 26
        macd_series.append(e12 - e26)

        for c in closes[26:]:
            e12 = (c * k12) + (e12 * (1 - k12))
            e26 = (c * k26) + (e26 * (1 - k26))
            macd_series.append(e12 - e26)

        macd_val = macd_series[-1]
        signal_val = self.compute_ema(macd_series, 9) or macd_val
        histogram = macd_val - signal_val

        return {
            "macd": macd_val,
            "signal": signal_val,
            "histogram": histogram,
        }

    def compute_bollinger_bands(self, closes: List[float], period: int = 20, std_mult: float = 2.0) -> Optional[Dict[str, float]]:
        if len(closes) < period:
            return None

        slice_closes = closes[-period:]
        mean = sum(slice_closes) / period
        variance = sum((x - mean) ** 2 for x in slice_closes) / period
        std_dev = math.sqrt(variance)

        upper = mean + (std_mult * std_dev)
        lower = mean - (std_mult * std_dev)
        bandwidth = ((upper - lower) / mean) * 100 if mean > 0 else 0.0
        percent_b = ((closes[-1] - lower) / (upper - lower)) if (upper - lower) > 0 else 0.5

        return {
            "middle": mean,
            "upper": upper,
            "lower": lower,
            "bandwidth": bandwidth,
            "percent_b": percent_b,
        }

    def compute_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
        if len(closes) < period + 1:
            return None

        tr_list = []
        for i in range(1, len(closes)):
            h = highs[i]
            l = lows[i]
            prev_c = closes[i - 1]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)

        atr = sum(tr_list[:period]) / period
        for tr in tr_list[period:]:
            atr = ((atr * (period - 1)) + tr) / period
        return atr

    def compute_adx(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[Dict[str, float]]:
        if len(closes) < (period * 2):
            return None

        plus_dm_list = []
        minus_dm_list = []
        tr_list = []

        for i in range(1, len(closes)):
            up_move = highs[i] - highs[i - 1]
            down_move = lows[i - 1] - lows[i]

            plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
            minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
            tr_list.append(tr)

        smooth_tr = sum(tr_list[:period])
        smooth_plus_dm = sum(plus_dm_list[:period])
        smooth_minus_dm = sum(minus_dm_list[:period])

        dx_list = []
        for i in range(period, len(tr_list)):
            smooth_tr = smooth_tr - (smooth_tr / period) + tr_list[i]
            smooth_plus_dm = smooth_plus_dm - (smooth_plus_dm / period) + plus_dm_list[i]
            smooth_minus_dm = smooth_minus_dm - (smooth_minus_dm / period) + minus_dm_list[i]

            plus_di = (smooth_plus_dm / smooth_tr) * 100 if smooth_tr > 0 else 0.0
            minus_di = (smooth_minus_dm / smooth_tr) * 100 if smooth_tr > 0 else 0.0
            di_sum = plus_di + minus_di
            dx = (abs(plus_di - minus_di) / di_sum * 100) if di_sum > 0 else 0.0
            dx_list.append(dx)

        if len(dx_list) < period:
            return None

        adx = sum(dx_list[:period]) / period
        for dx in dx_list[period:]:
            adx = ((adx * (period - 1)) + dx) / period

        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
        }

    def compute_vwap(self, highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> Optional[float]:
        total_vp = 0.0
        total_vol = 0.0
        for h, l, c, v in zip(highs, lows, closes, volumes):
            typical_price = (h + l + c) / 3
            total_vp += typical_price * v
            total_vol += v
        return (total_vp / total_vol) if total_vol > 0 else None

    def compute_support_resistance(self, highs: List[float], lows: List[float], closes: List[float]) -> Dict[str, Any]:
        """Calculates standard pivot points and 20-day high/low breakout bounds."""
        last_h = highs[-1]
        last_l = lows[-1]
        last_c = closes[-1]
        pivot = (last_h + last_l + last_c) / 3
        r1 = (2 * pivot) - last_l
        s1 = (2 * pivot) - last_h
        r2 = pivot + (last_h - last_l)
        s2 = pivot - (last_h - last_l)

        lookback = min(20, len(highs))
        highest_20d = max(highs[-lookback:])
        lowest_20d = min(lows[-lookback:])

        is_breakout_high = last_c >= highest_20d
        is_breakdown_low = last_c <= lowest_20d

        return {
            "pivot": round(pivot, 2),
            "resistance_1": round(r1, 2),
            "resistance_2": round(r2, 2),
            "support_1": round(s1, 2),
            "support_2": round(s2, 2),
            "breakout_high_20d": round(highest_20d, 2),
            "breakdown_low_20d": round(lowest_20d, 2),
            "is_20d_breakout_high": is_breakout_high,
            "is_20d_breakdown_low": is_breakdown_low,
        }


technical_signal_engine = TechnicalSignalEngine()
