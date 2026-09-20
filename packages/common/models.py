"""SQLAlchemy ORM models defining the complete database schema.

Built strictly according to Section 20 and the postgresql-table-design skill:
- UUID primary keys with gen_random_uuid()
- Explicit B-tree indexes on all Foreign Keys
- TIMESTAMPTZ for timestamps and NUMERIC for currency
- JSONB with GIN indexing for structured facts and AI outputs
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isin = Column(Text, unique=True, nullable=False, index=True)
    legal_name = Column(Text, nullable=False)
    common_name = Column(Text, nullable=True)
    sector = Column(Text, nullable=True, index=True)
    industry = Column(Text, nullable=True, index=True)
    cin = Column(Text, nullable=True)
    ir_url = Column(Text, nullable=True)
    website_url = Column(Text, nullable=True)
    status = Column(Text, default="ACTIVE", nullable=False)  # ACTIVE, SUSPENDED, DELISTED
    first_seen = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    securities = relationship("Security", back_populates="company", cascade="all, delete-orphan")
    aliases = relationship("CompanyAlias", back_populates="company", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="company")
    financial_snapshots = relationship("FinancialSnapshot", back_populates="company", cascade="all, delete-orphan")
    watchlist_items = relationship("WatchlistItem", back_populates="company", cascade="all, delete-orphan")


class Security(Base):
    __tablename__ = "securities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    exchange = Column(Text, nullable=False)  # NSE, BSE
    symbol = Column(Text, nullable=False)    # e.g. RELIANCE, TCS
    bse_scrip_code = Column(Text, nullable=True, index=True)  # e.g. 500325
    security_type = Column(Text, default="EQUITY", nullable=False)  # EQUITY, SME, ETF, REIT
    series = Column(Text, default="EQ", nullable=False)             # EQ, BE, SM
    upstox_instrument_key = Column(Text, nullable=True, index=True) # e.g. NSE_EQ|INE002A01018
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    listing_date = Column(Date, nullable=True)
    delisting_date = Column(Date, nullable=True)
    last_seen = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("exchange", "symbol", name="uq_securities_exchange_symbol"),
        Index("ix_securities_exchange_active", "exchange", "is_active"),
    )

    company = relationship("Company", back_populates="securities")
    market_snapshots = relationship("MarketSnapshot", back_populates="security")
    quote = relationship("MarketQuote", back_populates="security", uselist=False, cascade="all, delete-orphan")
    technical_signals = relationship("TechnicalSignal", back_populates="security", cascade="all, delete-orphan")


class CompanyAlias(Base):
    __tablename__ = "company_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    alias = Column(Text, nullable=False, index=True)
    alias_type = Column(Text, default="NAME", nullable=False)  # NAME, CIN, SYMBOL_HISTORY, BRAND
    source_id = Column(Text, nullable=True)

    company = relationship("Company", back_populates="aliases")


class Source(Base):
    __tablename__ = "sources"

    id = Column(Text, primary_key=True)  # e.g. nse-announcements, bse-announcements
    name = Column(Text, nullable=False)
    publisher = Column(Text, nullable=False)
    source_type = Column(Text, nullable=False)  # exchange_filing, government, regulator, rss_feed
    priority = Column(Integer, default=1, nullable=False)
    base_url = Column(Text, nullable=False)
    robots_or_policy_note = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    source_items = relationship("SourceItem", back_populates="source")
    health = relationship("SourceHealth", back_populates="source", uselist=False)


class SourceItem(Base):
    __tablename__ = "source_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(Text, ForeignKey("sources.id"), nullable=False, index=True)
    url = Column(Text, nullable=True)
    canonical_url = Column(Text, nullable=True)
    external_id = Column(Text, nullable=True, index=True)
    headline = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    fetched_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    content_type = Column(Text, default="text/html", nullable=False)
    content_hash = Column(Text, nullable=False)  # SHA-256
    raw_location = Column(Text, nullable=True)
    status = Column(Text, default="FETCHED", nullable=False)  # FETCHED, PROCESSED, ERROR, DUPLICATE

    __table_args__ = (
        UniqueConstraint("source_id", "content_hash", name="uq_source_items_source_content_hash"),
        Index("ix_source_items_status", "status"),
    )

    source = relationship("Source", back_populates="source_items")
    documents = relationship("Document", back_populates="source_item")
    events = relationship("Event", back_populates="source_item")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_item_id = Column(UUID(as_uuid=True), ForeignKey("source_items.id", ondelete="CASCADE"), nullable=False, index=True)
    mime_type = Column(Text, nullable=False)
    sha256 = Column(Text, nullable=False, unique=True, index=True)
    page_count = Column(Integer, default=1, nullable=False)
    text_quality = Column(Float, default=1.0, nullable=False)
    storage_path = Column(Text, nullable=False)
    extracted_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    source_item = relationship("SourceItem", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    image_path = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_pages_page"),
    )

    document = relationship("Document", back_populates="pages")


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    source_item_id = Column(UUID(as_uuid=True), ForeignKey("source_items.id"), nullable=False, index=True)
    event_type = Column(Text, nullable=False, index=True)  # FROM EventTaxonomy
    importance = Column(Text, default="MEDIUM", nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    headline = Column(Text, nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=True)
    announcement_time = Column(DateTime(timezone=True), nullable=True, index=True)
    amount = Column(Numeric(precision=18, scale=2), nullable=True)
    currency = Column(Text, default="INR", nullable=True)
    status = Column(Text, default="EXTRACTED", nullable=False)  # EXTRACTED, VERIFIED, ARCHIVED
    confidence = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_events_importance_announcement", "importance", "announcement_time"),
    )

    company = relationship("Company", back_populates="events")
    source_item = relationship("SourceItem", back_populates="events")
    facts = relationship("EventFact", back_populates="event", cascade="all, delete-orphan")
    relations = relationship("EventRelation", back_populates="event", cascade="all, delete-orphan")
    alerts = relationship("AlertRecord", back_populates="event")


class EventFact(Base):
    __tablename__ = "event_facts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    fact_key = Column(Text, nullable=False, index=True)  # e.g. order_amount, counterparty, duration
    fact_value = Column(JSONB, nullable=False)           # JSONB value
    source_page = Column(Integer, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    __table_args__ = (
        Index("ix_event_facts_value_gin", "fact_value", postgresql_using="gin"),
    )

    event = relationship("Event", back_populates="facts")


class EventRelation(Base):
    __tablename__ = "event_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    related_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    relation_type = Column(Text, nullable=False)  # COMPETITOR, CUSTOMER, SUPPLIER, SUBSIDIARY
    confidence = Column(Float, default=1.0, nullable=False)
    source_item_id = Column(UUID(as_uuid=True), ForeignKey("source_items.id"), nullable=True)

    event = relationship("Event", back_populates="relations")


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(Text, nullable=False)  # e.g. Q1-FY26, FY25
    period_type = Column(Text, default="QUARTERLY", nullable=False)  # QUARTERLY, ANNUAL
    is_consolidated = Column(Boolean, default=True, nullable=False)
    revenue = Column(Numeric(precision=18, scale=2), nullable=True)
    ebitda = Column(Numeric(precision=18, scale=2), nullable=True)
    pat = Column(Numeric(precision=18, scale=2), nullable=True)
    operating_cash_flow = Column(Numeric(precision=18, scale=2), nullable=True)
    free_cash_flow = Column(Numeric(precision=18, scale=2), nullable=True)
    debt = Column(Numeric(precision=18, scale=2), nullable=True)
    cash = Column(Numeric(precision=18, scale=2), nullable=True)
    market_cap = Column(Numeric(precision=18, scale=2), nullable=True)
    pe = Column(Numeric(precision=10, scale=2), nullable=True)
    pb = Column(Numeric(precision=10, scale=2), nullable=True)
    ev_ebitda = Column(Numeric(precision=10, scale=2), nullable=True)
    roce = Column(Numeric(precision=10, scale=2), nullable=True)
    roe = Column(Numeric(precision=10, scale=2), nullable=True)
    margins = Column(JSONB, default=dict, nullable=False)
    order_book = Column(Numeric(precision=18, scale=2), nullable=True)
    source = Column(Text, nullable=True)
    raw_data = Column(JSONB, default=dict, nullable=False)
    snapshot_date = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    company = relationship("Company", back_populates="financial_snapshots")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id = Column(UUID(as_uuid=True), ForeignKey("securities.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    interval = Column(Text, default="1d", nullable=False)  # 1m, 5m, 1d
    open = Column(Numeric(precision=12, scale=2), nullable=False)
    high = Column(Numeric(precision=12, scale=2), nullable=False)
    low = Column(Numeric(precision=12, scale=2), nullable=False)
    close = Column(Numeric(precision=12, scale=2), nullable=False)
    volume = Column(Numeric(precision=18, scale=0), nullable=False)
    vwap = Column(Numeric(precision=12, scale=2), nullable=True)
    delivery_pct = Column(Float, nullable=True)
    source = Column(Text, default="NSE_BHAVCOPY", nullable=False)

    security = relationship("Security", back_populates="market_snapshots")


class AIRun(Base):
    __tablename__ = "ai_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Text, nullable=False)  # gemini, openai_compatible, rule_fallback
    model = Column(Text, nullable=False)
    task = Column(Text, nullable=False, index=True)  # classification, extraction, materiality, research
    input_hash = Column(Text, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Text, default="RUNNING", nullable=False)  # SUCCESS, FAILED, RUNNING
    tokens_in = Column(Integer, default=0, nullable=False)
    tokens_out = Column(Integer, default=0, nullable=False)
    cached = Column(Boolean, default=False, nullable=False)
    error = Column(Text, nullable=True)

    outputs = relationship("AIOutput", back_populates="ai_run", cascade="all, delete-orphan")


class AIOutput(Base):
    __tablename__ = "ai_outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_run_id = Column(UUID(as_uuid=True), ForeignKey("ai_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    task = Column(Text, nullable=False)
    object_type = Column(Text, nullable=False)  # event, company, document
    object_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    schema_version = Column(Text, default="1.0", nullable=False)
    structured_output = Column(JSONB, nullable=False)
    evidence_ids = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_ai_outputs_structured_gin", "structured_output", postgresql_using="gin"),
    )

    ai_run = relationship("AIRun", back_populates="outputs")


class AlertRecord(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    channel = Column(Text, default="telegram", nullable=False)
    telegram_chat_id = Column(Text, nullable=True)
    telegram_message_id = Column(Text, nullable=True)
    alert_class = Column(Text, nullable=False)  # CRITICAL, HIGH, DIGEST
    delivery_status = Column(Text, default="PENDING", nullable=False)  # SENT, FAILED, PENDING
    sent_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("event_id", "alert_class", name="uq_alerts_event_class"),
    )

    event = relationship("Event", back_populates="alerts")


class SourceHealth(Base):
    __tablename__ = "source_health"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(Text, ForeignKey("sources.id"), unique=True, nullable=False, index=True)
    last_poll_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    success_rate_24h = Column(Float, default=100.0, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    rate_limit_status = Column(Text, default="OK", nullable=False)  # OK, THROTTLED, BLOCKED
    status = Column(Text, default="healthy", nullable=False)        # healthy, degraded, rate-limited, failed, stale
    notes = Column(Text, nullable=True)

    source = relationship("Source", back_populates="health")


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    target_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type = Column(Text, nullable=False)  # SUBSIDIARY, CUSTOMER, SUPPLIER, COMPETITOR, PROMOTER, THEME
    confidence = Column(Float, default=1.0, nullable=False)
    source_evidence = Column(JSONB, default=dict, nullable=False)
    first_seen = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_confirmed = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id = Column(UUID(as_uuid=True), ForeignKey("securities.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    last_price = Column(Numeric(precision=12, scale=2), nullable=False)
    change_pct = Column(Float, default=0.0, nullable=False)
    day_high = Column(Numeric(precision=12, scale=2), nullable=True)
    day_low = Column(Numeric(precision=12, scale=2), nullable=True)
    volume = Column(Numeric(precision=18, scale=0), nullable=False)
    vwap = Column(Numeric(precision=12, scale=2), nullable=True)
    as_of = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    source = Column(Text, default="FREE", nullable=False)  # FREE, UPSTOX, FALLBACK

    security = relationship("Security", back_populates="quote")


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, default="Default Watchlist", nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    watchlist_id = Column(UUID(as_uuid=True), ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    is_muted = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    added_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("watchlist_id", "company_id", name="uq_watchlist_items_company"),
    )

    watchlist = relationship("Watchlist", back_populates="items")
    company = relationship("Company", back_populates="watchlist_items")


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isin = Column(Text, nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    exchange = Column(Text, nullable=False)  # NSE, BSE
    symbol = Column(Text, nullable=False)
    quantity = Column(Numeric(precision=12, scale=2), default=0, nullable=False)
    average_price = Column(Numeric(precision=12, scale=2), default=0, nullable=False)
    last_price = Column(Numeric(precision=12, scale=2), nullable=True)
    pnl = Column(Numeric(precision=14, scale=2), nullable=True)
    as_of = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("exchange", "symbol", name="uq_portfolio_holdings_exchange_symbol"),
    )


class TechnicalSignal(Base):
    __tablename__ = "technical_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id = Column(UUID(as_uuid=True), ForeignKey("securities.id", ondelete="CASCADE"), nullable=False, index=True)
    indicator = Column(Text, nullable=False, index=True)  # RSI_14, SMA_50, SMA_200, MACD, BB, VWAP
    timeframe = Column(Text, default="1D", nullable=False)  # 1D, 1H
    value = Column(Float, nullable=False)
    metadata_json = Column(JSONB, default=dict, nullable=False)
    as_of = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    source = Column(Text, default="DETERMINISTIC_ENGINE", nullable=False)

    __table_args__ = (
        Index("ix_technical_signals_sec_indicator", "security_id", "indicator", "as_of"),
    )

    security = relationship("Security", back_populates="technical_signals")


class UniverseChangeEvent(Base):
    __tablename__ = "universe_change_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isin = Column(Text, nullable=False, index=True)
    exchange = Column(Text, nullable=False)  # NSE, BSE
    symbol = Column(Text, nullable=False)
    change_type = Column(Text, nullable=False, index=True)  # NEW_LISTING, DELISTING, SUSPENSION, SYMBOL_CHANGE
    details = Column(JSONB, default=dict, nullable=False)
    detected_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


# =====================================================================
# Advanced Scenario Engine & Model Registry Tables (§18, §84, §85)
# =====================================================================

class ModelRegistryRecord(Base):
    __tablename__ = "model_registry"

    id = Column(Text, primary_key=True)  # model_id
    model_name = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    family = Column(Text, nullable=False)
    status = Column(Text, default="ACTIVE", nullable=False)  # ACTIVE, VALIDATING, EXPERIMENTAL, RETIRED
    feature_set_version = Column(Text, default="2.0.0", nullable=False)
    metrics = Column(JSONB, default=dict, nullable=False)
    gating_passed = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class FeatureSnapshotRecord(Base):
    __tablename__ = "feature_snapshots"

    id = Column(Text, primary_key=True)  # snapshot_id hash
    symbol = Column(Text, nullable=False, index=True)
    feature_set_version = Column(Text, default="2.0.0", nullable=False)
    as_of = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    feature_count = Column(Integer, default=0, nullable=False)
    features = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProbabilityPredictionRecord(Base):
    """Prediction table for long-term calibration and empirical model tracking (§85)."""
    __tablename__ = "probability_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(Text, nullable=False, index=True)
    prediction_time = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    horizon = Column(Integer, nullable=False)  # trading days
    target_type = Column(Text, default="PRICE_TOUCH", nullable=False)
    target_value = Column(Numeric(precision=12, scale=2), nullable=False)
    entry_price = Column(Numeric(precision=12, scale=2), nullable=False)
    model_id = Column(Text, nullable=False, index=True)
    ensemble_id = Column(Text, nullable=False)
    raw_probability = Column(Float, nullable=False)
    calibrated_probability = Column(Float, nullable=False)
    forecast_quantiles = Column(JSONB, default=dict, nullable=False)
    feature_snapshot_id = Column(Text, nullable=True)
    data_snapshot_id = Column(Text, nullable=True)
    status = Column(Text, default="PENDING", nullable=False)  # PENDING, RESOLVED
    actual_value = Column(Numeric(precision=12, scale=2), nullable=True)
    target_hit = Column(Boolean, nullable=True)
    target_finished = Column(Boolean, nullable=True)
    max_favorable_excursion = Column(Numeric(precision=12, scale=2), nullable=True)
    max_adverse_excursion = Column(Numeric(precision=12, scale=2), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class ScenarioRunRecord(Base):
    __tablename__ = "scenario_runs"

    id = Column(Text, primary_key=True)  # scen_...
    symbol = Column(Text, nullable=False, index=True)
    capital = Column(Numeric(precision=14, scale=2), nullable=False)
    horizon_days = Column(Integer, nullable=False)
    current_price = Column(Numeric(precision=12, scale=2), nullable=False)
    target_price = Column(Numeric(precision=12, scale=2), nullable=False)
    scenarios = Column(JSONB, default=dict, nullable=False)
    capital_outcomes = Column(JSONB, default=dict, nullable=False)
    model_metadata = Column(JSONB, default=dict, nullable=False)
    ai_reasoning = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class MarketRegimeRecord(Base):
    __tablename__ = "market_regimes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regime_name = Column(Text, nullable=False, index=True)  # TRENDING_UP, TRENDING_DOWN, HIGH_VOLATILITY, RANGE_BOUND
    nifty_return_20d = Column(Float, nullable=False)
    india_vix = Column(Float, nullable=False)
    market_breadth_ad = Column(Float, nullable=False)
    detected_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


