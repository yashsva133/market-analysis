# India Market AI Research Terminal — Final Shipping Report

**Build version:** 1.0
**Verification date:** September 20, 2026
**Status:** Verified against the actual running system.

---

## 1. System Status

| Component | Status |
|-----------|--------|
| Environment | Python 3.13 + Node 22/24, verified |
| Database | **Not configured** — degrades to `DATABASE_UNAVAILABLE` |
| Backend (FastAPI, port 8000) | **Passing** — `/health` returns `healthy` |
| Frontend (Next.js, port 3000) | **Passing** — production build + HTTP 200 |

## 2. Data Sources

| Source | Status |
|--------|--------|
| NSE / BSE | Healthy (public collectors; universe + filings) |
| Yahoo Finance (free) | Healthy — used for price history fallback |
| Upstox V2 | **Not configured** — free provider active |
| PIB / SEBI / RBI | Collectors present; not exercised in this environment |

## 3. AI

| Component | Status |
|-----------|--------|
| Gemini | **Not configured** — deterministic rule engine active |
| Structured output | Implemented (`responseSchema` from Pydantic model) |
| Forecast models | Chronos-2 adapter (optional weights) + local statistical fallback |

## 4. Quant

| Component | Status |
|-----------|--------|
| Forecasting | Working (local heavy-tailed fallback) |
| Calibration | **INSUFFICIENT** (no persisted out-of-sample holdouts) |
| Backtesting / walk-forward | Working (validated by tests) |
| Scenario engine (5 tiers) | Working |
| Stress testing | Working (5 historical shock scenarios) |

## 5. Portfolio

| Component | Status |
|-----------|--------|
| Upstox holdings | **Not configured** |
| Paper trading | Working (in-memory simulator; verified by tests) |
| Transaction costs | Working (statutory schedule, configurable) |

## 6. Test Results

| Suite | Result |
|-------|--------|
| Pytest | **66 passed, 1 skipped** |
| Playwright UI | Skipped in this environment (Chromium system libraries unavailable); test is present and skips gracefully |
| Next.js build | **Passing** |

## 7. Real-Service Smoke Tests

| Service | Result |
|---------|--------|
| Upstox | NOT CONFIGURED |
| Gemini | NOT CONFIGURED |
| PostgreSQL | NOT CONFIGURED / OFFLINE |
| FastAPI + Next.js | PASSED |

No service is reported as passed unless it was actually exercised.

## 8. Live Scenario Verification

Executed against the running API:

- `POST /api/scenario/analyze` with `RELIANCE`, ₹500, 3M horizon.
- **Current price** fetched from real Yahoo Finance data (not fabricated).
- **Calibration** reported `INSUFFICIENT` with `brier_score: None` (honest).
- **5 scenarios** generated; **whole-share** rule correctly flags `INSUFFICIENT CAPITAL FOR ONE SHARE` at ₹500.
- **5 stress scenarios** and **evidence panel** present.

## 9. Known Limitations

- Database-dependent workspaces require PostgreSQL + pgvector.
- Calibration and model gating require persisted out-of-sample holdouts.
- Gemini/Upstox/Telegram require user credentials.
- Chronos-2/TimesFM neural paths require optional weights.

## 10. Configuration Status

- `.env.example` present and complete.
- `.env` not committed (gitignored).
- No secrets found in the repository.

## 11. Startup

```powershell
.\scripts\start.ps1
```

or manually:

```bash
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
cd apps/web && npm run start
```
