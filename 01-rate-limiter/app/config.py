from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration, read from environment variables."""

    rate_limit_requests: int = Field(default=5, gt=0)
    rate_limit_window_seconds: float = Field(default=60, gt=0)
    redis_url: str = "redis://localhost:6379/0"
    # Optional comma-separated allowlist. Empty -> any non-empty Bearer token is accepted.
    api_keys: str = ""

    @property
    def api_keys_set(self) -> frozenset[str]:
        return frozenset(k.strip() for k in self.api_keys.split(",") if k.strip())
