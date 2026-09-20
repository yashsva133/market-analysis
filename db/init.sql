-- India Market AI Research Terminal: Database Initialization Script
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Companies
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isin TEXT NOT NULL UNIQUE,
    legal_name TEXT NOT NULL,
    common_name TEXT,
    sector TEXT,
    industry TEXT,
    cin TEXT,
    ir_url TEXT,
    website_url TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_companies_isin ON companies (isin);
CREATE INDEX IF NOT EXISTS ix_companies_sector ON companies (sector);
CREATE INDEX IF NOT EXISTS ix_companies_industry ON companies (industry);
CREATE INDEX IF NOT EXISTS ix_companies_legal_name_trgm ON companies USING GIN (legal_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_companies_common_name_trgm ON companies USING GIN (common_name gin_trgm_ops);

-- 2. Securities
CREATE TABLE IF NOT EXISTS securities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    bse_scrip_code TEXT,
    security_type TEXT NOT NULL DEFAULT 'EQUITY',
    series TEXT NOT NULL DEFAULT 'EQ',
    upstox_instrument_key TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    listing_date DATE,
    delisting_date DATE,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_securities_exchange_symbol UNIQUE (exchange, symbol)
);

CREATE INDEX IF NOT EXISTS ix_securities_company_id ON securities (company_id);
CREATE INDEX IF NOT EXISTS ix_securities_bse_scrip_code ON securities (bse_scrip_code);
CREATE INDEX IF NOT EXISTS ix_securities_upstox_key ON securities (upstox_instrument_key);
CREATE INDEX IF NOT EXISTS ix_securities_exchange_active ON securities (exchange, is_active);
CREATE INDEX IF NOT EXISTS ix_securities_symbol_trgm ON securities USING GIN (symbol gin_trgm_ops);

-- 3. Company Aliases
CREATE TABLE IF NOT EXISTS company_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL DEFAULT 'NAME',
    source_id TEXT
);

CREATE INDEX IF NOT EXISTS ix_company_aliases_company_id ON company_aliases (company_id);
CREATE INDEX IF NOT EXISTS ix_company_aliases_alias_trgm ON company_aliases USING GIN (alias gin_trgm_ops);

-- 4. Sources
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    publisher TEXT NOT NULL,
    source_type TEXT NOT NULL,
    priority INT NOT NULL DEFAULT 1,
    base_url TEXT NOT NULL,
    robots_or_policy_note TEXT,
    active BOOLEAN NOT NULL DEFAULT true
);

-- 5. Source Items (Provenance & Raw Capture)
CREATE TABLE IF NOT EXISTS source_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL REFERENCES sources(id),
    url TEXT,
    canonical_url TEXT,
    external_id TEXT,
    headline TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_type TEXT NOT NULL DEFAULT 'text/html',
    content_hash TEXT NOT NULL,
    raw_location TEXT,
    status TEXT NOT NULL DEFAULT 'FETCHED',
    CONSTRAINT uq_source_items_source_content_hash UNIQUE (source_id, content_hash)
);

CREATE INDEX IF NOT EXISTS ix_source_items_source_id ON source_items (source_id);
CREATE INDEX IF NOT EXISTS ix_source_items_published_at ON source_items (published_at);
CREATE INDEX IF NOT EXISTS ix_source_items_status ON source_items (status);
CREATE INDEX IF NOT EXISTS ix_source_items_external_id ON source_items (external_id);

-- 6. Documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_item_id UUID NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    mime_type TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    page_count INT NOT NULL DEFAULT 1,
    text_quality REAL NOT NULL DEFAULT 1.0,
    storage_path TEXT NOT NULL,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_documents_source_item_id ON documents (source_item_id);
CREATE INDEX IF NOT EXISTS ix_documents_sha256 ON documents (sha256);

-- 7. Document Pages
CREATE TABLE IF NOT EXISTS document_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    text TEXT NOT NULL,
    image_path TEXT,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    CONSTRAINT uq_document_pages_page UNIQUE (document_id, page_number)
);

CREATE INDEX IF NOT EXISTS ix_document_pages_document_id ON document_pages (document_id);
CREATE INDEX IF NOT EXISTS ix_document_pages_tsv ON document_pages USING GIN (tsv);

-- 8. Events
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    source_item_id UUID NOT NULL REFERENCES source_items(id),
    event_type TEXT NOT NULL,
    importance TEXT NOT NULL DEFAULT 'MEDIUM',
    headline TEXT NOT NULL,
    event_time TIMESTAMPTZ,
    announcement_time TIMESTAMPTZ,
    amount NUMERIC(18,2),
    currency TEXT DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'EXTRACTED',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_events_company_id ON events (company_id);
CREATE INDEX IF NOT EXISTS ix_events_source_item_id ON events (source_item_id);
CREATE INDEX IF NOT EXISTS ix_events_event_type ON events (event_type);
CREATE INDEX IF NOT EXISTS ix_events_importance ON events (importance);
CREATE INDEX IF NOT EXISTS ix_events_announcement_time ON events (announcement_time);
CREATE INDEX IF NOT EXISTS ix_events_importance_announcement ON events (importance, announcement_time DESC);

