from __future__ import annotations

import json

import aiosqlite
import pytest

from app.db.database import (
    create_pipeline_run,
    create_session,
    create_transcription_record,
    initialize_database,
    list_tables,
)


@pytest.mark.asyncio
async def test_initialize_database_creates_expected_tables(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)
    tables = set(await list_tables(db_path))

    expected = {
        "sessions",
        "pipeline_runs",
        "transcriptions",
        "corrections",
        "metrics",
        "practice_results",
        "practice_plans",
    }

    assert expected.issubset(tables)


@pytest.mark.asyncio
async def test_database_can_store_session_pipeline_run_and_transcription(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    session_id = await create_session(
        db_path,
        title="Pytest session",
        source="pytest.wav",
    )

    run_id = await create_pipeline_run(
        db_path,
        session_id=session_id,
        job_id="pytest-job",
        status="completed",
        source="pytest.wav",
        final_audio_path="data/processed/pytest/input.wav",
        midi_path="artifacts/tracer/pytest/output.mid",
        detected_key="D major",
        hvs_score=0.81,
        metadata={"test": True},
    )

    notes = [
        {
            "id": "n0",
            "pitch": 69,
            "pitch_name": "A4",
            "confidence": 0.629446,
        }
    ]

    transcription_id = await create_transcription_record(
        db_path,
        pipeline_run_id=run_id,
        job_id="pytest-job",
        input_audio="data/processed/pytest/input.wav",
        midi_path="artifacts/tracer/pytest/output.mid",
        transcription_method="basic_pitch",
        status="completed",
        notes=notes,
    )

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT
                sessions.title,
                pipeline_runs.detected_key,
                pipeline_runs.hvs_score,
                transcriptions.transcription_method,
                transcriptions.note_count,
                transcriptions.notes_json
            FROM transcriptions
            JOIN pipeline_runs ON transcriptions.pipeline_run_id = pipeline_runs.id
            JOIN sessions ON pipeline_runs.session_id = sessions.id
            WHERE transcriptions.id = ?
            """,
            (transcription_id,),
        )

        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "Pytest session"
    assert row[1] == "D major"
    assert row[2] == 0.81
    assert row[3] == "basic_pitch"
    assert row[4] == 1

    stored_notes = json.loads(row[5])
    assert stored_notes[0]["confidence"] == 0.629446


@pytest.mark.asyncio
async def test_database_foreign_keys_are_enforced(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    with pytest.raises(aiosqlite.IntegrityError):
        await create_pipeline_run(
            db_path,
            session_id="missing-session",
            job_id="pytest-job",
            status="completed",
        )
