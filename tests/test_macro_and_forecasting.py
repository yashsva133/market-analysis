"""Tests for Macroeconomic Context and Forecasting Engine."""
import pytest
from apps.api.routers.macro import get_macro_indicators
from apps.api.routers.lab import run_backtest, BacktestRequest
from packages.market_data.forecasting import ForecastingEngine


@pytest.mark.asyncio
async def test_macro_indicators_grounded():
    """No macro feed is ingested, so the endpoint reports zero indicators instead of fabricated values."""
    res = await get_macro_indicators()
    assert res["status"] == "ok"
    assert res["count"] == 0
    assert res["indicators"] == []
    assert "not fabricated" in res["note"] or "No macroeconomic data feed" in res["note"]


def test_forecasting_engine_holt_winters():
    prices = [100.0 + i * 1.5 + (i % 3) for i in range(25)]
    fc = ForecastingEngine.forecast(symbol="TEST", prices=prices, horizon=5)

    assert fc.symbol == "TEST"
    assert fc.forecast_horizon == 5
    assert len(fc.points) == 5
    assert fc.last_known_price > 0
    assert fc.in_sample_mape_pct >= 0
    assert "STATISTICAL PROJECTION" in fc.disclaimer
    # Bounds should encompass projection
    for p in fc.points:
        assert p.lower_bound_80 <= p.projected_price <= p.upper_bound_80
        assert p.lower_bound_95 <= p.lower_bound_80


@pytest.mark.asyncio
async def test_lab_event_study_backtest():
    req = BacktestRequest(
        strategy_type="EVENT_STUDY_ORDER_WIN",
        holding_period_days=10,
        slippage_pct=0.05,
        fee_pct=0.10,
    )
    res = await run_backtest(req)
    assert res["status"] == "ok"
    assert res["total_events_tested"] > 0
    assert "sharpe_ratio" in res
    assert "sortino_ratio" in res
    assert "max_drawdown_pct" in res
    assert len(res["trade_log"]) > 0
    assert "disclaimer" in res
