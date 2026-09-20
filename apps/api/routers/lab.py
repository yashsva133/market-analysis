"""Research Lab & Deterministic Backtesting Router.

Event-study and rule backtests computed strictly from ingested events and
real historical candles fetched from the active market data provider. No
pre-computed trade logs and no synthetic price series: when there is no
ingested evidence or candle history, the endpoint says so. Strictly
non-advisory and non-predictive. No automated trading execution.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.common.database import get_db
from packages.common.models import Company, Event, Security
from packages.market_data.forecasting import ForecastingEngine, ForecastResult
from packages.market_data.manager import market_data_manager

router = APIRouter(prefix="/api/lab", tags=["lab"])

# Event-type SQL patterns per event-study strategy
STRATEGY_EVENT_PATTERNS: Dict[str, List[str]] = {
    "EVENT_STUDY_ORDER_WIN": ["%ORDER%", "%CONTRACT%"],
    "EARNINGS_BEAT": ["%EARNINGS%", "%RESULTS%", "%PROFIT%"],
}

DISCLAIMER = (
    "HISTORICAL OBSERVATION COMPUTED FROM INGESTED EVENTS AND REAL CANDLES. "
    "PAST STATISTICAL PERFORMANCE DOES NOT GUARANTEE FUTURE RESULTS. NO LIVE TRADING ORDERS."
)


class BacktestRequest(BaseModel):
    strategy_type: str = Field(
        description="EVENT_STUDY_ORDER_WIN, EARNINGS_BEAT, or RSI_OVERSOLD_REBOUND"
    )
    symbols: List[str] = Field(
        default_factory=list,
        description="Optional symbol filter. Required for RSI_OVERSOLD_REBOUND.",
    )
    holding_period_days: int = Field(default=10, ge=1, le=60)
    slippage_pct: float = Field(default=0.05, description="Slippage per round-trip trade")
    fee_pct: float = Field(default=0.10, description="STT, exchange turnover and brokerage fees")


def _parse_ts(ts: Any) -> Optional[datetime]:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


async def _load_close_series(sec: Security) -> List[tuple]:
    """Daily (timestamp, close) series from the live provider, sorted ascending."""
    try:
        candles = await market_data_manager.get_historical_candles(sec, interval="1d")
    except Exception:
        return []
    series = []
    for c in candles:
        ts = _parse_ts(c.get("timestamp"))
        close = c.get("close")
        if ts is not None and close:
            series.append((ts, float(close)))
    series.sort(key=lambda x: x[0])
    return series


async def _resolve_security(db: AsyncSession, symbol: str) -> Optional[Security]:
    sym = symbol.strip().upper()
    res = await db.execute(
        select(Security).where(Security.symbol == sym, Security.exchange == "NSE")
    )
    sec = res.scalar_one_or_none()
    if not sec:
        res = await db.execute(select(Security).where(Security.symbol == sym))
        sec = res.scalar_one_or_none()
    return sec


def _empty_result(strat: str, req: BacktestRequest, note: str) -> Dict[str, Any]:
    return {
        "status": "ok",
        "strategy": strat,
        "holding_period_days": req.holding_period_days,
        "transaction_costs_applied_pct": round(req.slippage_pct + req.fee_pct, 3),
        "total_events_tested": 0,
        "profitable_trades": 0,
        "losing_trades": 0,
        "win_rate_pct": 0.0,
        "average_net_return_per_event_pct": 0.0,
        "cumulative_net_return_pct": 0.0,
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "max_drawdown_pct": 0.0,
        "trade_log": [],
        "note": note,
        "disclaimer": DISCLAIMER,
    }


def _summarize(strat: str, req: BacktestRequest, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(trades)
    net_rets = [t["net_return_pct"] for t in trades]
    wins = sum(1 for r in net_rets if r > 0)
    avg = sum(net_rets) / n
    variance = sum((r - avg) ** 2 for r in net_rets) / max(1, n - 1)
    std = variance ** 0.5
    downside = [r for r in net_rets if r < 0]
    dstd = (sum(r * r for r in downside) / len(downside)) ** 0.5 if downside else 0.0

    # Annualize using the actual observation span, not an assumed frequency
    entry_dates = [t["entry_ts"] for t in trades]
    span_days = max(1, (max(entry_dates) - min(entry_dates)).days)
    obs_per_year = n * 365.0 / span_days
    sharpe = round((avg / std) * (obs_per_year ** 0.5), 2) if std > 0 else None
    sortino = round((avg / dstd) * (obs_per_year ** 0.5), 2) if dstd > 0 else None

    # Max drawdown over the cumulative return curve in entry-date order
    cum = 0.0
    peak = 0.0
    mdd = 0.0
    for t in sorted(trades, key=lambda x: x["entry_ts"]):
        cum += t["net_return_pct"]
        peak = max(peak, cum)
        mdd = max(mdd, peak - cum)

    return {
        "status": "ok",
        "strategy": strat,
        "holding_period_days": req.holding_period_days,
        "transaction_costs_applied_pct": round(req.slippage_pct + req.fee_pct, 3),
        "total_events_tested": n,
        "profitable_trades": wins,
        "losing_trades": n - wins,
        "win_rate_pct": round((wins / n) * 100, 1),
        "average_net_return_per_event_pct": round(avg, 2),
        "cumulative_net_return_pct": round(sum(net_rets), 2),
        "observation_span_days": span_days,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown_pct": round(mdd, 2),
        "trade_log": [
            {k: v for k, v in t.items() if k != "entry_ts"} for t in trades
        ],
        "disclaimer": DISCLAIMER,
    }


@router.post("/backtest")
async def run_backtest(req: BacktestRequest, db: AsyncSession = Depends(get_db)):
    """Execute a real event-study or rule backtest with transaction costs.

    Event studies match ingested events; RSI_OVERSOLD_REBOUND scans real
    candle history for RSI(14) < 30 entries. Every entry/exit price comes
    from the live historical candle feed.
    """
    strat = req.strategy_type.upper()
    cost = req.slippage_pct + req.fee_pct
    symbol_filter = [s.upper() for s in req.symbols] if req.symbols else None

    trades: List[Dict[str, Any]] = []

    if strat in STRATEGY_EVENT_PATTERNS:
        patterns = STRATEGY_EVENT_PATTERNS[strat]
        query = (
            select(Event)
            .options(selectinload(Event.company).selectinload(Company.securities))
            .where(or_(*[Event.event_type.ilike(p) for p in patterns]))
            .order_by(Event.announcement_time.desc().nullslast())
            .limit(100)
        )
        events = (await db.execute(query)).scalars().all()
        if not events:
            return _empty_result(
                strat, req,
                "No ingested events match this strategy. Sync the event pipeline and re-run; "
                "no synthetic trade log is served.",
            )

        for e in events:
            if not e.company:
                continue
            secs = [s for s in e.company.securities if s.exchange == "NSE"] or list(e.company.securities)
            if not secs:
                continue
            sec = secs[0]
            if symbol_filter and sec.symbol not in symbol_filter:
                continue
            ann = _parse_ts(e.announcement_time)
            if ann is None:
                continue
            series = await _load_close_series(sec)
            if len(series) < req.holding_period_days + 2:
                continue
            entry_idx = next((i for i, (ts, _) in enumerate(series) if ts >= ann), None)
            if entry_idx is None or entry_idx + req.holding_period_days >= len(series):
                continue
            entry_ts, entry_px = series[entry_idx]
            exit_ts, exit_px = series[entry_idx + req.holding_period_days]
            gross = (exit_px - entry_px) / entry_px * 100
            trades.append({
                "symbol": sec.symbol,
                "event_type": e.event_type,
                "event_date": ann.date().isoformat(),
                "entry_date": entry_ts.date().isoformat(),
                "exit_date": exit_ts.date().isoformat(),
                "entry_price": round(entry_px, 2),
                "exit_price": round(exit_px, 2),
                "gross_return_pct": round(gross, 2),
                "net_return_pct": round(gross - cost, 2),
                "holding_period_days": req.holding_period_days,
                "entry_ts": entry_ts,
            })

    elif strat == "RSI_OVERSOLD_REBOUND":
        if not symbol_filter:
            raise HTTPException(
                status_code=400,
                detail="RSI_OVERSOLD_REBOUND is a rule backtest over specified securities; "
                       "provide an explicit 'symbols' list.",
            )
        for sym in symbol_filter:
            sec = await _resolve_security(db, sym)
            if not sec:
                continue
            series = await _load_close_series(sec)
            closes = [px for _, px in series]
            if len(closes) < 14 + req.holding_period_days + 2:
                continue
            period = 14
            for i in range(period, len(closes) - req.holding_period_days):
                window = closes[i - period:i + 1]
                gains, losses = [], []
                for a, b in zip(window, window[1:]):
                    diff = b - a
                    (gains if diff > 0 else losses).append(abs(diff))
                avg_gain = sum(gains) / period
                avg_loss = sum(losses) / period
                if avg_loss == 0:
                    continue
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                if rsi >= 30:
                    continue
                entry_ts, entry_px = series[i]
                exit_ts, exit_px = series[i + req.holding_period_days]
                gross = (exit_px - entry_px) / entry_px * 100
                trades.append({
                    "symbol": sec.symbol,
                    "event_type": "RSI_OVERSOLD",
                    "event_date": entry_ts.date().isoformat(),
                    "entry_date": entry_ts.date().isoformat(),
                    "exit_date": exit_ts.date().isoformat(),
                    "entry_price": round(entry_px, 2),
                    "exit_price": round(exit_px, 2),
                    "rsi_at_entry": round(rsi, 1),
                    "gross_return_pct": round(gross, 2),
                    "net_return_pct": round(gross - cost, 2),
                    "holding_period_days": req.holding_period_days,
                    "entry_ts": entry_ts,
                })
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported strategy_type '{strat}'. Supported: "
                   f"{sorted(set(STRATEGY_EVENT_PATTERNS) | {'RSI_OVERSOLD_REBOUND'})}",
        )

    if not trades:
        return _empty_result(
            strat, req,
            "No tradable observations with sufficient real candle history. "
            "No synthetic trades are served.",
        )

    return _summarize(strat, req, trades)


@router.get("/forecast", response_model=ForecastResult)
async def get_forecast(
    symbol: str = Query(..., description="Stock ticker symbol"),
    horizon: int = Query(10, ge=1, le=30, description="Forecast horizon in trading days"),
    db: AsyncSession = Depends(get_db),
):
    """Generate a statistical projection from real historical closes.

    Requires at least 30 real daily closes from the live candle feed; no
    synthetic baseline series is ever substituted.
    """
    sym = symbol.strip().upper()
    sec = await _resolve_security(db, sym)
    if not sec:
        raise HTTPException(status_code=404, detail=f"Symbol {sym} not found in the ingested universe")

    series = await _load_close_series(sec)
    closes = [px for _, px in series]
    if len(closes) < 30:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Insufficient real candle history for {sym} ({len(closes)} bars; need >= 30). "
                "No synthetic projection is served. Verify market data connectivity."
            ),
        )

    return ForecastingEngine.forecast(symbol=sym, prices=closes[-120:], horizon=horizon)
