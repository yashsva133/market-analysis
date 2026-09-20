"""Local Watchlist Management Router."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.database import get_db
from packages.common.models import Watchlist, WatchlistItem, Company, Security, MarketQuote, Event
from packages.market_data.streaming import subscription_manager

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


class WatchlistItemAdd(BaseModel):
    company_id: UUID
    notes: Optional[str] = None


@router.get("")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Retrieve the active watchlist, its items, company identities, and current market quotes."""
    res = await db.execute(select(Watchlist).limit(1))
    wl = res.scalar_one_or_none()
    if not wl:
        # Create default watchlist if absent
        wl = Watchlist(name="Core Watchlist", description="Primary monitored equity universe")
        db.add(wl)
        await db.commit()
        await db.refresh(wl)

    items_res = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.watchlist_id == wl.id)
        .order_by(WatchlistItem.added_at.desc())
    )
    items = items_res.scalars().all()

    enriched_items = []
    for item in items:
        comp_res = await db.execute(select(Company).where(Company.id == item.company_id))
        comp = comp_res.scalar_one_or_none()
        if not comp:
            continue

        # Get primary security
        sec_res = await db.execute(
            select(Security).where(Security.company_id == comp.id, Security.is_active.is_(True))
        )
        sec = sec_res.scalars().first()

        quote = None
        if sec:
            mq_res = await db.execute(select(MarketQuote).where(MarketQuote.security_id == sec.id))
            mq = mq_res.scalar_one_or_none()
            if mq:
                quote = {
                    "last_price": float(mq.last_price),
                    "change_pct": mq.change_pct,
                    "volume": int(mq.volume),
                    "as_of": mq.as_of.isoformat(),
                }
            # Register with streaming subscription manager
            subscription_manager.add_symbol(sec.symbol, category="watched")

        enriched_items.append({
            "watchlist_item_id": str(item.id),
            "company_id": str(comp.id),
            "isin": comp.isin,
            "legal_name": comp.legal_name,
            "common_name": comp.common_name,
            "sector": comp.sector,
            "industry": comp.industry,
            "symbol": sec.symbol if sec else None,
            "exchange": sec.exchange if sec else None,
            "security_id": str(sec.id) if sec else None,
            "is_muted": item.is_muted,
            "notes": item.notes,
            "added_at": item.added_at.isoformat(),
            "quote": quote,
        })

    return {
        "watchlist_id": str(wl.id),
        "name": wl.name,
        "count": len(enriched_items),
        "items": enriched_items,
    }


@router.post("/items")
async def add_watchlist_item(payload: WatchlistItemAdd, db: AsyncSession = Depends(get_db)):
    """Add a company to the watchlist."""
    comp_res = await db.execute(select(Company).where(Company.id == payload.company_id))
    comp = comp_res.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Company not found")

    res = await db.execute(select(Watchlist).limit(1))
    wl = res.scalar_one_or_none()
    if not wl:
        wl = Watchlist(name="Core Watchlist", description="Primary monitored equity universe")
        db.add(wl)
        await db.flush()

    # Check if already present
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == wl.id,
            WatchlistItem.company_id == comp.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "exists", "message": "Company is already in watchlist"}

    item = WatchlistItem(
        watchlist_id=wl.id,
        company_id=comp.id,
        is_muted=False,
        notes=payload.notes,
        added_at=datetime.now(timezone.utc),
    )
    db.add(item)
    await db.commit()

    # Add primary securities to streaming subscription manager
    secs = (await db.execute(select(Security).where(Security.company_id == comp.id))).scalars().all()
    for s in secs:
        subscription_manager.add_symbol(s.symbol, category="watched")

    return {"status": "success", "message": f"{comp.legal_name} added to watchlist"}


@router.delete("/items/{company_id}")
async def remove_watchlist_item(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Remove a company from the watchlist."""
    res = await db.execute(select(Watchlist).limit(1))
    wl = res.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    item_res = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == wl.id,
            WatchlistItem.company_id == company_id,
        )
    )
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in watchlist")

    await db.delete(item)
    await db.commit()

    # Unsubscribe symbols
    secs = (await db.execute(select(Security).where(Security.company_id == company_id))).scalars().all()
    for s in secs:
        subscription_manager.remove_symbol(s.symbol, category="watched")

    return {"status": "success", "message": "Item removed from watchlist"}


@router.patch("/items/{company_id}/mute")
async def toggle_mute_alert(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Mute or unmute Telegram alerts for a specific watchlist company."""
    res = await db.execute(select(Watchlist).limit(1))
    wl = res.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    item_res = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == wl.id,
            WatchlistItem.company_id == company_id,
        )
    )
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in watchlist")

    item.is_muted = not item.is_muted
    await db.commit()
    return {"status": "success", "is_muted": item.is_muted}


@router.get("/events")
async def get_watchlist_events(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Returns recent events exclusively affecting companies in the watchlist."""
    res = await db.execute(select(Watchlist).limit(1))
    wl = res.scalar_one_or_none()
    if not wl:
        return {"events": []}

    item_comp_ids = (
        await db.execute(select(WatchlistItem.company_id).where(WatchlistItem.watchlist_id == wl.id))
    ).scalars().all()

    if not item_comp_ids:
        return {"events": []}

    events_res = await db.execute(
        select(Event)
        .where(Event.company_id.in_(item_comp_ids))
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    events = events_res.scalars().all()

    return {
        "count": len(events),
        "events": [
            {
                "event_id": str(e.id),
                "company_id": str(e.company_id),
                "event_type": e.event_type,
                "importance": e.importance,
                "headline": e.headline,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }
