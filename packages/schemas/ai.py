"""Pydantic schemas for structured AI runs, outputs, and agent contracts."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from .taxonomy import EventTaxonomy, ImportanceClass


class AIRunRead(BaseModel):
    id: UUID
    provider: str
    model: str
    task: str
    input_hash: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    tokens_in: int
    tokens_out: int
    cached: bool
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AIOutputRead(BaseModel):
    id: UUID
    ai_run_id: UUID
    task: str
    object_type: str
    object_id: UUID
    schema_version: str
    structured_output: Dict[str, Any]
    evidence_ids: List[Any] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Structured Contracts for Agents
class AIClassificationResult(BaseModel):
    event_type: EventTaxonomy
    is_binding: bool = Field(default=True, description="False if MoU, LOI, proposal, or non-binding interest")
    amount: Optional[Decimal] = Field(None, description="Numeric contract or capex value in INR if explicitly stated")
    counterparty: Optional[str] = Field(None, description="Name of client, partner, or acquirer")
    duration: Optional[str] = Field(None, description="Timeline or execution period")
    facts: List[Dict[str, Any]] = Field(default_factory=list, description="List of concrete extracted facts")
    unknowns: List[str] = Field(default_factory=list, description="Information not disclosed in source document")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class AIMaterialityAnalysis(BaseModel):
    importance: ImportanceClass
    why_flagged: List[str] = Field(..., description="Key factual reasons this event was triaged to this importance level")
    financial_scale_summary: Optional[str] = Field(None, description="Contextualizing event amount vs historical revenue/worth")
    what_is_unknown: List[str] = Field(default_factory=list, description="Missing crucial parameters (margins, financing, execution timeline)")
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list, description="Source references (document ID, page number)")

    @property
    def reasons(self) -> List[str]:
        return self.why_flagged


class DeepResearchReport(BaseModel):
    company_name: str
    isin: str
    timestamp: datetime
    business_overview: str
    recent_changes: str
    latest_financial_performance: str
    material_corporate_events: List[Dict[str, Any]]
    products_and_capacity: str
    order_book_and_contracts: str
    sector_and_policy_context: str
    competitive_landscape: str
    balance_sheet_risks: str
    market_reaction_summary: str
    open_questions: List[str]
    primary_sources: List[Dict[str, Any]]
    secondary_sources: List[Dict[str, Any]]
    grounded_findings: List[Dict[str, Any]] = Field(default_factory=list, description="Categorized into FACT, INFERENCE, UNKNOWN with citations")
    data_freshness_statement: str
