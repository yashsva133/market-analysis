"""Exchange discovery with canonical ISIN identities and persisted sync diagnostics."""
import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from packages.common.logging import get_logger
from packages.common.models import Company, Security, CompanyAlias, UniverseChangeEvent, Source, SourceHealth
from packages.source_clients.nse import NseAdapter
from packages.source_clients.bse import BseAdapter

logger = get_logger(__name__)
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

async def universe_status(session):
    total = (await session.execute(select(func.count(Company.id)))).scalar_one()
    nse = Company.securities.any(Security.exchange == "NSE")
    bse = Company.securities.any(Security.exchange == "BSE")
    counts = {}
    for key, condition in (("nse_count", nse), ("bse_count", bse), ("dual_listed_count", nse & bse)):
        counts[key] = (await session.execute(select(func.count(Company.id)).where(condition))).scalar_one()
    health = (await session.execute(select(SourceHealth).where(SourceHealth.source_id.in_(["nse-universe", "bse-universe"])))).scalars().all()
    providers = []
    for row in health:
        try:
            details = json.loads(row.notes or "{}")
        except (ValueError, TypeError):
            details = {"error": row.notes}
        providers.append({"exchange": row.source_id.split("-")[0].upper(), "status": row.status,
            "last_success_at": row.last_success_at, "last_poll_at": row.last_poll_at, **details})
    latest = [r.last_success_at for r in health if r.last_success_at]
    fresh = len(health) == 2 and all(r.status == "healthy" and r.last_success_at and
        datetime.now(timezone.utc) - r.last_success_at < timedelta(hours=36) for r in health)
    return {"status": "AVAILABLE" if fresh else "PARTIAL" if total else "UNAVAILABLE", "total_companies": total,
        **counts, "unique_isin_count": total, "missing_isin_count": sum(p.get("missing_isin", 0) for p in providers),
        "failed_ingestion_count": sum(p.get("rejected", 0) for p in providers),
        "failed_providers": [p["exchange"] for p in providers if p["status"] != "healthy"],
        "last_successful_sync": min(latest) if len(latest) == 2 else None, "providers": providers,
        "coverage_note": "Counts reflect ingested exchange feeds, not a guaranteed complete equity universe. Missing ISIN records are quarantined; absent listings are not assumed delisted."}

