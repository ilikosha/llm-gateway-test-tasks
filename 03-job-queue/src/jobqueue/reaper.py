import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from . import repository

log = logging.getLogger("jobqueue.reaper")


async def reaper_loop(
    engine: AsyncEngine, timeout_seconds: float, interval_seconds: float, max_attempts: int
) -> None:
    """Периодически возвращает зависшие running-задачи в очередь."""
    while True:
        try:
            count = await repository.reap_stuck(engine, timeout_seconds, max_attempts)
            if count:
                log.warning("reaper: %d stuck job(s) requeued/failed", count)
        except asyncio.CancelledError:
            raise
        except Exception:  # шаг не должен убивать цикл (например, моргнула БД)
            log.exception("reaper iteration failed")
        await asyncio.sleep(interval_seconds)
