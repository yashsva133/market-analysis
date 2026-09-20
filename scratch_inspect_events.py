import httpx

client = httpx.Client(timeout=5)
try:
    resp = client.get("http://127.0.0.1:8000/events")
    print("Status:", resp.status_code)
    data = resp.json()
    print("Events count:", len(data))
    for ev in data:
        print(" -", ev.get("symbol"), ev.get("importance"), ev.get("headline")[:60])
except Exception as e:
    print("Error:", e)
