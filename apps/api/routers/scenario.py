"""Scenario, Capital Simulation, and Quantitative Forecasting Router.

Implements Section 83 endpoints:
- POST /api/scenario/analyze & POST /scenario/analyze
- GET /api/scenario/{id} & GET /scenario/{id}
- POST /api/scenario/batch & POST /scenario/batch
- GET /api/forecast/{security_id} & GET /forecast/{security_id}
- GET /api/probabilities/{security_id} & GET /probabilities/{security_id}
- POST /api/capital/simulate & POST /capital/simulate
- POST /api/portfolio/optimize & POST /portfolio/optimize
- GET /api/quant/events & GET /quant/events
- GET /api/quant/backtests & GET /quant/backtests
- GET /api/sectors & GET /sectors
"""
from typing import Dict, Any, List, Optional, Union
import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from packages.scenario_engine import (
    global_scenario_orchestrator,
    CapitalAllocationEngine,
    ComparableEventEngine,
    MonteCarloSimulator,
)

router = APIRouter(tags=["scenario"])

# In-memory session cache for persistent scenario run retrieval
_scenario_runs_cache: Dict[str, Dict[str, Any]] = {}


async def _fetch_price_history(symbol: str, period: str = "1y") -> Optional[List[float]]:
    """Fetch real historical daily close prices for an NSE symbol via Yahoo Finance.

    Returns None when the feed is unreachable or the symbol is invalid — the
    scenario engine never fabricates a price series.
    """
    clean = symbol.upper().replace("&", "").strip()
    ticker = f"{clean}.NS"
    try:
        import yfinance as yf
        loop = asyncio.get_running_loop()

        def fetch():
            t = yf.Ticker(ticker)
            hist = t.history(period=period, interval="1d")
            closes = [float(x) for x in hist["Close"].tolist() if x is not None and float(x) > 0]
            return closes

        closes = await asyncio.wait_for(loop.run_in_executor(None, fetch), timeout=12.0)
        if closes and len(closes) >= 5:
            return closes
    except Exception:
        pass
    return None


def _data_unavailable_response(symbol: str) -> Dict[str, Any]:
    """Structured degraded response when no real price history is available."""
    return {
        "status": "DATA_UNAVAILABLE",
        "symbol": symbol.upper(),
        "message": "No real price history is available for this symbol. The scenario engine does not fabricate prices or forecasts.",
        "fallback": "Provide a valid NSE/BSE symbol and retry when market data is reachable.",
    }


def resolve_horizon_days(horizon_days: Optional[int], horizon: Optional[Any]) -> int:
    """Deterministically map user-facing horizon formats ('5D', '1M', '3M', '5M', '6M', '1Y') or raw ints to session count."""
    if horizon_days and horizon_days > 0:
        return horizon_days
    if horizon is not None:
        if isinstance(horizon, int) and horizon > 0:
            return horizon
        if isinstance(horizon, str):
            h_str = horizon.upper().strip()
            mapping = {
                "5D": 5, "10D": 10, "20D": 20,
                "1M": 21, "2M": 42, "3M": 63, "4M": 84, "5M": 105, "6M": 126,
                "9M": 189, "12M": 252, "1Y": 252, "2Y": 504
            }
            if h_str in mapping:
                return mapping[h_str]
            if h_str.endswith("D") and h_str[:-1].isdigit():
                return int(h_str[:-1])
            if h_str.endswith("M") and h_str[:-1].isdigit():
                return int(h_str[:-1]) * 21
            if h_str.isdigit():
                return int(h_str)
    return 63


class ScenarioAnalyzeRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g. RELIANCE, LT, TCS)")
    capital: float = Field(default=100000.0, description="Available cash capital in INR")
    horizon_days: Optional[int] = Field(default=None, description="Trading session horizon (e.g. 5, 10, 20, 21, 63, 105, 126, 252)")
    horizon: Optional[Union[str, int]] = Field(default=None, description="Horizon string (e.g. '1M', '3M', '5M', '6M', '12M') or int")
    target_price: Optional[float] = Field(default=None, description="Target price level in INR")
    stop_price: Optional[float] = Field(default=None, description="Stop-loss price level in INR")
    stop_loss: Optional[float] = Field(default=None, description="Alias for stop_price")
    sector: Optional[str] = Field(default=None, description="Optional sector override")
    benchmark: Optional[str] = Field(default="NIFTY 50", description="Benchmark index")


class CapitalSimulateRequest(BaseModel):
    symbol: str
    capital: float = Field(default=50000.0)
    current_price: Optional[float] = None
    target_price: Optional[float] = None
    horizon_days: int = Field(default=60)


