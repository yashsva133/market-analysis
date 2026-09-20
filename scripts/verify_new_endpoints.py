"""Verify all newly added endpoints in the FastAPI backend."""
import httpx
import sys

BASE_URL = "http://127.0.0.1:8000"

endpoints = [
    ("/api/macro/indicators", "GET", None),
    ("/api/calendar/actions", "GET", None),
    ("/api/calendar/summary", "GET", None),
    ("/api/compare?symbols=LT,RELIANCE", "GET", None),
    ("/api/search?q=Larsen", "GET", None),
    ("/api/simulator/account", "GET", None),
    ("/api/simulator/positions", "GET", None),
    ("/api/documents/list", "GET", None),
    ("/api/lab/backtest", "POST", {"strategy_type": "EVENT_STUDY_ORDER_WIN", "holding_period_days": 5}),
    ("/api/lab/forecast?symbol=LT&horizon=5", "GET", None),
    ("/companies", "GET", None),
    ("/events", "GET", None),
]

failed = 0
for path, method, payload in endpoints:
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            resp = httpx.get(url, timeout=5.0)
        else:
            resp = httpx.post(url, json=payload, timeout=5.0)
        
        if resp.status_code == 200:
            print(f"[PASS] {method} {path} -> 200 OK")
        else:
            print(f"[FAIL] {method} {path} -> {resp.status_code}: {resp.text[:100]}")
            failed += 1
    except Exception as e:
        print(f"[ERROR] {method} {path} -> {e}")
        failed += 1

if failed > 0:
    print(f"\n{failed} endpoints failed.")
    sys.exit(1)
else:
    print("\nALL NEW ENDPOINTS VERIFIED 100% OPERATIONAL!")
