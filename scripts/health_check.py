"""System diagnostic and endpoint health check script."""
import asyncio
import sys
from pathlib import Path
import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.common.config import settings


async def main():
    print("\n--- System Health Check Diagnostic ---")
    base_url = f"http://localhost:{settings.API_PORT}"

    async with httpx.AsyncClient(timeout=5) as client:
        # Check API health
        try:
            resp = await client.get(f"{base_url}/health")
            if resp.status_code == 200:
                print(f"✅ FastAPI Server: OK ({resp.json()})")
            else:
                print(f"❌ FastAPI Server Error: Status {resp.status_code}")
        except Exception as e:
            print(f"⚠️ FastAPI Server unreachable at {base_url}: {e}")

        # Check Sources Health
        try:
            resp = await client.get(f"{base_url}/sources/health")
            if resp.status_code == 200:
                sources = resp.json()
                print(f"✅ Sources Registry: {len(sources)} active sources monitored.")
                for s in sources:
                    status_icon = "🟢" if s.get("rate_limit_status") == "OK" else "🟡"
                    print(f"   {status_icon} [{s.get('source_id')}]: Success Rate {s.get('success_rate_24h')}% | Latency {s.get('latency_ms')}ms")
            else:
                print(f"❌ Sources Endpoint Error: Status {resp.status_code}")
        except Exception as e:
            print(f"⚠️ Sources health endpoint unreachable: {e}")

    print("--------------------------------------\n")


if __name__ == "__main__":
    asyncio.run(main())
