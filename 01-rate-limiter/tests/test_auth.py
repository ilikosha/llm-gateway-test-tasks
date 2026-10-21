import pytest


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer "}, {"Authorization": "Bearer"}],
)
def test_missing_or_invalid_authorization_is_401(client, headers):
    r = client.post("/v1/echo", json={"a": 1}, headers=headers)
    assert r.status_code == 401
    assert "X-RateLimit-Limit" not in r.headers
