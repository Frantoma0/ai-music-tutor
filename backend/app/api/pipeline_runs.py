from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.db import DEFAULT_DB_PATH, delete_pipeline_run_by_job_id, set_pipeline_run_thumbnail_url

from pydantic import BaseModel

router = APIRouter(prefix="/api/pipeline-runs", tags=["pipeline-runs"])

class PipelineRunThumbnailUpdate(BaseModel):
    thumbnail_url: str | None = None

@router.delete("/{job_id}")
async def delete_pipeline_run(
    job_id: str,
    db_path: str = Query(str(DEFAULT_DB_PATH)),
):
    deleted = await delete_pipeline_run_by_job_id(
        Path(db_path),
        job_id=job_id,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return {
        "status": "deleted",
        "job_id": job_id,
    }

@router.patch("/{job_id}/thumbnail")
async def update_pipeline_run_thumbnail(
    job_id: str,
    payload: PipelineRunThumbnailUpdate,
    db_path: str = Query(str(DEFAULT_DB_PATH)),
):
    updated = await set_pipeline_run_thumbnail_url(
        Path(db_path),
        job_id=job_id,
        thumbnail_url=payload.thumbnail_url,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return {
        "status": "updated",
        "job_id": job_id,
        "thumbnail_url": payload.thumbnail_url,
    }