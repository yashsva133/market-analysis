# India Market AI Research Terminal

> **Version:** 1.0 (Production Release)  
> **Target:** Personal-use, zero-budget (₹0 recurring), local-first Indian equity research, probabilistic forecasting & event-monitoring terminal covering NSE + BSE.  
> **Status:** 61/61 Pytest Suites Passing (100%) | Next.js Production Build Passing | Headless Playwright UI Verified | Live API Smoke Tests Verified  

---

## 1. What It Is

The **India Market AI Research Terminal** is an institutional-grade, personal-use research workstation tailored for the Indian equity markets (NSE and BSE). Built with a Bloomberg/Fincept dark terminal aesthetic, it combines deterministic quantitative engines, probabilistic time-series forecasting (Chronos-2 foundation quantiles), SEBI LODR materiality triage, and controlled Google Gemini AI document research.

### Core Distinctions
- **₹0 Recurring Software Cost**: Runs 100% locally on standard PC hardware.
- **Zero Fake Probabilities (§73)**: Numerical probabilities and distributions derive strictly from calibrated models (Chronos-2, HistGradientBoosting, empirical baselines). LLMs **never** invent numbers.
- **Whole-Shares Cash Equity Rule (§74)**: Real executable positions strictly enforce integer whole-shares `floor((capital - costs) / price)` according to Indian exchange rules. Insufficient capital triggers explicit flags; theoretical fractional exposure is presented purely as non-executable context.
- **Statutory Indian Transaction Costs (§19)**: Implements actual SEBI, STT (0.1% buy/sell delivery), exchange turnover, GST (18%), and stamp duty rate schedules.
- **Point-in-Time Anti-Leakage (§11)**: Strict temporal boundaries reject future announcements, candles, financial statements, and corporate actions during backtesting and feature engineering.
- **Strict Non-Advisory Mandate (§75)**: Strictly factual research and probabilistic scenarios. Zero automated trade placement, zero "buy/sell" tips.

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
 Upstox V3           News & Disclosures  Feature Store
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

- **Operating System:** Windows 10/11 (PowerShell), Linux (Ubuntu 20.04+), or macOS
- **Python:** 3.10, 3.11, 3.12, 3.13, or 3.14 (Verified on Python 3.14.6)
- **Node.js:** v18.0+ or v20+ LTS (Verified on Node.js v22.23.1)
- **Hardware Memory:** 4 GB RAM minimum (8 GB+ recommended for large neural forecasts)
- **Acceleration:** Standard CPU inference active by default (Zero-GPU required; CUDA supported if available)
- **Database (Optional):** PostgreSQL 16+ with `pgvector` extension (Runs in-memory and local cache if PostgreSQL is offline)

---

## 4. Installation

```bash
# 1. Clone repository
git clone https://github.com/your-username/india-market-terminal.git
cd "india-market-terminal"

# 2. Set up Python environment & dependencies
python -m pip install -r requirements.txt

# 3. Set up Frontend dependencies & build
cd apps/web
npm install
npm run build
cd ../..

# 4. Initialize Configuration
cp .env.example .env
```

---

## 5. Environment Variables

Configure `.env` in the repository root:

```ini
# Core Environment
ENVIRONMENT=production
PORT=8000
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/market_terminal

# Optional: Google Gemini API (Free Tier available at aistudio.google.com)
# If omitted, local deterministic rule-based research engine is used automatically
GEMINI_API_KEY=

# Optional: Upstox API V3 (Authenticated market quotes, candles, and holdings)
# If omitted, free public exchange data and paper portfolio are used automatically
UPSTOX_CLIENT_ID=
UPSTOX_CLIENT_SECRET=
UPSTOX_ACCESS_TOKEN=

# Optional: Telegram Alerts
# If omitted, alerts display inside the local terminal UI
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## 6. Upstox & Gemini Setup

### Upstox API V3 Setup
1. Create an app on [Upstox Developer Portal](https://developer.upstox.com).
2. Set your redirect URI (e.g. `http://localhost:8000/api/upstox/callback`).
3. Add `UPSTOX_CLIENT_ID` and `UPSTOX_CLIENT_SECRET` to `.env`.
4. Generate an access token and place it in `UPSTOX_ACCESS_TOKEN`.
5. The terminal is strictly **read-only**: it fetches holdings and quotes without ever executing orders.

