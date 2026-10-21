from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    prompt: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class CompleteRequest(BaseModel):
    result: str


class FailRequest(BaseModel):
    error: str


class JobOut(BaseModel):
    id: UUID
    prompt: str
    params: dict[str, Any]
    status: Literal["queued", "running", "succeeded", "failed"]
    result: str | None
    error: str | None
    attempts: int
    worker_id: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
