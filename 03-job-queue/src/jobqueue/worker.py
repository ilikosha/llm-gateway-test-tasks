"""Воркер: claim -> имитация генерации -> complete/fail. Общается только через HTTP API."""

import asyncio
import logging
import random

import httpx

from .config import Settings

log = logging.getLogger("worker")


async def generate(job: dict, settings: Settings) -> str:
    """Имитация генерации. params.fail=true принудительно роняет задачу (для демо)."""
    await asyncio.sleep(random.uniform(settings.work_min_seconds, settings.work_max_seconds))
    if job["params"].get("fail") or random.random() < settings.work_fail_rate:
        raise RuntimeError("generation failed")
    return f"Generated text for prompt: {job['prompt']!r}"


async def process_one(client: httpx.AsyncClient, settings: Settings) -> bool:
    """Обрабатывает одну задачу. Возвращает False, если очередь пуста."""
    resp = await client.post("/jobs/claim")
    if resp.status_code == httpx.codes.NO_CONTENT:
        return False
    resp.raise_for_status()
    job = resp.json()
    me = job["worker_id"]  # id выдаёт сервер по токену
    log.info("%s claimed job %s (attempt %d)", me, job["id"], job["attempts"])

    try:
        result = await generate(job, settings)
    except Exception as exc:
        done = await client.post(
            f"/jobs/{job['id']}/fail", json={"error": str(exc)}
        )
        outcome = "failed"
    else:
        done = await client.post(
            f"/jobs/{job['id']}/complete", json={"result": result},
        )
        outcome = "completed"

    if done.status_code == httpx.codes.CONFLICT:
        # Задачу успел забрать reaper — наш результат уже не нужен.
        log.warning("%s lost job %s: %s", me, job["id"], done.json()["detail"])
    else:
        done.raise_for_status()
        log.info("%s %s job %s", me, outcome, job["id"])
    return True


async def run(settings: Settings) -> None:
    headers = {"Authorization": f"Bearer {settings.worker_token}"}
    async with httpx.AsyncClient(
        base_url=settings.api_url, timeout=30, headers=headers
    ) as client:
        while True:
            try:
                busy = await process_one(client, settings)
            except httpx.HTTPError as exc:  # API недоступен — просто повторяем
                log.error("API error: %r", exc)
                busy = False
            if not busy:
                await asyncio.sleep(settings.poll_interval_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run(Settings()))


if __name__ == "__main__":
    main()
