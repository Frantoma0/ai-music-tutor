from __future__ import annotations

from pathlib import Path
from typing import Any

from app.db.database import (
    create_pipeline_run,
    create_session,
    create_transcription_record,
    initialize_database,
)


async def persist_audio_to_analysis_result(
    result: Any,
    db_path: str | Path = "data/app.sqlite3",
    *,
    session_title: str | None = None,
) -> dict[str, str]:
    """
    Persist an AudioToAnalysisPipelineResult into SQLite.

    This is intentionally separate from the orchestrator so the pipeline can
    still run without persistence in tests or lightweight scripts.
    """
    await initialize_database(db_path)

    data = result.to_dict()

    session_id = await create_session(
        db_path,
        title=session_title or f"Pipeline run {data.get('job_id')}",
        source=data.get("source"),
    )

    run_id = await create_pipeline_run(
        db_path,
        session_id=session_id,
        job_id=data["job_id"],
        status=data["status"],
        source=data.get("source"),
        final_audio_path=data.get("final_audio_path"),
        midi_path=data.get("midi_path"),
        detected_key=data.get("detected_key"),
        hvs_score=data.get("hvs_score"),
        error=data.get("error"),
        metadata={
            "extract": data.get("extract"),
            "separation": data.get("separation"),
            "separation_quality": data.get("separation_quality"),
            "analysis": data.get("analysis"),
        },
    )

    transcription = data.get("transcription") or {}

    transcription_id = await create_transcription_record(
        db_path,
        pipeline_run_id=run_id,
        job_id=data["job_id"],
        input_audio=transcription.get("input_audio") or data.get("final_audio_path") or "",
        midi_path=transcription.get("midi_path") or data.get("midi_path"),
        transcription_method=transcription.get("transcription_method") or "unknown",
        status=transcription.get("status") or data["status"],
        notes=transcription.get("notes") or [],
        error=transcription.get("error"),
    )

    return {
        "session_id": session_id,
        "pipeline_run_id": run_id,
        "transcription_id": transcription_id,
    }
