"""Abstract Base Interface for Market Data Providers."""
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional
from packages.common.models import Security, MarketQuote


class MarketDataProvider(ABC):
    """Abstract interface that all market data adapters must implement."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for provider (e.g. 'free', 'upstox', 'mock')."""
        pass

    @abstractmethod
    async def get_quote(self, security: Security) -> Optional[Dict[str, Any]]:
        """Fetch latest quote for a single security."""
        pass

    @abstractmethod
    async def get_quotes(self, securities: List[Security]) -> Dict[str, Dict[str, Any]]:
        """Fetch quotes for a batch of securities keyed by security ID string."""
        pass

    @abstractmethod
    async def get_historical_candles(
        self,
        security: Security,
        interval: str = "1d",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch historical OHLCV candle series."""
        pass

    @abstractmethod
    async def get_intraday_candles(
        self,
        security: Security,
        interval: str = "5m",
    ) -> List[Dict[str, Any]]:
        """Fetch intraday candle series for the current or last active session."""
        pass

    @abstractmethod
    async def get_market_status(self) -> Dict[str, Any]:
        """Check market status (OPEN, CLOSED, PRE_OPEN)."""
        pass

    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Retrieve portfolio holdings if supported by provider (optional)."""
        return []

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Retrieve open positions if supported by provider (optional)."""
        return []

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Return diagnostic health and connectivity status."""
        pass
