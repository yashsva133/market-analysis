"""Unit tests for deterministic TechnicalSignalEngine."""
import math
from packages.market_data.technical import technical_signal_engine


def test_sma_ema_calculation():
    series = [10.0, 11.0, 12.0, 13.0, 14.0]
    sma = technical_signal_engine.compute_sma(series, period=5)
    assert sma == 12.0

    ema = technical_signal_engine.compute_ema(series, period=3)
    assert ema is not None
    assert round(ema, 2) > 12.0


def test_rsi_calculation():
    # Continual upward trend should yield high RSI (>70)
    up_closes = [100.0 + (i * 2.0) for i in range(25)]
    rsi_high = technical_signal_engine.compute_rsi(up_closes, period=14)
    assert rsi_high is not None
    assert rsi_high > 70.0

    # Continual downward trend should yield low RSI (<30)
    down_closes = [200.0 - (i * 2.0) for i in range(25)]
    rsi_low = technical_signal_engine.compute_rsi(down_closes, period=14)
    assert rsi_low is not None
    assert rsi_low < 30.0


def test_bollinger_bands():
    closes = [100.0] * 20
    bb = technical_signal_engine.compute_bollinger_bands(closes, period=20, std_mult=2.0)
    assert bb is not None
    assert bb["middle"] == 100.0
    assert bb["upper"] == 100.0
    assert bb["lower"] == 100.0


def test_compute_all_signals_structure():
    # 40 days of synthetic candles
    candles = []
    base_price = 1000.0
    for i in range(40):
        c = base_price + (math.sin(i * 0.2) * 20.0)
        candles.append({
            "timestamp": f"2026-08-{i+1:02d}T00:00:00Z" if i < 30 else f"2026-09-{i-29:02d}T00:00:00Z",
            "open": c - 2.0,
            "high": c + 5.0,
            "low": c - 4.0,
            "close": c,
            "volume": 100000 + (i * 5000),
        })

    signals = technical_signal_engine.compute_all_signals(candles, timeframe="1D")
    assert len(signals) >= 8

    # Verify structured signal keys
    indicators = {s["indicator"] for s in signals}
    assert "RSI_14" in indicators
    assert "SMA_20" in indicators
    assert "EMA_9" in indicators
    assert "BOLLINGER_BANDS" in indicators
    assert "VOLUME_SPIKE_20D" in indicators
    assert "HIGH_LOW_52W_DISTANCE" in indicators

    for s in signals:
        assert "indicator" in s
        assert "timeframe" in s
        assert "value" in s
        assert "as_of" in s
        assert s["source"] == "DETERMINISTIC_MATH_ENGINE"
