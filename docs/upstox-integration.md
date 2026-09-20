# Upstox V2 API Integration Guide

**System:** India Market AI Research Terminal  
**Status:** Implemented & Verified (Optional Provider)  
**Security Level:** Read-Only / Zero-Trading / Non-Advisory  

---

## 1. Overview & Architecture Role

The Upstox integration acts as an **optional, authenticated market data and portfolio provider**. It is designed strictly to enrich the terminal with real-time market quotes, historical/intraday candlestick charts, and personal portfolio visibility without compromising the system's core architecture or independence.

### Core Architecture Principles:
1. **Not a Single Source of Truth:** Upstox is **never** used as the primary source for corporate filings, exchange announcements, regulatory disclosures, or company identities.
2. **Canonical Identity Preservation:** The system's primary company identity remains the **ISIN** (International Securities Identification Number) and internal `company_id`. An Upstox `instrument_key` (e.g. `NSE_EQ|INE002A01018`) is strictly a provider-specific mapping attribute.
3. **Multi-Exchange Independence:** NSE and BSE securities maintain distinct `instrument_key` values and are never conflated even when sharing an ISIN.
4. **Zero-Trading / Read-Only Guardrail:** No trading endpoints exist. The codebase contains no automated order execution, rebalancing algorithms, or buy/sell execution logic.
5. **Full System Decoupling:** The entire terminal operates completely and normally when `UPSTOX_ENABLED=false`. All market features transparently fall back to the `FreeMarketDataProvider` (NSE Bhavcopy / Yahoo Finance / deterministic models).

---

## 2. Configuration & Environment Variables

Credentials must **only** come from local environment configuration (`.env`). They are never hardcoded, never committed to git, never exposed to frontend clients, never passed to LLMs, and never persisted in PostgreSQL.

In `.env`:

```bash
# Enable or disable Upstox integration (Default: false)
UPSTOX_ENABLED=false

# Upstox API v2 Credentials (from Upstox Developer Console)
UPSTOX_API_KEY=your_upstox_api_key_here
UPSTOX_API_SECRET=your_upstox_api_secret_here
UPSTOX_REDIRECT_URI=http://127.0.0.1:8000/api/auth/upstox/callback

# Explicit Access Token (for local, non-interactive personal use)
UPSTOX_ACCESS_TOKEN=your_generated_access_token_here
```

> [!IMPORTANT]
> When `UPSTOX_ENABLED=false`, none of the `UPSTOX_*` environment variables are required. The system initializes without checking or logging them.

---

## 3. Token Lifecycle & Authentication

Upstox V2 uses standard OAuth 2.0. In production brokerage APIs in India, OAuth access tokens expire daily (typically at 03:30 AM IST).

### Recommended Personal Use Workflow:
1. **Interactive Login:** If using UI login, visit your Upstox authorization URL:
   ```
   https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={API_KEY}&redirect_uri={REDIRECT_URI}
   ```
2. **Token Exchange:** The authorization code returned to your redirect URI is exchanged for an `access_token` via:
   ```
   POST https://api.upstox.com/v2/login/authorization/token
   ```
3. **Direct Token Insertion:** For local development and private terminal usage, you can obtain an access token once in the morning from the Upstox Developer Portal and export it in `.env` as `UPSTOX_ACCESS_TOKEN`. The terminal will immediately use it for that trading day.

---

## 4. Instrument Mapping & Database Schema

The relationship between canonical companies, exchange securities, and Upstox instrument keys is stored in the database:

```sql
-- Schema representation in PostgreSQL:
CREATE TABLE securities (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    exchange VARCHAR(10) NOT NULL,       -- 'NSE' or 'BSE'
    symbol VARCHAR(30) NOT NULL,         -- e.g. 'RELIANCE' or '500325'
    isin VARCHAR(12) NOT NULL,           -- e.g. 'INE002A01018'
    upstox_instrument_key VARCHAR(100),  -- e.g. 'NSE_EQ|INE002A01018'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Mapping Rules:
- NSE Equity: `NSE_EQ|{ISIN}` or `NSE_EQ|{SYMBOL}`
- BSE Equity: `BSE_EQ|{ISIN}` or `BSE_EQ|{SCRIP_CODE}`
- Querying a company fetches all associated securities. If a company is dual-listed, both NSE and BSE securities maintain their respective Upstox keys.

---

## 5. API Capabilities & Fallback Behavior

All market data requests route through the `MarketDataManager`, which respects `MARKET_DATA_PRIMARY` and `MARKET_DATA_FALLBACK`:

| API Endpoint | Upstox Enabled Response | Upstox Disabled / Offline Fallback |
| :--- | :--- | :--- |
| `GET /api/market/providers` | Lists `UpstoxProvider` as active primary, `FreeMarketDataProvider` as fallback | Lists `FreeMarketDataProvider` as active primary |
| `GET /api/market/health` | Real-time connectivity and token validity check | Status of local free market data provider |
| `GET /api/market/quote/{security_id}` | Live market quote (LTP, OHLC, 52W High/Low, volume) from Upstox v2 API | Quotes from NSE Bhavcopy / Free provider |
| `GET /api/market/history/{security_id}` | Intraday or daily historical candle series from Upstox historical endpoints | Historical candles from Yahoo/Bhavcopy or deterministic series |
| `GET /api/portfolio` | User's actual holdings and open positions from Upstox | Returns empty portfolio with status `{"status": "upstox_disabled", "holdings": []}` |

---

## 6. Live Streaming & Subscription Manager

To prevent saturating network bandwidth and breaching API rate limits:
- The terminal **never** attempts to subscribe to thousands of instruments simultaneously.
- The `MarketSubscriptionManager` maintains a selective subscription set containing:
  1. Securities currently visible in the active Watchlist
  2. Securities present in the user's Portfolio
  3. Securities flagged in high-materiality corporate events within the last 2 hours
- Only this selective subset receives real-time tick streaming, while OHLCV snapshots are stored in PostgreSQL without polluting the database with sub-second tick noise.

---

## 7. Security & Compliance Checklist

- [x] **No Secrets in Logs:** Access tokens and client secrets are masked in all structured logger outputs.
- [x] **No Secrets in Frontend:** API endpoints never transmit `client_secret` or `access_token` to Next.js or browser DOM.
- [x] **No LLM Leakage:** Prompts sent to Gemini or Ollama never contain brokerage credentials or portfolio account IDs.
- [x] **Non-Advisory Mandate:** Portfolio screens and alerts are strictly informational. The terminal never issues buy/sell recommendations or price targets.
