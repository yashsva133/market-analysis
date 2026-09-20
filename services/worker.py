"""Background Ingestion and Processing Worker."""
import asyncio
import signal
from packages.common.logging import get_logger
from packages.common.database import AsyncSessionLocal
from services.collector.universe_manager import universe_manager
from services.collector.poller import collector_poller
from services.processor.pipeline import event_processor_pipeline
from services.notifier.telegram_bot import telegram_notifier

logger = get_logger(__name__)


class BackgroundWorker:
    """Orchestrates periodic collection, processing, and alerting in the background."""

    def __init__(self):
        self.is_running = True

    def stop(self):
        logger.info("Stopping background worker...")
        self.is_running = False

    async def run(self):
        logger.info("Initializing India Market Research Terminal Background Worker...")

        # 1. Initial universe check
        async with AsyncSessionLocal() as session:
            try:
                await universe_manager.refresh_universe(session)
            except Exception as e:
                logger.error(f"Initial universe bootstrap error: {e}")

        # 2. Main execution loop
        while self.is_running:
            try:
                async with AsyncSessionLocal() as session:
                    # Poll sources
                    await collector_poller.poll_all(session)
                    # Process events
                    await event_processor_pipeline.process_batch(session)
                    # Deliver alerts
                    await telegram_notifier.send_pending_alerts(session)
            except Exception as e:
                logger.error(f"Worker iteration exception: {e}")

            # Polling cadence: sleep 90s
            for _ in range(90):
                if not self.is_running:
                    break
                await asyncio.sleep(1)


async def main():
    worker = BackgroundWorker()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            pass  # Windows event loop limitation

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
