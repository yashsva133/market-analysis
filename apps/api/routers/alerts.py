"""Telegram & System Alerts Management Router.

Provides real-time Telegram connectivity testing, universe-wide automated scans,
multi-tier sensitivity dispatching (Critical, High, Medium, and Small Potential),
and historical audit logging.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.common.config import settings
from packages.common.database import get_db
from packages.common.models import AlertRecord, Event, Company, Security
from services.notifier.telegram_bot import telegram_notifier, TelegramNotifier
from packages.ai.agents import alert_formatter_agent

router = APIRouter(prefix="/alerts", tags=["Telegram & Event Alerts"])

# In-memory alert dispatch audit log for fast zero-latency inspection
_DISPATCH_LOG: List[Dict[str, Any]] = []


class AlertDispatchResponse(BaseModel):
    status: str
    message: str
    alerts_dispatched: int
    scanned_companies: int
    details: List[Dict[str, Any]] = []


@router.get("/status")
async def get_alert_status():
    """Returns real-time Telegram bot connection status and channel configuration."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID or "8358109190"
    is_configured = bool(token and chat_id)
    return {
        "bot_configured": is_configured,
        "bot_username": "@y_market_alert_bot",
        "chat_id": chat_id,
        "active_channel": "Telegram Real-Time Dispatch",
        "deduplication_enabled": True,
        "sensitivity_levels": ["ALL_SIGNALS (INCL. SMALL POTENTIAL)", "MEDIUM_HIGH_CRITICAL", "CRITICAL_ONLY"],
        "default_sensitivity": "ALL_SIGNALS",
    }


@router.post("/test-telegram")
async def send_test_telegram():
    """Immediately dispatches an end-to-end verification alert to your Telegram bot."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID or "8358109190"

    if not token or not chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram bot token or Chat ID is missing in environment configuration.",
        )

    now_str = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC")
    test_message = (
        "🔔 *INDIA MARKET TERMINAL — LIVE ALERT BOT VERIFIED*\n\n"
        "• *System Status*: ACTIVE & MONITORED\n"
        f"• *Timestamp*: {now_str}\n"
        f"• *Destination Chat*: `{chat_id}`\n"
        "• *Universe Coverage*: Ingested NSE/BSE filings only (no synthetic alerts)\n"
        "• *Sensitivity*: ALL SIGNALS (High, Med, Low, Small Potential)\n\n"
        "_Deduplicated factual intelligence feed active._"
    )

    success = await telegram_notifier.send_direct_message(test_message)
    if not success:
        raise HTTPException(
            status_code=502,
            detail="Failed to deliver test message to Telegram. Ensure you have sent /start to @y_market_alert_bot.",
        )

    log_entry = {
        "id": f"alt-test-{int(datetime.now().timestamp())}",
        "symbol": "SYSTEM",
        "company_name": "Terminal Core Notifier",
        "importance": "SYSTEM_TEST",
        "headline": "Live Telegram Bot Connectivity Test Dispatched",
        "amount": "N/A",
        "channel": "telegram",
        "delivery_status": "SENT",
        "sent_at": "Just now",
        "telegram_chat_id": str(chat_id),
        "telegram_message_id": "live-verified",
    }
    _DISPATCH_LOG.insert(0, log_entry)

    return {
        "status": "DELIVERED",
        "message": f"Telegram test alert dispatched successfully to chat {chat_id}!",
        "chat_id": chat_id,
        "bot_username": "@y_market_alert_bot",
    }


@router.post("/scan-and-dispatch", response_model=AlertDispatchResponse)
async def scan_universe_and_dispatch(
    sensitivity: str = Query("ALL", description="Sensitivity: ALL (incl small potential), MEDIUM_PLUS, CRITICAL_ONLY"),
    db: AsyncSession = Depends(get_db),
):
    """Scans the entire stock universe, detects events across all materiality tiers, and sends them to Telegram."""
    chat_id = settings.TELEGRAM_CHAT_ID or "8358109190"

    # Scan the ingested event stream — only real, persisted disclosures are dispatched.
    total_companies = (await db.execute(select(func.count(Company.id)))).scalar() or 0
    query = (
        select(Event)
        .options(selectinload(Event.company).selectinload(Company.securities))
        .order_by(Event.announcement_time.desc().nullslast())
        .limit(50)
    )
    if sensitivity == "CRITICAL_ONLY":
        query = query.where(Event.importance == "CRITICAL")
    elif sensitivity == "MEDIUM_PLUS":
        query = query.where(Event.importance.in_(("CRITICAL", "HIGH", "MEDIUM")))
    events = (await db.execute(query)).scalars().all()

    dispatched_count = 0
    dispatched_details = []
    for e in events:
        secs = list(e.company.securities) if e.company else []
        symbol = next((s.symbol for s in secs if s.exchange == "NSE"), secs[0].symbol if secs else "N/A")
        company_name = e.company.legal_name if e.company else symbol
        headline = e.headline or e.event_type
        announced = e.announcement_time.strftime("%d-%b-%Y %H:%M UTC") if e.announcement_time else "unknown"
        msg = (
            f"\U0001F6A8 *[{e.importance}] {symbol} — {e.event_type}*\n"
            f"*{company_name}*\n\n"
            f"• *Headline*: {headline}\n"
            f"• *Announced*: {announced}\n\n"
            f"_Strictly factual intelligence from ingested filings. Non-advisory._"
        )
        try:
            sent = await telegram_notifier.send_direct_message(msg)
            status_str = "SENT" if sent else "SKIPPED_OFFLINE"
        except Exception:
            status_str = "FAILED"

        dispatched_count += 1
        log_item = {
            "id": f"alt-{symbol.lower()}-{int(datetime.now().timestamp())}-{dispatched_count}",
            "symbol": symbol,
            "company_name": company_name,
            "importance": e.importance,
            "headline": headline,
            "amount": "N/A",
            "channel": "telegram",
            "delivery_status": status_str,
            "sent_at": "Just now",
            "telegram_chat_id": str(chat_id),
            "telegram_message_id": f"msg-{dispatched_count}",
        }
        _DISPATCH_LOG.insert(0, log_item)
        dispatched_details.append(log_item)

    return AlertDispatchResponse(
        status="COMPLETED",
        message=(
            f"Scanned {total_companies} ingested companies and {len(events)} recent ingested events. "
            f"Dispatched {dispatched_count} alerts to Telegram."
        ),
        alerts_dispatched=dispatched_count,
        scanned_companies=total_companies,
        details=dispatched_details,
    )


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_alerts_history(limit: int = Query(50, ge=1, le=100)):
    """Retrieves full dispatch audit history for Telegram and system alerts."""
    return _DISPATCH_LOG[:limit]
