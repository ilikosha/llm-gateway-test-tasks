import asyncio

from helpers import auth

from jobqueue import repository


async def test_concurrent_claims_never_return_same_job(client):
    ids = {(await client.post("/jobs", json={"prompt": f"p{i}"})).json()["id"] for i in range(20)}
    assert len(ids) == 20

    # 50 одновременных claimer'ов на 20 задач.
    responses = await asyncio.gather(
        *(client.post("/jobs/claim", headers=auth(f"w{i}")) for i in range(50))
    )

    claimed = [r.json()["id"] for r in responses if r.status_code == 200]
    assert sorted(r.status_code for r in responses).count(204) == 30
    assert len(claimed) == 20
    assert len(set(claimed)) == 20, "одна задача выдана двум воркерам"
    assert set(claimed) == ids


async def test_concurrent_claims_at_repository_level(engine):
    for i in range(20):
        await repository.create(engine, f"p{i}", {})

    results = await asyncio.gather(*(repository.claim(engine, f"w{i}") for i in range(40)))

    claimed = [j["id"] for j in results if j]
    assert len(claimed) == len(set(claimed)) == 20
    assert all(j["attempts"] == 1 and j["status"] == "running" for j in results if j)


async def test_claim_returns_204_when_queue_empty(client):
    resp = await client.post("/jobs/claim", headers=auth("w"))
    assert resp.status_code == 204
    assert resp.content == b""


async def test_claim_is_fifo(client):
    first = (await client.post("/jobs", json={"prompt": "a"})).json()["id"]
    await client.post("/jobs", json={"prompt": "b"})
    resp = await client.post("/jobs/claim", headers=auth("w"))
    assert resp.json()["id"] == first
