"""Corporate Actions & Market Calendar Router.

Corporate actions are derived exclusively from ingested exchange events
(dividends, bonuses, splits, buybacks, board meetings, AGMs). Ex-dates and
record dates are not part of the ingested announcement payload, so they are
reported as null instead of being synthesized.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.common.database import get_db
from packages.common.models import Company, Event

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

CORPORATE_ACTION_TYPES = (
    "DIVIDEND",
    "BONUS",
    "SPLIT",
    "BUYBACK",
    "BOARD_MEETING",
    "AGM",
    "RIGHTS",
)


def _serialize_event(e: Event) -> Dict[str, Any]:
    company = e.company
    symbol = None
    if company and company.securities:
        symbol = next(
            (s.symbol for s in company.securities if s.exchange == "NSE"),
            company.securities[0].symbol,
        )
    announced = e.announcement_time
    return {
        "id": str(e.id),
        "symbol": symbol,
        "company_name": company.legal_name if company else None,
        "isin": company.isin if company else None,
        "action_type": e.event_type,
        "purpose": e.headline,
        "announcement_date": announced.date().isoformat() if announced else None,
        # Ex-date and record date are not present in ingested announcements
        "ex_date": None,
        "record_date": None,
        "dividend_amount": None,
        "ratio": None,
        "source": e.source_item.source_id if e.source_item else None,
        "filing_url": e.source_item.url if e.source_item and hasattr(e.source_item, "url") else None,
        "status": "ANNOUNCED",
        "days_until": None,
        "timing_label": (
            f"Announced {announced.strftime('%d %b %Y')}" if announced else "Announcement date not ingested"
        ),
    }


@router.get("/actions")
async def get_corporate_actions(
    symbol: Optional[str] = Query(None, description="Filter by ticker (e.g. LT, TCS)"),
    action_type: Optional[str] = Query(None, description="DIVIDEND, BONUS, SPLIT, BUYBACK, BOARD_MEETING, AGM"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve ingested corporate actions with filtering by symbol, action type, and date window."""
    query = (
        select(Event)
        .where(Event.event_type.in_(CORPORATE_ACTION_TYPES))
        .options(selectinload(Event.company).selectinload(Company.securities), selectinload(Event.source_item))
        .order_by(Event.announcement_time.desc().nullslast())
        .limit(500)
    )
    events = (await db.execute(query)).scalars().all()

    actions = [_serialize_event(e) for e in events]

    if isinstance(symbol, str) and symbol.strip():
        actions = [x for x in actions if x["symbol"] and x["symbol"].upper() == symbol.strip().upper()]

    if isinstance(action_type, str) and action_type.strip() and action_type.upper() != "ALL":
        actions = [x for x in actions if x["action_type"].upper() == action_type.strip().upper()]

    if isinstance(start_date, str) and start_date.strip():
        actions = [x for x in actions if x["announcement_date"] and x["announcement_date"] >= start_date.strip()]

    if isinstance(end_date, str) and end_date.strip():
        actions = [x for x in actions if x["announcement_date"] and x["announcement_date"] <= end_date.strip()]

    lim = limit if isinstance(limit, int) else 50

    return {
        "status": "ok",
        "count": len(actions),
        "actions": actions[:lim],
        "note": "Derived from ingested exchange announcements only. Ex/record dates are not yet ingested and are reported as null.",
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary")
async def get_actions_summary(db: AsyncSession = Depends(get_db)):
    """Get high-level statistics on ingested corporate actions."""
    query = (
        select(Event)
        .where(Event.event_type.in_(CORPORATE_ACTION_TYPES))
        .options(selectinload(Event.company).selectinload(Company.securities))
        .order_by(Event.announcement_time.desc().nullslast())
        .limit(500)
    )
    events = (await db.execute(query)).scalars().all()
    actions = [_serialize_event(e) for e in events]

    counts: Dict[str, int] = {}
    for a in actions:
        t = a["action_type"]
        counts[t] = counts.get(t, 0) + 1

    return {
        "total_actions": len(actions),
        "by_type": counts,
        "upcoming_30_days": 0,
        "note": "Upcoming-window counts require ex-dates, which are not part of ingested announcements.",
    }
