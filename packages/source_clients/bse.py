"""BSE India source adapter for corporate announcements and scrip lookup."""
import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from packages.common.logging import get_logger
from packages.schemas.source import SourceItemBase
from .base import ProviderAdapter

logger = get_logger(__name__)


class BseAdapter(ProviderAdapter):
    """Adapter for BSE India (Bombay Stock Exchange)."""

    def __init__(self):
        super().__init__(
            source_id="bse-announcements",
            name="BSE Corporate Announcements",
            base_url="https://api.bseindia.com",
            requests_per_minute=20,
            timeout_seconds=15,
            max_retries=3,
        )

    async def fetch(self, **kwargs) -> List[SourceItemBase]:
        """Fetch latest corporate announcements from BSE."""
        self.last_poll_at = datetime.now(timezone.utc)
        api_url = f"{self.base_url}/BseIndiaAPI/api/AnnSubCategoryGetData/w"
        params = {
            "pageno": "1",
            "strCat": "-1",
            "strPrevDate": "",
            "strScrip": "",
            "strSearch": "P",
            "strToDate": "",
            "strType": "C",
        }
        headers = {
            "Referer": "https://www.bseindia.com/corporates/ann.html",
            "Origin": "https://www.bseindia.com",
        }

        items: List[SourceItemBase] = []
        try:
            resp = await self._execute_http_request(api_url, headers=headers, params=params)
            data = resp.json()
            table = data.get("Table", [])

            for row in table:
                scrip_code = str(row.get("SCRIP_CD", "")).strip()
                company_name = row.get("SLONGNAME", row.get("SC_NAME", "")).strip()
                headline = row.get("HEADLINE", row.get("NEWSSUB", "")).strip()
                attachment = row.get("ATTACHMENTNAME", "")
                dt_str = row.get("NEWS_DT", "")

                published_at = None
                if dt_str:
                    try:
                        published_at = datetime.fromisoformat(dt_str)
                    except Exception:
                        published_at = datetime.now(timezone.utc)

                doc_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}" if attachment else None
                full_headline = f"[{scrip_code}] {company_name}: {headline}"
                content_hash = self.compute_hash(f"{scrip_code}:{headline}:{attachment}:{dt_str}")

                items.append(
                    SourceItemBase(
                        source_id=self.source_id,
                        url=doc_url or api_url,
                        canonical_url=doc_url,
                        external_id=str(row.get("NEWSID", scrip_code)),
                        headline=full_headline,
                        published_at=published_at,
                        content_type="application/pdf" if doc_url and doc_url.endswith(".pdf") else "text/html",
                        content_hash=content_hash,
                        raw_location=doc_url,
                        status="FETCHED",
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching BSE announcements: {e}")

        return items

    async def fetch_security_master(self) -> List[Dict[str, Any]]:
        """Fetch list of BSE listed scrips."""
        # Using BSE public scrip directory endpoint or csv
        scrip_url = "https://www.bseindia.com/downloads/Help/file/equity.csv"
        try:
            resp = await self._execute_http_request(scrip_url)
            reader = csv.DictReader(io.StringIO(resp.text))
            scrips = []
            for row in reader:
                # Expected fields: Security Code, Security Id, Security Name, Status, Group, Face Value, ISIN No, Industry, Instrument
                scrip_code = str(row.get("Security Code", "")).strip()
                symbol = row.get("Security Id", "").strip()
                isin = row.get("ISIN No", "").strip()
                name = row.get("Security Name", "").strip()
                group = row.get("Group", "A").strip()
                status = row.get("Status", "Active").strip()

                if isin and scrip_code:
                    scrips.append({
                        "isin": isin,
                        "symbol": symbol or scrip_code,
                        "bse_scrip_code": scrip_code,
                        "legal_name": name,
                        "exchange": "BSE",
                        "series": group,
                        "security_type": "SME" if group in ("M", "MT") else "EQUITY",
                        "is_active": status.lower() == "active",
                    })
            return scrips
        except Exception as e:
            logger.warning(f"Could not load live BSE equity.csv: {e}")
            return []
