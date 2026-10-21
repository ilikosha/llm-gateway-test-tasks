import asyncio
import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncEngine

from . import repository
from .config import Settings
from .db import make_engine
from .reaper import reaper_loop
from .schemas import CompleteRequest, FailRequest, JobCreate, JobOut

log = logging.getLogger("jobqueue.api")
_bearer = HTTPBearer(auto_error=False)

# Ошибки недоступности БД (отказ соединения, обрыв, исчерпан пул) -> 503.
_DB_DOWN = (sa_exc.OperationalError, sa_exc.InterfaceError, sa_exc.TimeoutError, OSError)


def create_app(settings: Settings | None = None, engine: AsyncEngine | None = None) -> FastAPI:
    settings = settings or Settings()
    tokens = settings.token_map()  # падаем на старте при кривом WORKER_TOKENS

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = engine or make_engine(settings.database_url)
        reaper = None
        if settings.reaper_enabled:
            reaper = asyncio.create_task(
                reaper_loop(
                    app.state.engine,
                    settings.stuck_timeout_seconds,
                    settings.reaper_interval_seconds,
                    settings.max_attempts,
                )
            )
        yield
        if reaper:
            reaper.cancel()
        if engine is None:
            await app.state.engine.dispose()

    app = FastAPI(title="Job queue", lifespan=lifespan)

    async def _db_unavailable(request: Request, exc: Exception):
        log.error("database unavailable: %r", exc)
        return JSONResponse(
            {"detail": "database unavailable, retry later"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={"Retry-After": "5"},
        )

    for exc_type in _DB_DOWN:
        app.add_exception_handler(exc_type, _db_unavailable)

    def current_worker(
        creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> str:
        """worker_id определяется по токену; перебираем ВСЕ токены без раннего выхода,
        сравнение constant-time (hmac.compare_digest)."""
        found = None
        presented = (creds.credentials if creds else "").encode()
        for worker_id, token in tokens:
            if hmac.compare_digest(presented, token.encode()):
                found = worker_id
        if found is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "missing or invalid worker token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return found

    def db(request: Request) -> AsyncEngine:
        return request.app.state.engine

    @app.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
    async def create_job(body: JobCreate, request: Request):
        return await repository.create(db(request), body.prompt, body.params)

    # Статический путь /jobs/claim объявлен раньше /jobs/{job_id}.
    @app.post("/jobs/claim", response_model=JobOut)
    async def claim_job(request: Request, worker_id: str = Depends(current_worker)):
        job = await repository.claim(db(request), worker_id)
        if job is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return job

    @app.post("/jobs/{job_id}/complete", response_model=JobOut)
    async def complete_job(
        job_id: UUID, body: CompleteRequest, request: Request,
        worker_id: str = Depends(current_worker),
    ):
        return await _transition(
            repository.complete(db(request), job_id, worker_id, body.result)
        )

    @app.post("/jobs/{job_id}/fail", response_model=JobOut)
    async def fail_job(
        job_id: UUID, body: FailRequest, request: Request,
        worker_id: str = Depends(current_worker),
    ):
        return await _transition(
            repository.fail(db(request), job_id, worker_id, body.error)
        )

    @app.get("/jobs/{job_id}", response_model=JobOut)
    async def get_job(job_id: UUID, request: Request):
        try:
            return await repository.get(db(request), job_id)
        except repository.JobNotFound:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found") from None

    return app


async def _transition(call):
    try:
        return await call
    except repository.JobNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found") from None
    except repository.InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None


def app_factory() -> FastAPI:
    """Точка входа для uvicorn: `uvicorn --factory jobqueue.api:app_factory`."""
    return create_app()
