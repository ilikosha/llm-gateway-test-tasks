from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки API и воркера; переопределяются переменными окружения."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://jobs:jobs@localhost:5432/jobs"

    # Авторизация воркеров: "worker-1:token1,worker-2:token2". Пусто -> воркерам закрыто всё.
    worker_tokens: str = ""

    # Reaper
    stuck_timeout_seconds: float = 600.0  # 10 минут
    reaper_interval_seconds: float = 30.0
    reaper_enabled: bool = True
    max_attempts: int = 3

    # Worker
    api_url: str = "http://localhost:8000"
    worker_token: str = ""  # Bearer-токен этого воркера
    poll_interval_seconds: float = 1.0
    work_min_seconds: float = 1.0
    work_max_seconds: float = 4.0
    work_fail_rate: float = 0.0

    def token_map(self) -> list[tuple[str, str]]:
        """[(worker_id, token)] из WORKER_TOKENS; ошибка при неверном формате."""
        pairs = []
        for item in filter(None, (p.strip() for p in self.worker_tokens.split(","))):
            worker_id, sep, token = item.partition(":")
            if not sep or not worker_id.strip() or not token.strip():
                raise ValueError("WORKER_TOKENS: ожидается 'worker-id:token,...'")
            pairs.append((worker_id.strip(), token.strip()))
        return pairs
