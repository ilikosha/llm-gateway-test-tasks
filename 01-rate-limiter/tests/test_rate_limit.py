from tests.conftest import LIMIT, WINDOW, auth


def test_within_limit(client):
    for i in range(LIMIT):
        r = client.post("/v1/echo", json={"n": i}, headers=auth())
        assert r.status_code == 200
        assert r.json() == {"n": i}
        assert r.headers["X-RateLimit-Limit"] == str(LIMIT)
        assert r.headers["X-RateLimit-Remaining"] == str(LIMIT - i - 1)


def test_limit_exceeded_returns_429_with_retry_after(client, clock):
    for _ in range(LIMIT):
        assert client.post("/v1/echo", json={}, headers=auth()).status_code == 200
    clock.advance(3.5)
    r = client.post("/v1/echo", json={}, headers=auth())
    assert r.status_code == 429
    # The oldest request was 3.5s ago, so a slot frees in 6.5s -> rounded up to 7.
    assert r.headers["Retry-After"] == "7"
    assert r.headers["X-RateLimit-Remaining"] == "0"


def test_window_slides(client, clock):
    # Requests at t=0, t=6, t=7 fill the limit.
    for dt in (0, 6, 1):
        clock.advance(dt)
        assert client.post("/v1/echo", json={}, headers=auth()).status_code == 200
    assert client.post("/v1/echo", json={}, headers=auth()).status_code == 429

    # t=10.5: only the t=0 request left the window -> exactly one slot frees up
    # (a fixed window would have reset all of them).
    clock.advance(3.5)
    assert client.post("/v1/echo", json={}, headers=auth()).status_code == 200
    r = client.post("/v1/echo", json={}, headers=auth())
    assert r.status_code == 429
    # The oldest request in the window is t=6 and expires at t=16: 5.5s -> 6.
    assert r.headers["Retry-After"] == "6"


def test_different_keys_are_independent(client):
    for _ in range(LIMIT):
        assert client.post("/v1/echo", json={}, headers=auth("key-a")).status_code == 200
    assert client.post("/v1/echo", json={}, headers=auth("key-a")).status_code == 429
    r = client.post("/v1/echo", json={}, headers=auth("key-b"))
    assert r.status_code == 200
    assert r.headers["X-RateLimit-Remaining"] == str(LIMIT - 1)


def test_full_window_passes_all_allowed_again(client, clock):
    for _ in range(LIMIT):
        client.post("/v1/echo", json={}, headers=auth())
    clock.advance(WINDOW + 0.1)
    assert client.post("/v1/echo", json={}, headers=auth()).status_code == 200


# Boundary semantics: the window is (now - T, now]. An entry with
# timestamp <= now - T is expired; an entry exactly T - 1ms old still counts.
def _fill_at_t0(client):
    for _ in range(LIMIT):
        assert client.post("/v1/echo", json={}, headers=auth()).status_code == 200


def test_boundary_one_ms_before_window_end_is_still_limited(client, clock):
    _fill_at_t0(client)
    clock.advance(WINDOW - 0.001)
    r = client.post("/v1/echo", json={}, headers=auth())
    assert r.status_code == 429
    # 1ms left until the oldest entries expire -> rounded up to 1s.
    assert r.headers["Retry-After"] == "1"


def test_boundary_exactly_at_window_end_first_request_expires(client, clock):
    _fill_at_t0(client)
    clock.advance(WINDOW)  # now - T == timestamp of the first requests -> dropped
    r = client.post("/v1/echo", json={}, headers=auth())
    assert r.status_code == 200
    assert r.headers["X-RateLimit-Remaining"] == str(LIMIT - 1)


def test_boundary_only_expired_entries_are_dropped(client, clock):
    # One request at t=0, the others at t=5; at t=T only the first expires.
    assert client.post("/v1/echo", json={}, headers=auth()).status_code == 200
    clock.advance(5)
    for _ in range(LIMIT - 1):
        assert client.post("/v1/echo", json={}, headers=auth()).status_code == 200
    clock.advance(WINDOW - 5 - 0.001)
    assert client.post("/v1/echo", json={}, headers=auth()).status_code == 429
    clock.advance(0.001)  # exactly t=T
    assert client.post("/v1/echo", json={}, headers=auth()).status_code == 200
    r = client.post("/v1/echo", json={}, headers=auth())
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "5"


def test_same_millisecond_requests_are_counted_separately(client):
    # Fake clock does not move: all requests share one timestamp but are unique members.
    _fill_at_t0(client)
    assert client.post("/v1/echo", json={}, headers=auth()).status_code == 429
