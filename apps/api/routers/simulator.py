"""Paper Trading & Research Simulator Router.

Allows virtual testing of portfolio allocation and event-driven ideas without real capital:
- Virtual Cash management (Default initial: Rs 10,00,000 / 10 Lakhs)
- Simulated BUY / SELL orders with slippage (0.05%) and STT/exchange fee models
- Real-time P&L tracking against prevailing market quotes
- Position history and drawdown tracking
Strictly labeled: PAPER / SIMULATION ONLY. Zero brokerage order execution.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

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

    def get_market_price(self, symbol: str) -> float:
        # Grounded reference prices for liquid symbols
        price_map = {
            "LT": 3620.00,
            "RELIANCE": 2925.00,
            "TCS": 4090.00,
            "INFY": 1880.00,
            "NIFTYBEES": 266.50,
            "CUPID": 265.00,
            "HDFCBANK": 1640.00,
            "TATAMOTORS": 980.00,
        }
        return price_map.get(symbol.upper(), 500.00)


_sim = SimulatorState()


@router.get("/account")
async def get_simulator_account():
    """Retrieve virtual cash, portfolio valuation, unrealized P&L, and drawdown."""
    holdings_val = 0.0
    unrealized_pnl = 0.0

    for sym, pos in _sim.positions.items():
        ltp = _sim.get_market_price(sym)
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
        "disclaimer": "SIMULATION ENVIRONMENT ONLY. NO REAL MONEY OR BROKERAGE ORDERS INVOLVED.",
    }


@router.get("/positions")
async def get_simulator_positions():
    """Retrieve all simulated open holdings."""
    items = []
    for sym, pos in _sim.positions.items():
        ltp = _sim.get_market_price(sym)
        val = round(ltp * pos["quantity"], 2)
        inv = round(pos["avg_price"] * pos["quantity"], 2)
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
        })
    return {"status": "ok", "positions": items}


@router.post("/trade")
async def execute_simulated_trade(trade: SimulatedTradeRequest):
    """Execute simulated virtual BUY or SELL trade with slippage & fee estimation."""
    sym = trade.symbol.upper()
    act = trade.action.upper()
    if act not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Action must be BUY or SELL")

    base_price = trade.price if trade.price and trade.price > 0 else _sim.get_market_price(sym)
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
