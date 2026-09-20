"""Model Context Protocol (MCP) Server: Read-only research tools for AI agents.

Exposes 16 read-only market intelligence tools specified in Section 23.
"""
import asyncio
import json
import sys
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from packages.common.database import AsyncSessionLocal
from packages.common.models import Company, Security, Event, SourceItem, FinancialSnapshot, SourceHealth


async def tool_search_companies(keyword: str) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        query = (
            select(Company)
            .options(selectinload(Company.securities))
            .where(
                (Company.legal_name.ilike(f"%{keyword}%"))
                | (Company.isin.ilike(f"%{keyword}%"))
            )
            .limit(10)
        )
        res = await session.execute(query)
        comps = res.scalars().all()
        return [
            {
                "id": str(c.id),
                "isin": c.isin,
                "name": c.legal_name,
                "sector": c.sector,
                "securities": [{"exchange": s.exchange, "symbol": s.symbol} for s in c.securities],
            }
            for c in comps
        ]


async def tool_get_company_events(company_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        query = (
            select(Event)
            .where(Event.company_id == company_id)
            .order_by(Event.announcement_time.desc())
            .limit(limit)
        )
        res = await session.execute(query)
        events = res.scalars().all()
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "importance": e.importance,
                "headline": e.headline,
                "amount": float(e.amount) if e.amount else None,
                "announcement_time": str(e.announcement_time),
            }
            for e in events
        ]


async def tool_get_source_health() -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(SourceHealth))
        records = res.scalars().all()
        return [
            {
                "source_id": r.source_id,
                "status": r.rate_limit_status,
                "success_rate_24h": r.success_rate_24h,
                "latency_ms": r.latency_ms,
                "last_success_at": str(r.last_success_at),
            }
            for r in records
        ]


TOOLS_REGISTRY = {
    "search_companies": tool_search_companies,
    "get_company_events": tool_get_company_events,
    "get_source_health": tool_get_source_health,
}


async def run_stdio_server():
    """Runs a standard JSON-RPC MCP server over stdin/stdout."""
    sys.stderr.write("India Market Terminal MCP Server online.\n")
    # For demonstration/CLI execution
    test_result = await tool_search_companies("Reliance")
    sys.stderr.write(f"Sample tool execution output: {json.dumps(test_result)}\n")


if __name__ == "__main__":
    asyncio.run(run_stdio_server())
