"""Market Data Manager: Unified provider mesh and automatic fallback orchestrator."""
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.config import settings
from packages.common.logging import get_logger
from packages.common.models import Security, MarketQuote
from .base import MarketDataProvider
from .free_provider import FreeMarketDataProvider
from .upstox_provider import UpstoxProvider

logger = get_logger(__name__)


class MarketDataManager:
    """Coordinates market data requests across primary and fallback adapters."""

    def __init__(self):
        self.free_provider = FreeMarketDataProvider()
        self.upstox_provider = UpstoxProvider()

    def get_active_provider(self) -> MarketDataProvider:
        """Determines primary provider based on configuration and authentication."""
        if settings.UPSTOX_ENABLED and self.upstox_provider.is_enabled:
            return self.upstox_provider
        return self.free_provider

    async def get_quote(self, security: Security, session: Optional[AsyncSession] = None) -> Optional[Dict[str, Any]]:
        """Fetch quote from active provider with fallback, and optionally cache to database."""
        provider = self.get_active_provider()
        quote = await provider.get_quote(security)

        # Fallback to free provider if primary returned None and primary wasn't free provider
        if not quote and provider.provider_id != "free":
            logger.info(f"Primary provider {provider.provider_id} returned no quote for {security.symbol}, falling back to free provider.")
            quote = await self.free_provider.get_quote(security)

        if quote and session:
            await self._persist_quote(session, security, quote)

        return quote

    async def get_quotes(self, securities: List[Security], session: Optional[AsyncSession] = None) -> Dict[str, Dict[str, Any]]:
        """Fetch quotes in batch across active provider and fallback."""
        if not securities:
            return {}

        provider = self.get_active_provider()
        quotes = await provider.get_quotes(securities)

        # Find missing securities
        missing = [s for s in securities if str(s.id) not in quotes]
        if missing and provider.provider_id != "free":
            fallback_quotes = await self.free_provider.get_quotes(missing)
            quotes.update(fallback_quotes)

        if session and quotes:
            for s in securities:
                sec_id = str(s.id)
                if sec_id in quotes:
                    await self._persist_quote(session, s, quotes[sec_id])

        return quotes

    async def get_historical_candles(
        self,
        security: Security,
        interval: str = "1d",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch historical candles with fallback."""
        provider = self.get_active_provider()
        candles = await provider.get_historical_candles(security, interval, from_date, to_date)
        if not candles and provider.provider_id != "free":
            candles = await self.free_provider.get_historical_candles(security, interval, from_date, to_date)
        return candles

    async def get_intraday_candles(
        self,
        security: Security,
        interval: str = "5m",
    ) -> List[Dict[str, Any]]:
        """Fetch intraday candles with fallback."""
        provider = self.get_active_provider()
        candles = await provider.get_intraday_candles(security, interval)
        if not candles and provider.provider_id != "free":
            candles = await self.free_provider.get_intraday_candles(security, interval)
        return candles

    async def get_market_status(self) -> Dict[str, Any]:
        """Fetch market status from active provider."""
        return await self.get_active_provider().get_market_status()

    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Fetch holdings if Upstox is enabled."""
        if self.upstox_provider.is_enabled:
            return await self.upstox_provider.get_holdings()
        return []

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch open positions if Upstox is enabled."""
        if self.upstox_provider.is_enabled:
            return await self.upstox_provider.get_positions()
        return []

    async def get_providers_status(self) -> List[Dict[str, Any]]:
        """Health and configuration report of all market data providers."""
        free_health = await self.free_provider.health_check()
        upstox_health = await self.upstox_provider.health_check()
        return [free_health, upstox_health]

    async def get_live_indices(self) -> List[Dict[str, Any]]:
        """Fetch live index quotes (NIFTY 50, SENSEX, BANK NIFTY, INDIA VIX)."""
        return await self.free_provider.get_live_indices()

    async def get_live_market_breadth(self) -> Dict[str, Any]:
        """Fetch live market breadth (Advances/Declines/Unchanged & Market Cap) from NSE India."""
        return await self.free_provider.get_live_market_breadth()


    async def _persist_quote(self, session: AsyncSession, security: Security, quote_data: Dict[str, Any]):
        """Persists or updates the single latest quote record in market_quotes."""
        try:
            res = await session.execute(
                select(MarketQuote).where(MarketQuote.security_id == security.id)
            )
            mq = res.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if not mq:
                mq = MarketQuote(
                    security_id=security.id,
                    last_price=quote_data["last_price"],
                    change_pct=quote_data.get("change_pct", 0.0),
                    day_high=quote_data.get("day_high"),
                    day_low=quote_data.get("day_low"),
                    volume=quote_data.get("volume", 0),
                    vwap=quote_data.get("vwap"),
                    as_of=now,
                    source=quote_data.get("source", "MARKET_MESH"),
                )
                session.add(mq)
            else:
                mq.last_price = quote_data["last_price"]
                mq.change_pct = quote_data.get("change_pct", 0.0)
                mq.day_high = quote_data.get("day_high")
                mq.day_low = quote_data.get("day_low")
                mq.volume = quote_data.get("volume", 0)
                mq.vwap = quote_data.get("vwap")
                mq.as_of = now
                mq.source = quote_data.get("source", mq.source)
            await session.commit()
        except Exception as e:
            logger.debug(f"Failed to persist latest quote for {security.symbol}: {e}")
            await session.rollback()


market_data_manager = MarketDataManager()
