"""Применение миграций: `python -m jobqueue.migrate` (one-shot сервис в compose)."""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from .config import Settings


def make_config(database_url: str | None = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    cfg.set_main_option("sqlalchemy.url", (database_url or Settings().database_url).replace("%", "%%"))
    return cfg


def upgrade(database_url: str | None = None, revision: str = "head") -> None:
    command.upgrade(make_config(database_url), revision)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    upgrade()
    logging.getLogger("jobqueue.migrate").info("migrations applied")


if __name__ == "__main__":
    main()
