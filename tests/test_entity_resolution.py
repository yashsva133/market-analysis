"""Tests for EntityResolverAgent and MarketReactionCalculator."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from packages.ai.agents import entity_resolver_agent
from packages.market_data.reaction import market_reaction_calculator


def test_entity_resolution_by_symbol():
    comp_id = uuid.uuid4()
    symbols_index = {"RELIANCE": comp_id, "TCS": uuid.uuid4()}
    scrips_index = {"500325": comp_id}
    names_index = {"Reliance Industries Limited": comp_id}

    headline_symbol = "[RELIANCE] Reliance announces commercial operation of new solar unit"
    resolved_id = entity_resolver_agent.resolve(headline_symbol, symbols_index, scrips_index, names_index)
    assert resolved_id == comp_id

    headline_scrip = "[500325] Corporate action update"
    resolved_scrip = entity_resolver_agent.resolve(headline_scrip, symbols_index, scrips_index, names_index)
    assert resolved_scrip == comp_id


def test_market_reaction_calculation():
    event_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    price_publish = Decimal("400.00")
    price_close = Decimal("420.00")
    vol_today = Decimal("2000000")
    vol_history = [Decimal("1000000")] * 20

    res = market_reaction_calculator.calculate(
        event_id=event_id,
        announcement_time=now,
        price_at_publish=price_publish,
        close_price=price_close,
        volume_today=vol_today,
        volume_history_20d=vol_history,
    )
    # (420 - 400)/400 = 5%
    assert res.same_day_pct_change == 5.0
    # 2,000,000 / 1,000,000 = 2.0x
    assert res.volume_multiple_20d == 2.0
    assert "+5.0" in res.interpretation
