"""Deterministic Equity & Event Screener Router."""
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.database import get_db
from packages.common.models import Company, Security, FinancialSnapshot, MarketQuote, Event

router = APIRouter(prefix="/screener", tags=["Deterministic Screener"])


@router.get("/run")
async def run_screener(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    min_market_cap_cr: Optional[float] = Query(None, description="Min Market Cap in ₹ Crores"),
    max_market_cap_cr: Optional[float] = Query(None, description="Max Market Cap in ₹ Crores"),
    min_pe: Optional[float] = Query(None, description="Min PE ratio"),
    max_pe: Optional[float] = Query(None, description="Max PE ratio"),
    min_roce: Optional[float] = Query(None, description="Min ROCE %"),
    min_roe: Optional[float] = Query(None, description="Min ROE %"),
    event_importance: Optional[str] = Query(None, description="Recent event importance: CRITICAL, HIGH"),
    event_type: Optional[str] = Query(None, description="Filter by event type: ORDER_WIN, CAPEX, etc."),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Execute deterministic multi-factor query over fundamentals, pricing, and corporate events without LLM overhead."""
    # 1. Base query over companies
    stmt = (
        select(Company)
        .where(Company.status == "ACTIVE")
    )

    if sector:
        stmt = stmt.where(func.lower(Company.sector) == sector.lower())
    if industry:
        stmt = stmt.where(func.lower(Company.industry) == industry.lower())

    res = await db.execute(stmt)
    companies = res.scalars().all()

    filtered_results = []

    for comp in companies:
        # Check latest financial snapshot
        fin_res = await db.execute(
            select(FinancialSnapshot)
            .where(FinancialSnapshot.company_id == comp.id)
            .order_by(desc(FinancialSnapshot.snapshot_date))
            .limit(1)
        )
        fin = fin_res.scalar_one_or_none()

        # Check market cap filter (1 Crore = 10,000,000)
        mcap_val = float(fin.market_cap) if fin and fin.market_cap else None
        if min_market_cap_cr is not None:
            if mcap_val is None or (mcap_val / 1e7) < min_market_cap_cr:
                continue
        if max_market_cap_cr is not None:
            if mcap_val is None or (mcap_val / 1e7) > max_market_cap_cr:
                continue

        # Check valuation filters
        pe_val = float(fin.pe) if fin and fin.pe else None
        if min_pe is not None and (pe_val is None or pe_val < min_pe):
            continue
        if max_pe is not None and (pe_val is None or pe_val > max_pe):
            continue

        roce_val = float(fin.roce) if fin and fin.roce else None
        if min_roce is not None and (roce_val is None or roce_val < min_roce):
            continue

        roe_val = float(fin.roe) if fin and fin.roe else None
        if min_roe is not None and (roe_val is None or roe_val < min_roe):
            continue

        # Check event filter if requested
        if event_importance or event_type:
            ev_stmt = select(func.count(Event.id)).where(Event.company_id == comp.id)
            if event_importance:
                ev_stmt = ev_stmt.where(Event.importance == event_importance.upper())
            if event_type:
                ev_stmt = ev_stmt.where(Event.event_type == event_type.upper())
            ev_count = (await db.execute(ev_stmt)).scalar() or 0
            if ev_count == 0:
                continue

        # Fetch primary security and quote
        sec_res = await db.execute(
            select(Security).where(Security.company_id == comp.id, Security.is_active.is_(True))
        )
        securities = sec_res.scalars().all()
        primary_sec = securities[0] if securities else None

        quote_data = None
        if primary_sec:
            mq_res = await db.execute(
                select(MarketQuote).where(MarketQuote.security_id == primary_sec.id)
            )
            mq = mq_res.scalar_one_or_none()
            if mq:
                quote_data = {
                    "last_price": float(mq.last_price),
                    "change_pct": mq.change_pct,
                    "volume": int(mq.volume),
                    "vwap": float(mq.vwap) if mq.vwap else None,
                }

        filtered_results.append({
            "company_id": str(comp.id),
            "isin": comp.isin,
            "legal_name": comp.legal_name,
            "common_name": comp.common_name,
            "sector": comp.sector,
            "industry": comp.industry,
            "primary_symbol": primary_sec.symbol if primary_sec else None,
            "primary_exchange": primary_sec.exchange if primary_sec else None,
            "quote": quote_data,
            "financials": {
                "pe": pe_val,
                "pb": float(fin.pb) if fin and fin.pb else None,
                "roce": roce_val,
                "roe": roe_val,
                "market_cap_cr": round(mcap_val / 1e7, 2) if mcap_val else None,
                "debt_cr": round(float(fin.debt) / 1e7, 2) if fin and fin.debt else None,
            } if fin else None,
        })

    paginated = filtered_results[offset : offset + limit]

    return {
        "total": len(filtered_results),
        "limit": limit,
        "offset": offset,
        "results": paginated,
    }


@router.get("/filters")
async def get_screener_available_filters(db: AsyncSession = Depends(get_db)):
    """Returns available unique sectors, industries, and taxonomy classes for populating screener UI dropdowns."""
    sectors_res = await db.execute(
        select(Company.sector).where(Company.sector.is_not(None)).distinct()
    )
    sectors = [s for s in sectors_res.scalars().all() if s]

    industries_res = await db.execute(
        select(Company.industry).where(Company.industry.is_not(None)).distinct()
    )
    industries = [i for i in industries_res.scalars().all() if i]

    from packages.schemas.taxonomy import EventTaxonomy, ImportanceClass
    return {
        "sectors": sorted(sectors),
        "industries": sorted(industries),
        "importance_levels": [i.value for i in ImportanceClass],
        "event_types": [e.value for e in EventTaxonomy],
    }
