"""Pydantic schemas for data sources, provenance items, and health tracking."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SourceRead(BaseModel):
    id: str
    name: str
    publisher: str
    source_type: str
    priority: int
    base_url: str
    robots_or_policy_note: Optional[str] = None
    active: bool

    model_config = ConfigDict(from_attributes=True)


class SourceItemBase(BaseModel):
    source_id: str
    url: Optional[str] = None
    canonical_url: Optional[str] = None
    external_id: Optional[str] = None
    headline: str
    published_at: Optional[datetime] = None
    content_type: str = "text/html"
    content_hash: str
    raw_location: Optional[str] = None
    status: str = "FETCHED"


class SourceItemCreate(SourceItemBase):
    pass


class SourceItemRead(SourceItemBase):
    id: UUID
    fetched_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceHealthRead(BaseModel):
    id: UUID
    source_id: str
    last_poll_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    consecutive_failures: int = 0
    success_rate_24h: float = 100.0
    latency_ms: int = 0
    rate_limit_status: str = "OK"
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
