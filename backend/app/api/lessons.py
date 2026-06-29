from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.db.database import DEFAULT_DB_PATH, get_pipeline_run
from app.pipeline.lesson_preparation import prepare_lesson_for_job
from app.pipeline.lesson_schema import LessonResponse
from fastapi import HTTPException

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/{job_id}", response_model=LessonResponse)
async def get_lesson(
    job_id: str,
    db_path: str = Query(default=str(DEFAULT_DB_PATH)),
) -> LessonResponse:
    lesson = await prepare_lesson_for_job(job_id, db_path=Path(db_path))

    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson not found for job_id={job_id}")

    return lesson

def resolve_midi_path(midi_path: str | None) -> Path | None:
    if not midi_path:
        return None

    path = Path(midi_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    return path


@router.get("/{job_id}/midi/{version}")
async def get_lesson_midi(
    job_id: str,
    version: Literal["raw", "corrected"],
    db_path: str = Query(default=str(DEFAULT_DB_PATH)),
) -> FileResponse:
    run = await get_pipeline_run(Path(db_path), job_id=job_id)

    if run is None:
        raise HTTPException(status_code=404, detail=f"Lesson not found for job_id={job_id}")

    if version == "corrected":
        raise HTTPException(status_code=404, detail="Corrected MIDI is not available for this lesson yet")

    transcription = run.get("transcription") or {}
    midi_path = transcription.get("midi_path") or run.get("midi_path")
    resolved_path = resolve_midi_path(midi_path)

    if resolved_path is None or not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail=f"Raw MIDI file not found for job_id={job_id}")

    return FileResponse(
        path=resolved_path,
        media_type="audio/midi",
        filename=f"{job_id}-{version}.mid",
    )

