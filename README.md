# India Market AI Research Terminal

> **Version:** 1.0
> **Target:** Local-first, personal-use Indian equity research, probabilistic forecasting, and event-monitoring terminal covering NSE + BSE.
> **Cost model:** ₹0 recurring where practical; Gemini used only where cloud intelligence materially improves the product.

A Bloomberg/Fincept-style dark terminal for the Indian equity market. It combines deterministic quantitative engines, probabilistic time-series forecasting (Chronos-2 adapter with a local statistical fallback), SEBI LODR materiality triage, and a controlled Google Gemini research agent.

---

## 1. What It Is

The terminal is a **research and intelligence system**, not a stock picker and not an auto-trader. It produces:

- **SOURCE-DERIVED** facts (NSE/BSE/Upstox ticks and filings)
- **CALCULATED** metrics (deterministic technicals, returns, volatility)
- **MODEL-DERIVED** probabilities (calibrated statistical models)
- **LLM-INTERPRETED** narrative (Gemini synthesis, never invented numbers)

### Core guarantees

- **No fake data.** When a feed is unreachable, the terminal reports `UNAVAILABLE` — it never substitutes a synthetic price, a fabricated probability, or a made-up financial figure.
- **No fabricated probabilities.** Probabilities come from statistical models and Monte Carlo simulation. The LLM explains them; it never changes them.
- **Whole-share cash equity.** Executable positions are `floor((capital − costs) / price)`. Insufficient capital is flagged explicitly.
- **No autonomous order execution.** `LIVE_EXECUTION = false`. The terminal is read-only against brokers.
- **Point-in-time anti-leakage.** Backtests and features reject future candles, announcements, financials, and corporate actions.

---

## 2. Architecture

```
                         USER
                          │
                          ▼
                 NEXT.JS TERMINAL (Port 3000)
                          │
             ┌────────────┼────────────┐
             │            │            │
          REST API      WebSocket    Search
             │            │            │
             └────────────┼────────────┘
                          ▼
                     FASTAPI CORE (Port 8000)
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
 DATA PLATFORM       RESEARCH PLATFORM   QUANT PLATFORM
       │                  │                  │
       ▼                  ▼                  ▼
 NSE / BSE           Documents / Filings Historical Data
 Upstox V2           News & Disclosures  Feature Store
 PIB Disclosures     RAG / Vector DB     Forecasting
 Corporate Actions   Gemini Analyst      Calibration / Scenarios
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ▼
                  MODEL ORCHESTRATOR
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
     Chronos-2       Lightweight ML    Statistical
    Forecasting        Models           Baselines
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                 PROBABILITY ENGINE (ECE / Brier)
                          │
                          ▼
                  SCENARIO ENGINE (5 Tiers)
                          │
                          ▼
              CAPITAL & STATUTORY COST ENGINE
                          │
                          ▼
                    GEMINI ANALYST (Qualitative Synthesis)
                          │
                          ▼
                    TERMINAL UI (18 Workspaces)
```

---

## 3. Requirements

- **OS:** Windows 10/11 (PowerShell), Linux, or macOS
- **Python:** 3.10+ (verified on 3.13)
- **Node.js:** 18+ (verified on 22/24)
- **RAM:** 4 GB minimum (8 GB+ recommended for neural forecasts)
- **Acceleration:** CPU by default; CUDA used automatically if available
- **Database (optional):** PostgreSQL 16+ with `pgvector` — the terminal runs in degraded in-memory mode when PostgreSQL is offline

---

## 4. Installation

```bash
# 1. Clone
git clone <repo-url> india-market-terminal
cd india-market-terminal

# 2. Python environment & dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Frontend
cd apps/web
npm install
npm run build
cd ../..

# 4. Configuration
cp .env.example .env
```

---

## 5. Environment Variables

Configure `.env` in the repository root (see `.env.example`):

```ini
ENVIRONMENT=development
TIMEZONE=Asia/Kolkata

# Database (PostgreSQL 16 + pgvector) — optional
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/india_market_terminal
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@localhost:5432/india_market_terminal

# Optional: Google Gemini (Free tier at aistudio.google.com)
# If omitted, a deterministic rule-based research engine is used.
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# Optional: Upstox (authenticated market data + holdings)
UPSTOX_ENABLED=false
UPSTOX_CLIENT_ID=
UPSTOX_CLIENT_SECRET=
UPSTOX_ACCESS_TOKEN=
UPSTOX_REDIRECT_URI=http://localhost:8000/market/upstox/callback

# Optional: Telegram alerts
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

`.env` is gitignored. Never commit credentials.

---

## 6. Upstox Setup (optional)

1. Create an app on the [Upstox Developer Portal](https://developer.upstox.com).
2. Set the redirect URI to `http://localhost:8000/market/upstox/callback`.
3. Add `UPSTOX_CLIENT_ID` and `UPSTOX_CLIENT_SECRET` to `.env`.
4. Set `UPSTOX_ENABLED=true` and provide `UPSTOX_ACCESS_TOKEN`.

