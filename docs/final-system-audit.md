# India Market AI Research Terminal — Complete Final System Audit

**Audit Date:** 2026-09-20  
**Status:** FULL SYSTEM REPOSITORY AUDIT & GAP ANALYSIS  
**Standard:** Verified against the complete Final Implementation Specification (Sections 1–155).  
**Classification Criteria:**
- **REAL:** Fully implemented with active executable code, persistence, and verified by passing test suites or live runs.
- **PARTIAL:** Core code exists but requires missing edge case handling, dedicated endpoints, or deeper feature integration.
- **MOCK:** Uses static fixtures or simulations in place of live calculations.
- **MISSING:** Feature requested in the specification that is not yet implemented.
- **BROKEN:** Code exists but crashes, fails tests, or contains errors.
- **UNVERIFIED:** Code exists but lacks unit/integration tests or runtime proof.

---

## 1. System Inventory & Classification Matrix

| Subsystem / Requirement Area | Prompt § | Classification | Current State & Findings | Target Action |
| :--- | :--- | :--- | :--- | :--- |
| **0. Stack & Architecture** | §0, §4 | **REAL** | FastAPI backend, Next.js 14 frontend, PostgreSQL 16 + pgvector, Provider abstraction. | Maintain architecture. |
| **1. Dynamic Universe Discovery** | §1, §4 | **REAL** | `services/collector/universe_manager.py` — ISIN deduplication, NSE+BSE mapping. | Verified passing in `tests/test_universe.py`. |
| **2. Source Collection Engine** | §3, §97-99 | **REAL** | NSE, BSE, SEBI, PIB, RSS clients with circuit breaker, rate limiting, and health checks. | Retain and maintain resilience. |
| **3. Document Intelligence & Diff** | §6, §7, §35 | **REAL** | `packages/documents/extractor.py` and `diff.py` — PyMuPDF, checksumming, page citations. | Retain and maintain. |
| **4. Event Taxonomy & Materiality** | §8, §10, §36 | **REAL** | 45+ event categories, quantitative LTM scaling (>25% CRITICAL). | Retain. |
| **5. Technical Analysis Engine** | §13, §45 | **REAL** | Deterministic SMA, EMA, RSI (Wilder), MACD, ATR, ADX, Bollinger Bands, VWAP. | Keep deterministic. |
| **6. Market Data & Upstox V3** | §41-44 | **REAL** | `packages/market_data/` — Upstox v2/v3 support, free Bhavcopy fallback, read-only portfolio. | Verified live with user credentials. |
| **7. Feature Engineering Suite** | §16 | **MISSING** | `packages/scenario_engine/features/` not created as dedicated modular package. | Implement 10 feature modules. |
| **8. Primary Forecast Model (Chronos-2)** | §5, §132 | **PARTIAL** | Holt-Winters smoothing exists in `packages/market_data/forecasting.py`. Chronos-2 foundation adapter with CPU/GPU auto & fallback needed. | Build `ChronosForecastModel` with fallback. |
| **9. Tabular Probabilistic ML Stack** | §5, §6 | **MISSING** | HistGradientBoosting / LightGBM tabular probability estimator for target hits & downside. | Implement `TabularProbabilityModel`. |
| **10. Forecast Ensemble Engine** | §6, §20 | **MISSING** | ForecastEnsemble combining Chronos, tabular ML, and baselines with validation scoring. | Implement `ForecastEnsemble`. |
| **11. Deterministic Baselines** | §5 | **MISSING** | Random walk, zero-return, historical return distribution, volatility-adjusted baseline. | Implement `BaselineForecastModels`. |
| **12. Probability Engine & No Fake Probabilities** | §7, §9 | **MISSING** | P(target touched), P(target finished above), P(drawdown threshold), P(return > threshold). | Implement `ProbabilityEngine`. |
| **13. Probability Calibration Engine** | §12, §13 | **MISSING** | Isotonic regression, Platt scaling, Brier score, log loss, reliability error, GOOD/ACCEPTABLE/POOR. | Implement `ProbabilityCalibrationEngine`. |
| **14. Scenario Engine (5 Scenarios)** | §10, §22 | **MISSING** | SEVERE BEAR, BEAR, BASE, BULL, STRONG BULL with quantiles, assumptions, failure conditions. | Implement `ScenarioEngine`. |
| **15. Monte Carlo Path Simulation** | §11 | **MISSING** | Path simulation for target-touch, drawdown, terminal value, reproducible random seed. | Implement `MonteCarloSimulator`. |
| **16. Capital Scenario Engine (Indian Whole Shares)** | §23-25 | **MISSING** | Whole share `floor((capital - costs)/price)`, insufficient capital alert, theoretical fractional. | Implement `CapitalScenarioEngine`. |
| **17. Capital Allocation Engine** | §26, §70 | **MISSING** | Deterministic portfolio optimization (equal weight, min variance, risk parity, mean-risk, CVaR). | Implement `CapitalAllocationEngine`. |
| **18. Risk Engine & Stress Testing** | §28 | **MISSING** | VaR, CVaR, max drawdown, expected shortfall, beta, market shock (-5%, -10%, -20%). | Implement `RiskEngine`. |
| **19. Model Registry & Model Gating** | §18, §19 | **MISSING** | Model registry, versioning, status (ACTIVE, VALIDATING, EXPERIMENTAL, RETIRED), gating gates. | Implement `ModelRegistry` & `ModelGating`. |
| **20. Data Quality & Research Quality** | §124, §125 | **PARTIAL** | Basic badges exist; comprehensive `DataQualityEngine` & `ResearchQualityEngine` needed. | Implement full quality engines. |
| **21. Comparable Event Engine** | §37, §38 | **PARTIAL** | `reaction.py` computes price moves; need structured `ComparableEventEngine`. | Implement `ComparableEventEngine`. |
| **22. Gemini Reasoning & Synthesis Layer** | §30-33 | **REAL** | `GeminiProvider` exists; enforce strict structured JSON schema without numerical fabrication. | Enforce JSON contract. |
| **23. Telegram Bot Workflows** | §50, §93 | **REAL** | Token validated, Chat ID saved, direct alerts working. Add `/scenario` command handler. | Enhance with scenario command. |
| **24. API Endpoints for Scenario & Quant** | §83 | **PARTIAL** | Existing endpoints work; need `/scenario/analyze`, `/models`, `/capital/simulate`, `/quant/events`, etc. | Add dedicated routers. |
| **25. Database Schema Extensions** | §84, §85 | **PARTIAL** | 23 core tables exist; need `forecast_runs`, `scenario_runs`, `probability_predictions`, `model_registry`, etc. | Add SQLAlchemy models & SQL. |
| **26. Terminal UI Workspaces** | §72-77 | **PARTIAL** | 9 tabs exist; expand to all 18 workspaces with full AI Capital Analyst and fan charts. | Update frontend UI. |
| **27. Comprehensive Test Suite** | §128-136 | **PARTIAL** | 32/33 tests passing; add scenario, forecast, calibration, leakage, whole shares, and mock tests. | Expand tests to 45+ suites. |

