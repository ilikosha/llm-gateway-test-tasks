"""create jobs table

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE jobs (
            id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            prompt      text        NOT NULL,
            params      jsonb       NOT NULL DEFAULT '{}'::jsonb,
            status      text        NOT NULL DEFAULT 'queued',
            result      text,
            error       text,
            attempts    integer     NOT NULL DEFAULT 0,
            worker_id   text,
            created_at  timestamptz NOT NULL DEFAULT now(),
            started_at  timestamptz,
            finished_at timestamptz,
            CONSTRAINT jobs_status_check
                CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
            CONSTRAINT jobs_attempts_check CHECK (attempts >= 0)
        )
    """)
    # claim: самая старая queued-задача (FIFO) — частичный индекс только по queued.
    op.execute(
        "CREATE INDEX jobs_queued_idx ON jobs (created_at, id) WHERE status = 'queued'"
    )
    # reaper: поиск зависших running по started_at.
    op.execute(
        "CREATE INDEX jobs_running_idx ON jobs (started_at) WHERE status = 'running'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE jobs")
