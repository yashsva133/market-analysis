"""Global Unified Search Router.

Multi-entity search across the ingested database only: companies (name,
ticker, BSE scrip, ISIN, aliases) and corporate events. No hardcoded index —
results reflect exactly what has been synced.
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.common.database import get_db
from packages.common.models import Company, CompanyAlias, Event, Security

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search_all(
    q: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Global search returning matching companies and events from the ingested universe."""
    query = q.strip()
    lim = limit if isinstance(limit, int) else 20
    if not query:
        return {"status": "ok", "query": q, "count": 0, "companies": [], "events": [], "sectors": []}

    pattern = f"%{query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%"
    upper_key = query.upper()

    company_res = await db.execute(
        select(Company)
        .where(or_(
            Company.isin.ilike(pattern),
            Company.legal_name.ilike(pattern),
            Company.common_name.ilike(pattern),
            Company.securities.any(or_(Security.symbol.ilike(pattern), Security.bse_scrip_code.ilike(pattern))),
            Company.aliases.any(CompanyAlias.alias.ilike(pattern)),
        ))
        .options(selectinload(Company.securities))
        .order_by(Company.legal_name)
        .limit(lim)
    )
    companies = company_res.scalars().all()

    matched_companies = []
    for c in companies:
        secs = list(c.securities)
        nse_sec = next((s for s in secs if s.exchange == "NSE"), None)
        bse_sec = next((s for s in secs if s.exchange == "BSE"), None)
        matched_companies.append({
            "symbol": (nse_sec or secs[0]).symbol if secs else None,
            "name": c.legal_name,
            "isin": c.isin,
            "sector": c.sector,
            "bse_scrip": bse_sec.bse_scrip_code if bse_sec else None,
            "company_id": str(c.id),
        })

    event_res = await db.execute(
        select(Event)
        .where(or_(Event.headline.ilike(pattern), Event.event_type.ilike(pattern)))
        .options(selectinload(Event.company))
        .order_by(Event.announcement_time.desc().nullslast())
        .limit(lim)
    )
    events = event_res.scalars().all()

    matched_events = []
    for e in events:
        matched_events.append({
            "id": str(e.id),
            "symbol": None,
            "company_name": e.company.legal_name if e.company else None,
            "headline": e.headline,
            "event_type": e.event_type,
            "importance": e.importance,
        })

    # Sectors are derived from the ingested company master, not a hardcoded list
    sector_res = await db.execute(
        select(Company.sector, func.count(Company.id))
        .where(Company.sector.ilike(pattern))
        .group_by(Company.sector)
        .limit(10)
    )
    matched_sectors = [
        {"name": sector, "company_count": count} for sector, count in sector_res.all() if sector
    ]

    total_results = len(matched_companies) + len(matched_events) + len(matched_sectors)

    return {
        "status": "ok",
        "query": q,
        "count": total_results,
        "companies": matched_companies[:lim],
        "events": matched_events[:lim],
        "sectors": matched_sectors[:lim],
        "note": "Search covers the ingested universe only. Sync exchange masters to broaden coverage.",
    }
