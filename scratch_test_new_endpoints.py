import httpx

client = httpx.Client(timeout=5)

# 1. Health
print("Health:", client.get("http://127.0.0.1:8000/health").status_code)

# 2. Indices
idx_res = client.get("http://127.0.0.1:8000/market/indices")
print("Indices status:", idx_res.status_code)
if idx_res.status_code == 200:
    for item in idx_res.json():
        print(" ->", item["name"], item["val"], item["chg"])

# 3. Catalysts
cat_res = client.get("http://127.0.0.1:8000/market/catalysts")
print("Catalysts status:", cat_res.status_code, "Count:", len(cat_res.json()))

# 4. Events
ev_res = client.get("http://127.0.0.1:8000/events?limit=5")
print("Events status:", ev_res.status_code)
if ev_res.status_code == 200:
    for e in ev_res.json():
        print(" ->", e.get("symbol"), "|", e.get("company_name"), "|", e.get("amount_formatted"))

# 5. Alerts status
alt_res = client.get("http://127.0.0.1:8000/alerts/status")
print("Alerts status:", alt_res.status_code, alt_res.json())
