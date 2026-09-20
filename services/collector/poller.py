"""Ingestion Poller: Idempotently polls registered adapters and tracks source health."""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.logging import get_logger
from packages.common.models import SourceItem, SourceHealth
from packages.source_clients.nse import NseAdapter
from packages.source_clients.bse import BseAdapter
from packages.source_clients.pib import PibAdapter

logger = get_logger(__name__)


class CollectorPoller:
    """Orchestrates periodic collection from official exchange & government feeds."""

    def __init__(self):
        self.adapters = [
            NseAdapter(),
            BseAdapter(),
            PibAdapter(),
        ]

    async def poll_all(self, session: AsyncSession) -> Dict[str, int]:
        """Polls all adapters concurrently and persists new source items."""
        stats = {"total_fetched": 0, "new_items": 0, "duplicates": 0}

        tasks = [adapter.fetch() for adapter in self.adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for adapter, res in zip(self.adapters, results):
            health_diag = adapter.get_health()

            # Update SourceHealth record in DB
            sh_res = await session.execute(
                select(SourceHealth).where(SourceHealth.source_id == adapter.source_id)
            )
            sh = sh_res.scalar_one_or_none()
            if sh:
                sh.last_poll_at = health_diag["last_poll_at"]
                if health_diag["last_success_at"]:
                    sh.last_success_at = health_diag["last_success_at"]
                sh.consecutive_failures = health_diag["consecutive_failures"]
                sh.success_rate_24h = health_diag["success_rate_24h"]
                sh.latency_ms = health_diag["latency_ms"]
                sh.rate_limit_status = health_diag["rate_limit_status"]

            if isinstance(res, Exception):
                logger.error(f"Collector error on source {adapter.source_id}: {res}")
                continue

            for item in res:
                stats["total_fetched"] += 1
                # Check for existing item by unique (source_id, content_hash)
                exists_query = select(SourceItem).where(
                    SourceItem.source_id == item.source_id,
                    SourceItem.content_hash == item.content_hash,
                )
                existing = (await session.execute(exists_query)).scalar_one_or_none()

                if not existing:
                    db_item = SourceItem(
                        source_id=item.source_id,
                        url=item.url,
                        canonical_url=item.canonical_url,
                        external_id=item.external_id,
                        headline=item.headline,
                        published_at=item.published_at,
                        content_type=item.content_type,
                        content_hash=item.content_hash,
                        raw_location=item.raw_location,
                        status="FETCHED",
                    )
                    session.add(db_item)
                    stats["new_items"] += 1
                else:
                    stats["duplicates"] += 1

        await session.commit()
        logger.info(f"Ingestion cycle completed: {stats}")
        return stats


collector_poller = CollectorPoller()
