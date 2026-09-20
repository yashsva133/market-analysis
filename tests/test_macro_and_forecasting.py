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


def test_forecasting_engine_refuses_short_series():
    """A short series cannot support an honest projection; the engine must refuse."""
    with pytest.raises(ValueError):
        ForecastingEngine.forecast(symbol="TEST", prices=[100.0, 101.0, 99.5], horizon=5)


@pytest.mark.asyncio
async def test_lab_event_study_backtest_reports_empty_honestly():
    """With no ingested events, the backtest returns an empty log — never a fabricated one."""
    from unittest.mock import AsyncMock, MagicMock

    req = BacktestRequest(
        strategy_type="EVENT_STUDY_ORDER_WIN",
        holding_period_days=10,
        slippage_pct=0.05,
        fee_pct=0.10,
    )
    mock_db = AsyncMock()
    res = MagicMock()
    res.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=res)

    out = await run_backtest(req, db=mock_db)
    assert out["status"] == "ok"
    assert out["total_events_tested"] == 0
    assert out["trade_log"] == []
    assert "no synthetic trade log" in out["note"]
    assert out["sharpe_ratio"] is None


@pytest.mark.asyncio
async def test_lab_rsi_backtest_requires_symbols():
    """Rule backtests run over specified securities; no default symbol list is invented."""
    from unittest.mock import AsyncMock
    from fastapi import HTTPException

    req = BacktestRequest(strategy_type="RSI_OVERSOLD_REBOUND", symbols=[])
    mock_db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await run_backtest(req, db=mock_db)
    assert exc_info.value.status_code == 400
