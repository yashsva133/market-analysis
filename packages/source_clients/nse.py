"""NSE India source adapter for corporate announcements and security master discovery."""
import csv
import io
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from packages.common.config import settings
from packages.common.logging import get_logger
from packages.schemas.source import SourceItemBase
from .base import ProviderAdapter

logger = get_logger(__name__)


class NseAdapter(ProviderAdapter):
    """Adapter for National Stock Exchange of India (NSE)."""

    def __init__(self):
        super().__init__(
            source_id="nse-announcements",
            name="NSE Corporate Filings",
            base_url="https://www.nseindia.com",
            requests_per_minute=15,
            timeout_seconds=15,
            max_retries=3,
        )
        self.session_cookies: Dict[str, str] = {}
        self.last_cookie_time: float = 0.0

    async def _ensure_session(self):
        """NSE requires initial cookie bootstrap by loading the home page."""
        now = time.time()
        # Refresh cookies if older than 5 minutes
        if not self.session_cookies or (now - self.last_cookie_time > 300):
            try:
                headers = {
                    "User-Agent": settings.COLLECTOR_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    resp = await client.get(self.base_url, headers=headers)
                    self.session_cookies = dict(resp.cookies)
                    self.last_cookie_time = now
                    logger.debug("Successfully bootstrapped NSE session cookies.")
            except Exception as e:
                logger.warning(f"Could not bootstrap NSE cookies directly: {e}")

    async def fetch(self, **kwargs) -> List[SourceItemBase]:
        """Fetch latest corporate announcements from NSE."""
        self.last_poll_at = datetime.now(timezone.utc)
        await self._ensure_session()

        api_url = f"{self.base_url}/api/corporate-announcements?index=equities"
        headers = {
            "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        }
        if self.session_cookies:
            headers["Cookie"] = "; ".join([f"{k}={v}" for k, v in self.session_cookies.items()])

        items: List[SourceItemBase] = []
        try:
            resp = await self._execute_http_request(api_url, headers=headers)
            data = resp.json()
            # NSE returns list of announcements or object with data array
            raw_list = data if isinstance(data, list) else data.get("data", [])

            for row in raw_list:
                symbol = row.get("symbol", "").strip()
                company_name = row.get("companyName", row.get("sm_name", "")).strip()
                desc = row.get("desc", row.get("an_headline", "")).strip()
                att_link = row.get("attmntText", row.get("attachment", ""))
                dt_str = row.get("an_dt", row.get("dt", ""))

                published_at = None
                if dt_str:
                    try:
                        published_at = datetime.fromisoformat(dt_str)
                    except Exception:
                        published_at = datetime.now(timezone.utc)

                doc_url = f"https://nsearchives.nseindia.com/corporate/{att_link}" if att_link else None
                headline = f"[{symbol}] {company_name}: {desc}"
                content_hash = self.compute_hash(f"{symbol}:{desc}:{att_link}:{dt_str}")

                items.append(
                    SourceItemBase(
                        source_id=self.source_id,
                        url=doc_url or api_url,
                        canonical_url=doc_url,
                        external_id=str(row.get("seq_id", symbol)),
                        headline=headline,
                        published_at=published_at,
                        content_type="application/pdf" if doc_url and doc_url.endswith(".pdf") else "text/html",
                        content_hash=content_hash,
                        raw_location=doc_url,
                        status="FETCHED",
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching NSE announcements: {e}")

        return items

    async def fetch_security_master(self) -> List[Dict[str, Any]]:
        """Fetch current list of active NSE equity securities (EQUITY_L.csv)."""
        securities_url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
        resp = await self._execute_http_request(securities_url)
        content = resp.text

        reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), skipinitialspace=True)
        reader.fieldnames = [name.strip() for name in (reader.fieldnames or [])]
        if not {"SYMBOL", "NAME OF COMPANY", "ISIN NUMBER"}.issubset(reader.fieldnames):
            raise ValueError("NSE security master returned an unexpected CSV schema (possibly an HTML error page)")
        securities = []
        for row in reader:
            # Fields: SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE
            isin = row.get("ISIN NUMBER", row.get("ISIN", "")).strip()
            symbol = row.get("SYMBOL", "").strip()
            name = row.get("NAME OF COMPANY", "").strip()
            series = row.get("SERIES", "EQ").strip()

            if symbol:
                securities.append({
                    "isin": isin,
                    "symbol": symbol,
                    "legal_name": name,
                    "exchange": "NSE",
                    "series": series,
                    "security_type": "SME" if series in ("SM", "ST") else "EQUITY",
                })
        return securities
