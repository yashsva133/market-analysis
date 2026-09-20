"""Telegram Notifier: Dispatches structured, deduplicated alerts for CRITICAL and HIGH events."""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.common.config import settings
from packages.common.logging import get_logger
from packages.common.models import AlertRecord, Event, Company, Security, SourceItem, EventFact, WatchlistItem
from packages.ai.agents import alert_formatter_agent

logger = get_logger(__name__)


class TelegramNotifier:
    """Delivers real-time critical market alerts to Telegram with retry, mute checks, and deduplication."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._client = http_client

    async def send_pending_alerts(
        self,
        session: AsyncSession,
        max_retries: int = 3,
    ) -> Dict[str, int]:
        """Queries pending and retry-eligible alerts and delivers them with strict deduplication."""
        token = self.bot_token or settings.TELEGRAM_BOT_TOKEN
        chat = self.chat_id or settings.TELEGRAM_CHAT_ID

        query = (
            select(AlertRecord)
            .where(AlertRecord.delivery_status.in_(["PENDING", "RETRY"]))
            .options(
                selectinload(AlertRecord.event).selectinload(Event.company).selectinload(Company.securities),
                selectinload(AlertRecord.event).selectinload(Event.source_item),
                selectinload(AlertRecord.event).selectinload(Event.facts),
            )
            .limit(20)
        )
        alerts = (await session.execute(query)).scalars().all()
        if not alerts:
            return {"sent": 0, "skipped": 0, "failed": 0, "muted": 0}

        stats = {"sent": 0, "skipped": 0, "failed": 0, "muted": 0}

        if not token or not chat:
            logger.info("Telegram Bot Token or Chat ID not configured. Marking alerts as SKIPPED_NO_TOKEN.")
            for a in alerts:
                a.delivery_status = "SKIPPED_NO_TOKEN"
                a.sent_at = datetime.now(timezone.utc)
                stats["skipped"] += 1
            await session.commit()
            return stats

        url = f"https://api.telegram.org/bot{token}/sendMessage"

        for alert in alerts:
            event = alert.event
            if not event:
                alert.delivery_status = "SKIPPED_NO_EVENT"
                stats["skipped"] += 1
                continue

            # 1. Check if alert was already sent for this event
            existing_sent = await session.execute(
                select(AlertRecord.id).where(
                    AlertRecord.event_id == event.id,
                    AlertRecord.id != alert.id,
                    AlertRecord.delivery_status == "SENT",
                )
            )
            if existing_sent.scalar_one_or_none():
                logger.info(f"Duplicate alert for event {event.id} already sent. Skipping.")
                alert.delivery_status = "DUPLICATE_SKIPPED"
                stats["skipped"] += 1
                continue

            # 2. Check if company alerts are muted in Watchlist
            if event.company_id:
                mute_check = await session.execute(
                    select(WatchlistItem.id).where(
                        WatchlistItem.company_id == event.company_id,
                        WatchlistItem.is_muted == True,
                    ).limit(1)
                )
                if mute_check.scalar_one_or_none():
                    logger.info(f"Alerts for company {event.company_id} are muted in watchlist. Skipping.")
                    alert.delivery_status = "MUTED_SKIPPED"
                    stats["muted"] += 1
                    continue

            company_name = event.company.legal_name if event.company else "Unknown Entity"
            symbol = "N/A"
            bse_code = None
            if event.company and event.company.securities:
                for s in event.company.securities:
                    if s.exchange == "NSE":
                        symbol = s.symbol
                    elif s.exchange == "BSE":
                        bse_code = s.bse_scrip_code or s.symbol

            # Extract financial context and market reaction from facts
            financial_ctx = None
            market_rxn = None
            why_flagged = [f"Material {event.event_type} disclosure"]
            unknowns = ["Execution schedule", "Margin metrics"]

            if event.facts:
                for fact in event.facts:
                    if fact.fact_key == "why_flagged" and isinstance(fact.fact_value, dict):
                        reasons = fact.fact_value.get("reasons", [])
                        if reasons:
                            why_flagged = reasons
                    elif fact.fact_key == "scale_vs_revenue" and isinstance(fact.fact_value, dict):
                        pct = fact.fact_value.get("percent_of_revenue")
                        rev = fact.fact_value.get("annual_revenue_inr")
                        financial_ctx = f"Order represents ~{pct}% of LTM Annual Revenue (₹{rev:,.0f} INR)."
                    elif fact.fact_key == "market_reaction" and isinstance(fact.fact_value, dict):
                        market_rxn = fact.fact_value.get("summary")

            message_text = alert_formatter_agent.format_telegram_alert(
                company_name=company_name,
                symbol=symbol,
                bse_code=bse_code,
                event_type=event.event_type,
                importance=alert.alert_class,
                headline=event.headline,
                why_flagged=why_flagged,
                unknowns=unknowns,
                source_url=event.source_item.url if event.source_item else None,
                source_publisher=event.source_item.source_id if event.source_item else "Exchange",
                financial_context=financial_ctx,
                market_reaction=market_rxn,
            )

            delivered = False
            client = self._client or httpx.AsyncClient(timeout=10)
            try:
                for attempt in range(1, max_retries + 1):
                    try:
                        resp = await client.post(
                            url,
                            json={
                                "chat_id": chat,
                                "text": message_text,
                                "parse_mode": "Markdown",
                                "disable_web_page_preview": True,
                            },
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        alert.telegram_chat_id = str(chat)
                        alert.telegram_message_id = str(data.get("result", {}).get("message_id", ""))
                        alert.delivery_status = "SENT"
                        alert.sent_at = datetime.now(timezone.utc)
                        stats["sent"] += 1
                        delivered = True
                        break
                    except Exception as attempt_err:
                        logger.warning(f"Telegram dispatch attempt {attempt}/{max_retries} failed: {attempt_err}")
                        if attempt < max_retries:
                            await asyncio.sleep(0.2 * (2 ** (attempt - 1)))
                
                if not delivered:
                    alert.delivery_status = "FAILED"
                    stats["failed"] += 1
            finally:
                if not self._client:
                    await client.aclose()

        await session.commit()
        return stats

    async def send_direct_message(self, text: str) -> bool:
        """Sends an immediate message directly to the configured Telegram chat."""
        token = self.bot_token or settings.TELEGRAM_BOT_TOKEN
        chat = self.chat_id or settings.TELEGRAM_CHAT_ID
        if not token or not chat:
            logger.warning("Telegram bot_token or chat_id not configured.")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        client = self._client or httpx.AsyncClient(timeout=10)
        try:
            resp = await client.post(
                url,
                json={
                    "chat_id": chat,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            resp.raise_for_status()
            logger.info("Direct Telegram message delivered successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send direct Telegram message: {e}")
            return False
        finally:
            if not self._client:
                await client.aclose()


telegram_notifier = TelegramNotifier()
