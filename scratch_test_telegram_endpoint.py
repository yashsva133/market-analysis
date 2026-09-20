import httpx

client = httpx.Client(timeout=10)
resp = client.post("http://127.0.0.1:8000/alerts/test-telegram")
print("test-telegram status:", resp.status_code, resp.json())