The integration is **read-only**: it fetches quotes, historical candles, and holdings. It never executes orders, and credentials are never exposed to the browser or to the LLM.

---

## 7. Gemini Setup (optional)

1. Obtain an API key from [Google AI Studio](https://aistudio.google.com).
2. Set `GEMINI_API_KEY` in `.env`.

Gemini is used for document interpretation, news classification, research synthesis, and natural-language explanation — via schema-validated structured output and controlled tool calls. It **cannot** alter numerical outputs or invent probabilities.

---

## 8. Starting the Terminal

### One-command launcher (Windows PowerShell)

```powershell
.\scripts\start.ps1
```

Validates the environment, boots FastAPI (port 8000), starts the Next.js terminal (port 3000), and opens the browser.

### Manual

```bash
# Backend
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

# Frontend
cd apps/web && npm run start
```

### URLs

- Terminal UI: `http://localhost:3000`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

---

## 9. Running Tests

```bash
python -m pytest tests/ -v
```

The suite includes adversarial boundary tests, temporal anti-leakage tests, walk-forward validation, probability calibration, whole-share capital simulation, and a Playwright UI test. The Playwright test skips automatically if Playwright/Chromium is not installed:

```bash
pip install playwright && python -m playwright install chromium
```

---

## 10. Forecasting Modes

1. **FULL** — Chronos-2 + tabular ML + Gemini (requires model weights + API key).
2. **LOCAL QUANT** — Chronos-2 (or local statistical fallback) + deterministic research.
3. **LIGHTWEIGHT** — heavy-tailed empirical quantile forecaster + statistical baselines.
4. **RESEARCH-ONLY** — fundamentals + events + documents + technicals.

When a model cannot run, the terminal reports `MODEL STATUS: UNAVAILABLE` with a reason and fallback — it never substitutes a fake prediction.

### Honest calibration

The calibration engine is fitted **only** on real out-of-sample walk-forward holdouts. In a fresh deployment with no persisted holdout set, calibration is reported as `INSUFFICIENT` and raw probabilities are returned unchanged. A `GOOD`/`ACCEPTABLE` calibration rating is only ever produced from real data.

---

## 11. Data Sources

| Priority | Source | Purpose |
|----------|--------|---------|
| P0 | NSE, BSE, company IR | Primary filings, corporate actions, universe |
| P1 | SEBI, RBI, PIB | Regulatory and government disclosures |
| P2 | News/RSS | Discovery and context |
| P3 | Yahoo Finance (free) | Public price history fallback |
| Auth | Upstox V2 | Authenticated quotes, candles, holdings |

Every dataset carries `last_updated`, `source`, and freshness status (`LIVE` / `FRESH` / `STALE` / `UNAVAILABLE`). Primary sources take priority; secondary reporting is never treated as primary evidence.

---

## 12. Troubleshooting

- **Port in use** — the launcher reuses existing verified processes.
- **Database refused** — the terminal runs in in-memory degraded mode; search/research/portfolio endpoints return `DATABASE_UNAVAILABLE` rather than sample data.
- **No internet** — historical analysis, technicals, cached research, paper trading, and portfolio analytics still work; external data is marked stale/unavailable.
- **Missing keys** — Gemini/Upstox/Telegram report `NOT CONFIGURED` and fall back to deterministic/local behavior.

---

## 13. Security

- No secrets in the frontend bundle or logs.
- Upstox credentials are backend-only; the browser calls the backend, never Upstox directly.
- `LIVE_EXECUTION = false` — no autonomous order placement.
- Structured logging with correlation IDs; no secret values logged.

---

## 14. Limitations

- **Database-dependent features** (search, research, watchlist, portfolio, source health) require PostgreSQL + pgvector. Without it they degrade gracefully.
- **Gemini, Upstox, Telegram** require user-provided credentials; without them the terminal uses deterministic/local fallbacks.
- **Chronos-2 / TimesFM** require optional model weights; without them a local statistical fallback runs.
- **Calibration** is `INSUFFICIENT` until real out-of-sample holdouts are persisted.
- **Sector aggregates** and **macro indicators** are not ingested in a fresh deployment and report `UNAVAILABLE` rather than fabricated values.

This is an information and research terminal. It does not provide buy/sell advice, guaranteed returns, or autonomous trading.
