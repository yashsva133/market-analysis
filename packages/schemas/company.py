"""Pydantic schemas for companies, securities, and corporate entities."""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SecurityBase(BaseModel):
    exchange: str = Field(..., description="NSE or BSE")
    symbol: str = Field(..., description="Ticker symbol (e.g. RELIANCE, TCS)")
    bse_scrip_code: Optional[str] = Field(None, description="BSE numeric scrip code")
    security_type: str = Field(default="EQUITY", description="EQUITY, SME, ETF, REIT")
    series: str = Field(default="EQ", description="EQ, BE, SM")
    is_active: bool = Field(default=True)
    listing_date: Optional[date] = None
    delisting_date: Optional[date] = None


class SecurityCreate(SecurityBase):
    company_id: Optional[UUID] = None


class SecurityRead(SecurityBase):
    id: UUID
    company_id: UUID
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyAliasRead(BaseModel):
    id: UUID
    alias: str
    alias_type: str
    source_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyBase(BaseModel):
    isin: str = Field(..., description="International Securities Identification Number (12 characters)")
    legal_name: str = Field(..., description="Official registered company name")
    common_name: Optional[str] = Field(None, description="Popular trade name")
    sector: Optional[str] = Field(None, description="Macro sector")
    industry: Optional[str] = Field(None, description="Specific industry classification")
    cin: Optional[str] = Field(None, description="Corporate Identification Number")
    ir_url: Optional[str] = Field(None, description="Investor relations web portal")
    website_url: Optional[str] = Field(None, description="Official company website")
    status: str = Field(default="ACTIVE", description="ACTIVE, SUSPENDED, DELISTED")


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    id: UUID
    first_seen: datetime
    last_seen: datetime
    securities: List[SecurityRead] = []

    # Display & Market Snapshot Helpers
    name: Optional[str] = None
    symbol: Optional[str] = None
    bse_code: Optional[str] = None
    market_cap: Optional[str] = None
    revenue: Optional[str] = None
    pat: Optional[str] = None
    pe: Optional[str] = None
    roce: Optional[str] = None
    price: Optional[str] = None
    rsi: Optional[str] = None
    sma50: Optional[str] = None
    is_demo: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)
