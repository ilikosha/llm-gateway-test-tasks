import httpx
from helpers import WORKER_TOKENS, auth

from jobqueue.api import create_app
from jobqueue.config import Settings
from jobqueue.db import make_engine


async def test_validation_errors_are_422(client):
    assert (await client.post("/jobs", json={})).status_code == 422
    assert (await client.post("/jobs", json={"prompt": "x", "params": "nope"})).status_code == 422
    assert (await client.get("/jobs/not-a-uuid")).status_code == 422
    resp = await client.post(
        "/jobs/00000000-0000-0000-0000-000000000001/complete", headers=auth("w1"), json={}
    )
    assert resp.status_code == 422


async def test_database_down_is_503():
    # Порт, на котором никто не слушает.
    engine = make_engine("postgresql+asyncpg://jobs:jobs@127.0.0.1:1/jobs")
    app = create_app(Settings(reaper_enabled=False, worker_tokens=WORKER_TOKENS), engine=engine)
    app.state.engine = engine
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as c:
        for resp in (
            await c.post("/jobs", json={"prompt": "x"}),
            await c.get("/jobs/00000000-0000-0000-0000-000000000001"),
            await c.post("/jobs/claim", headers=auth("w1")),
        ):
            assert resp.status_code == 503
            assert resp.json()["detail"] == "database unavailable, retry later"
            assert resp.headers["retry-after"] == "5"
    await engine.dispose()
