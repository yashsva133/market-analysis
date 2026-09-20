"""Developer and Research Data Explorer Router.

Provides transparent inspection into:
- Companies & Securities
- Events & Event Facts
- Documents & Document Pages
- Financial Snapshots
- Market Quotes & Snapshots
- AI Runs & Audited Tokens
- Telegram Alerts & Delivery Logs
- Source Health Records
"""
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.database import get_db
from packages.common.models import (
    Company,
    Security,
    Event,
    EventFact,
    Document,
    DocumentPage,
    FinancialSnapshot,
    MarketQuote,
    AIRun,
    AIOutput,
    AlertRecord,
    SourceHealth,
    UniverseChangeEvent,
)

router = APIRouter(prefix="/explorer", tags=["Data Explorer"])


@router.get("/summary")
async def get_explorer_summary(db: AsyncSession = Depends(get_db)):
    """Returns row counts and freshness across all core tables. Database failures surface as 503."""
    return {
        "companies": (await db.execute(select(func.count(Company.id)))).scalar() or 0,
        "securities": (await db.execute(select(func.count(Security.id)))).scalar() or 0,
        "events": (await db.execute(select(func.count(Event.id)))).scalar() or 0,
        "documents": (await db.execute(select(func.count(Document.id)))).scalar() or 0,
        "document_pages": (await db.execute(select(func.count(DocumentPage.id)))).scalar() or 0,
        "financial_snapshots": (await db.execute(select(func.count(FinancialSnapshot.id)))).scalar() or 0,
        "market_quotes": (await db.execute(select(func.count(MarketQuote.id)))).scalar() or 0,
        "ai_runs": (await db.execute(select(func.count(AIRun.id)))).scalar() or 0,
        "alerts": (await db.execute(select(func.count(AlertRecord.id)))).scalar() or 0,
        "universe_changes": (await db.execute(select(func.count(UniverseChangeEvent.id)))).scalar() or 0,
    }


@router.get("/documents")
async def list_documents(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse stored filing documents with SHA256 and page counts."""
    res = await db.execute(
        select(Document).order_by(desc(Document.extracted_at)).offset(offset).limit(limit)
    )
    docs = res.scalars().all()
    total = (await db.execute(select(func.count(Document.id)))).scalar() or 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "documents": [
            {
                "id": str(d.id),
                "source_item_id": str(d.source_item_id),
                "mime_type": d.mime_type,
                "sha256": d.sha256,
                "page_count": d.page_count,
                "text_quality": d.text_quality,
                "extracted_at": d.extracted_at.isoformat(),
            }
            for d in docs
        ],
    }


@router.get("/documents/{document_id}/pages")
async def get_document_pages(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all extracted text pages and citations for a document."""
    res = await db.execute(
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
    )
    pages = res.scalars().all()
    return {
        "document_id": str(document_id),
        "count": len(pages),
        "pages": [
            {
                "page_number": p.page_number,
                "char_length": len(p.text),
                "snippet": p.text[:300] + ("..." if len(p.text) > 300 else ""),
            }
            for p in pages
        ],
    }


@router.get("/ai-runs")
async def list_ai_runs(
    task: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse audited AI model invocations, token counts, and cache performance."""
    stmt = select(AIRun).order_by(desc(AIRun.started_at)).offset(offset).limit(limit)
    if task:
        stmt = stmt.where(AIRun.task == task)

    res = await db.execute(stmt)
    runs = res.scalars().all()
    total = (await db.execute(select(func.count(AIRun.id)))).scalar() or 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "runs": [
            {
                "id": str(r.id),
                "provider": r.provider,
                "model": r.model,
                "task": r.task,
                "started_at": r.started_at.isoformat(),
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "status": r.status,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
                "cached": r.cached,
                "error": r.error,
            }
            for r in runs
        ],
    }


@router.get("/alerts")
async def list_alerts(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse sent and queued Telegram alerts."""
    res = await db.execute(
        select(AlertRecord).order_by(desc(AlertRecord.sent_at)).offset(offset).limit(limit)
    )
    alerts = res.scalars().all()
    total = (await db.execute(select(func.count(AlertRecord.id)))).scalar() or 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "alerts": [
            {
                "id": str(a.id),
                "event_id": str(a.event_id),
                "channel": a.channel,
                "alert_class": a.alert_class,
                "delivery_status": a.delivery_status,
                "sent_at": a.sent_at.isoformat() if a.sent_at else None,
            }
            for a in alerts
        ],
    }


@router.get("/universe-changes")
async def list_universe_changes(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse dynamic NSE+BSE universe changes (new listings, symbol changes, suspensions)."""
    res = await db.execute(
        select(UniverseChangeEvent)
        .order_by(desc(UniverseChangeEvent.detected_at))
        .offset(offset)
        .limit(limit)
    )
    changes = res.scalars().all()
    total = (await db.execute(select(func.count(UniverseChangeEvent.id)))).scalar() or 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "changes": [
            {
                "id": str(c.id),
                "isin": c.isin,
                "exchange": c.exchange,
                "symbol": c.symbol,
                "change_type": c.change_type,
                "details": c.details,
                "detected_at": c.detected_at.isoformat(),
            }
            for c in changes
        ],
    }
