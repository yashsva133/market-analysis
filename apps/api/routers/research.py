"""AI Deep Research endpoints with evidence grounding (§25, §28, §29, §56).

Every section of the returned report is derived exclusively from ingested
database evidence (events, extracted facts, financial snapshots). When the
Gemini provider is configured it synthesizes the narrative from that evidence;
otherwise the report is assembled deterministically from the same evidence with
explicit "no ingested evidence" statements for gaps. Nothing is invented.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.common.database import get_db
from packages.common.models import Company, Event, EventFact, FinancialSnapshot, Security
from packages.schemas.ai import DeepResearchReport
from packages.common.logging import get_logger
from packages.common.config import settings

logger = get_logger(__name__)
router = APIRouter(tags=["AI Deep Research"])

NO_EVIDENCE = "No ingested evidence available for this section yet. Sync filings and events for this company."


class ResearchQueryRequest(BaseModel):
    company_id: Optional[UUID] = None
    symbol: Optional[str] = Field(default=None, description="Stock symbol (e.g. RELIANCE, LT, TCS)")
    question: Optional[str] = Field(default=None, description="Research query or focus area")
    query: Optional[str] = Field(default=None, description="Alternative key for research query")


async def _resolve_company(db: AsyncSession, request: ResearchQueryRequest) -> Company:
    if request.company_id:
        res = await db.execute(
            select(Company).where(Company.id == request.company_id).options(selectinload(Company.securities))
        )
        company = res.scalar_one_or_none()
        if company is None:
            raise HTTPException(404, detail="Company ID not found in the ingested universe.")
        return company

    sym = (request.symbol or "").strip().upper()
    if not sym:
        raise HTTPException(400, detail="Provide either company_id or symbol.")

    sec_res = await db.execute(
        select(Security).where(func_upper(Security.symbol) == sym).options(selectinload(Security.company)).limit(2)
    )
    secs = sec_res.scalars().all()
    if not secs:
        raise HTTPException(404, detail=f"Symbol '{sym}' not found in the ingested universe. Sync exchange masters first.")
    if len(secs) > 1 and len({s.company_id for s in secs}) > 1:
        raise HTTPException(409, detail=f"Ambiguous symbol '{sym}'. Use company_id instead.")
    return secs[0].company


def func_upper(col):
    from sqlalchemy import func
    return func.upper(col)


def _fact_statement(fact: EventFact) -> str:
    value = fact.fact_value
    if isinstance(value, dict):
        value = value.get("value", value)
    return f"{str(fact.fact_key).replace('_', ' ').title()}: {value}"


def _build_evidence(company: Company, events: List[Event], facts: List[EventFact], financials: List[FinancialSnapshot]) -> Dict[str, Any]:
    grounded: List[Dict[str, Any]] = []
    for f in facts:
        grounded.append({
            "classification": "FACT",
            "key": f.fact_key,
            "statement": _fact_statement(f),
            "evidence_page": f.source_page,
            "confidence": f.confidence,
            "source": "Official Filing / Event Fact",
        })

    events_summary = "\n".join(
        f"- [{e.announcement_time}] {e.event_type}: {e.headline}" for e in events
    ) if events else ""
    fin = financials[0] if financials else None
    fin_summary = (
        f"Period: {fin.period} | Revenue: {fin.revenue if fin.revenue is not None else 'not ingested'} | "
        f"PAT: {fin.pat if fin.pat is not None else 'not ingested'}"
    ) if fin else ""

    return {
        "grounded_findings": grounded,
        "events_summary": events_summary,
        "fin_summary": fin_summary,
        "material_events": [
            {"headline": e.headline, "type": e.event_type, "importance": e.importance} for e in events[:5]
        ],
    }


def _evidence_only_report(company: Company, evidence: Dict[str, Any], question: str, now: datetime) -> DeepResearchReport:
    grounded = evidence["grounded_findings"]
    facts_text = "\n".join(f"- {g['statement']}" for g in grounded) or "None extracted yet."
    return DeepResearchReport(
        company_name=company.legal_name,
        isin=company.isin,
        timestamp=now,
        business_overview=(
            f"{company.legal_name} (ISIN {company.isin})"
            + (f", sector: {company.sector}" if company.sector else "")
            + (f", industry: {company.industry}" if company.industry else "")
            + "."
        ),
        recent_changes=(
            f"Question: '{question}'\nIngested announcements:\n{evidence['events_summary']}"
            if evidence["events_summary"] else f"Question: '{question}'.\n{NO_EVIDENCE}"
        ),
        latest_financial_performance=evidence["fin_summary"] or NO_EVIDENCE,
        material_corporate_events=evidence["material_events"],
        products_and_capacity=NO_EVIDENCE,
        order_book_and_contracts=NO_EVIDENCE,
        sector_and_policy_context=NO_EVIDENCE,
        competitive_landscape=NO_EVIDENCE,
        balance_sheet_risks=NO_EVIDENCE,
        market_reaction_summary=NO_EVIDENCE,
        open_questions=[question] if question else [],
        primary_sources=[{"publisher": "Ingested exchange filings and event facts", "isin": company.isin}],
        secondary_sources=[],
        grounded_findings=grounded,
        data_freshness_statement=(
            f"Report assembled deterministically from ingested evidence only, as of "
            f"{now.strftime('%Y-%m-%d %H:%M:%S UTC')}. Extracted facts:\n{facts_text}"
        ),
    )


@router.post("/research", response_model=DeepResearchReport)
@router.post("/api/research", response_model=DeepResearchReport)
@router.post("/research/query", response_model=DeepResearchReport)
@router.post("/api/research/query", response_model=DeepResearchReport)
async def conduct_deep_research(request: ResearchQueryRequest, db: AsyncSession = Depends(get_db)):
    """Generates an evidence-grounded research report over ingested filings and data."""
    active_question = request.question or request.query or "What are the key drivers and risk factors?"
    company = await _resolve_company(db, request)

    ev_res = await db.execute(
        select(Event).where(Event.company_id == company.id)
        .order_by(Event.announcement_time.desc().nullslast()).limit(10)
    )
    events = list(ev_res.scalars().all())

    fin_res = await db.execute(
        select(FinancialSnapshot).where(FinancialSnapshot.company_id == company.id)
        .order_by(FinancialSnapshot.snapshot_date.desc()).limit(2)
    )
    financials = list(fin_res.scalars().all())

    facts: List[EventFact] = []
    event_ids = [e.id for e in events]
    if event_ids:
        facts_res = await db.execute(
            select(EventFact).where(EventFact.event_id.in_(event_ids)).limit(20)
        )
        facts = list(facts_res.scalars().all())

    evidence = _build_evidence(company, events, facts, financials)
    now = datetime.now(timezone.utc)

    # Narrative synthesis via Gemini only when configured; otherwise the
    # deterministic evidence-only report. The rule provider is an event
    # classifier, not a synthesizer, so it must not write report prose.
    if settings.AI_ACTIVE_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        try:
            from packages.ai.router import ai_router
            prompt = (
                f"Company: {company.legal_name} (ISIN {company.isin}, "
                f"sector: {company.sector or 'unknown'}, industry: {company.industry or 'unknown'}).\n"
                f"Research question: {active_question}\n\n"
                f"Ingested announcements:\n{evidence['events_summary'] or 'None.'}\n\n"
                f"Extracted facts:\n"
                + ("\n".join(f"- {g['statement']}" for g in evidence["grounded_findings"]) or "None.")
                + f"\n\nLatest financial snapshot: {evidence['fin_summary'] or 'None.'}\n\n"
                "Write a strictly evidence-grounded research brief. Use ONLY the facts above. "
                "For any section without supporting evidence, write exactly: " + NO_EVIDENCE + "\n\n"
                'Return JSON with keys: business_overview, recent_changes, latest_financial_performance, '
                'products_and_capacity, order_book_and_contracts, sector_and_policy_context, '
                'competitive_landscape, balance_sheet_risks, market_reaction_summary (all strings), '
                'open_questions (list of strings).'
            )
            response = await ai_router.execute_task(task="deep_research", prompt=prompt, db_session=db)
            parsed = response.parsed_json or {}
            if not isinstance(parsed, dict) or not parsed:
                raise RuntimeError("Model returned no structured output")

            def section(key: str) -> str:
                value = parsed.get(key)
                return value if isinstance(value, str) and value.strip() else NO_EVIDENCE

            open_questions = parsed.get("open_questions")
            if not isinstance(open_questions, list):
                open_questions = [active_question]

            return DeepResearchReport(
                company_name=company.legal_name,
                isin=company.isin,
                timestamp=now,
                business_overview=section("business_overview"),
                recent_changes=section("recent_changes"),
                latest_financial_performance=section("latest_financial_performance"),
                material_corporate_events=evidence["material_events"],
                products_and_capacity=section("products_and_capacity"),
                order_book_and_contracts=section("order_book_and_contracts"),
                sector_and_policy_context=section("sector_and_policy_context"),
                competitive_landscape=section("competitive_landscape"),
                balance_sheet_risks=section("balance_sheet_risks"),
                market_reaction_summary=section("market_reaction_summary"),
                open_questions=[str(q) for q in open_questions][:8],
                primary_sources=[{"publisher": "Ingested exchange filings and event facts", "isin": company.isin}],
                secondary_sources=[],
                grounded_findings=evidence["grounded_findings"],
                data_freshness_statement=(
                    f"Narrative synthesized by {response.provider}/{response.model} from ingested evidence only, "
                    f"as of {now.strftime('%Y-%m-%d %H:%M:%S UTC')}."
                ),
            )
        except Exception as e:
            logger.warning(f"Gemini research synthesis failed ({type(e).__name__}); using evidence-only report: {e}")

    return _evidence_only_report(company, evidence, active_question, now)