class UniverseManager:
    def __init__(self):
        self.nse_adapter = NseAdapter()
        self.bse_adapter = BseAdapter()

    async def refresh_universe(self, session: AsyncSession, custom_nse=None, custom_bse=None) -> Dict[str, Any]:
        async def fetch(adapter, custom):
            if custom is not None:
                return custom
            try:
                records = await adapter.fetch_security_master()
                if not records:
                    raise ValueError("Exchange returned no securities")
                return records
            except Exception as exc:
                return exc
        results = await asyncio.gather(fetch(self.nse_adapter, custom_nse), fetch(self.bse_adapter, custom_bse))
        # A transaction lock prevents the API and worker inserting the same listing concurrently.
        await session.execute(text("SELECT pg_advisory_xact_lock(728401)"))
        companies = {c.isin: c for c in (await session.execute(select(Company))).scalars().all()}
        securities = {(s.exchange, s.symbol): s for s in (await session.execute(select(Security))).scalars().all()}
        stats = dict(created_companies=0, created_securities=0, updated_companies=0, new_listings=0, symbol_changes=0, deactivations=0)
        now = datetime.now(timezone.utc)
        diagnostics = []
        for exchange, result, adapter, custom in zip(("NSE", "BSE"), results, (self.nse_adapter, self.bse_adapter), (custom_nse, custom_bse)):
            detail = {"exchange": exchange, "received": 0, "accepted": 0, "rejected": 0, "missing_isin": 0, "error": None}
            if isinstance(result, Exception):
                detail["error"] = f"{type(result).__name__}: {str(result)[:300]}"
                records = []
            else:
                records = result
            detail["received"] = len(records)
            seen = set()
            for raw in records:
                isin = str(raw.get("isin") or "").strip().upper()
                symbol = str(raw.get("symbol") or raw.get("bse_scrip_code") or "").strip().upper()
                name = " ".join(str(raw.get("legal_name") or "").split())
                if not isin:
                    detail["missing_isin"] += 1
                if not ISIN_PATTERN.fullmatch(isin) or not symbol or not name:
                    detail["rejected"] += 1
                    continue
                if (isin, symbol) in seen:
                    continue
                seen.add((isin, symbol))
                company = companies.get(isin)
                if company is None:
                    company = Company(isin=isin, legal_name=name, status="ACTIVE", first_seen=now, last_seen=now)
                    session.add(company)
                    await session.flush()
                    companies[isin] = company
                    stats["created_companies"] += 1
                else:
                    company.last_seen = now
                    company.legal_name = name
                    stats["updated_companies"] += 1
                if raw.get("sector"):
                    company.sector = raw["sector"]
                if raw.get("industry"):
                    company.industry = raw["industry"]
                key = (exchange, symbol)
                security = securities.get(key)
                if security is not None and security.company_id != company.id:
                    detail["rejected"] += 1
                    detail["error"] = "Listing identity conflict requires review; no company reassignment performed."
                    continue
                active = raw.get("is_active", True) is True
                if security is None:
                    previous = [s for s in securities.values() if s.company_id == company.id and s.exchange == exchange and s.is_active]
                    for prev in previous:
                        if prev.symbol != symbol:
                            prev.is_active = False
                            session.add(CompanyAlias(company_id=company.id, alias=prev.symbol, alias_type="SYMBOL_HISTORY"))
                            session.add(UniverseChangeEvent(isin=isin, exchange=exchange, symbol=symbol, change_type="SYMBOL_CHANGE", details={"previous_symbol": prev.symbol, "new_symbol": symbol}, detected_at=now))
                            stats["symbol_changes"] += 1
                    security = Security(company_id=company.id, exchange=exchange, symbol=symbol,
                        bse_scrip_code=raw.get("bse_scrip_code"), series=raw.get("series", "EQ"),
                        security_type=raw.get("security_type", "EQUITY"), is_active=active,
                        upstox_instrument_key=f"{exchange}_EQ|{isin}", last_seen=now)
                    session.add(security)
                    securities[key] = security
                    session.add(UniverseChangeEvent(isin=isin, exchange=exchange, symbol=symbol, change_type="NEW_LISTING", details={"source": adapter.base_url}, detected_at=now))
                    stats["created_securities"] += 1
                    stats["new_listings"] += 1
                else:
                    if security.is_active and not active:
                        stats["deactivations"] += 1
                    security.is_active = active
                    security.last_seen = now
                    security.series = raw.get("series", security.series)
                    security.bse_scrip_code = raw.get("bse_scrip_code") or security.bse_scrip_code
                detail["accepted"] += 1
            status = "failed" if detail["error"] and not detail["accepted"] else "degraded" if detail["error"] or detail["rejected"] else "healthy"
            if not records and custom is None:
                status = "failed"
            detail["status"] = status
            diagnostics.append(detail)
            source_id = f"{exchange.lower()}-universe"
            source = await session.get(Source, source_id)
            if source is None:
                session.add(Source(id=source_id, name=f"{exchange} security master", publisher=exchange, source_type="security_master", base_url=adapter.base_url, priority=1))
                await session.flush()
            health = (await session.execute(select(SourceHealth).where(SourceHealth.source_id == source_id))).scalar_one_or_none()
            if health is None:
                health = SourceHealth(source_id=source_id, consecutive_failures=0)
                session.add(health)
            health.last_poll_at = now
            health.status = status
            health.notes = json.dumps(detail)
            if status == "healthy":
                health.last_success_at = now
                health.consecutive_failures = 0
            else:
                health.consecutive_failures = (health.consecutive_failures or 0) + 1
        for company in companies.values():
            listings = [s for s in securities.values() if s.company_id == company.id]
            if listings:
                company.status = "ACTIVE" if any(s.is_active for s in listings) else "INACTIVE"
        await session.commit()
        stats.update(status="AVAILABLE" if all(d["status"] == "healthy" for d in diagnostics) else "PARTIAL" if any(d["accepted"] for d in diagnostics) else "FAILED", providers=diagnostics)
        return stats

universe_manager = UniverseManager()
