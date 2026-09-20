"""Upstox API v2 optional authenticated market data provider."""
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
import urllib.parse
import httpx

from packages.common.config import settings
from packages.common.logging import get_logger
from packages.common.models import Security
from .base import MarketDataProvider

logger = get_logger(__name__)


class UpstoxProvider(MarketDataProvider):
    """Optional authenticated Upstox v2 provider for live/OHLCV data and portfolio sync.
    
    Adheres strictly to security guardrails:
    - Never prints secrets, passwords, or tokens in logs or responses.
    - Uses Upstox instrument_key (e.g. NSE_EQ|INE002A01018) without replacing ISIN.
    - Does not support autonomous trading or order execution.
    """

    BASE_URL = "https://api.upstox.com/v2"

    @property
    def provider_id(self) -> str:
        return "upstox"

    @property
    def is_enabled(self) -> bool:
        return bool(settings.UPSTOX_ENABLED and settings.UPSTOX_ACCESS_TOKEN)

    def _get_headers(self) -> Dict[str, str]:
        if not settings.UPSTOX_ACCESS_TOKEN:
            raise ValueError("Upstox access token is not configured.")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {settings.UPSTOX_ACCESS_TOKEN}",
            "User-Agent": "IndiaMarketAITerminal/1.0",
        }

    def _resolve_instrument_key(self, security: Security) -> str:
        """Derives Upstox instrument key (e.g. NSE_EQ|INE002A01018)."""
        if security.upstox_instrument_key:
            return security.upstox_instrument_key
        # Default fallback key format based on exchange and ISIN/symbol
        exchange_segment = "NSE_EQ" if security.exchange == "NSE" else "BSE_EQ"
        isin = getattr(security.company, "isin", None) if hasattr(security, "company") and security.company else None
        identifier = isin or security.symbol
        return f"{exchange_segment}|{identifier}"

    def get_login_url(self) -> Optional[str]:
        """Generates the local user-facing OAuth authorization dialog URL."""
        if not settings.UPSTOX_CLIENT_ID:
            return None
        params = {
            "response_type": "code",
            "client_id": settings.UPSTOX_CLIENT_ID,
            "redirect_uri": settings.UPSTOX_REDIRECT_URI,
        }
        return f"{self.BASE_URL}/login/authorization/dialog?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchanges authorization code for an access token."""
        if not settings.UPSTOX_CLIENT_ID or not settings.UPSTOX_CLIENT_SECRET:
            raise ValueError("Upstox client credentials not configured.")

        url = f"{self.BASE_URL}/login/authorization/token"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "code": code,
            "client_id": settings.UPSTOX_CLIENT_ID,
            "client_secret": settings.UPSTOX_CLIENT_SECRET,
            "redirect_uri": settings.UPSTOX_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, data=payload)
            resp.raise_for_status()
            data = resp.json()
            # Return token information without logging sensitive values
            return {
                "access_token": data.get("access_token"),
                "token_type": data.get("token_type"),
                "user_name": data.get("user_name"),
                "user_id": data.get("user_id"),
                "expires_in": data.get("expires_in"),
            }

    async def get_quote(self, security: Security) -> Optional[Dict[str, Any]]:
        if not self.is_enabled:
            return None

        instrument_key = self._resolve_instrument_key(security)
        encoded_key = urllib.parse.quote(instrument_key)
        url = f"{self.BASE_URL}/market-quote/quotes?instrument_key={encoded_key}"

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                resp.raise_for_status()
                data = resp.json()
                
                # Upstox v2 format: data: { "NSE_EQ:RELIANCE": { last_price, ohlc, volume, ... } }
                res_data = data.get("data", {})
                quote_obj = None
                for k, v in res_data.items():
                    quote_obj = v
                    break

                if quote_obj:
                    ohlc = quote_obj.get("ohlc", {})
                    last_price = float(quote_obj.get("last_price", 0.0))
                    close_p = float(ohlc.get("close", last_price))
                    change_pct = ((last_price - close_p) / close_p * 100) if close_p > 0 else 0.0

                    return {
                        "security_id": str(security.id),
                        "symbol": security.symbol,
                        "exchange": security.exchange,
                        "last_price": last_price,
                        "change_pct": round(change_pct, 2),
                        "day_high": float(ohlc.get("high", 0.0)),
                        "day_low": float(ohlc.get("low", 0.0)),
                        "volume": int(quote_obj.get("volume", 0)),
                        "vwap": float(quote_obj.get("average_price", last_price)),
                        "as_of": datetime.now(timezone.utc).isoformat(),
                        "source": "UPSTOX_V2",
                    }
        except Exception as e:
            logger.warning(f"Upstox quote fetch failed for {security.symbol}: {e}")
            return None

    async def get_quotes(self, securities: List[Security]) -> Dict[str, Dict[str, Any]]:
        if not self.is_enabled or not securities:
            return {}

        results = {}
        # Batch by up to 20 instruments per Upstox limits
        batch_keys = [self._resolve_instrument_key(s) for s in securities[:20]]
        param_str = ",".join(urllib.parse.quote(k) for k in batch_keys)
        url = f"{self.BASE_URL}/market-quote/quotes?instrument_key={param_str}"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                resp.raise_for_status()
                data = resp.json().get("data", {})

                key_to_sec = {self._resolve_instrument_key(s): s for s in securities}
                for key_str, q in data.items():
                    # Format in data can be NSE_EQ:RELIANCE or NSE_EQ|INE...
                    matched_sec = None
                    for orig_k, sec in key_to_sec.items():
                        if orig_k in key_str or sec.symbol in key_str:
                            matched_sec = sec
                            break
                    if matched_sec:
                        ohlc = q.get("ohlc", {})
                        lp = float(q.get("last_price", 0.0))
                        cp = float(ohlc.get("close", lp))
                        pct = ((lp - cp) / cp * 100) if cp > 0 else 0.0
                        results[str(matched_sec.id)] = {
                            "security_id": str(matched_sec.id),
                            "symbol": matched_sec.symbol,
                            "exchange": matched_sec.exchange,
                            "last_price": lp,
                            "change_pct": round(pct, 2),
                            "day_high": float(ohlc.get("high", 0.0)),
                            "day_low": float(ohlc.get("low", 0.0)),
                            "volume": int(q.get("volume", 0)),
                            "vwap": float(q.get("average_price", lp)),
                            "as_of": datetime.now(timezone.utc).isoformat(),
                            "source": "UPSTOX_V2",
                        }
        except Exception as e:
            logger.warning(f"Upstox bulk quote fetch failed: {e}")

        return results

    async def get_historical_candles(
        self,
        security: Security,
        interval: str = "1d",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_enabled:
            return []

        instrument_key = urllib.parse.quote(self._resolve_instrument_key(security))
        to_d = to_date.strftime("%Y-%m-%d") if to_date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        from_d = from_date.strftime("%Y-%m-%d") if from_date else "2020-01-01"
        
        upstox_interval = "day" if interval in ("1d", "1D", "day") else "30minute"
        url = f"{self.BASE_URL}/historical-candle/{instrument_key}/{upstox_interval}/{to_d}/{from_d}"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                resp.raise_for_status()
                candles_raw = resp.json().get("data", {}).get("candles", [])
                
                # Format: [timestamp, open, high, low, close, volume, open_interest]
                results = []
                for c in reversed(candles_raw):
                    results.append({
                        "timestamp": c[0],
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": int(c[5]),
                    })
                return results
        except Exception as e:
            logger.warning(f"Upstox historical candles failed for {security.symbol}: {e}")
            return []

    async def get_intraday_candles(
        self,
        security: Security,
        interval: str = "5m",
    ) -> List[Dict[str, Any]]:
        if not self.is_enabled:
            return []

        instrument_key = urllib.parse.quote(self._resolve_instrument_key(security))
        upstox_interval = "5minute" if interval in ("5m", "5minute") else "1minute"
        url = f"{self.BASE_URL}/historical-candle/intraday/{instrument_key}/{upstox_interval}"

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                resp.raise_for_status()
                candles_raw = resp.json().get("data", {}).get("candles", [])
                results = []
                for c in reversed(candles_raw):
                    results.append({
                        "timestamp": c[0],
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": int(c[5]),
                    })
                return results
        except Exception as e:
            logger.warning(f"Upstox intraday candles failed for {security.symbol}: {e}")
            return []

    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Fetch long-term portfolio holdings."""
        if not self.is_enabled:
            return []

        url = f"{self.BASE_URL}/portfolio/long-term-holdings"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                resp.raise_for_status()
                holdings_raw = resp.json().get("data", [])
                
                results = []
                for h in holdings_raw:
                    results.append({
                        "isin": h.get("isin"),
                        "symbol": h.get("trading_symbol"),
                        "exchange": h.get("exchange"),
                        "company_name": h.get("company_name"),
                        "quantity": float(h.get("quantity", 0)),
                        "average_price": float(h.get("average_price", 0.0)),
                        "last_price": float(h.get("last_price", 0.0)),
                        "pnl": float(h.get("pnl", 0.0)),
                        "instrument_token": h.get("instrument_token"),
                    })
                return results
        except Exception as e:
            logger.warning(f"Upstox holdings fetch failed: {e}")
            return []

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch open trading positions."""
        if not self.is_enabled:
            return []

        url = f"{self.BASE_URL}/portfolio/short-term-positions"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                resp.raise_for_status()
                positions_raw = resp.json().get("data", [])
                return positions_raw
        except Exception as e:
            logger.warning(f"Upstox positions fetch failed: {e}")
            return []

    async def get_market_status(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/market/status/NSE"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                resp.raise_for_status()
                data = resp.json().get("data", {})
                return {
                    "status": data.get("status", "CLOSED"),
                    "market_type": data.get("market_type"),
                    "provider": "upstox",
                }
        except Exception:
            return {"status": "UNKNOWN", "provider": "upstox"}

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_id,
            "enabled": settings.UPSTOX_ENABLED,
            "has_client_id": bool(settings.UPSTOX_CLIENT_ID),
            "authenticated": bool(settings.UPSTOX_ACCESS_TOKEN),
            "status": "healthy" if self.is_enabled else ("configured" if settings.UPSTOX_ENABLED else "disabled"),
            "note": "Authenticated live quote and portfolio adapter (Order execution disabled)",
        }
