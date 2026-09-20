"""Tests for Corporate Actions Calendar and Company Comparison APIs."""
import pytest
from apps.api.routers.calendar import CORPORATE_ACTIONS_REGISTRY, get_corporate_actions, get_actions_summary
from apps.api.routers.compare import compare_companies


@pytest.mark.asyncio
async def test_corporate_actions_calendar_filtering():
    # Filter by symbol
    res = await get_corporate_actions(symbol="LT")
    assert res["status"] == "ok"
    assert len(res["actions"]) > 0
    assert all(a["symbol"] == "LT" for a in res["actions"])

    # Filter by action type
    res_div = await get_corporate_actions(action_type="DIVIDEND")
    assert res_div["status"] == "ok"
    assert all(a["action_type"] == "DIVIDEND" for a in res_div["actions"])


@pytest.mark.asyncio
async def test_corporate_actions_summary():
    res = await get_actions_summary()
    assert res["total_actions"] >= 5
    assert "DIVIDEND" in res["by_type"]
    assert res["upcoming_30_days"] > 0


@pytest.mark.asyncio
async def test_company_comparison_multi_equity():
    res = await compare_companies(symbols="LT,RELIANCE,TCS")
    assert res["status"] == "ok"
    assert res["count"] == 3
    assert "disclaimer" in res
    assert "Strictly descriptive" in res["disclaimer"]

    # Verify metrics exist for each company
    for item in res["comparison"]:
        assert "symbol" in item
        assert "pe_ratio" in item
        assert "roe_pct" in item
        assert "ebitda_margin_pct" in item
        assert "current_price" in item
        assert "price_52w_high" in item
        assert "rsi_14" in item
