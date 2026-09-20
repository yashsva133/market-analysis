"""Agent Framework: Agents A through J from Section 16 of Specification.

Small, typed, deterministic pipelines where AI is only invoked after strict filtering.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from packages.common.logging import get_logger
from packages.schemas.taxonomy import EventTaxonomy, ImportanceClass
from packages.schemas.ai import AIClassificationResult, AIMaterialityAnalysis, DeepResearchReport
from packages.schemas.source import SourceItemBase
from .router import ai_router

logger = get_logger(__name__)


# Agent C: Entity Resolver
class EntityResolverAgent:
    """Agent C: Resolves companies from text using deterministic matching first (ISIN/Symbol/Scrip)."""

    def resolve(
        self,
        headline: str,
        symbols_index: Dict[str, UUID],
        scrips_index: Dict[str, UUID],
        names_index: Dict[str, UUID],
    ) -> Optional[UUID]:
        # 1. Match bracketed symbols, e.g. [RELIANCE] or [500325]
        for word in headline.split():
            clean = word.strip("[](),.:; ")
            if clean in symbols_index:
                return symbols_index[clean]
            if clean in scrips_index:
                return scrips_index[clean]

        # 2. Match exact known company names
        lower_headline = headline.lower()
        for name, company_id in names_index.items():
            if name.lower() in lower_headline:
                return company_id

        return None


# Agent D: Event Classifier
class EventClassifierAgent:
    """Agent D: Classifies normalized source item into structured Event with facts."""

    async def classify(self, item: SourceItemBase, filing_text: Optional[str] = None) -> AIClassificationResult:
        content_to_analyze = f"Headline: {item.headline}\n"
        if filing_text:
            # First 2,000 characters of primary filing
            content_to_analyze += f"Filing Excerpt:\n{filing_text[:2000]}\n"

        prompt = (
            f"Extract structured event information from this Indian corporate disclosure:\n"
            f"{content_to_analyze}"
        )
        system_instruction = (
            "You are an expert Indian equity research analyst. "
            "Extract the exact event type, whether it is a binding contract vs preliminary MoU/LOI, "
            "the order/capex amount in INR if explicitly stated, and list concrete facts vs unknowns."
        )

        resp = await ai_router.execute_task(
            task="event_classification",
            prompt=prompt,
            system_instruction=system_instruction,
            schema=AIClassificationResult,
        )

        if resp.parsed_json:
            try:
                return AIClassificationResult(**resp.parsed_json)
            except Exception as e:
                logger.warning(f"Schema validation error on AI output: {e}")

        # Fallback to rule provider
        rule_resp = await ai_router.rule_provider.complete(content_to_analyze)
        return AIClassificationResult(**rule_resp.parsed_json)


# Agent F: Materiality Analyst
class MaterialityAnalystAgent:
    """Agent F: Performs deterministic importance triage with evidence-backed rationale."""

    def analyze(
        self,
        event_type: EventTaxonomy,
        amount_inr: Optional[Decimal] = None,
        annual_revenue_inr: Optional[Decimal] = None,
    ) -> AIMaterialityAnalysis:
        # Critical events that always trigger CRITICAL
        critical_types = {
            EventTaxonomy.INSOLVENCY,
            EventTaxonomy.AUDITOR_CHANGE,
            EventTaxonomy.PLEDGE,
            EventTaxonomy.ORDER_CANCELLATION,
            EventTaxonomy.MNA,
            EventTaxonomy.RESTRUCTURING,
            EventTaxonomy.CYBER_EVENT,
            EventTaxonomy.DATA_BREACH,
            EventTaxonomy.DELISTING,
            EventTaxonomy.SUSPENSION,
        }

        if event_type in critical_types:
            return AIMaterialityAnalysis(
                importance=ImportanceClass.CRITICAL,
                why_flagged=[
                    f"Event category '{event_type.value}' is designated high governance/operational risk",
                    "Requires immediate investor evaluation",
                ],
                what_is_unknown=["Detailed management plan", "Timeline for legal/regulatory resolution"],
            )

        # Scale relative to revenue
        if amount_inr and annual_revenue_inr and annual_revenue_inr > 0:
            ratio = float(amount_inr / annual_revenue_inr)
            amount_cr = float(amount_inr / Decimal(10000000))
            rev_cr = float(annual_revenue_inr / Decimal(10000000))

            if ratio >= 0.50 or amount_inr >= Decimal(50000000000): # >= 50% revenue or ₹5,000 Cr
                return AIMaterialityAnalysis(
                    importance=ImportanceClass.CRITICAL,
                    why_flagged=[
                        f"Order/transaction value of ₹{amount_cr:.1f} Cr is {ratio*100:.1f}% of annual revenue (₹{rev_cr:.1f} Cr)",
                        "Materially shifts forward revenue trajectory",
                    ],
                    financial_scale_summary=f"Represents {ratio*100:.1f}% of LTM revenue",
                    what_is_unknown=["Operating margin of the contract", "Execution schedule & milestone payments"],
                )
            elif ratio >= 0.15 or amount_inr >= Decimal(5000000000): # >= 15% revenue or ₹500 Cr
                return AIMaterialityAnalysis(
                    importance=ImportanceClass.HIGH,
                    why_flagged=[
                        f"Order/transaction value of ₹{amount_cr:.1f} Cr represents {ratio*100:.1f}% of annual revenue",
                        "Significant commercial milestone",
                    ],
                    financial_scale_summary=f"Represents {ratio*100:.1f}% of LTM revenue",
                    what_is_unknown=["Working capital impact", "Delivery schedule"],
                )

        # High priority default types
        high_types = {
            EventTaxonomy.ORDER_WIN,
            EventTaxonomy.CAPEX,
            EventTaxonomy.CAPACITY_EXPANSION,
            EventTaxonomy.PLANT,
            EventTaxonomy.RESULTS,
            EventTaxonomy.MANAGEMENT_CHANGE,
            EventTaxonomy.GOVERNMENT_APPROVAL,
            EventTaxonomy.REGULATORY_APPROVAL,
            EventTaxonomy.BUYBACK,
            EventTaxonomy.FUND_RAISE,
        }
        if event_type in high_types:
            return AIMaterialityAnalysis(
                importance=ImportanceClass.HIGH,
                why_flagged=[f"Material corporate milestone: {event_type.value}"],
                what_is_unknown=["Detailed financial breakdown"],
            )

        return AIMaterialityAnalysis(
            importance=ImportanceClass.MEDIUM,
            why_flagged=[f"Routine disclosure: {event_type.value}"],
            what_is_unknown=[],
        )


# Agent J: Alert Formatter
class AlertFormatterAgent:
    """Agent J: Formats high/critical events into clean Telegram/UI alert payloads."""

    def format_telegram_alert(
        self,
        company_name: str,
        symbol: str,
        bse_code: Optional[str],
        event_type: str,
        importance: str,
        headline: str,
        why_flagged: List[str],
        unknowns: List[str],
        source_url: Optional[str] = None,
        source_publisher: str = "NSE",
        financial_context: Optional[str] = None,
        market_reaction: Optional[str] = None,
    ) -> str:
        icon = "🚨" if importance == "CRITICAL" else "⚠️"
        bse_str = f" / BSE: {bse_code}" if bse_code else ""
        
        why_bullets = "\n".join([f"• {r}" for r in why_flagged[:3]]) or "• Material corporate event"
        unknown_bullets = "\n".join([f"• {u}" for u in unknowns[:2]]) if unknowns else "• None disclosed"

        sections = [
            f"{icon} *{importance} EVENT*",
            f"*{company_name}*\nNSE: {symbol}{bse_str}",
            f"*EVENT*\n{event_type}",
            f"*WHAT HAPPENED*\n{headline}",
            f"*PRIMARY SOURCE*\n{source_publisher} Filing",
            f"*WHY FLAGGED*\n{why_bullets}",
        ]

        if financial_context:
            sections.append(f"*FINANCIAL CONTEXT*\n{financial_context}")

        if market_reaction:
            sections.append(f"*MARKET REACTION*\n{market_reaction}")

        sections.append(f"*WHAT IS STILL UNKNOWN*\n{unknown_bullets}")

        if source_url:
            sections.append(f"[Open Primary Source]({source_url})")

        sections.append("_Factual market intelligence only. Strictly non-advisory._")

        return "\n\n".join(sections)


# Agent Singletons
entity_resolver_agent = EntityResolverAgent()
event_classifier_agent = EventClassifierAgent()
materiality_analyst_agent = MaterialityAnalystAgent()
alert_formatter_agent = AlertFormatterAgent()
