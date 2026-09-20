# India Market AI Research Terminal — Final Audit

**Audit date:** September 20, 2026
**Status:** Verified against the actual codebase (not against prior documentation).

This audit reflects the repository as inspected and executed, not the claims of earlier reports. Where earlier documentation overstated a capability, this document corrects it.

---

## 1. Verification Summary

| Check | Result |
|-------|--------|
| Python test suite | **66 passed, 1 skipped** (Playwright skips when Chromium is unavailable) |
| Next.js production build | **Passing** |
| FastAPI startup + `/health` | **Passing** |
| Scenario endpoint (real data) | **Working** — fetches real price history via Yahoo Finance; reports `DATA_UNAVAILABLE` when unreachable |
| Database | **Not configured** in this environment — degrades to `DATABASE_UNAVAILABLE` |
| Gemini | **Not configured** — deterministic rule engine active |
| Upstox | **Not configured** — free provider active |
| Telegram | **Not configured** |

---

## 2. Subsystem Classification

| Subsystem | Classification | Notes |
|-----------|----------------|-------|
| FastAPI core + 22 routers | REAL | Starts cleanly; health, scenario, search, research, models, macro endpoints verified |
| Next.js terminal (18 workspaces) | REAL | Production build passes; single-page dense terminal |
| PostgreSQL/pgvector schema (`db/init.sql`) | REAL | Schema present; not exercised in this environment (no DB) |
| Dynamic NSE+BSE universe | REAL | `services/collector/universe_manager.py`; ISIN dedup verified by tests |
| Document extraction (PyMuPDF, SHA-256, pages) | REAL | Verified by `test_pipeline_e2e.py` |
| Event taxonomy + materiality | REAL | SEBI LODR triage; verified by tests |
| Technical engine (SMA/EMA/RSI/MACD/ATR/BB/VWAP) | REAL | Deterministic; verified by `test_technical.py` |
| Forecasting (Chronos-2 adapter + local fallback) | REAL | Neural path optional; local heavy-tailed fallback always available |
| Probability engine (Brier/ECE/isotonic) | REAL | Fitted only on real holdouts; `INSUFFICIENT` until then |
| Scenario engine (5 tiers) | REAL | Derived from forecast distribution |
| Capital/cost engine (whole shares, statutory costs) | REAL | Verified by adversarial + scenario tests |
| Walk-forward validation | REAL | `simulation/walk_forward.py`; verified by tests |
| Anti-leakage | REAL | Future candle/announcement/financial/action rejected; verified by tests |
| Upstox V2 provider | REAL (unconfigured) | Read-only adapter; not smoke-tested (no credentials) |
| Gemini provider | REAL (unconfigured) | Structured output + tool calling; not smoke-tested (no key) |
| Telegram alerts | REAL (unconfigured) | Dedup + non-advisory; verified by tests |
| MCP server | REAL | Read-only research tools |
| System doctor / smoke test / launcher | REAL | `scripts/doctor.py`, `scripts/smoke_test.py`, `scripts/start.ps1` |

---

## 3. Issues Found and Fixed

The following fabricated-data paths were present and have been removed:

1. **Scenario orchestrator fabricated price history** (`base_px_map` + seeded synthetic series) when no prices were supplied. **Fixed:** the orchestrator now requires ≥5 real price observations and raises `DATA_UNAVAILABLE` otherwise.
2. **Calibration engine seeded with synthetic data** to produce an out-of-the-box "GOOD" rating. **Fixed:** the calibrator starts unfitted; empty evaluation returns `INSUFFICIENT` with `None` metrics.
3. **Ensemble fabricated a calibration evaluation** from 3 synthetic "actual outcomes". **Fixed:** reports `INSUFFICIENT` until real holdouts exist.
4. **Risk engine returned hardcoded risk metrics** for short return series. **Fixed:** returns `INSUFFICIENT_DATA` with `None` metrics.
5. **TimesFM returned a hardcoded `confidence_score: 0.88`.** **Fixed:** removed.
6. **Scenario router hardcoded portfolio prices / synthetic returns and hardcoded sector statistics.** **Fixed:** portfolio optimization now uses real price history; sector aggregates report `UNAVAILABLE`.
7. **Health router fabricated activity counters when the DB was offline.** **Fixed:** returns zero/unknown counters with `db_status: offline_resilient`.
8. **Gemini structured output set `responseMimeType` but no JSON schema.** **Fixed:** now passes a `responseSchema` derived from the Pydantic model.

---

## 4. Remaining Limitations (honest)

- **Database-dependent workspaces** (search, research, watchlist, portfolio, source health) require PostgreSQL + pgvector; they return `DATABASE_UNAVAILABLE` without it.
- **Calibration** is `INSUFFICIENT` until real out-of-sample holdouts are persisted (there is no persisted evaluation dataset in this deployment).
- **All models are `EXPERIMENTAL`** in the registry until they pass gating on real holdouts.
- **Gemini / Upstox / Telegram** are not configured here; real-service smoke tests report `NOT CONFIGURED`, not `PASSED`.
- **Chronos-2 / TimesFM neural paths** require optional weights; the local statistical fallback runs otherwise.
- **Playwright UI test** requires Chromium system libraries; it skips gracefully when unavailable.

---

## 5. Verdict

The terminal is a real, working, local-first research system with honest degradation. The fabricated-data paths that would have misled a user (fake prices, fake calibration, fake confidence, fake metrics) have been removed. External-service integrations are correctly gated behind configuration and report `NOT CONFIGURED` rather than false passes.
