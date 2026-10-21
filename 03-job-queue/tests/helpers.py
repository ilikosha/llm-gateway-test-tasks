WORKER_NAMES = ["w", "w1", "w2", "slow", "fast", "intruder", *[f"w{i}" for i in range(50)]]
WORKER_TOKENS = ",".join(f"{n}:tok-{n}" for n in dict.fromkeys(WORKER_NAMES))


def auth(name: str) -> dict:
    """Заголовок авторизации воркера `name` (токен tok-<name>)."""
    return {"Authorization": f"Bearer tok-{name}"}
