import httpx

client = httpx.Client(timeout=15)
resp = client.post("http://127.0.0.1:8000/alerts/scan-and-dispatch?sensitivity=ALL")
print("scan-and-dispatch status:", resp.status_code, resp.json())
