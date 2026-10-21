import uuid

import pytest
from helpers import auth


async def _create(client, **params):
    return (await client.post("/jobs", json={"prompt": "hello", "params": params})).json()


async def _claim(client, worker="w1"):
    return (await client.post("/jobs/claim", headers=auth(worker))).json()


async def test_create_returns_queued(client):
    job = await _create(client, temperature=0.7)
    assert job["status"] == "queued"
    assert job["params"] == {"temperature": 0.7}
    assert job["attempts"] == 0


async def test_create_validates_prompt(client):
    assert (await client.post("/jobs", json={"prompt": ""})).status_code == 422


async def test_happy_path_complete(client):
    job = await _create(client)
    claimed = await _claim(client)
    assert claimed["status"] == "running" and claimed["attempts"] == 1

    resp = await client.post(
        f"/jobs/{job['id']}/complete", headers=auth("w1"), json={"result": "text"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "succeeded"
    assert resp.json()["result"] == "text"
    assert resp.json()["finished_at"] is not None

    fetched = (await client.get(f"/jobs/{job['id']}")).json()
    assert fetched["status"] == "succeeded"


async def test_happy_path_fail(client):
    job = await _create(client)
    await _claim(client)
    resp = await client.post(f"/jobs/{job['id']}/fail", headers=auth("w1"), json={"error": "boom"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"
    assert resp.json()["error"] == "boom"


@pytest.mark.parametrize("action,body", [
    ("complete", {"result": "x"}),
    ("fail", {"error": "x"}),
])
async def test_cannot_finish_queued_job(client, action, body):
    job = await _create(client)
    resp = await client.post(f"/jobs/{job['id']}/{action}", headers=auth("w1"), json=body)
    assert resp.status_code == 409
    assert (await client.get(f"/jobs/{job['id']}")).json()["status"] == "queued"


@pytest.mark.parametrize("first,second", [
    ("complete", "complete"), ("complete", "fail"), ("fail", "complete"), ("fail", "fail"),
])
async def test_cannot_finish_twice(client, first, second):
    job = await _create(client)
    await _claim(client)
    bodies = {
        "complete": {"result": "x"},
        "fail": {"error": "x"},
    }
    assert (await client.post(f"/jobs/{job['id']}/{first}", headers=auth("w1"), json=bodies[first])).status_code == 200
    resp = await client.post(f"/jobs/{job['id']}/{second}", headers=auth("w1"), json=bodies[second])
    assert resp.status_code == 409


async def test_other_worker_cannot_finish_job(client):
    job = await _create(client)
    await _claim(client, "w1")
    resp = await client.post(
        f"/jobs/{job['id']}/complete", headers=auth("intruder"), json={"result": "x"}
    )
    assert resp.status_code == 409
    assert (await client.get(f"/jobs/{job['id']}")).json()["status"] == "running"


async def test_unknown_job_is_404(client):
    missing = uuid.uuid4()
    assert (await client.get(f"/jobs/{missing}")).status_code == 404
    resp = await client.post(f"/jobs/{missing}/complete", headers=auth("w"), json={"result": "x"})
    assert resp.status_code == 404
