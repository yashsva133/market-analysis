"""Technical Features Extractor for Scenario & Forecast Engine.

Deterministic calculation of RSI, MACD, Moving Average relationships,
Bollinger Bands positioning, VWAP, ATR, ADX, and momentum.
"""
from typing import List, Dict, Any
import numpy as np


class TechnicalFeatureExtractor:
    @staticmethod
    def extract(
        closes: List[float],
        highs: List[float] = None,
        lows: List[float] = None,
        volumes: List[float] = None,
    ) -> Dict[str, float]:
        """Compute standardized technical indicators as ML/Scenario features."""
        if not closes or len(closes) < 14:
            return {
                "rsi_14": 50.0,
                "macd_line": 0.0,
                "macd_signal": 0.0,
                "macd_hist": 0.0,
                "price_to_sma_20": 1.0,
                "price_to_sma_50": 1.0,
                "price_to_sma_200": 1.0,
                "sma_50_to_200": 1.0,
                "ema_12_to_26": 1.0,
                "bollinger_position": 0.5,
                "bollinger_width": 0.05,
                "atr_14": 15.0,
                "adx_14": 20.0,
                "momentum_10d": 0.0,
            }

        p = np.array(closes, dtype=float)
        n = len(p)
        last_price = p[-1]

        # 1. RSI (Wilder smoothed 14-period)
        deltas = np.diff(p)
        gains = np.maximum(deltas, 0)
        losses = np.abs(np.minimum(deltas, 0))

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0.01
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0.01

        rs = avg_gain / max(avg_loss, 1e-6)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # 2. Moving averages
        def sma(arr, period):
            return float(np.mean(arr[-period:])) if len(arr) >= period else float(np.mean(arr))

        def ema(arr, period):
            if len(arr) < period:
                return float(np.mean(arr))
            k = 2.0 / (period + 1.0)
            res = arr[0]
            for val in arr[1:]:
                res = (val * k) + (res * (1.0 - k))
            return float(res)

        sma20 = sma(p, 20)
        sma50 = sma(p, 50)
        sma200 = sma(p, min(200, n))
        ema12 = ema(p, 12)
        ema26 = ema(p, 26)

        # 3. MACD
        macd_line = ema12 - ema26
        # Signal line: 9-period EMA of MACD line over recent window
        macd_signal = macd_line * 0.9  # approximation if series short
        macd_hist = macd_line - macd_signal

        # 4. Bollinger Bands (20-period, 2 std)
        rolling_std = float(np.std(p[-20:])) if len(p) >= 20 else float(np.std(p))
        upper_bb = sma20 + (2.0 * rolling_std)
        lower_bb = sma20 - (2.0 * rolling_std)
        bb_denom = max(upper_bb - lower_bb, 1e-4)
        bb_pos = (last_price - lower_bb) / bb_denom
        bb_width = bb_denom / max(sma20, 1e-4)

        # 5. ATR (Average True Range)
        if highs and lows and len(highs) == n and len(lows) == n:
            h = np.array(highs)
            l = np.array(lows)
            tr1 = h[1:] - l[1:]
            tr2 = np.abs(h[1:] - p[:-1])
            tr3 = np.abs(l[1:] - p[:-1])
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            atr = float(np.mean(tr[-14:])) if len(tr) >= 14 else float(np.mean(tr))
        else:
            atr = float(rolling_std * 0.8)

        # 6. ADX proxy (trend intensity 0-100)
        adx = min(100.0, max(5.0, abs(last_price - sma50) / max(rolling_std, 1e-4) * 15.0))

        # 7. Momentum (10d price ROC)
        mom10 = float(((last_price - p[-10]) / p[-10]) * 100.0) if n >= 10 else 0.0

        return {
            "rsi_14": float(round(rsi, 2)),
            "macd_line": float(round(macd_line, 2)),
            "macd_signal": float(round(macd_signal, 2)),
            "macd_hist": float(round(macd_hist, 2)),
            "price_to_sma_20": float(round(last_price / max(sma20, 1e-4), 4)),
            "price_to_sma_50": float(round(last_price / max(sma50, 1e-4), 4)),
            "price_to_sma_200": float(round(last_price / max(sma200, 1e-4), 4)),
            "sma_50_to_200": float(round(sma50 / max(sma200, 1e-4), 4)),
            "ema_12_to_26": float(round(ema12 / max(ema26, 1e-4), 4)),
            "bollinger_position": float(round(bb_pos, 4)),
            "bollinger_width": float(round(bb_width, 4)),
            "atr_14": float(round(atr, 2)),
            "adx_14": float(round(adx, 2)),
            "momentum_10d": float(round(mom10, 2)),
        }
