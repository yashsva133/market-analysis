# System Runbook & Operator Guide

**System:** India Market AI Research Terminal  
**Environment:** Local-First / Production-Hardened  
**OS Support:** Windows (PowerShell), Linux, macOS  

---

## 1. Quick Start & Launch

### One-Command Startup (Windows PowerShell)
```powershell
.\scripts\start.ps1
```
This launcher automatically:
1. Executes `python scripts/doctor.py` to validate system health.
2. Checks configuration and initializes `.env` from `.env.example` if needed.
3. Checks and boots the FastAPI backend on `http://127.0.0.1:8000`.
4. Checks and boots the Next.js production web terminal on `http://localhost:3000`.
5. Verifies service health metrics and opens the terminal in your default browser.

### Linux / macOS Manual Startup
```bash
# Terminal 1: Backend
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Web Terminal
cd apps/web && npm run start
```

---

## 2. System Verification & Diagnostics

### A. System Doctor Diagnostic (§76)
Inspects Python runtime, Node.js, available RAM, disk space, compute mode (CPU/CUDA), quant engines, listening ports, and secret token availability:
```powershell
python scripts/doctor.py
```
Output: `SYSTEM READY` | `SYSTEM READY WITH WARNINGS` | `SYSTEM NOT READY`

### B. Real-Service Smoke Tests (§68)
Tests live integrations against Upstox V3, Google Gemini, PostgreSQL, and local web services.
```powershell
python scripts/smoke_test.py
```
*Strict Audit Rule:* Reports `NOT CONFIGURED` when keys are not supplied. Never reports false passes.

### C. Live End-to-End Scenario & Research Chain (§88)
Validates the complete quantitative chain (Data -> Features -> Models -> Probabilities -> Scenarios -> Capital -> Evidence -> UI):
```powershell
python scripts/verify_live_api.py
```

### D. Automated Test Suite (61 Tests)
```powershell
python -m pytest tests/ -v
```

---

## 3. Environment & Credential Configuration

Create or update `.env` in the repository root:
```ini
# Environment
ENVIRONMENT=production
PORT=8000
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/market_terminal

# Optional: Google Gemini API (Free tier supported)
# If omitted, local deterministic rule-based research engine is used
GEMINI_API_KEY=

# Optional: Upstox API V3 (Authenticated market & portfolio data)
# If omitted, free public exchange data and paper portfolio are used
UPSTOX_CLIENT_ID=
UPSTOX_CLIENT_SECRET=
UPSTOX_ACCESS_TOKEN=

# Optional: Telegram Alerts
# If omitted, notifications remain within the local terminal UI
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## 4. Forecasting & Quantitative Engines

### Chronos-2 Foundation Forecaster
- **Mode:** Hardware-aware. If PyTorch and Hugging Face weights are present, runs neural time-series quantiles; otherwise, runs local heavy-tailed empirical quantile engine without network stalls.
- **Quantiles Computed:** Q10, Q25, Q40, Q50, Q60, Q75, Q90, Q95.
- **Model Gating:** Automatically flags models as `POOR` or `GATED` when Brier score or Expected Calibration Error (ECE) exceed acceptable thresholds.

### Whole-Shares Capital Execution Simulator (§18, §23)
- Indian cash equities do not permit fractional execution.
- Executable shares = `floor((capital - estimated_costs) / current_price)`.
- If `shares == 0`: Explicitly renders `INSUFFICIENT CAPITAL FOR ONE WHOLE SHARE`.
- Fractional exposure is displayed purely as non-executable mathematical context.

### Statutory Indian Transaction Costs (§19)
- **STT (Securities Transaction Tax):** 0.1% on delivery buy and delivery sell.
- **Brokerage:** ₹0 (discount delivery) or max ₹20 / 0.05%.
- **Exchange Turnover:** 0.00297% (NSE) / 0.00375% (BSE).
- **SEBI Turnover Fee:** ₹10 per Crore (0.0001%).
- **Stamp Duty:** 0.015% (Buy only).
- **GST:** 18% on brokerage, exchange turnover, and SEBI fees.

---

## 5. Offline & Degraded Operation (§72)

The terminal is designed to operate completely offline:
- **No Internet:** Local historical candles, technical indicators, financial statements, and paper trading continue to operate seamlessly.
- **Database Offline:** In-memory models and local cache provide full scenario simulation and technical calculations without crashing.
- **No External Keys:** Rule-based qualitative explanations contextualize model outputs without requiring cloud API keys.

---

## 6. Port Reference

| Service | Port | Endpoint | Description |
|---------|------|----------|-------------|
| Next.js Web Terminal | 3000 | `http://localhost:3000` | Bloomberg-style dark UI |
| FastAPI Backend | 8000 | `http://127.0.0.1:8000` | REST API |
| API Interactive Docs | 8000 | `http://127.0.0.1:8000/docs` | OpenAPI / Swagger Docs |
| Health & Telemetry | 8000 | `http://127.0.0.1:8000/health` | Health check & counters |
