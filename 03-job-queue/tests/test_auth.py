import pytest
from helpers import auth


async def _create(client):
    return (await client.post("/jobs", json={"prompt": "hello"})).json()


WORKER_CALLS = [
    ("/jobs/claim", None),
    ("/jobs/00000000-0000-0000-0000-000000000001/complete", {"result": "x"}),
    ("/jobs/00000000-0000-0000-0000-000000000001/fail", {"error": "x"}),
]


@pytest.mark.parametrize("path,body", WORKER_CALLS)
@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer wrong"},
    {"Authorization": "Basic tok-w1"},
    {"Authorization": "Bearer "},
    {"Authorization": "Bearer tok-w1x"},
])
async def test_worker_endpoints_require_valid_token(client, path, body, headers):
    resp = await client.post(path, headers=headers, json=body)
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


async def test_invalid_token_does_not_claim(client):
    job = await _create(client)
    await client.post("/jobs/claim", headers={"Authorization": "Bearer nope"})
    assert (await client.get(f"/jobs/{job['id']}")).json()["status"] == "queued"


async def test_client_endpoints_are_open(client):
    job = await _create(client)
    assert (await client.get(f"/jobs/{job['id']}")).status_code == 200


async def test_worker_id_comes_from_token_not_body(client):
    await _create(client)
    resp = await client.post("/jobs/claim", headers=auth("w1"), json={"worker_id": "spoofed"})
    assert resp.json()["worker_id"] == "w1"


async def test_worker_cannot_finish_another_workers_job(client):
    job = await _create(client)
    await client.post("/jobs/claim", headers=auth("w1"))
    for action, body in [("complete", {"result": "x"}), ("fail", {"error": "x"})]:
        resp = await client.post(f"/jobs/{job['id']}/{action}", headers=auth("w2"), json=body)
        assert resp.status_code == 409
    got = (await client.get(f"/jobs/{job['id']}")).json()
    assert got["status"] == "running" and got["worker_id"] == "w1"
    ok = await client.post(f"/jobs/{job['id']}/complete", headers=auth("w1"), json={"result": "y"})
    assert ok.status_code == 200


async def test_no_tokens_configured_rejects_everything(engine):
    import httpx

    from jobqueue.api import create_app
    from jobqueue.config import Settings

    app = create_app(Settings(reaper_enabled=False), engine=engine)
    app.state.engine = engine
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as c:
        assert (await c.post("/jobs/claim", headers=auth("w1"))).status_code == 401


def test_worker_tokens_format():
    from jobqueue.config import Settings

    assert Settings(worker_tokens="a:1, b:t:2").token_map() == [("a", "1"), ("b", "t:2")]
    with pytest.raises(ValueError):
        Settings(worker_tokens="broken").token_map()
