"""Bootstrap script to discover and load Indian listed equity universe."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.common.database import AsyncSessionLocal, engine, Base
from packages.common.logging import get_logger
from services.collector.universe_manager import universe_manager

logger = get_logger("bootstrap_universe")


async def main():
    logger.info("Initializing database schema if not present...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Bootstrapping dynamic NSE & BSE universe...")
    async with AsyncSessionLocal() as session:
        stats = await universe_manager.refresh_universe(session)
        print("\n==========================================")
        print("  INDIA MARKET TERMINAL UNIVERSE BOOTSTRAP")
        print("==========================================")
        print(f"  Companies Created:  {stats['created_companies']}")
        print(f"  Companies Updated:  {stats['updated_companies']}")
        print(f"  Securities Mapped:  {stats['created_securities']}")
        print("==========================================\n")


if __name__ == "__main__":
    asyncio.run(main())
