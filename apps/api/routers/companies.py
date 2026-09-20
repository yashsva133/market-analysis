"""Database-backed canonical company lookup and bounded pagination."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from packages.common.database import get_db
from packages.common.models import Company, Security, FinancialSnapshot, CompanyAlias
from packages.schemas.company import CompanyRead

router = APIRouter(tags=["Companies & Securities"])

def company_query(keyword=None, exchange=None, sector=None, active_only=True):
    query = select(Company).options(selectinload(Company.securities))
    conditions = []
    if exchange:
        conditions.append(Security.exchange == exchange.upper())
    if active_only:
        conditions.append(Security.is_active.is_(True))
    if conditions:
        query = query.where(Company.securities.any(and_(*conditions)))
    if sector:
        query = query.where(func.lower(Company.sector) == sector.lower())
    if keyword and keyword.strip():
        value = keyword.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{value}%"
        query = query.where(or_(Company.isin.ilike(pattern), Company.legal_name.ilike(pattern),
            Company.common_name.ilike(pattern), Company.securities.any(or_(Security.symbol.ilike(pattern), Security.bse_scrip_code.ilike(pattern))),
            Company.aliases.any(CompanyAlias.alias.ilike(pattern))))
    return query

def serialize_company(company):
    data = CompanyRead.model_validate(company)
    securities = sorted(company.securities, key=lambda s: (not s.is_active, s.exchange != "NSE", s.symbol))
    data.name = company.legal_name
    data.symbol = securities[0].symbol if securities else None
    data.bse_code = next((s.bse_scrip_code for s in securities if s.exchange == "BSE"), None)
    return data

async def resolve_company(db, identifier):
    key = str(identifier).strip()
    tests = [func.upper(Company.isin) == key.upper(), func.lower(Company.legal_name) == key.lower(),
        func.lower(Company.common_name) == key.lower(),
        Company.securities.any(or_(func.upper(Security.symbol) == key.upper(), Security.bse_scrip_code == key)),
        Company.aliases.any(func.lower(CompanyAlias.alias) == key.lower())]
    try:
        tests.append(Company.id == UUID(key))
    except ValueError:
        pass
    result = await db.execute(select(Company).where(or_(*tests)).options(selectinload(Company.securities)).limit(2))
    companies = result.scalars().all()
    if not companies:
        raise HTTPException(404, detail="Company not found in the ingested universe. Sync exchange masters first.")
    if len(companies) > 1:
        raise HTTPException(409, detail="Ambiguous company identifier. Use an ISIN or company ID.")
    return companies[0]

@router.get("/companies", response_model=List[CompanyRead])
@router.get("/api/companies", response_model=List[CompanyRead])
async def list_companies(exchange: Optional[str] = Query(None, pattern="^(NSE|BSE)$"),
    sector: Optional[str] = None, active_only: bool = True, keyword: Optional[str] = Query(None, max_length=160),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    query = company_query(keyword, exchange, sector, active_only)
    rows = (await db.execute(query.order_by(Company.legal_name, Company.id).offset(offset).limit(limit))).scalars().all()
    return [serialize_company(c) for c in rows]

@router.get("/universe")
@router.get("/api/universe")
async def universe_page(exchange: Optional[str] = Query(None, pattern="^(NSE|BSE)$"), sector: Optional[str] = None,
    active_only: bool = True, keyword: Optional[str] = Query(None, max_length=160),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    from services.collector.universe_manager import universe_status
    query = company_query(keyword, exchange, sector, active_only)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (await db.execute(query.order_by(Company.legal_name, Company.id).offset(offset).limit(limit))).scalars().all()
    return {"items": [serialize_company(c) for c in rows], "total": total, "limit": limit, "offset": offset,
        "has_more": offset + len(rows) < total, "universe": await universe_status(db)}

@router.get("/companies/{company_id}", response_model=CompanyRead)
@router.get("/api/companies/{company_id}", response_model=CompanyRead)
async def get_company(company_id: str, db: AsyncSession = Depends(get_db)):
    return serialize_company(await resolve_company(db, company_id))

@router.get("/companies/{company_id}/financials")
@router.get("/api/companies/{company_id}/financials")
async def get_company_financials(company_id: str, db: AsyncSession = Depends(get_db)):
    company = await resolve_company(db, company_id)
    rows = (await db.execute(select(FinancialSnapshot).where(FinancialSnapshot.company_id == company.id)
        .order_by(FinancialSnapshot.snapshot_date.desc()).limit(40))).scalars().all()
    return [{"id": str(s.id), "period": s.period, "snapshot_date": s.snapshot_date, "source": s.source,
        **{name: float(getattr(s, name)) if getattr(s, name) is not None else None
        for name in ("revenue", "pat", "ebitda", "pe", "roce", "debt", "market_cap")}} for s in rows]
