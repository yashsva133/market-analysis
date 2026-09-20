"""Market reaction and volume anomaly calculation."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from packages.schemas.market import MarketReactionResult


class MarketReactionCalculator:
    """Computes price and volume reaction following a corporate event disclosure.
    
    Adheres strictly to factual language:
    - Never generates buy/sell/bullish/bearish recommendations.
    - Accurately computes event-window moves (pre-event, same-day, 1D, 3D, 5D, 20D, gap %, volume multiple).
    """

    def calculate(
        self,
        event_id: UUID,
        announcement_time: Optional[datetime] = None,
        price_before_event: Optional[Decimal] = None,
        price_at_publish: Optional[Decimal] = None,
        close_price: Optional[Decimal] = None,
        volume_today: Optional[Decimal] = None,
        volume_history_20d: Optional[List[Decimal]] = None,
        prices_future_5d: Optional[List[Decimal]] = None,
        prices_future_20d: Optional[List[Decimal]] = None,
    ) -> MarketReactionResult:
        same_day_change = None
        base_price = price_at_publish or price_before_event

        if base_price and close_price and base_price > 0:
            same_day_change = float((close_price - base_price) / base_price * Decimal(100))

        # Gap %: open price on day vs previous day close
        gap_pct = None
        if price_before_event and price_at_publish and price_before_event > 0:
            gap_pct = float((price_at_publish - price_before_event) / price_before_event * Decimal(100))

        # Volume multiple vs 20-day average
        volume_multiple = None
        if volume_today and volume_history_20d and len(volume_history_20d) > 0:
            avg_vol = sum(volume_history_20d) / Decimal(len(volume_history_20d))
            if avg_vol > 0:
                volume_multiple = float(volume_today / avg_vol)

        one_day = None
        three_day = None
        five_day = None
        twenty_day = None

        futures = prices_future_20d or prices_future_5d or []
        if futures and base_price and base_price > 0:
            if len(futures) >= 1:
                one_day = float((futures[0] - base_price) / base_price * Decimal(100))
            if len(futures) >= 3:
                three_day = float((futures[2] - base_price) / base_price * Decimal(100))
            if len(futures) >= 5:
                five_day = float((futures[4] - base_price) / base_price * Decimal(100))
            if len(futures) >= 20:
                twenty_day = float((futures[19] - base_price) / base_price * Decimal(100))

        # Factual description: "What happened after the event?"
        interpretation = "Market reaction data pending post-announcement trading session"
        if same_day_change is not None:
            sign = "+" if same_day_change > 0 else ""
            vol_str = f" with {volume_multiple:.1f}x 20D average volume" if volume_multiple is not None else ""
            interpretation = f"Same-day price reaction: {sign}{same_day_change:.2f}%{vol_str}."
            if one_day is not None:
                interpretation += f" 1-Day: {one_day:+.2f}%."
            if three_day is not None:
                interpretation += f" 3-Day: {three_day:+.2f}%."

        return MarketReactionResult(
            event_id=event_id,
            announcement_time=announcement_time,
            price_at_publish=price_at_publish,
            close_price=close_price,
            same_day_pct_change=same_day_change,
            one_day_pct_change=one_day,
            three_day_pct_change=three_day,
            five_day_pct_change=five_day,
            twenty_day_pct_change=twenty_day,
            volume_multiple_20d=volume_multiple,
            gap_pct=gap_pct,
            interpretation=interpretation,
        )


market_reaction_calculator = MarketReactionCalculator()
market_reaction_engine = market_reaction_calculator


