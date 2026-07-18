"""API endpoints for per-lesson practice progress and sessions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..db.progress import (
    list_sessions_for_job,
    progress_summary,
    save_position,
    save_practice_session,
)

router = APIRouter(prefix="/api/progress", tags=["progress"])


class SessionIn(BaseModel):
    job_id: str = Field(min_length=1, max_length=96)
    hits: int = Field(ge=0)
    missed: int = Field(ge=0)
    wrong: int = Field(ge=0)
    accuracy: int = Field(ge=0, le=100)
    stars: int = Field(ge=0, le=3)
    mode: str | None = Field(default=None, max_length=24)
    note_view: str | None = Field(default=None, max_length=24)
    duration_seconds: float | None = Field(default=None, ge=0)
    weak_spots: list[dict] | None = Field(default=None, max_length=300)


class PositionIn(BaseModel):
    position_seconds: float = Field(ge=0)
    note_view: str | None = Field(default=None, max_length=24)


@router.post("")
async def create_session(payload: SessionIn) -> dict:
    record = await save_practice_session(**payload.model_dump())
    return {"status": "ok", "session": record}


@router.put("/{job_id}/position")
async def update_position(job_id: str, payload: PositionIn) -> dict:
    if not job_id or len(job_id) > 96:
        raise HTTPException(status_code=400, detail="Invalid job_id")

    await save_position(job_id, payload.position_seconds, payload.note_view)
    return {"status": "ok"}


@router.get("/summary")
async def get_progress_summary() -> dict:
    return {"summary": await progress_summary()}


@router.get("/{job_id}")
async def get_sessions_for_job(job_id: str) -> dict:
    if not job_id or len(job_id) > 96:
        raise HTTPException(status_code=400, detail="Invalid job_id")

    return {"job_id": job_id, "sessions": await list_sessions_for_job(job_id)}
