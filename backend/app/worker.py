"""Long-running content processing worker entry point."""

import asyncio
import logging
import signal

from app.config import get_settings
from app.database import async_session_maker
from app.services.processing import ContentProcessor
from app.services.processing_worker import ProcessingWorker
from app.services.storage import get_storage_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    worker = ProcessingWorker(
        async_session_maker,
        ContentProcessor(get_storage_service(), settings),
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for event in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(event, stop.set)
    logger.info("Memoryhive processing worker started")
    while not stop.is_set():
        if not await worker.run_once():
            try:
                await asyncio.wait_for(stop.wait(), settings.processing_poll_seconds)
            except TimeoutError:
                pass
    logger.info("Memoryhive processing worker stopped")


if __name__ == "__main__":
    asyncio.run(run())
