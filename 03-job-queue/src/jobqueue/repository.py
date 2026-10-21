"""Все SQL-операции над очередью. Каждый переход состояния — один атомарный запрос."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

_COLUMNS = (
    "id, prompt, params, status, result, error, attempts, worker_id, "
    "created_at, started_at, finished_at"
)


class JobNotFound(Exception):
    pass


class InvalidTransition(Exception):
    def __init__(self, status: str):
        super().__init__(f"job is in status {status!r}")
        self.status = status


async def create(engine: AsyncEngine, prompt: str, params: dict[str, Any]) -> dict:
    async with engine.begin() as conn:
        row = await conn.execute(
            text(f"INSERT INTO jobs (prompt, params) "
                 f"VALUES (:prompt, CAST(:params AS jsonb)) RETURNING {_COLUMNS}"),
            {"prompt": prompt, "params": json.dumps(params)},
        )
        return dict(row.mappings().one())


async def get(engine: AsyncEngine, job_id: UUID) -> dict:
    async with engine.connect() as conn:
        row = await conn.execute(
            text(f"SELECT {_COLUMNS} FROM jobs WHERE id = :id"), {"id": job_id}
        )
        found = row.mappings().first()
    if found is None:
        raise JobNotFound
    return dict(found)


async def claim(engine: AsyncEngine, worker_id: str) -> dict | None:
    """Атомарно забирает одну queued-задачу. Параллельные claim'ы не блокируют
    друг друга: залоченные строки SKIP LOCKED пропускаются."""
    async with engine.begin() as conn:
        row = await conn.execute(
            text(
                f"""
                UPDATE jobs
                   SET status = 'running', worker_id = :worker_id,
                       started_at = now(), attempts = attempts + 1
                 WHERE id = (SELECT id FROM jobs
                              WHERE status = 'queued'
                              ORDER BY created_at, id
                              LIMIT 1
                              FOR UPDATE SKIP LOCKED)
                RETURNING {_COLUMNS}
                """
            ),
            {"worker_id": worker_id},
        )
        found = row.mappings().first()
    return dict(found) if found else None


async def _finish(
    engine: AsyncEngine, job_id: UUID, worker_id: str, status: str,
    result: str | None, error: str | None,
) -> dict:
    """running -> succeeded|failed. Только владелец (worker_id) может завершить задачу."""
    async with engine.begin() as conn:
        row = await conn.execute(
            text(
                f"""
                UPDATE jobs
                   SET status = :status, result = :result, error = :error,
                       finished_at = now()
                 WHERE id = :id AND status = 'running' AND worker_id = :worker_id
                RETURNING {_COLUMNS}
                """
            ),
            {"id": job_id, "worker_id": worker_id, "status": status,
             "result": result, "error": error},
        )
        found = row.mappings().first()
        if found:
            return dict(found)
        current = await conn.execute(
            text("SELECT status, worker_id FROM jobs WHERE id = :id"), {"id": job_id}
        )
        state = current.mappings().first()
    if state is None:
        raise JobNotFound
    if state["status"] == "running":  # running, но у другого воркера
        raise InvalidTransition("running (owned by another worker)")
    raise InvalidTransition(state["status"])


async def complete(engine: AsyncEngine, job_id: UUID, worker_id: str, result: str) -> dict:
    return await _finish(engine, job_id, worker_id, "succeeded", result, None)


async def fail(engine: AsyncEngine, job_id: UUID, worker_id: str, error: str) -> dict:
    return await _finish(engine, job_id, worker_id, "failed", None, error)


async def reap_stuck(engine: AsyncEngine, timeout_seconds: float, max_attempts: int) -> int:
    """Возвращает в очередь задачи, зависшие в running дольше timeout.
    Если попытки исчерпаны (attempts >= max_attempts) — переводит в failed."""
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                """
                UPDATE jobs
                   SET status      = CASE WHEN attempts >= :max_attempts
                                          THEN 'failed' ELSE 'queued' END,
                       error       = CASE WHEN attempts >= :max_attempts
                                          THEN 'stuck in running; attempts exhausted'
                                          ELSE error END,
                       finished_at = CASE WHEN attempts >= :max_attempts
                                          THEN now() ELSE NULL END,
                       worker_id   = NULL,
                       started_at  = NULL
                 WHERE status = 'running'
                   AND started_at < now() - make_interval(secs => :timeout)
                """
            ),
            {"timeout": timeout_seconds, "max_attempts": max_attempts},
        )
        return res.rowcount