-- 9. Event Facts
CREATE TABLE IF NOT EXISTS event_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    fact_key TEXT NOT NULL,
    fact_value JSONB NOT NULL,
    source_page INT,
    confidence REAL NOT NULL DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS ix_event_facts_event_id ON event_facts (event_id);
CREATE INDEX IF NOT EXISTS ix_event_facts_fact_key ON event_facts (fact_key);
CREATE INDEX IF NOT EXISTS ix_event_facts_value_gin ON event_facts USING GIN (fact_value);

-- 10. Event Relations
CREATE TABLE IF NOT EXISTS event_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    related_company_id UUID NOT NULL REFERENCES companies(id),
    relation_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_item_id UUID REFERENCES source_items(id)
);

CREATE INDEX IF NOT EXISTS ix_event_relations_event_id ON event_relations (event_id);
CREATE INDEX IF NOT EXISTS ix_event_relations_related_company ON event_relations (related_company_id);

-- 11. Financial Snapshots
CREATE TABLE IF NOT EXISTS financial_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    period TEXT NOT NULL,
    period_type TEXT NOT NULL DEFAULT 'QUARTERLY',
    is_consolidated BOOLEAN NOT NULL DEFAULT true,
    revenue NUMERIC(18,2),
    ebitda NUMERIC(18,2),
    pat NUMERIC(18,2),
    operating_cash_flow NUMERIC(18,2),
    free_cash_flow NUMERIC(18,2),
    debt NUMERIC(18,2),
    cash NUMERIC(18,2),
    market_cap NUMERIC(18,2),
    pe NUMERIC(10,2),
    pb NUMERIC(10,2),
    ev_ebitda NUMERIC(10,2),
    roce NUMERIC(10,2),
    roe NUMERIC(10,2),
    margins JSONB NOT NULL DEFAULT '{}'::jsonb,
    order_book NUMERIC(18,2),
    source TEXT,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    snapshot_date TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_financial_snapshots_company_id ON financial_snapshots (company_id);
CREATE INDEX IF NOT EXISTS ix_financial_snapshots_period ON financial_snapshots (company_id, period);

-- 12. Market Snapshots (OHLCV)
CREATE TABLE IF NOT EXISTS market_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id UUID NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    interval TEXT NOT NULL DEFAULT '1d',
    open NUMERIC(12,2) NOT NULL,
    high NUMERIC(12,2) NOT NULL,
    low NUMERIC(12,2) NOT NULL,
    close NUMERIC(12,2) NOT NULL,
    volume NUMERIC(18,0) NOT NULL,
    vwap NUMERIC(12,2),
    delivery_pct REAL,
    source TEXT NOT NULL DEFAULT 'NSE_BHAVCOPY'
);

CREATE INDEX IF NOT EXISTS ix_market_snapshots_security_time ON market_snapshots (security_id, timestamp DESC);

-- 13. AI Runs
CREATE TABLE IF NOT EXISTS ai_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    task TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    tokens_in INT NOT NULL DEFAULT 0,
    tokens_out INT NOT NULL DEFAULT 0,
    cached BOOLEAN NOT NULL DEFAULT false,
    error TEXT
);

CREATE INDEX IF NOT EXISTS ix_ai_runs_input_hash ON ai_runs (input_hash);
CREATE INDEX IF NOT EXISTS ix_ai_runs_task ON ai_runs (task);

-- 14. AI Outputs
CREATE TABLE IF NOT EXISTS ai_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_run_id UUID NOT NULL REFERENCES ai_runs(id) ON DELETE CASCADE,
    task TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id UUID NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    structured_output JSONB NOT NULL,
    evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_outputs_object ON ai_outputs (object_type, object_id);
CREATE INDEX IF NOT EXISTS ix_ai_outputs_structured_gin ON ai_outputs USING GIN (structured_output);

-- 15. Embeddings (pgvector)
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type TEXT NOT NULL,
    object_id UUID NOT NULL,
    chunk_index INT NOT NULL DEFAULT 0,
    embedding vector(384),
    text_snippet TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_embeddings_object ON embeddings (object_type, object_id);
CREATE INDEX IF NOT EXISTS ix_embeddings_vector_cosine ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 16. Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id),
    channel TEXT NOT NULL DEFAULT 'telegram',
    telegram_chat_id TEXT,
    telegram_message_id TEXT,
    alert_class TEXT NOT NULL,
    delivery_status TEXT NOT NULL DEFAULT 'PENDING',
    sent_at TIMESTAMPTZ,
    CONSTRAINT uq_alerts_event_class UNIQUE (event_id, alert_class)
);

CREATE INDEX IF NOT EXISTS ix_alerts_event_id ON alerts (event_id);
CREATE INDEX IF NOT EXISTS ix_alerts_delivery_status ON alerts (delivery_status);

