"""Manual ingestion and pipeline trigger endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.database import get_db
from services.collector.universe_manager import universe_manager
from services.collector.poller import collector_poller
from services.processor.pipeline import event_processor_pipeline
from services.notifier.telegram_bot import telegram_notifier

router = APIRouter(prefix="/ingest", tags=["Ingestion & Pipeline Control"])


@router.post("/universe")
async def trigger_universe_refresh(db: AsyncSession = Depends(get_db)):
    """Manually trigger dynamic NSE + BSE universe discovery and ISIN deduplication."""
    stats = await universe_manager.refresh_universe(db)
    return {"status": "success", "message": "Universe refresh completed", "stats": stats}


@router.post("/poll")
async def trigger_source_polling(db: AsyncSession = Depends(get_db)):
    """Manually trigger source collection from all active adapters."""
    stats = await collector_poller.poll_all(db)
    return {"status": "success", "message": "Source polling completed", "stats": stats}


@router.post("/process")
async def trigger_event_processing(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Manually trigger event extraction, entity matching, and materiality triage."""
    stats = await event_processor_pipeline.process_batch(db, limit=limit)
    return {"status": "success", "message": "Batch processing completed", "stats": stats}


@router.post("/alerts")
async def trigger_alert_dispatch(db: AsyncSession = Depends(get_db)):
    """Manually trigger Telegram alert dispatch for pending HIGH/CRITICAL events."""
    stats = await telegram_notifier.send_pending_alerts(db)
    return {"status": "success", "message": "Alert dispatch completed", "stats": stats}
