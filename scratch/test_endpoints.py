import asyncio
import httpx
import json

async def test():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0) as client:
        endpoints = [
            "/market/breadth",
            "/news",
            "/portfolio/holdings",
            "/api/calendar/actions",
            "/api/compare?symbols=RELIANCE,LT,TCS,HDFCBANK",
            "/models",
            "/explorer/summary",
        ]
        for ep in endpoints:
            try:
                res = await client.get(ep)
                print(f"{ep}: status {res.status_code}")
                if res.status_code == 200:
                    data = res.json()
                    preview = json.dumps(data, indent=2)[:200]
                    print(f"  preview: {preview}...")
                else:
                    print(f"  err: {res.text[:150]}")
            except Exception as e:
                print(f"{ep}: exception {e}")

if __name__ == "__main__":
    asyncio.run(test())
