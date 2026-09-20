"""Event Processing Pipeline: Entity matching, document extraction, fact extraction, and materiality triage."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.logging import get_logger
from packages.common.models import (
    Company,
    Security,
    SourceItem,
    Document,
    DocumentPage,
    Event,
    EventFact,
    AlertRecord,
    FinancialSnapshot,
    MarketSnapshot,
)
from packages.schemas.source import SourceItemBase
from packages.documents.extractor import document_extractor
from packages.market_data.reaction import market_reaction_engine
from packages.ai.agents import (
    entity_resolver_agent,
    event_classifier_agent,
    materiality_analyst_agent,
)

logger = get_logger(__name__)


class EventProcessorPipeline:
    """Processes newly fetched source items into validated, triaged Event entities with strict provenance."""

    async def _load_entity_lookup_maps(self, session: AsyncSession):
        """Build in-memory lookup caches for symbols, scrip codes, and names."""
        # 1. Securities map: symbol -> company_id
        sec_res = await session.execute(select(Security.symbol, Security.company_id))
        symbols_index = {row[0]: row[1] for row in sec_res.all()}

        # 2. BSE scrip codes map: scrip_code -> company_id
        scrip_res = await session.execute(
            select(Security.bse_scrip_code, Security.company_id).where(Security.bse_scrip_code.isnot(None))
        )
        scrips_index = {str(row[0]): row[1] for row in scrip_res.all()}

        # 3. Company names map: legal_name -> company_id
        comp_res = await session.execute(select(Company.legal_name, Company.id))
        names_index = {row[0]: row[1] for row in comp_res.all()}

        return symbols_index, scrips_index, names_index

    async def process_item(
        self,
        session: AsyncSession,
        item: Optional[SourceItem] = None,
        source_item: Optional[SourceItem] = None,
        content_bytes: Optional[bytes] = None,
        raw_content: Optional[bytes] = None,
        symbols_index: Optional[Dict[str, UUID]] = None,
        scrips_index: Optional[Dict[str, UUID]] = None,
        names_index: Optional[Dict[str, UUID]] = None,
        run_id: Optional[str] = None,
    ) -> Optional[Event]:
        """Processes a single source item through the complete extraction, triage, and persistence pipeline."""
        target_item = item or source_item
        if not target_item:
            raise ValueError("An item or source_item must be provided to process_item.")

        cid = run_id or str(uuid.uuid4())

        # 1. Document extraction & storage if content is available
        doc_record: Optional[Document] = None
        raw_data = content_bytes or raw_content or (target_item.headline.encode("utf-8") if target_item.headline else None)
        if raw_data:
            doc_info = document_extractor.extract_document(
                raw_data,
                mime_type=target_item.content_type or "text/plain",
            )
            sha256 = doc_info["sha256"]

            # Idempotent document lookup
            doc_q = select(Document).where(Document.sha256 == sha256)
            doc_record = (await session.execute(doc_q)).scalar_one_or_none()

            if not doc_record:
                doc_record = Document(
                    source_item_id=target_item.id,
                    mime_type=doc_info["mime_type"],
                    sha256=sha256,
                    page_count=doc_info["page_count"],
                    text_quality=doc_info["text_quality"],
                    storage_path=target_item.raw_location or f"memory://{sha256}",
                )
                session.add(doc_record)
                await session.flush()

                for p in doc_info["pages"]:
                    p_num = p["page_number"] if isinstance(p, dict) else p[0]
                    p_text = p["text"] if isinstance(p, dict) else p[1]
                    page = DocumentPage(
                        document_id=doc_record.id,
                        page_number=p_num,
                        text=p_text,
                    )
                    session.add(page)
                await session.flush()


        # 2. Entity Resolution
        company_id = entity_resolver_agent.resolve(
            target_item.headline,
            symbols_index=symbols_index or {},
            scrips_index=scrips_index or {},
            names_index=names_index or {},
        )

        # 3. Classify event deterministically
        text_content = ""
        if raw_data:
            try:
                if isinstance(raw_data, bytes):
                    text_content = raw_data.decode("utf-8", errors="ignore")
                elif isinstance(raw_data, str):
                    text_content = raw_data
            except Exception:
                pass

        item_schema = SourceItemBase(
            source_id=target_item.source_id,
            url=target_item.url,
            headline=target_item.headline,
            published_at=target_item.published_at,
            content_hash=target_item.content_hash,
        )
        classification = await event_classifier_agent.classify(item_schema, filing_text=text_content)

        # 4. Check for duplicate event on this source_item and event_type
        existing_ev_q = select(Event).where(
            Event.source_item_id == target_item.id,
            Event.event_type == classification.event_type.value,
        )
        existing_event = (await session.execute(existing_ev_q)).scalar_one_or_none()
        if existing_event:
            logger.info(f"Event already extracted for source item {target_item.id}. Skipping duplicate.")
            target_item.status = "PROCESSED"
            return existing_event

        # 5. Lookup company LTM revenue for materiality triage
        annual_rev: Optional[Decimal] = None
        if company_id:
            fin_res = await session.execute(
                select(FinancialSnapshot.revenue)
                .where(FinancialSnapshot.company_id == company_id)
                .order_by(FinancialSnapshot.snapshot_date.desc())
                .limit(1)
            )
            annual_rev = fin_res.scalar_one_or_none()

        # 6. Materiality triage
        materiality = materiality_analyst_agent.analyze(
            event_type=classification.event_type,
            amount_inr=classification.amount,
            annual_revenue_inr=annual_rev,
        )

        # 7. Create Event record
        event = Event(
            company_id=company_id,
            source_item_id=target_item.id,
            event_type=classification.event_type.value,
            importance=materiality.importance.value,
            headline=target_item.headline,
            event_time=target_item.published_at or target_item.fetched_at,
            announcement_time=target_item.published_at or target_item.fetched_at,
            amount=classification.amount,
            currency="INR",
            status="EXTRACTED",
            confidence=classification.confidence,
        )
        session.add(event)
        await session.flush()


        # 8. Save extracted facts with document provenance
        for fact in classification.facts:
            event_fact = EventFact(
                event_id=event.id,
                fact_key=fact.get("key", "metric"),
                fact_value=fact,
                source_page=1,
                confidence=classification.confidence,
            )
            session.add(event_fact)

        # Add why_flagged reasons to facts
        flagged_reasons = getattr(materiality, "why_flagged", None) or getattr(materiality, "reasons", None)
        if flagged_reasons:
            session.add(
                EventFact(
                    event_id=event.id,
                    fact_key="why_flagged",
                    fact_value={"reasons": flagged_reasons},
                    source_page=1,
                    confidence=1.0,
                )
            )

        # 9. Enrich with financial context (e.g. order % of revenue)
        if classification.amount and annual_rev and annual_rev > 0:
            pct_rev = float((classification.amount / annual_rev) * Decimal(100))
            session.add(
                EventFact(
                    event_id=event.id,
                    fact_key="scale_vs_revenue",
                    fact_value={"annual_revenue_inr": float(annual_rev), "percent_of_revenue": round(pct_rev, 2)},
                    source_page=1,
                    confidence=1.0,
                )
            )

        # 10. Check market reaction if snapshots exist
        if company_id:
            # Query recent market snapshots for company securities
            sec_q = select(Security.id).where(Security.company_id == company_id)
            raw_sec_ids = (await session.execute(sec_q)).scalars().all()
            sec_ids = [s.id if hasattr(s, "id") else s for s in raw_sec_ids if s is not None]
            if sec_ids:
                snap_q = (
                    select(MarketSnapshot)
                    .where(MarketSnapshot.security_id.in_(sec_ids))
                    .order_by(MarketSnapshot.timestamp.desc())
                    .limit(25)
                )
                snapshots = (await session.execute(snap_q)).scalars().all()
                if len(snapshots) >= 2:
                    prices = [float(s.close) for s in reversed(snapshots)]
                    volumes = [float(s.volume) for s in reversed(snapshots)]
                    price_publish = Decimal(str(prices[-2]))
                    price_close = Decimal(str(prices[-1]))
                    vol_today = Decimal(str(volumes[-1]))
                    vol_hist = [Decimal(str(v)) for v in volumes[:-1]]
                    reaction = market_reaction_engine.calculate(
                        event_id=event.id,
                        announcement_time=event.announcement_time,
                        price_at_publish=price_publish,
                        close_price=price_close,
                        volume_today=vol_today,
                        volume_history_20d=vol_hist,
                    )
                    session.add(
                        EventFact(
                            event_id=event.id,
                            fact_key="market_reaction",
                            fact_value=reaction.model_dump(mode="json"),
                            source_page=1,
                            confidence=1.0,
                        )
                    )


        # 11. Queue alert if HIGH or CRITICAL
        if materiality.importance.value in ("CRITICAL", "HIGH"):
            # Check if alert already exists for this event and alert_class
            existing_alert = (
                await session.execute(
                    select(AlertRecord).where(
                        AlertRecord.event_id == event.id,
                        AlertRecord.alert_class == materiality.importance.value,
                    )
                )
            ).scalar_one_or_none()

            if not existing_alert:
                alert = AlertRecord(
                    event_id=event.id,
                    channel="telegram",
                    alert_class=materiality.importance.value,
                    delivery_status="PENDING",
                )
                session.add(alert)

        target_item.status = "PROCESSED"
        return event


    async def process_batch(self, session: AsyncSession, limit: int = 50) -> Dict[str, int]:
        """Process a batch of pending source items."""
        query = (
            select(SourceItem)
            .where(SourceItem.status == "FETCHED")
            .order_by(SourceItem.fetched_at.asc())
            .limit(limit)
        )
        items = (await session.execute(query)).scalars().all()
        if not items:
            return {"processed": 0, "events_created": 0, "alerts_queued": 0}

        symbols_index, scrips_index, names_index = await self._load_entity_lookup_maps(session)
        stats = {"processed": 0, "events_created": 0, "alerts_queued": 0}

        for item in items:
            stats["processed"] += 1
            event = await self.process_item(
                session=session,
                item=item,
                symbols_index=symbols_index,
                scrips_index=scrips_index,
                names_index=names_index,
            )
            if event:
                stats["events_created"] += 1
                if event.importance in ("CRITICAL", "HIGH"):
                    stats["alerts_queued"] += 1

        await session.commit()
        logger.info(f"Batch processing complete: {stats}")
        return stats


event_processor_pipeline = EventProcessorPipeline()
