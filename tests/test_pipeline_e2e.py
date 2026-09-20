"""End-to-end Pipeline Replay and Deduplication Integration Tests."""
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from packages.common.models import Company, Security, SourceItem, Document, Event, EventFact, AlertRecord
from packages.documents.extractor import extract_document
from packages.schemas.taxonomy import EventTaxonomy, ImportanceClass
from services.processor.pipeline import EventProcessorPipeline


def test_document_extractor_sha256_and_pages():
    """Verify document extractor generates deterministic SHA-256 and text quality scores."""
    sample_text = (
        "LARSEN & TOUBRO LIMITED\n"
        "Corporate Disclosure under Regulation 30 of SEBI (LODR) Regulations, 2015.\n"
        "The company has secured a significant order valued at INR 8,500 Crores from the Ministry of Railways.\n"
        "The project execution timeline is 36 months across the Western corridor."
    )

    doc_info = extract_document(
        raw_bytes=sample_text.encode("utf-8"),
        content_type="text/plain",
        filename="lt_order_announcement.txt",
    )

    assert doc_info["sha256"] == hashlib.sha256(sample_text.encode("utf-8")).hexdigest()
    assert doc_info["page_count"] == 1
    assert doc_info["text_quality"] > 0.8
    assert len(doc_info["pages"]) == 1
    assert "8,500 Crores" in doc_info["pages"][0]["text"]


@pytest.mark.asyncio
async def test_complete_pipeline_replay_and_idempotency():
    """Verify complete path from raw capture to event, document, reaction, and alert; and verify duplicate ingestion creates no duplicates."""
    pipeline = EventProcessorPipeline()

    company_id = uuid.uuid4()
    company = Company(
        id=company_id,
        isin="INE018A01030",
        legal_name="Larsen & Toubro Limited",
        status="ACTIVE",
    )
    security = Security(
        id=uuid.uuid4(),
        company_id=company_id,
        exchange="NSE",
        symbol="LT",
        is_active=True,
    )

    raw_text = (
        "Larsen & Toubro wins major contract worth Rs 8500 crore from Ministry of Railways. "
        "The contract is binding and spans a duration of 36 months for railway electrification."
    )
    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    source_item = SourceItem(
        id=uuid.uuid4(),
        source_id="nse-announcements",
        headline="Larsen & Toubro wins major contract worth Rs 8500 crore from Ministry of Railways",
        published_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        content_type="text/plain",
        content_hash=content_hash,
        raw_location=None,
        status="FETCHED",
    )

    persisted_objects = []

    # Setup mock session
    mock_session = AsyncMock()
    mock_session.add = MagicMock(side_effect=lambda obj: persisted_objects.append(obj))
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    # Track execute queries to simulate database lookups
    created_events = []
    created_documents = []

    async def mock_execute(query):
        q_str = str(query)
        res = MagicMock()
        if "companies" in q_str:
            res.scalar_one_or_none.return_value = company
        elif "financial_snapshots" in q_str:
            # Return financial snapshot with LTM revenue of ₹10,000 Cr
            # ₹8,500 Cr / ₹10,000 Cr = 85% -> CRITICAL!
            res.scalar_one_or_none.return_value = Decimal("100000000000")  # 10,000 Cr
        elif "documents.sha256 =" in q_str:
            # Check for existing document
            res.scalar_one_or_none.return_value = created_documents[0] if created_documents else None
        elif "events.source_item_id =" in q_str:
            # Check for existing event
            res.scalar_one_or_none.return_value = created_events[0] if created_events else None
        elif "securities" in q_str:
            res.scalars.return_value.all.return_value = [security]
        elif "market_snapshots" in q_str:
            res.scalars.return_value.all.return_value = []
        elif "alerts.event_id =" in q_str:
            res.scalar_one_or_none.return_value = None
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute = AsyncMock(side_effect=mock_execute)

    # First pass: Run pipeline with raw text
    event_1 = await pipeline.process_item(
        source_item=source_item,
        session=mock_session,
        raw_content=raw_text.encode("utf-8"),
        names_index={"Larsen & Toubro": company_id},
    )

    assert event_1 is not None
    assert event_1.event_type == EventTaxonomy.ORDER_WIN
    assert event_1.importance == ImportanceClass.CRITICAL
    assert event_1.company_id == company_id

    # Verify document and page created
    docs = [o for o in persisted_objects if isinstance(o, Document)]
    assert len(docs) == 1
    created_documents.append(docs[0])

    # Verify event facts created
    facts = [o for o in persisted_objects if isinstance(o, EventFact)]
    fact_keys = {f.fact_key for f in facts}
    assert "scale_vs_revenue" in fact_keys or "contract_amount_inr" in fact_keys

    # Verify alert was queued for CRITICAL importance
    alerts = [o for o in persisted_objects if isinstance(o, AlertRecord)]
    assert len(alerts) == 1
    assert alerts[0].alert_class == ImportanceClass.CRITICAL
    assert alerts[0].channel == "telegram"

    created_events.append(event_1)

    # Second pass: Ingest the EXACT same source item again to verify deduplication
    persisted_objects.clear()
    event_2 = await pipeline.process_item(
        source_item=source_item,
        session=mock_session,
        raw_content=raw_text.encode("utf-8"),
        names_index={"Larsen & Toubro": company_id},
    )

    # Should return existing event without adding duplicate Document or Event objects
    assert event_2.id == event_1.id
    new_docs = [o for o in persisted_objects if isinstance(o, Document)]
    new_events = [o for o in persisted_objects if isinstance(o, Event)]
    assert len(new_docs) == 0
    assert len(new_events) == 0