---

## 2. Key Codebase Inspection Findings

1. **Python 3.14 Environment & Dependency Reality:**
   - `numpy`, `scipy`, `sklearn` (Scikit-Learn) are available and fully functional.
   - `scikit-learn` provides `HistGradientBoostingClassifier`, `HistGradientBoostingRegressor`, `IsotonicRegression`, and `LogisticRegression`.
   - `torch` is available; `transformers` and `chronos` are not installed natively on this Python 3.14 Windows machine.
   - **Specification adherence (§5, §67):** The architecture explicitly requires:
     * Chronos foundation model adapter with automatic fallback to CPU / lightweight local autoregressive distribution when memory/packages dictate.
     * Tabular fallback: `scikit-learn HistGradientBoosting`.
     * This ensures zero failure on startup and rock-solid execution on any local machine.

2. **No Fake Probabilities Rule (§7):**
   - No LLM may hallucinate probabilities. Every probability (touch, finish above, drawdown, loss) must be computed directly by the statistical probability engine and calibrated out-of-sample.

3. **Indian Cash Equity Whole Shares Rule (§23):**
   - Fractional shares are not executable on NSE/BSE. The system must compute whole shares `floor((capital - costs) / price)`. If 0, flag `INSUFFICIENT CAPITAL FOR ONE SHARE` and show non-executable theoretical fractional exposure.

4. **Point-In-Time Integrity & Leakage Prevention (§14, §15, §131):**
   - Time-series validation must be chronological walk-forward. Future corporate actions or financial statements must never leak backward before their announcement date.

---

## 3. Implementation Roadmap
1. **Create `packages/scenario_engine/features/`**: Implement all 10 feature extractors.
2. **Create `packages/scenario_engine/`**:
   - `models/`: Chronos-2 adapter + fallback, tabular ML, baselines, ensemble.
   - `probability/`: Engine & calibration (Isotonic/Platt, Brier, log-loss, reliability curve).
   - `simulation/`: Monte Carlo path simulation.
   - `scenarios/`: 5-scenario engine (Severe Bear to Strong Bull).
   - `capital/`: Whole-share Indian equity simulator, allocation, transaction costs.
   - `risk/`: VaR, CVaR, drawdown, stress testing.
   - `registry/`: Model registry, versioning, gating.
   - `comparable/`: Comparable event engine.
   - `quality/`: Data quality and research quality engines.
3. **Database & API Integration**: Add models to `packages/common/models.py`, create routers in `apps/api/routers/scenario.py` and `apps/api/routers/models.py`, wire to `apps/api/main.py`.
4. **Frontend UI Workspaces**: Complete all 18 workspaces in `apps/web/src/app/page.tsx` including AI Capital Analyst.
5. **Testing & Verification**: Add test suites in `tests/`, run pytest, test UI with Playwright, and ship.
