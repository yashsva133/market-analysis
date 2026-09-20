"""Company Comparison Router.

Side-by-side comparative analysis grounded exclusively in ingested database
records (financial snapshots, securities) plus live quotes when a feed is
configured. Unknown symbols return 404; missing metrics return null. No
hardcoded peer profiles and no generated placeholder metrics.
"""
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.common.database import get_db
from packages.common.models import Company, FinancialSnapshot, Security
from packages.market_data.free_provider import free_provider

router = APIRouter(prefix="/api/compare", tags=["compare"])


def _num(value):
    return float(value) if value is not None else None


@router.get("")
@router.get("/")
async def compare_companies(
    symbols: str = Query(..., description="Comma-separated ticker symbols (e.g. 'LT,RELIANCE' or 'TCS,INFY')"),
    db: AsyncSession = Depends(get_db),
):
    """Compare 2-5 companies on ingested valuation, profitability, and balance-sheet metrics."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(sym_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 symbols to compare.")
    if len(sym_list) > 5:
        raise HTTPException(status_code=400, detail="Comparison limited to at most 5 companies concurrently.")

    results = []
    for s in sym_list:
        res = await db.execute(
            select(Company)
            .where(Company.securities.any(or_(func.upper(Security.symbol) == s, Security.bse_scrip_code == s)))
            .options(selectinload(Company.securities))
            .limit(2)
        )
        companies = res.scalars().all()
        if not companies:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol '{s}' not found in the ingested universe. Sync exchange masters first.",
            )
        if len(companies) > 1:
            raise HTTPException(status_code=409, detail=f"Ambiguous symbol '{s}'. Use ISIN-based identifiers.")
        company = companies[0]

        fin_res = await db.execute(
            select(FinancialSnapshot)
            .where(FinancialSnapshot.company_id == company.id)
            .order_by(FinancialSnapshot.snapshot_date.desc())
            .limit(1)
        )
        fin = fin_res.scalar_one_or_none()

        item: Dict[str, Any] = {
            "symbol": s,
            "name": company.legal_name,
            "isin": company.isin,
            "sector": company.sector,
            "market_cap_cr": _num(fin.market_cap) if fin else None,
            "pe_ratio": _num(fin.pe) if fin else None,
            "pb_ratio": None,
            "ev_ebitda": None,
            "roe_pct": None,
            "roce_pct": _num(fin.roce) if fin else None,
            "ebitda_margin_pct": None,
            "pat_margin_pct": None,
            "debt_to_equity": _num(fin.debt) if fin else None,
            "promoter_holding_pct": None,
            "institutional_holding_pct": None,
            "current_price": None,
            "price_52w_high": None,
            "price_52w_low": None,
            "snapshot_period": fin.period if fin else None,
            "snapshot_date": fin.snapshot_date if fin else None,
        }
        if fin and fin.revenue:
            if fin.ebitda is not None:
                item["ebitda_margin_pct"] = round(float(fin.ebitda) / float(fin.revenue) * 100, 1)
            if fin.pat is not None:
                item["pat_margin_pct"] = round(float(fin.pat) / float(fin.revenue) * 100, 1)

        try:
            quote = await free_provider.get_live_quote(s)
            if quote and quote.last_price > 0:
                item["current_price"] = round(quote.last_price, 2)
                item["change_pct"] = round(quote.change_pct, 2)
        except Exception:
            pass

        results.append(item)

    return {
        "status": "ok",
        "symbols": sym_list,
        "count": len(results),
        "comparison": results,
        "disclaimer": (
            "Descriptive comparison of ingested financial snapshots only. Null fields indicate "
            "metrics not present in ingested data. No investment winner or buy/sell rating generated."
        ),
        "as_of": datetime.now().isoformat(),
    }