class PortfolioOptimizeRequest(BaseModel):
    symbols: List[str] = Field(default=["LT", "RELIANCE", "TCS", "INFY", "HDFCBANK"])
    capital: float = Field(default=1000000.0)
    method: str = Field(default="RISK_PARITY", description="EQUAL_WEIGHT, RISK_PARITY, MINIMUM_VARIANCE, MEAN_VARIANCE, CVAR_OPTIMIZATION")
    max_single_weight: float = Field(default=0.30)
    min_cash_pct: float = Field(default=0.05)


@router.post("/scenario/analyze")
@router.post("/api/scenario/analyze")
async def analyze_scenario(req: ScenarioAnalyzeRequest):
    """Run full scenario analysis, forecasting, probability calibration, and capital simulation."""
    days = resolve_horizon_days(req.horizon_days, req.horizon)
    stop_p = req.stop_price if req.stop_price is not None else req.stop_loss

    prices = await _fetch_price_history(req.symbol)
    if not prices:
        return _data_unavailable_response(req.symbol)

    try:
        res = global_scenario_orchestrator.run_full_scenario_analysis(
            symbol=req.symbol,
            capital_inr=req.capital,
            horizon_days=days,
            target_price=req.target_price,
            stop_price=stop_p,
            sector_name=req.sector,
            prices=prices,
        )
    except ValueError as exc:
        return _data_unavailable_response(req.symbol)

    _scenario_runs_cache[res["scenario_run_id"]] = res
    return res


@router.post("/scenario/council")
@router.post("/api/scenario/council")
async def evaluate_council(req: ScenarioAnalyzeRequest):
    """Run Multi-Agent Decision Council deliberation (4 Specialist Agents + Council Chief)."""
    days = resolve_horizon_days(req.horizon_days, req.horizon)
    stop_p = req.stop_price if req.stop_price is not None else req.stop_loss
    prices = await _fetch_price_history(req.symbol)
    if not prices:
        return _data_unavailable_response(req.symbol)
    res = global_scenario_orchestrator.run_full_scenario_analysis(
        symbol=req.symbol,
        capital_inr=req.capital,
        horizon_days=days,
        target_price=req.target_price,
        stop_price=stop_p,
        sector_name=req.sector,
        prices=prices,
    )
    _scenario_runs_cache[res["scenario_run_id"]] = res
    return {
        "status": "ok",
        "symbol": req.symbol.upper(),
        "decision_council": res["decision_council"],
        "model_comparison": res["model_comparison"],
        "execution_position": res["execution_position"],
    }


@router.post("/scenario/compare-models")
@router.post("/api/scenario/compare-models")
async def compare_forecasting_models(req: ScenarioAnalyzeRequest):
    """Head-to-head comparison: Amazon Chronos-2 vs Google TimesFM 3.0 vs Tabular ML."""
    days = resolve_horizon_days(req.horizon_days, req.horizon)
    prices = await _fetch_price_history(req.symbol)
    if not prices:
        return _data_unavailable_response(req.symbol)
    res = global_scenario_orchestrator.run_full_scenario_analysis(
        symbol=req.symbol,
        horizon_days=days,
        target_price=req.target_price,
        prices=prices,
    )
    return {
        "status": "ok",
        "symbol": req.symbol.upper(),
        "horizon_days": req.horizon_days,
        "current_price": res["inputs"]["current_price"],
        "model_comparison": res["model_comparison"],
        "chronos_forecast": res["forecast_distribution"],
        "timesfm_forecast": res["timesfm_forecast"],
        "probabilities": res["target_probabilities"],
    }


@router.get("/scenario/{id}")
@router.get("/api/scenario/{id}")
async def get_scenario_run(id: str):
    """Retrieve previously executed scenario analysis run by ID."""
    run = _scenario_runs_cache.get(id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail="Scenario run not found. Runs are cached in memory after /scenario/analyze; re-run the analysis.",
        )
    return run


@router.post("/scenario/batch")
@router.post("/api/scenario/batch")
async def batch_scenario(symbols: List[str] = Query(default=["RELIANCE", "LT", "TCS"])):
    """Run batch scenario analysis across multiple symbols."""
    results = []
    for s in symbols[:5]:
        prices = await _fetch_price_history(s)
        if not prices:
            results.append({"symbol": s, "status": "DATA_UNAVAILABLE"})
            continue
        res = global_scenario_orchestrator.run_full_scenario_analysis(symbol=s, prices=prices)
        _scenario_runs_cache[res["scenario_run_id"]] = res
        results.append({
            "symbol": s,
            "current_price": res["inputs"]["current_price"],
            "target_touch_prob": res["target_probabilities"]["calibrated_p_target_touched"],
            "p_loss": res["downside_probabilities"]["p_loss_overall"],
            "base_median": res["scenarios"]["base"]["price_median"],
        })
    return {"status": "ok", "count": len(results), "batch": results}


@router.get("/forecast/{security_id}")
@router.get("/api/forecast/{security_id}")
async def get_security_forecast(security_id: str, horizon: int = Query(default=20, ge=1, le=252)):
    """Get multi-step forecast distribution and fan chart for security."""
    prices = await _fetch_price_history(security_id)
    if not prices:
        return _data_unavailable_response(security_id)
    res = global_scenario_orchestrator.run_full_scenario_analysis(
        symbol=security_id,
        horizon_days=horizon,
        prices=prices,
    )
    return {
        "symbol": security_id.upper(),
        "horizon_days": horizon,
        "current_price": res["inputs"]["current_price"],
        "forecast_distribution": res["forecast_distribution"],
        "fan_chart": res["fan_chart"],
        "baselines": res["model_metadata"],
    }


@router.get("/probabilities/{security_id}")
@router.get("/api/probabilities/{security_id}")
async def get_security_probabilities(
    security_id: str,
    target: Optional[float] = Query(default=None),
    horizon: int = Query(default=20),
):
    """Retrieve calibrated target touch, finish above, and downside probabilities."""
    prices = await _fetch_price_history(security_id)
    if not prices:
        return _data_unavailable_response(security_id)
    res = global_scenario_orchestrator.run_full_scenario_analysis(
        symbol=security_id,
        target_price=target,
        horizon_days=horizon,
        prices=prices,
    )
    return {
        "symbol": security_id.upper(),
        "target_price": res["inputs"]["target_price"],
        "horizon_days": horizon,
        "probabilities": res["target_probabilities"],
        "downside_risk": res["downside_probabilities"],
        "calibration": res["model_metadata"],
    }


@router.post("/capital/simulate")
@router.post("/api/capital/simulate")
async def simulate_capital(req: CapitalSimulateRequest):
    """Execute whole-share Indian equity capital simulation."""
    prices = await _fetch_price_history(req.symbol)
    if not prices:
        return _data_unavailable_response(req.symbol)
    res = global_scenario_orchestrator.run_full_scenario_analysis(
        symbol=req.symbol,
        capital_inr=req.capital,
        target_price=req.target_price,
        horizon_days=req.horizon_days,
        prices=prices,
    )
    return {
        "execution": res["execution_position"],
        "scenarios_capital_outcomes": res["capital_outcomes"],
        "quantile_outcomes": res["quantile_capital_outcomes"],
        "expected_value": res["model_implied_expected_value"],
    }


@router.post("/portfolio/optimize")
@router.post("/api/portfolio/optimize")
async def optimize_portfolio(req: PortfolioOptimizeRequest):
    """Run deterministic portfolio optimization (Equal Weight, Risk Parity, Min Variance, etc.).

    Prices and returns are derived from real historical data; no hardcoded or
    synthetic price/return series is substituted.
    """
    px: Dict[str, float] = {}
    rets: Dict[str, List[float]] = {}
    for s in req.symbols:
        closes = await _fetch_price_history(s)
        if not closes:
            continue
        px[s] = closes[-1]
        rets[s] = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
        ]

    if not px:
        return {
            "status": "DATA_UNAVAILABLE",
            "message": "No real price history available for the requested symbols. Portfolio optimization requires real market data.",
        }

    result = CapitalAllocationEngine.optimize(
        symbols=list(px.keys()),
        prices=px,
        historical_returns=rets,
        capital=req.capital,
        method=req.method,
        max_single_weight=req.max_single_weight,
        min_cash_pct=req.min_cash_pct,
        sectors=None,
    )
    return result


@router.get("/quant/events")
@router.get("/api/quant/events")
async def get_quant_events(event_type: str = Query(default="ORDER_WIN"), sector: Optional[str] = None):
    """Retrieve empirical comparable event studies and reaction statistics (§37, §38)."""
    return ComparableEventEngine.find_comparables(event_type=event_type, sector=sector)


@router.get("/quant/backtests")
@router.get("/api/quant/backtests")
async def get_quant_backtests():
    """Backtest records are not persisted yet; report that honestly instead of serving canned stats."""
    return {
        "status": "ok",
        "active_backtests": [],
        "note": "No backtest runs are persisted in this deployment. Execute a study via the quant lab and persist results to serve them here.",
    }


@router.get("/sectors")
@router.get("/api/sectors")
async def get_sectors():
    """Retrieve performance, event intensity, and valuation across major Indian sectors.

    Sector-level aggregates are not persisted in this deployment, so no
    hardcoded sector statistics are served.
    """
    return {
        "status": "UNAVAILABLE",
        "sectors": [],
        "note": "Sector-level aggregates are not persisted in this deployment. No hardcoded sector statistics are served.",
    }
