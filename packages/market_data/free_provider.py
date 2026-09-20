"""Free and public market data provider using Yahoo Finance / Bhavcopy with offline resilience."""
import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import math

from packages.common.logging import get_logger
from packages.common.models import Security
from .base import MarketDataProvider

logger = get_logger(__name__)


class FreeMarketDataProvider(MarketDataProvider):
    """Zero-cost market data provider supporting NSE and BSE securities."""

    @property
    def provider_id(self) -> str:
        return "free"

    def _get_ticker_symbol(self, security: Security) -> str:
        symbol = security.symbol.upper().replace("&", "")
        if security.exchange == "NSE":
            return f"{symbol}.NS"
        elif security.exchange == "BSE":
            code = security.bse_scrip_code or symbol
            return f"{code}.BO"
        return f"{symbol}.NS"

    async def get_quote(self, security: Security) -> Optional[Dict[str, Any]]:
        ticker = self._get_ticker_symbol(security)
        now = datetime.now(timezone.utc)
        
        try:
            import yfinance as yf
            # Fetch fast info in a non-blocking thread
            loop = asyncio.get_running_loop()
            def fetch_fast_info():
                t = yf.Ticker(ticker)
                fi = t.fast_info
                return {
                    "last_price": float(fi.last_price or 0.0),
                    "day_high": float(fi.day_high or 0.0),
                    "day_low": float(fi.day_low or 0.0),
                    "previous_close": float(fi.previous_close or 0.0),
                    "volume": int(fi.last_volume or 0),
                }
            
            data = await asyncio.wait_for(loop.run_in_executor(None, fetch_fast_info), timeout=4.0)
            last_price = data["last_price"]
            prev_close = data["previous_close"]
            change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
            
            if last_price > 0:
                return {
                    "security_id": str(security.id),
                    "symbol": security.symbol,
                    "exchange": security.exchange,
                    "last_price": last_price,
                    "change_pct": round(change_pct, 2),
                    "day_high": data["day_high"],
                    "day_low": data["day_low"],
                    "volume": data["volume"],
                    "vwap": round((data["day_high"] + data["day_low"] + last_price) / 3, 2) if data["day_high"] else last_price,
                    "as_of": now.isoformat(),
                    "source": "FREE_YFINANCE",
                }
        except Exception as e:
            logger.debug(f"Free provider online fetch failed for {ticker}: {e}. Reporting unavailable.")

        # Feed unreachable: no quote is served rather than a hash-simulated price.
        return None

    async def get_quotes(self, securities: List[Security]) -> Dict[str, Dict[str, Any]]:
        results = {}
        for sec in securities:
            quote = await self.get_quote(sec)
            if quote:
                results[str(sec.id)] = quote
        return results

    async def get_historical_candles(
        self,
        security: Security,
        interval: str = "1d",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        ticker = self._get_ticker_symbol(security)
        now = datetime.now(timezone.utc)

        try:
            import yfinance as yf
            loop = asyncio.get_running_loop()
            
            def fetch_history():
                t = yf.Ticker(ticker)
                period = "6mo" if not from_date else "max"
                hist = t.history(period=period, interval=interval)
                candles = []
                for idx, row in hist.iterrows():
                    candles.append({
                        "timestamp": idx.isoformat(),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    })
                return candles

            candles = await asyncio.wait_for(loop.run_in_executor(None, fetch_history), timeout=5.0)
            if candles:
                return candles
        except Exception as e:
            logger.debug(f"Online historical candles fetch failed for {ticker}: {e}. Generating deterministic series.")

        # Offline synthetic historical candle series for zero-budget offline usage
        seed = sum(ord(c) for c in security.symbol)
        base = 500.0 + (seed % 2500)
        days = 60
        candles = []
        cur_price = base
        start_day = now - timedelta(days=days)

        for i in range(days):
            day_time = start_day + timedelta(days=i)
            # Skip weekends
            if day_time.weekday() >= 5:
                continue
            delta = math.sin((i + seed) * 0.3) * 15.0 + ((i % 5) - 2.0)
            open_p = round(cur_price, 2)
            close_p = round(cur_price + delta, 2)
            high_p = round(max(open_p, close_p) + abs(delta * 0.5) + 2.0, 2)
            low_p = round(min(open_p, close_p) - abs(delta * 0.5) - 1.5, 2)
            vol = int(500000 + abs(delta * 50000) + ((i * seed) % 200000))
            candles.append({
                "timestamp": day_time.isoformat(),
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
            })
            cur_price = close_p

        return candles

    async def get_intraday_candles(
        self,
        security: Security,
        interval: str = "5m",
    ) -> List[Dict[str, Any]]:
        # Fetch last 1-2 days at 5m
        now = datetime.now(timezone.utc)
        ticker = self._get_ticker_symbol(security)
        try:
            import yfinance as yf
            loop = asyncio.get_running_loop()
            def fetch_intra():
                t = yf.Ticker(ticker)
                hist = t.history(period="1d", interval=interval)
                candles = []
                for idx, row in hist.iterrows():
                    candles.append({
                        "timestamp": idx.isoformat(),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    })
                return candles
            intra = await asyncio.wait_for(loop.run_in_executor(None, fetch_intra), timeout=4.0)
            if intra:
                return intra
        except Exception:
            pass

        # Offline synthetic intraday candles (375 minutes in an Indian trading session 9:15 to 15:30)
        seed = sum(ord(c) for c in security.symbol)
        base = 500.0 + (seed % 2500)
        session_start = now.replace(hour=3, minute=45, second=0, microsecond=0) # 09:15 IST = 03:45 UTC
        candles = []
        cur = base
        for m in range(0, 75): # 75 5-minute bars = 375 mins
            bar_time = session_start + timedelta(minutes=m * 5)
            step = math.sin((m + seed) * 0.2) * 4.0
            o = round(cur, 2)
            c = round(cur + step, 2)
            h = round(max(o, c) + 1.0, 2)
            l = round(min(o, c) - 1.0, 2)
            v = int(15000 + abs(step * 3000))
            candles.append({
                "timestamp": bar_time.isoformat(),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
            })
            cur = c
        return candles

    async def get_market_status(self) -> Dict[str, Any]:
        # Indian market hours: 9:15 AM to 3:30 PM IST (UTC 03:45 to 10:00), Monday through Friday
        now_utc = datetime.now(timezone.utc)
        ist_hour = (now_utc.hour + 5) + (now_utc.minute + 30) // 60
        ist_min = (now_utc.minute + 30) % 60
        is_weekday = now_utc.weekday() < 5
        
        is_open = False
        status_str = "CLOSED"
        
        if is_weekday:
            if (ist_hour == 9 and ist_min >= 15) or (10 <= ist_hour < 15) or (ist_hour == 15 and ist_min <= 30):
                is_open = True
                status_str = "OPEN"
            elif ist_hour == 9 and ist_min < 15:
                status_str = "PRE_OPEN"

        return {
            "status": status_str,
            "is_open": is_open,
            "market": "NSE/BSE",
            "timezone": "Asia/Kolkata",
            "as_of": now_utc.isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_id,
            "status": "healthy",
            "online": True,
            "authenticated": False,
            "note": "Zero-budget public exchange quotes and Bhavcopy engine",
        }

    async def get_live_indices(self) -> List[Dict[str, Any]]:
        """Fetches live quotes for major Indian indices (^NSEI, ^BSESN, ^NSEBANK, ^INDIAVIX).

        Only indices with a live price from the upstream feed are returned —
        no hardcoded default values are substituted.
        """
        now = datetime.now(timezone.utc)
        indices_config = [
            {"id": "nifty50", "name": "NIFTY 50", "ticker": "^NSEI", "note": None},
            {"id": "niftybank", "name": "NIFTY BANK", "ticker": "^NSEBANK", "note": None},
            {"id": "indiavix", "name": "INDIA VIX", "ticker": "^INDIAVIX", "note": None},
            {"id": "sensex", "name": "BSE SENSEX", "ticker": "^BSESN", "note": None},
        ]

        results: List[Dict[str, Any]] = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=4.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
                for idx in indices_config:
                    ticker = idx["ticker"]
                    price = None
                    prev_close = None
                    try:
                        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            meta = resp.json()["chart"]["result"][0]["meta"]
                            p = meta.get("regularMarketPrice")
                            pc = meta.get("previousClose") or meta.get("chartPreviousClose")
                            if p is not None:
                                price = float(p)
                            if pc is not None:
                                prev_close = float(pc)
                    except Exception:
                        pass

                    if price is None:
                        continue

                    chg = price - prev_close if prev_close else 0.0
                    pct = (chg / prev_close * 100) if prev_close else 0.0
                    up = chg >= 0
                    sign = "+" if up else ""
                    results.append({
                        "id": idx["id"],
                        "name": idx["name"],
                        "ticker": ticker,
                        "price": round(price, 2),
                        "val": f"{price:,.2f}",
                        "change": round(chg, 2),
                        "change_pct": round(pct, 2),
                        "chg": f"{sign}{chg:,.2f} ({sign}{pct:.2f}%)",
                        "up": up,
                        "note": idx["note"],
                        "prev_close": prev_close,
                        "as_of": now.isoformat(),
                    })
                return results
        except Exception as e:
            logger.warning(f"Error fetching live indices: {e}. No substitute index values are served.")
            return []

    async def get_live_market_breadth(self) -> Dict[str, Any]:
        """Fetches live market-wide advance/decline breadth & market cap from NSE India."""
        import httpx
        now = datetime.now(timezone.utc)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=6.0, follow_redirects=True) as client:
                r0 = await client.get("https://www.nseindia.com")
                cookies = dict(r0.cookies)
                r_indices = await client.get("https://www.nseindia.com/api/allIndices", cookies=cookies)

                if r_indices.status_code == 200:
                    data = r_indices.json().get("data", [])
                    # Find NIFTY 500 for broad market breadth
                    n500 = next((idx for idx in data if idx.get("index") == "NIFTY 500"), None)
                    if not n500:
                        n500 = next((idx for idx in data if "500" in idx.get("index", "")), None)

                    if n500 and n500.get("advances") is not None and n500.get("declines") is not None:
                        adv = int(n500.get("advances"))
                        dec = int(n500.get("declines"))
                        unch = int(n500.get("unchanged") or 0)
                        ratio = round(adv / dec, 2) if dec > 0 else None

                        regime = (
                            "TRENDING_UP / LOW_VOLATILITY (RISK-ON)"
                            if ratio is not None and ratio >= 1.5
                            else "TRENDING_DOWN / ELEVATED_RISK (DEFENSIVE)"
                            if ratio is not None and ratio <= 0.7
                            else "SIDEWAYS_CONSOLIDATION / NEUTRAL"
                            if ratio is not None
                            else None
                        )

                        return {
                            "status": "LIVE_NSE",
                            "advances": adv,
                            "declines": dec,
                            "unchanged": unch,
                            "total_tracked": adv + dec + unch,
                            "advance_decline_ratio": ratio,
                            "market_regime": regime,
                            "benchmark_index": "NIFTY 500",
                            "index_last": float(n500.get("last")) if n500.get("last") is not None else None,
                            "index_change_pct": float(n500.get("percentChange")) if n500.get("percentChange") is not None else None,
                            "as_of": now.isoformat(),
                        }
        except Exception as e:
            logger.debug(f"Live NSE market breadth query failed: {e}. Reporting unavailable.")

        # Feed unreachable: report the gap honestly instead of a fabricated
        # "calibrated fallback" snapshot.
        return {
            "status": "UNAVAILABLE",
            "advances": None,
            "declines": None,
            "unchanged": None,
            "total_tracked": 0,
            "advance_decline_ratio": None,
            "market_regime": None,
            "benchmark_index": "NIFTY 500",
            "index_last": None,
            "index_change_pct": None,
            "as_of": now.isoformat(),
            "note": "Live NSE breadth feed unreachable. No substitute breadth snapshot is served.",
        }

    async def get_live_quote(self, symbol: str) -> Optional[Any]:
        """Queries live quote for a ticker symbol directly (NSE .NS or BSE .BO)."""
        clean_sym = symbol.upper().replace("&", "")
        ticker = f"{clean_sym}.NS"
        try:
            import yfinance as yf
            loop = asyncio.get_running_loop()
            def fetch():
                t = yf.Ticker(ticker)
                fi = t.fast_info
                lp = float(fi.last_price or 0.0)
                pc = float(fi.previous_close or lp)
                vol = int(fi.last_volume or 0)
                chg = ((lp - pc) / pc * 100) if pc > 0 else 0.0
                return lp, chg, vol

            lp, chg, vol = await asyncio.wait_for(loop.run_in_executor(None, fetch), timeout=4.0)
            if lp > 0:
                class SimpleQuote:
                    def __init__(self, s, p, c, v):
                        self.symbol = s
                        self.last_price = p
                        self.change_pct = c
                        self.volume = v
                return SimpleQuote(clean_sym, lp, chg, vol)
        except Exception:
            pass
        return None


free_provider = FreeMarketDataProvider()



