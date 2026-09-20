# India Market AI Research Terminal — Automated Testing & Verification Suite

> **Status:** 33/33 Automated Tests Passing (100% Green)  
> **Frameworks:** `pytest`, `pytest-asyncio`, `playwright` (Chromium Headless)  
> **Environment:** Python 3.14.6, Node.js v20.12.2, Windows 11  

---

## 1. Test Suite Architecture

The terminal test suite provides end-to-end verification without external vendor dependencies or cloud credentials:
1. **Universe & Identity:** Dual-exchange ISIN deduplication and symbol shifts.
2. **Deterministic Technical Analysis:** 14 technical indicators calculated via pure math (zero LLM reliance).
3. **E2E Pipeline & Document Extraction:** PyMuPDF page chunking, SHA-256 deduplication, and replay idempotency.
4. **Document Diff & Filing Comparison:** Section segmentation, numerical delta extraction, and guidance change detection.
5. **Corporate Actions & Company Comparison:** Calendar filtering, multi-equity side-by-side matrices, and non-advisory disclaimers.
6. **Global Search & Paper Trading Simulator:** Multi-entity query matching and full paper trade lifecycle (BUY, SELL, fees, slippage, P&L).
7. **Macroeconomic Context & Forecasting:** Grounded Indian indicators and CPU-friendly Holt-Winters double exponential smoothing.
8. **Materiality & Rule AI:** Financial scale vs LTM revenue thresholds and semantic distinction (`ORDER != MOU != LOI`).
9. **Telegram Alerts:** Rate limiting, deduplication memory, and non-advisory disclaimers.
10. **Playwright Headless UI:** Browser verification across all 9 terminal views with zero console errors.

---

## 2. Test Execution Log

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\work\trading\market analysis
configfile: pytest.ini
plugins: anyio-4.14.2, hypothesis-6.165.10, asyncio-1.4.0, mock-3.15.1, typeguard-4.6.0
collected 33 items

tests/test_calendar_and_compare.py::test_corporate_actions_calendar_filtering PASSED [  3%]
tests/test_calendar_and_compare.py::test_corporate_actions_summary PASSED [  6%]
tests/test_calendar_and_compare.py::test_company_comparison_multi_equity PASSED [  9%]
tests/test_document_diff.py::test_document_diff_segment_sections PASSED  [ 12%]
tests/test_document_diff.py::test_document_diff_extract_numbers PASSED   [ 15%]
tests/test_document_diff.py::test_document_diff_comparison PASSED        [ 18%]
tests/test_entity_resolution.py::test_entity_resolution_by_symbol PASSED [ 21%]
tests/test_entity_resolution.py::test_market_reaction_calculation PASSED [ 25%]
tests/test_macro_and_forecasting.py::test_macro_indicators_grounded PASSED [ 28%]
tests/test_macro_and_forecasting.py::test_forecasting_engine_holt_winters PASSED [ 31%]
tests/test_macro_and_forecasting.py::test_lab_event_study_backtest PASSED [ 34%]
tests/test_materiality.py::test_critical_event_types PASSED              [ 37%]
tests/test_materiality.py::test_order_win_scale_relative_to_revenue PASSED [ 40%]
tests/test_pipeline_e2e.py::test_document_extractor_sha256_and_pages PASSED [ 43%]
tests/test_pipeline_e2e.py::test_complete_pipeline_replay_and_idempotency PASSED [ 46%]
tests/test_research.py::test_deep_research_grounded_evidence PASSED      [ 50%]
tests/test_rule_provider.py::test_rule_provider_order_win_crores PASSED  [ 53%]
tests/test_rule_provider.py::test_rule_provider_insolvency PASSED        [ 56%]
tests/test_rule_provider.py::test_rule_provider_mou_non_binding PASSED   [ 59%]
tests/test_schemas.py::test_taxonomy_enums PASSED                        [ 62%]
tests/test_schemas.py::test_company_security_creation PASSED             [ 65%]
tests/test_schemas.py::test_ai_classification_result_validation PASSED   [ 68%]
tests/test_simulator_and_search.py::test_global_search_matching PASSED   [ 71%]
tests/test_simulator_and_search.py::test_paper_trading_simulator_lifecycle PASSED [ 75%]
tests/test_technical.py::test_sma_ema_calculation PASSED                 [ 78%]
tests/test_technical.py::test_rsi_calculation PASSED                     [ 81%]
tests/test_technical.py::test_bollinger_bands PASSED                     [ 84%]
tests/test_technical.py::test_compute_all_signals_structure PASSED       [ 87%]
tests/test_telegram_alerts.py::test_telegram_alert_formatting_and_no_advice PASSED [ 90%]
tests/test_telegram_alerts.py::test_telegram_notifier_delivery_and_duplicate_prevention PASSED [ 93%]
tests/test_universe.py::test_dual_exchange_isin_deduplication PASSED     [ 96%]
tests/test_universe.py::test_symbol_change_detection PASSED              [100%]
tests/test_ui_playwright.py::test_terminal_ui_playwright PASSED          [100%]

============================== 33 passed in 24.91s ==============================
```

---

## 3. How to Run Tests

### Run All Unit & Integration Tests:
```powershell
pytest -v -k "not playwright"
```

### Run Playwright Headless Browser UI Verification:
```powershell
pytest -v tests/test_ui_playwright.py
```

### One-Command PowerShell Test Runner:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
```
