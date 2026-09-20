"""Streaming Market Subscription Manager: selective WebSocket / polling stream router."""
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
import asyncio

from packages.common.logging import get_logger

logger = get_logger(__name__)


class MarketSubscriptionManager:
    """Manages active streaming subscriptions for selective real-time updates.
    
    Ensures the system does not open blind WebSocket connections for thousands of instruments.
    Maintains sets:
    - watched symbols (from user watchlists)
    - portfolio symbols (from holdings)
    - event-affected symbols (companies with recent critical/high events)
    - user-selected symbols (active tab in terminal UI)
    """

    def __init__(self):
        self._watched_symbols: Set[str] = set()
        self._portfolio_symbols: Set[str] = set()
        self._event_affected_symbols: Set[str] = set()
        self._user_selected_symbols: Set[str] = set()

        # In-memory latest quotes cache to eliminate DB write contention on every tick
        self._latest_quotes_cache: Dict[str, Dict[str, Any]] = {}
        self._subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self._is_running: bool = False

    def add_symbol(self, symbol: str, category: str = "watched"):
        """Add symbol to a specific streaming subscription category."""
        clean_sym = symbol.upper().strip()
        if category == "portfolio":
            self._portfolio_symbols.add(clean_sym)
        elif category == "event":
            self._event_affected_symbols.add(clean_sym)
        elif category == "active_view":
            self._user_selected_symbols.add(clean_sym)
        else:
            self._watched_symbols.add(clean_sym)
        logger.debug(f"Subscribed {clean_sym} to {category} stream.")

    def remove_symbol(self, symbol: str, category: str = "watched"):
        """Remove symbol from a subscription category."""
        clean_sym = symbol.upper().strip()
        if category == "portfolio":
            self._portfolio_symbols.discard(clean_sym)
        elif category == "event":
            self._event_affected_symbols.discard(clean_sym)
        elif category == "active_view":
            self._user_selected_symbols.discard(clean_sym)
        else:
            self._watched_symbols.discard(clean_sym)

    def get_subscribed_symbols(self) -> Set[str]:
        """Returns the union of all active streaming candidates."""
        return self._watched_symbols | self._portfolio_symbols | self._event_affected_symbols | self._user_selected_symbols

    def get_subscription_stats(self) -> Dict[str, Any]:
        """Diagnostic breakdown of currently monitored instruments."""
        return {
            "total_active": len(self.get_subscribed_symbols()),
            "watched_count": len(self._watched_symbols),
            "portfolio_count": len(self._portfolio_symbols),
            "event_affected_count": len(self._event_affected_symbols),
            "user_selected_count": len(self._user_selected_symbols),
            "symbols": list(self.get_subscribed_symbols()),
        }

    def on_quote_update(self, quote: Dict[str, Any]):
        """Callback invoked when a new tick or quote update arrives."""
        sym = quote.get("symbol", "").upper()
        if sym:
            self._latest_quotes_cache[sym] = quote

        for cb in self._subscribers:
            try:
                cb(quote)
            except Exception as e:
                logger.error(f"Error in quote subscriber callback: {e}")

    def register_callback(self, cb: Callable[[Dict[str, Any]], Any]):
        """Register a callback (e.g. WebSocket client broadcaster)."""
        self._subscribers.append(cb)

    def get_cached_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieve most recent tick/quote from in-memory cache."""
        return self._latest_quotes_cache.get(symbol.upper())


subscription_manager = MarketSubscriptionManager()