### Google Gemini API Setup
1. Obtain an API key from [Google AI Studio](https://aistudio.google.com).
2. Set `GEMINI_API_KEY` in `.env`.
3. Gemini is used **exclusively** for document reading, filing summaries, and qualitative explanation. Gemini **cannot** alter numerical outputs or invent probabilities.

---

## 7. Starting the Terminal

### One-Command Launcher (Windows PowerShell)
```powershell
.\scripts\start.ps1
```
This launcher automatically validates your environment, boots FastAPI (port 8000), starts the Next.js web terminal (port 3000), checks health metrics, and opens the terminal in your browser.

### Manual Startup
```bash
# Backend (Terminal 1)
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

# Frontend (Terminal 2)
cd apps/web && npm run start
```

### URLs
- **Terminal UI:** `http://localhost:3000`
- **Interactive REST Docs:** `http://127.0.0.1:8000/docs`
- **Health Metrics:** `http://127.0.0.1:8000/health`

---

## 8. Diagnostic & Smoke Test Tools

### System Doctor (§76)
Validate runtime, dependencies, hardware, model readiness, ports, and configuration:
```powershell
python scripts/doctor.py
```

### Real-Service Smoke Tests (§68)
Test live Upstox authentication, Gemini calls, database connectivity, and local networking:
```powershell
python scripts/smoke_test.py
```
*Audit Rule:* When keys are missing, reports `NOT CONFIGURED` with active fallback. Never reports false passes.

### Live Scenario & Research Verification (§88)
Validate the full quantitative chain (Data -> Features -> Models -> Probabilities -> Scenarios -> Capital -> Evidence -> UI):
```powershell
python scripts/verify_live_api.py
```

---

## 9. Running Tests

Execute all 61 automated tests:
```powershell
python -m pytest tests/ -v
```
Verified coverage includes:
- Adversarial tests (`test_adversarial.py`: negative capital, zero capital, huge capital, NaN/inf prices, corrupt series)
- Temporal anti-leakage (`test_leakage_detection.py`: future announcements, candles, financials, corporate actions)
- Walk-forward validation (`test_walk_forward.py`: expanding and rolling temporal slices)
- Probabilistic calibration (`test_probability_calibration.py`: ECE, Brier score, deciles)
- Whole-shares capital simulation (`test_scenario_engine.py`)
- Headless Playwright UI test (`test_ui_playwright.py`)

---

## 10. Forecasting Modes & Models

The terminal supports 4 distinct operational modes:
1. **FULL MODE:** Chronos-2 Foundation Model + HistGradientBoosting Tabular Classifier + Google Gemini Research Agent.
2. **LOCAL QUANT MODE:** Chronos-2 + deterministic research synthesis (Zero external API dependencies).
3. **LIGHTWEIGHT MODE:** Heavy-tailed empirical quantile forecaster + local statistical baselines (<50MB RAM).
4. **RESEARCH-ONLY MODE:** Point-in-time fundamentals + corporate filings + technical indicators.

### Quantile Output
For every forecast, the engine generates 8 quantiles: Q10, Q25, Q40, Q50 (Median), Q60, Q75, Q90, Q95, mapped into 5 scenario tiers:
- `SEVERE BEAR` (Q10–Q25)
- `BEAR` (Q25–Q40)
- `BASE` (Q40–Q60)
- `BULL` (Q75–Q90)
- `STRONG BULL` (Q90–Q95)

---

## 11. 18 Terminal Workspaces

1. **MARKET:** Broad market regime, advance/decline breadth, sector leaders.
2. **UNIVERSE:** ISIN-deduplicated security master across NSE and BSE.
3. **COMPANY:** Central dossier: price, market cap, fundamentals, technicals, filings.
4. **EVENTS:** Material corporate disclosures triaged under SEBI LODR Regulation 30.
5. **NEWS:** Real-time sentiment and headline extraction.
6. **SCREENER:** Deterministic SQL filtering by market cap, P/E, ROE, RSI, volume.
7. **RESEARCH:** Grounded Q&A with page-level document citations (FACT, INFERENCE, UNKNOWN).
8. **SCENARIO:** Flagship probabilistic capital analyst (₹500 / ₹5,000 / ₹50,000 capital simulation).
9. **WATCHLIST:** Local-persisted user watchlists.
10. **PORTFOLIO:** Upstox V3 holdings + paper trading simulator.
11. **TECHNICALS:** Pure deterministic indicators: SMA, EMA, RSI, MACD, Bollinger Bands, VWAP.
12. **CALENDAR:** Corporate actions: dividends, stock splits, bonuses, board meetings.
13. **COMPARE:** Side-by-side comparative matrix across 2–5 equities.
14. **MODEL LAB:** Quantile distributions, calibration curves, Brier scores, ECE.
15. **QUANT LAB:** Walk-forward backtesting and event-study engine.
16. **DATA EXPLORER:** Raw database record and table inspector.
17. **SOURCE HEALTH:** Latency metrics, failure counts, circuit breaker states.
18. **ALERTS:** Real-time deduplicated notifications to Telegram.

---

## 12. Troubleshooting & FAQ

- **Port 8000 or 3000 already in use:** The launcher script detects active ports and reuses existing verified processes without crashing.
- **Database Refused Connection:** If PostgreSQL is not running, the terminal automatically activates standalone in-memory mode (`OFFLINE_RESILIENT`) with zero disruption.
- **Windows Unicode / cp1252 Error:** All diagnostic and launcher scripts enforce ASCII-safe indicators (`[OK]`, `[WARN]`, `[INFO]`).
- **Low Memory / No GPU:** The terminal defaults to standard CPU inference using optimized numpy/scipy routines, ensuring smooth execution even on modest hardware.

---

## 13. Security & Regulatory Compliance

- **No Secrets in Frontend:** API keys and access tokens reside strictly in the backend `.env`. They are never passed to the browser or logged in traces.
- **Strict Non-Advisory Status:** In accordance with SEBI (Research Analysts) Regulations, the terminal provides mathematical, historical, and factual market research only. It never provides buy/sell/hold calls or guarantees returns.
- **Read-Only Portfolio:** Upstox integration is limited strictly to balance and holdings retrieval. Automated order execution is disabled by default (`LIVE_EXECUTION = false`).
