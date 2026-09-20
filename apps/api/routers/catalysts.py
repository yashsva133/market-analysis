"""High-Impact Catalyst Opportunities Router.

Catalysts are derived exclusively from ingested high-importance exchange
events (order wins, capex, capacity expansion, M&A). Live quotes enrich the
entries when a feed is configured; no curated or fabricated catalog is served.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.common.database import get_db
from packages.common.logging import get_logger
from packages.common.models import Event
from packages.market_data.free_provider import free_provider

logger = get_logger(__name__)

router = APIRouter(prefix="/market/catalysts", tags=["Catalysts & 5%+ Movers"])

CATALYST_EVENT_TYPES = (
    "ORDER_WIN",
    "CAPEX",
    "CAPACITY_EXPANSION",
    "MNA",
    "PLANT",
    "DEMERGER",
)


@router.get("", response_model=List[Dict[str, Any]])
async def get_catalysts(db: AsyncSession = Depends(get_db)):
    """Retrieves high-importance ingested events as catalyst candidates, enriched with live ticks when available."""
    query = (
        select(Event)
        .where(Event.event_type.in_(CATALYST_EVENT_TYPES))
        .where(Event.importance.in_(("CRITICAL", "HIGH")))
        .options(selectinload(Event.company).selectinload(Event.company.securities), selectinload(Event.source_item))
        .order_by(Event.announcement_time.desc().nullslast())
        .limit(24)
    )
    events = (await db.execute(query)).scalars().all()

    results: List[Dict[str, Any]] = []
    for e in events:
        company = e.company
        symbol = None
        bse_code = None
        if company and company.securities:
            nse_sec = next((s for s in company.securities if s.exchange == "NSE"), None)
            symbol = (nse_sec or company.securities[0]).symbol
            bse_code = next((s.bse_scrip_code for s in company.securities if s.bse_scrip_code), None)

        entry: Dict[str, Any] = {
            "id": str(e.id),
            "symbol": symbol,
            "bse_code": bse_code,
            "company_name": company.legal_name if company else None,
            "sector": company.sector if company else None,
            "catalyst_title": e.headline,
            "catalyst_type": e.event_type,
            "importance": e.importance,
            "announcement_time": e.announcement_time.isoformat() if e.announcement_time else None,
            "source": e.source_item.source_id if e.source_item else None,
        }

        if symbol:
            try:
                quote = await free_provider.get_live_quote(symbol)
                if quote and quote.last_price > 0:
                    entry["last_price"] = f"₹{quote.last_price:,.2f}"
                    sign = "+" if quote.change_pct >= 0 else ""
                    entry["change_pct"] = f"{sign}{quote.change_pct:.2f}%"
                    entry["recent_move"] = f"{sign}{quote.change_pct:.2f}% Live Move | {quote.volume:,} Vol"
            except Exception as ex:
                logger.warning(f"Failed to fetch live quote for catalyst {symbol}: {ex}")

        results.append(entry)
    return results
