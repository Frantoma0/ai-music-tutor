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


@pytest.mark.asyncio
async def test_database_can_list_and_get_pipeline_runs(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    session_id = await create_session(
        db_path,
        title="History test session",
        source="history.wav",
    )

    run_id = await create_pipeline_run(
        db_path,
        session_id=session_id,
        job_id="history-job",
        status="completed",
        source="history.wav",
        final_audio_path="data/processed/history/input.wav",
        midi_path="artifacts/tracer/history/output.mid",
        detected_key="F major",
        hvs_score=0.8065,
        metadata={"kind": "history-test"},
    )

    await create_transcription_record(
        db_path,
        pipeline_run_id=run_id,
        job_id="history-job",
        input_audio="data/processed/history/input.wav",
        midi_path="artifacts/tracer/history/output.mid",
        transcription_method="basic_pitch",
        status="completed",
        notes=[
            {
                "id": "n0",
                "pitch": 60,
                "pitch_name": "C4",
                "confidence": 0.722311,
            }
        ],
    )

    from app.db.database import get_pipeline_run, list_pipeline_runs

    runs = await list_pipeline_runs(db_path, limit=10)

    assert len(runs) == 1
    assert runs[0]["job_id"] == "history-job"
    assert runs[0]["session_title"] == "History test session"
    assert runs[0]["transcription_method"] == "basic_pitch"
    assert runs[0]["note_count"] == 1

    run = await get_pipeline_run(db_path, job_id="history-job")

    assert run is not None
    assert run["job_id"] == "history-job"
    assert run["detected_key"] == "F major"
    assert run["metadata"]["kind"] == "history-test"
    assert run["transcription"]["notes"][0]["confidence"] == 0.722311


@pytest.mark.asyncio
async def test_get_pipeline_run_returns_none_for_missing_job(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    from app.db.database import get_pipeline_run

    result = await get_pipeline_run(db_path, job_id="missing-job")

    assert result is None


@pytest.mark.asyncio
async def test_database_can_store_metric_records(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    session_id = await create_session(
        db_path,
        title="Metric test session",
        source="metric.wav",
    )

    run_id = await create_pipeline_run(
        db_path,
        session_id=session_id,
        job_id="metric-job",
        status="completed",
    )

    from app.db.database import create_metric_record

    metric_id = await create_metric_record(
        db_path,
        pipeline_run_id=run_id,
        metric_name="baseline_f1",
        metric_value=0.081379,
        metric_json={
            "precision": 0.088185,
            "recall": 0.076167,
            "f1": 0.081379,
            "overlap": 0.808445,
        },
    )

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT metric_name, metric_value, metric_json
            FROM metrics
            WHERE id = ?
            """,
            (metric_id,),
        )
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "baseline_f1"
    assert row[1] == 0.081379

    stored = json.loads(row[2])
    assert stored["f1"] == 0.081379
    assert stored["overlap"] == 0.808445
