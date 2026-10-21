from helpers import auth
from sqlalchemy import text

from jobqueue import repository

TIMEOUT = 600


async def _backdate(engine, job_id, seconds):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE jobs SET started_at = now() - make_interval(secs => :s) WHERE id = :id"),
            {"s": seconds, "id": job_id},
        )


async def test_stuck_job_returns_to_queue_and_counts_attempts(engine):
    job = await repository.create(engine, "p", {})
    await repository.claim(engine, "w1")
    await _backdate(engine, job["id"], TIMEOUT + 5)

    assert await repository.reap_stuck(engine, TIMEOUT, max_attempts=3) == 1

    requeued = await repository.get(engine, job["id"])
    assert requeued["status"] == "queued"
    assert requeued["attempts"] == 1
    assert requeued["worker_id"] is None

    again = await repository.claim(engine, "w2")
    assert again["id"] == job["id"]
    assert again["attempts"] == 2


async def test_fresh_running_job_is_left_alone(engine):
    job = await repository.create(engine, "p", {})
    await repository.claim(engine, "w1")
    await _backdate(engine, job["id"], TIMEOUT - 60)

    assert await repository.reap_stuck(engine, TIMEOUT, max_attempts=3) == 0
    assert (await repository.get(engine, job["id"]))["status"] == "running"


async def test_job_fails_when_attempts_exhausted(engine):
    job = await repository.create(engine, "p", {})
    for attempt in (1, 2):
        await repository.claim(engine, "w1")
        await _backdate(engine, job["id"], TIMEOUT + 5)
        await repository.reap_stuck(engine, TIMEOUT, max_attempts=2)
        status = (await repository.get(engine, job["id"]))["status"]
        assert status == ("queued" if attempt == 1 else "failed")

    final = await repository.get(engine, job["id"])
    assert final["attempts"] == 2
    assert "attempts exhausted" in final["error"]


async def test_late_result_from_old_worker_is_rejected_after_requeue(client, engine):
    job = (await client.post("/jobs", json={"prompt": "p"})).json()
    await client.post("/jobs/claim", headers=auth("slow"))
    await _backdate(engine, job["id"], TIMEOUT + 5)
    await repository.reap_stuck(engine, TIMEOUT, max_attempts=3)
    await client.post("/jobs/claim", headers=auth("fast"))

    late = await client.post(
        f"/jobs/{job['id']}/complete", headers=auth("slow"), json={"result": "late"}
    )
    assert late.status_code == 409
    ok = await client.post(
        f"/jobs/{job['id']}/complete", headers=auth("fast"), json={"result": "ok"}
    )
    assert ok.status_code == 200
