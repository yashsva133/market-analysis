"""Pydantic schemas for events, facts, relations, and detailed event payloads."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from .taxonomy import EventTaxonomy, ImportanceClass
from .company import CompanyRead
from .source import SourceItemRead


class EventFactBase(BaseModel):
    fact_key: str = Field(..., description="Key describing the factual metric (e.g., amount, counterparty, duration)")
    fact_value: Any = Field(..., description="Arbitrary JSONB value")
    source_page: Optional[int] = Field(None, description="Page number in original filing where fact occurs")
    confidence: float = Field(default=1.0)


class EventFactCreate(EventFactBase):
    event_id: Optional[UUID] = None


class EventFactRead(EventFactBase):
    id: UUID
    event_id: UUID

    model_config = ConfigDict(from_attributes=True)


class EventRelationRead(BaseModel):
    id: UUID
    event_id: UUID
    related_company_id: UUID
    relation_type: str
    confidence: float

    model_config = ConfigDict(from_attributes=True)


class EventBase(BaseModel):
    company_id: Optional[UUID] = None
    source_item_id: UUID
    event_type: EventTaxonomy
    importance: ImportanceClass = ImportanceClass.MEDIUM
    headline: str
    event_time: Optional[datetime] = None
    announcement_time: Optional[datetime] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = "INR"
    status: str = "EXTRACTED"
    confidence: float = 1.0


class EventCreate(EventBase):
    pass


class EventRead(EventBase):
    id: UUID
    created_at: datetime
    company: Optional[CompanyRead] = None
    source_item: Optional[SourceItemRead] = None
    # Flattened presentation attributes for UI inspector & alerts
    company_name: Optional[str] = None
    symbol: Optional[str] = None
    bse_code: Optional[str] = None
    amount_formatted: Optional[str] = None
    amount_str: Optional[str] = None
    source_name: Optional[str] = None
    reaction: Optional[str] = None
    why_flagged: List[str] = []
    unknowns: List[str] = []

    model_config = ConfigDict(from_attributes=True)



class EventDetailRead(EventRead):
    facts: List[EventFactRead] = []
    relations: List[EventRelationRead] = []
    ai_explanation: Optional[Dict[str, Any]] = None
    market_reaction: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