-- 17. Source Health
CREATE TABLE IF NOT EXISTS source_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL UNIQUE REFERENCES sources(id),
    last_poll_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    consecutive_failures INT NOT NULL DEFAULT 0,
    success_rate_24h REAL NOT NULL DEFAULT 100.0,
    latency_ms INT NOT NULL DEFAULT 0,
    rate_limit_status TEXT NOT NULL DEFAULT 'OK',
    notes TEXT
);

-- 18. Knowledge Edges
CREATE TABLE IF NOT EXISTS knowledge_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    target_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_confirmed TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_knowledge_edges_source ON knowledge_edges (source_company_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_edges_target ON knowledge_edges (target_company_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_edges_relation ON knowledge_edges (relation_type);

-- 19. Market Quotes (Latest live state)
CREATE TABLE IF NOT EXISTS market_quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id UUID NOT NULL UNIQUE REFERENCES securities(id) ON DELETE CASCADE,
    last_price NUMERIC(12,2) NOT NULL,
    change_pct REAL NOT NULL DEFAULT 0.0,
    day_high NUMERIC(12,2),
    day_low NUMERIC(12,2),
    volume NUMERIC(18,0) NOT NULL,
    vwap NUMERIC(12,2),
    as_of TIMESTAMPTZ NOT NULL DEFAULT now(),
    source TEXT NOT NULL DEFAULT 'FREE'
);

CREATE INDEX IF NOT EXISTS ix_market_quotes_security_id ON market_quotes (security_id);
CREATE INDEX IF NOT EXISTS ix_market_quotes_as_of ON market_quotes (as_of DESC);

-- 20. Watchlists & Items
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL DEFAULT 'Default Watchlist',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    is_muted BOOLEAN NOT NULL DEFAULT false,
    notes TEXT,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_watchlist_items_company UNIQUE (watchlist_id, company_id)
);

CREATE INDEX IF NOT EXISTS ix_watchlist_items_watchlist_id ON watchlist_items (watchlist_id);
CREATE INDEX IF NOT EXISTS ix_watchlist_items_company_id ON watchlist_items (company_id);

-- 21. Portfolio Holdings (Optional Read-Only Broker Sync)
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isin TEXT NOT NULL,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity NUMERIC(12,2) NOT NULL DEFAULT 0,
    average_price NUMERIC(12,2) NOT NULL DEFAULT 0,
    last_price NUMERIC(12,2),
    pnl NUMERIC(14,2),
    as_of TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_portfolio_holdings_exchange_symbol UNIQUE (exchange, symbol)
);

CREATE INDEX IF NOT EXISTS ix_portfolio_holdings_isin ON portfolio_holdings (isin);
CREATE INDEX IF NOT EXISTS ix_portfolio_holdings_company_id ON portfolio_holdings (company_id);

-- 22. Technical Signals
CREATE TABLE IF NOT EXISTS technical_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id UUID NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    indicator TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1D',
    value REAL NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    as_of TIMESTAMPTZ NOT NULL DEFAULT now(),
    source TEXT NOT NULL DEFAULT 'DETERMINISTIC_ENGINE'
);

CREATE INDEX IF NOT EXISTS ix_technical_signals_sec_indicator ON technical_signals (security_id, indicator, as_of DESC);

-- 23. Universe Change Events
CREATE TABLE IF NOT EXISTS universe_change_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isin TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    change_type TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_universe_change_events_isin ON universe_change_events (isin);
CREATE INDEX IF NOT EXISTS ix_universe_change_events_detected ON universe_change_events (detected_at DESC);

-- Seed Base Sources
INSERT INTO sources (id, name, publisher, source_type, priority, base_url, active)
VALUES
    ('nse-announcements', 'NSE Corporate Filings', 'National Stock Exchange of India', 'exchange_filing', 1, 'https://www.nseindia.com/api/corporate-announcements', true),
    ('bse-announcements', 'BSE Corporate Announcements', 'BSE India', 'exchange_filing', 1, 'https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w', true),
    ('sebi-circulars', 'SEBI Regulatory Disclosures', 'Securities and Exchange Board of India', 'regulator', 2, 'https://www.sebi.gov.in/curation/corporate_filings.html', true),
    ('pib-press-releases', 'Press Information Bureau', 'Government of India', 'government', 2, 'https://pib.gov.in/RssMain.aspx', true),
    ('rbi-notifications', 'RBI Press Releases', 'Reserve Bank of India', 'regulator', 2, 'https://rbi.org.in/scripts/BS_PressReleaseDisplay.aspx', true),
    ('google-news-rss', 'Indian Equities News Feed', 'Public RSS aggregator', 'rss_feed', 3, 'https://news.google.com/rss/search', true),
    ('yahoo-market-data', 'Market Prices & OHLCV Fallback', 'Yahoo Finance API', 'market_price_fallback', 4, 'https://query1.finance.yahoo.com', true)
ON CONFLICT (id) DO NOTHING;

-- Initialize Source Health records
INSERT INTO source_health (id, source_id, last_poll_at, last_success_at, consecutive_failures, success_rate_24h, latency_ms, rate_limit_status)
SELECT gen_random_uuid(), s.id, now(), now(), 0, 100.0, 0, 'OK'
FROM sources s
ON CONFLICT (source_id) DO NOTHING;
