"""Tests for Global Search and Paper Trading Simulator."""
import pytest
from apps.api.routers.search import search_all
from apps.api.routers.simulator import (
    _sim,
    get_simulator_account,
    get_simulator_positions,
    execute_simulated_trade,
    reset_simulator,
    SimulatedTradeRequest,
)


@pytest.mark.asyncio
async def test_global_search_matching():
    # Search for company
    res_comp = await search_all(q="Larsen")
    assert res_comp["status"] == "ok"
    assert len(res_comp["results"]["companies"]) > 0
    assert res_comp["results"]["companies"][0]["symbol"] == "LT"

    # Search for event type
    res_evt = await search_all(q="Order")
    assert res_evt["status"] == "ok"
    assert len(res_evt["results"]["events"]) > 0


@pytest.mark.asyncio
async def test_paper_trading_simulator_lifecycle():
    # 1. Reset simulator
    await reset_simulator()
    acc = await get_simulator_account()
    assert acc["cash_balance"] == 1000000.0
    assert acc["positions_count"] == 0

    # 2. Execute simulated BUY
    buy_trade = SimulatedTradeRequest(
        symbol="LT",
        action="BUY",
        quantity=10,
        price=3620.0,
        slippage_pct=0.05,
    )
    buy_res = await execute_simulated_trade(buy_trade)
    assert buy_res["status"] == "ok"
    assert buy_res["remaining_cash"] < 1000000.0

    # 3. Verify open positions
    pos_res = await get_simulator_positions()
    assert len(pos_res["positions"]) == 1
    assert pos_res["positions"][0]["symbol"] == "LT"
    assert pos_res["positions"][0]["quantity"] == 10

    # 4. Execute simulated SELL
    sell_trade = SimulatedTradeRequest(
        symbol="LT",
        action="SELL",
        quantity=5,
        price=3650.0,
        slippage_pct=0.05,
    )
    sell_res = await execute_simulated_trade(sell_trade)
    assert sell_res["status"] == "ok"

    # 5. Check remaining positions
    pos_after = await get_simulator_positions()
    assert pos_after["positions"][0]["quantity"] == 5

    # 6. Reset
    await reset_simulator()
    acc_after = await get_simulator_account()
    assert acc_after["cash_balance"] == 1000000.0
    assert acc_after["positions_count"] == 0
