"""Deterministic RuleProvider for zero-cost, air-gapped event classification and fact extraction."""
import re
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

from packages.schemas.taxonomy import EventTaxonomy, ImportanceClass
from .base import LLMProvider, LLMResponse


class RuleProvider(LLMProvider):
    """Deterministic extractor utilizing regex, keywords, and financial heuristics."""

    def __init__(self):
        super().__init__(name="rule_fallback", model_name="deterministic_rules_v1")

    async def is_available(self) -> bool:
        return True

    def _extract_amount_inr(self, text: str) -> Optional[Decimal]:
        """Extract Indian rupee amount (e.g., 'Rs 850 Crore', '₹1,200 Cr', '500 Lakhs')."""
        # Patterns like: Rs. 850 Cr, INR 850 Crore, ₹ 850.50 Crores, 850 Cr
        cr_pattern = r"(?:(?:Rs\.?|INR|₹)\s*)?([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(?:Cr(?:ore)?s?)\b"
        match_cr = re.search(cr_pattern, text, re.IGNORECASE)
        if match_cr:
            val_str = match_cr.group(1).replace(",", "")
            try:
                # 1 Crore = 10,000,000 (10^7)
                return Decimal(val_str) * Decimal(10000000)
            except Exception:
                pass

        lakh_pattern = r"(?:(?:Rs\.?|INR|₹)\s*)?([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(?:Lakh(?:s)?)\b"
        match_lakh = re.search(lakh_pattern, text, re.IGNORECASE)
        if match_lakh:
            val_str = match_lakh.group(1).replace(",", "")
            try:
                # 1 Lakh = 100,000 (10^5)
                return Decimal(val_str) * Decimal(100000)
            except Exception:
                pass

        return None

    def _classify_event_type(self, text: str) -> EventTaxonomy:
        """Determines EventTaxonomy based on headline and filing text keywords."""
        lower = text.lower()

        if any(k in lower for k in ["insolvency", "nclt", "cirp", "ibc 2016", "resolution professional"]):
            return EventTaxonomy.INSOLVENCY
        if any(k in lower for k in ["resignation of auditor", "auditor resigned", "removal of auditor"]):
            return EventTaxonomy.AUDITOR_CHANGE
        if any(k in lower for k in ["pledge", "invocation of pledge", "revocation of pledge"]):
            return EventTaxonomy.PLEDGE
        if any(k in lower for k in ["cancellation of order", "termination of contract", "order terminated"]):
            return EventTaxonomy.ORDER_CANCELLATION
        order_win_terms = [
            "order win", "bagged order", "bags order", "bags mega order", "bags contract",
            "awarded contract", "received order", "letter of award", "loa", "secured order",
            "wins order", "won order", "contract award", "wins contract", "won contract",
            "major contract", "wins major contract", "awarded order", "secures contract"
        ]
        if any(k in lower for k in order_win_terms) or ("bags" in lower and "order" in lower) or ("order worth" in lower) or ("contract worth" in lower) or ("wins" in lower and "contract" in lower):
            return EventTaxonomy.ORDER_WIN
        if any(k in lower for k in ["mou", "memorandum of understanding"]):
            return EventTaxonomy.MOU
        if any(k in lower for k in ["letter of intent", "loi"]):
            return EventTaxonomy.LOI
        if any(k in lower for k in ["acquisition", "merger", "amalgamation", "takeover", "acquired"]):
            return EventTaxonomy.MNA
        if any(k in lower for k in ["capex", "capital expenditure"]):
            return EventTaxonomy.CAPEX
        if any(k in lower for k in ["capacity expansion", "expansion of capacity"]):
            return EventTaxonomy.CAPACITY_EXPANSION
        if any(k in lower for k in ["new plant", "manufacturing facility", "new unit"]):
            return EventTaxonomy.PLANT
        if any(k in lower for k in ["financial results", "quarterly results", "audited financial"]):
            return EventTaxonomy.RESULTS
        if any(k in lower for k in ["dividend", "interim dividend", "final dividend"]):
            return EventTaxonomy.DIVIDEND
        if any(k in lower for k in ["bonus issue", "bonus share"]):
            return EventTaxonomy.BONUS
        if any(k in lower for k in ["stock split", "sub-division of shares"]):
            return EventTaxonomy.SPLIT
        if any(k in lower for k in ["buyback", "share repurchase"]):
            return EventTaxonomy.BUYBACK
        if any(k in lower for k in ["resignation of md", "appointment of ceo", "appointment of cfo", "change in management"]):
            return EventTaxonomy.MANAGEMENT_CHANGE
        if any(k in lower for k in ["board meeting", "outcome of board"]):
            return EventTaxonomy.BOARD_MEETING
        if any(k in lower for k in ["credit rating", "rating upgrade", "rating downgrade"]):
            return EventTaxonomy.CREDIT_RATING

        return EventTaxonomy.CORPORATE_ANNOUNCEMENT

    async def complete(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Emulates LLM extraction deterministically."""
        start_time = time.time()
        event_type = self._classify_event_type(prompt)
        amount = self._extract_amount_inr(prompt)

        # Build structured output
        is_binding = event_type not in (EventTaxonomy.MOU, EventTaxonomy.LOI)
        parsed: Dict[str, Any] = {
            "event_type": event_type.value,
            "is_binding": is_binding,
            "amount": float(amount) if amount else None,
            "currency": "INR" if amount else None,
            "facts": [],
            "unknowns": ["Execution timeline not verified", "Margin not disclosed"],
            # Deterministic rule extraction has no calibrated confidence; it is
            # reported as None rather than a fabricated numeric score.
            "confidence": None,
        }

        if amount:
            parsed["facts"].append({"key": "contract_amount_inr", "value": float(amount)})

        latency = int((time.time() - start_time) * 1000)
        return LLMResponse(
            raw_text=str(parsed),
            parsed_json=parsed,
            provider=self.name,
            model=self.model_name,
            tokens_in=len(prompt.split()),
            tokens_out=len(str(parsed).split()),
            latency_ms=latency,
        )
