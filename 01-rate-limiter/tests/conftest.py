import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

LIMIT = 3
WINDOW = 10


class FakeClock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(clock: FakeClock):
    settings = Settings(rate_limit_requests=LIMIT, rate_limit_window_seconds=WINDOW)
    app = create_app(settings, redis=FakeAsyncRedis(), clock=clock)
    with TestClient(app) as c:
        yield c


def auth(key: str = "key-a") -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}
