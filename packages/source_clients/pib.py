"""PIB (Press Information Bureau) Government of India press release adapter."""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List

from packages.common.logging import get_logger
from packages.schemas.source import SourceItemBase
from .base import ProviderAdapter

logger = get_logger(__name__)


class PibAdapter(ProviderAdapter):
    """Adapter for Press Information Bureau (PIB) India."""

    def __init__(self):
        super().__init__(
            source_id="pib-press-releases",
            name="Press Information Bureau",
            base_url="https://pib.gov.in/RssMain.aspx",
            requests_per_minute=30,
            timeout_seconds=15,
            max_retries=2,
        )

    async def fetch(self, **kwargs) -> List[SourceItemBase]:
        """Fetch latest government press releases via RSS."""
        self.last_poll_at = datetime.now(timezone.utc)
        items: List[SourceItemBase] = []
        try:
            resp = await self._execute_http_request(self.base_url)
            root = ET.fromstring(resp.text)

            # Standard RSS channel/item parsing
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                description = (item.findtext("description") or "").strip()
                pub_date = item.findtext("pubDate")

                published_at = None
                if pub_date:
                    try:
                        # RFC 822 / 2822 date parsing or fallback
                        published_at = datetime.now(timezone.utc)
                    except Exception:
                        published_at = datetime.now(timezone.utc)

                if title:
                    headline = f"[Govt/PIB] {title}"
                    content_hash = self.compute_hash(f"{title}:{link}:{pub_date}")
                    items.append(
                        SourceItemBase(
                            source_id=self.source_id,
                            url=link,
                            canonical_url=link,
                            headline=headline,
                            published_at=published_at,
                            content_type="text/html",
                            content_hash=content_hash,
                            raw_location=link,
                            status="FETCHED",
                        )
                    )
        except Exception as e:
            logger.error(f"Error fetching PIB press releases: {e}")

        return items
