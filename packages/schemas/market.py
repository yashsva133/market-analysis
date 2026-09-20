"""Pydantic schemas for financial statements, market data, and event price reaction."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class FinancialSnapshotRead(BaseModel):
    id: UUID
    company_id: UUID
    period: str
    period_type: str
    is_consolidated: bool
    revenue: Optional[Decimal] = None
    ebitda: Optional[Decimal] = None
    pat: Optional[Decimal] = None
    operating_cash_flow: Optional[Decimal] = None
    free_cash_flow: Optional[Decimal] = None
    debt: Optional[Decimal] = None
    cash: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    pe: Optional[Decimal] = None
    pb: Optional[Decimal] = None
    ev_ebitda: Optional[Decimal] = None
    roce: Optional[Decimal] = None
    roe: Optional[Decimal] = None
    margins: Dict[str, Any] = {}
    order_book: Optional[Decimal] = None
    source: Optional[str] = None
    snapshot_date: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketSnapshotRead(BaseModel):
    id: UUID
    security_id: UUID
    timestamp: datetime
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Optional[Decimal] = None
    delivery_pct: Optional[float] = None
    source: str

    model_config = ConfigDict(from_attributes=True)


class MarketReactionResult(BaseModel):
    event_id: UUID
    announcement_time: Optional[datetime] = None
    price_at_publish: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    same_day_pct_change: Optional[float] = None
    one_day_pct_change: Optional[float] = None
    three_day_pct_change: Optional[float] = None
    five_day_pct_change: Optional[float] = None
    twenty_day_pct_change: Optional[float] = None
    volume_multiple_20d: Optional[float] = None
    gap_pct: Optional[float] = None
    interpretation: Optional[str] = Field(None, description="Purely factual description of reaction")
