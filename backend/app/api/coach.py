"""API endpoints for the Practice Coach agent."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..agent.practice_coach import get_latest_plan, run_practice_coach

router = APIRouter(prefix="/api/coach", tags=["coach"])


@router.post("/{job_id}")
async def create_plan(
    job_id: str,
    language: str = Query(default="en", pattern="^(en|bg)$"),
) -> dict:
    if not job_id or len(job_id) > 96:
        raise HTTPException(status_code=400, detail="Invalid job_id")

    return await run_practice_coach(job_id=job_id, language=language)


@router.get("/{job_id}")
async def latest_plan(job_id: str) -> dict:
    if not job_id or len(job_id) > 96:
        raise HTTPException(status_code=400, detail="Invalid job_id")

    stored = await get_latest_plan(job_id)

    if stored is None:
        return {"job_id": job_id, "status": "no_plan", "plan": None}

    return {"job_id": job_id, "status": "ok", **stored}
