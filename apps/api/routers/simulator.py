"""Paper Trading & Research Simulator Router.

Allows virtual testing of portfolio allocation and event-driven ideas without real capital:
- Virtual Cash management (Default initial: Rs 10,00,000 / 10 Lakhs)
- Simulated BUY / SELL orders with slippage (0.05%) and STT/exchange fee models
- Real-time P&L tracking against prevailing market quotes
- Position history and drawdown tracking
Strictly labeled: PAPER / SIMULATION ONLY. Zero brokerage order execution.
Execution prices come from the live market data provider; when no quote is
available the trade is rejected rather than filled at a made-up price.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.database import get_db
from packages.common.models import Security
from packages.market_data.manager import market_data_manager

router = APIRouter(prefix="/api/simulator", tags=["simulator"])


class SimulatedTradeRequest(BaseModel):
    symbol: str
    action: str = Field(description="BUY or SELL")
    quantity: int = Field(gt=0, description="Number of shares")
    price: Optional[float] = Field(None, description="Optional override price; if omitted, uses current LTP")
    slippage_pct: float = Field(0.05, description="Slippage assumption percentage (e.g. 0.05%)")


class SimulatorState:
    INITIAL_CASH = 1000000.0  # 10 Lakhs INR

    def __init__(self):
        self.reset()

    def reset(self):
        self.cash = self.INITIAL_CASH
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trades: List[Dict[str, Any]] = []
        self.peak_equity = self.INITIAL_CASH


_sim = SimulatorState()


async def resolve_ltp(db: AsyncSession, symbol: str) -> Optional[float]:
    """Resolve the last traded price from the live market data provider.

    Returns None when the symbol is unknown or no live quote is available —
    never a substituted price.
    """
    sym = symbol.strip().upper()
    res = await db.execute(
        select(Security).where(Security.symbol == sym, Security.exchange == "NSE")
    )
    sec = res.scalar_one_or_none()
    if not sec:
        res = await db.execute(select(Security).where(Security.symbol == sym))
        sec = res.scalar_one_or_none()
    if not sec:
        return None
    try:
        quote = await market_data_manager.get_quote(sec)
    except Exception:
        return None
    if quote and quote.get("last_price", 0) > 0:
        return float(quote["last_price"])
    return None


@router.get("/account")
async def get_simulator_account(db: AsyncSession = Depends(get_db)):
    """Retrieve virtual cash, portfolio valuation, unrealized P&L, and drawdown."""
    holdings_val = 0.0
    unrealized_pnl = 0.0
    stale_symbols: List[str] = []

    for sym, pos in _sim.positions.items():
        ltp = await resolve_ltp(db, sym)
        if ltp is None:
            # No live quote: value the position at cost basis and flag it,
            # rather than inventing a market price.
            stale_symbols.append(sym)
            val = pos["avg_price"] * pos["quantity"]
            holdings_val += val
            continue
        val = ltp * pos["quantity"]
        holdings_val += val
        pnl = (ltp - pos["avg_price"]) * pos["quantity"]
        unrealized_pnl += pnl

    total_equity = _sim.cash + holdings_val
    if total_equity > _sim.peak_equity:
        _sim.peak_equity = total_equity

    drawdown_pct = 0.0
    if _sim.peak_equity > 0:
        drawdown_pct = round(((_sim.peak_equity - total_equity) / _sim.peak_equity) * 100, 2)

    return {
        "status": "ok",
        "is_simulation": True,
        "mode": "PAPER_SIMULATOR",
        "currency": "INR",
        "initial_cash": _sim.INITIAL_CASH,
        "cash_balance": round(_sim.cash, 2),
        "holdings_valuation": round(holdings_val, 2),
        "total_equity": round(total_equity, 2),
        "total_unrealized_pnl": round(unrealized_pnl, 2),
        "total_unrealized_pnl_pct": round((unrealized_pnl / _sim.INITIAL_CASH) * 100, 2),
        "peak_equity": round(_sim.peak_equity, 2),
        "max_drawdown_pct": drawdown_pct,
        "positions_count": len(_sim.positions),
        "trades_count": len(_sim.trades),
        "stale_valuation_symbols": stale_symbols,
        "valuation_note": (
            "Positions without a live quote are valued at cost basis and listed in "
            "stale_valuation_symbols; no substitute market price is used."
        ) if stale_symbols else None,
        "disclaimer": "SIMULATION ENVIRONMENT ONLY. NO REAL MONEY OR BROKERAGE ORDERS INVOLVED.",
    }


@router.get("/positions")
async def get_simulator_positions(db: AsyncSession = Depends(get_db)):
    """Retrieve all simulated open holdings."""
    items = []
    for sym, pos in _sim.positions.items():
        ltp = await resolve_ltp(db, sym)
        inv = round(pos["avg_price"] * pos["quantity"], 2)
        if ltp is None:
            items.append({
                "symbol": sym,
                "quantity": pos["quantity"],
                "avg_price": round(pos["avg_price"], 2),
                "current_price": None,
                "invested_value": inv,
                "current_value": inv,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
                "price_available": False,
            })
            continue
        val = round(ltp * pos["quantity"], 2)
        pnl = round(val - inv, 2)
        pnl_pct = round((pnl / inv) * 100, 2) if inv > 0 else 0.0
        items.append({
            "symbol": sym,
            "quantity": pos["quantity"],
            "avg_price": round(pos["avg_price"], 2),
            "current_price": ltp,
            "invested_value": inv,
            "current_value": val,
            "unrealized_pnl": pnl,
            "unrealized_pnl_pct": pnl_pct,
            "price_available": True,
        })
    return {"status": "ok", "positions": items}


@router.post("/trade")
async def execute_simulated_trade(trade: SimulatedTradeRequest, db: AsyncSession = Depends(get_db)):
    """Execute simulated virtual BUY or SELL trade with slippage & fee estimation."""
    sym = trade.symbol.upper()
    act = trade.action.upper()
    if act not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Action must be BUY or SELL")

    if trade.price and trade.price > 0:
        base_price = trade.price
        price_source = "USER_OVERRIDE"
    else:
        base_price = await resolve_ltp(db, sym)
        price_source = "LIVE_QUOTE"
        if base_price is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"No live quote available for {sym}; the paper simulator does not fill "
                    "orders at substituted prices. Provide an explicit 'price' or retry when "
                    "the market data feed is reachable."
                ),
            )

    # Apply slippage: buy pays slightly more, sell gets slightly less
    slip_mult = 1.0 + (trade.slippage_pct / 100.0) if act == "BUY" else 1.0 - (trade.slippage_pct / 100.0)
    exec_price = round(base_price * slip_mult, 2)
    trade_value = round(exec_price * trade.quantity, 2)

    # Statutory charges assumption (STT, exchange turnover, GST ~0.1%)
    estimated_fees = round(max(20.0, trade_value * 0.001), 2)

    if act == "BUY":
        total_cost = trade_value + estimated_fees
        if total_cost > _sim.cash:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient virtual cash: Required Rs {total_cost:,.2f}, Available Rs {_sim.cash:,.2f}"
            )
        _sim.cash -= total_cost

        if sym in _sim.positions:
            old_qty = _sim.positions[sym]["quantity"]
            old_avg = _sim.positions[sym]["avg_price"]
            new_qty = old_qty + trade.quantity
            new_avg = ((old_avg * old_qty) + trade_value) / new_qty
            _sim.positions[sym] = {"quantity": new_qty, "avg_price": new_avg}
        else:
            _sim.positions[sym] = {"quantity": trade.quantity, "avg_price": exec_price}

    elif act == "SELL":
        if sym not in _sim.positions or _sim.positions[sym]["quantity"] < trade.quantity:
            avail = _sim.positions.get(sym, {}).get("quantity", 0)
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient holdings: Attempting to sell {trade.quantity}, only {avail} held."
            )
        proceeds = trade_value - estimated_fees
        _sim.cash += proceeds
        _sim.positions[sym]["quantity"] -= trade.quantity
        if _sim.positions[sym]["quantity"] == 0:
            del _sim.positions[sym]

    record = {
        "timestamp": datetime.now().isoformat(),
        "symbol": sym,
        "action": act,
        "quantity": trade.quantity,
        "price": exec_price,
        "price_source": price_source,
        "trade_value": trade_value,
        "estimated_fees": estimated_fees,
    }
    _sim.trades.append(record)

    return {
        "status": "ok",
        "trade": record,
        "remaining_cash": round(_sim.cash, 2),
        "message": f"Simulated {act} of {trade.quantity} {sym} executed at Rs {exec_price:,.2f}."
    }


@router.post("/reset")
async def reset_simulator():
    """Reset simulated account back to 10 Lakhs virtual cash and empty positions."""
    _sim.reset()
    return {"status": "ok", "message": "Paper simulator account reset to Rs 10,00,000 virtual cash."}
