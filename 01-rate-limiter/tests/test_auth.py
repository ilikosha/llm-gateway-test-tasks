import pytest
from fakeredis import FakeAsyncRedis

from app.config import Settings
from app.main import create_app


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer "}, {"Authorization": "Bearer"}],
)
def test_missing_or_invalid_authorization_is_401(client, headers):
    r = client.post("/v1/echo", json={"a": 1}, headers=headers)
    assert r.status_code == 401
    assert "X-RateLimit-Limit" not in r.headers


def test_unknown_key_is_rejected(client):
    assert client.post("/v1/echo", json={}, headers={"Authorization": "Bearer stranger"}).status_code == 401


def test_service_refuses_to_start_without_keys():
    with pytest.raises(RuntimeError):
        create_app(Settings(api_keys=""), redis=FakeAsyncRedis())
