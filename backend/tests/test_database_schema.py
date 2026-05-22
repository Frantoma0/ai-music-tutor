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


@pytest.mark.asyncio
async def test_database_can_list_metrics_and_get_metrics_for_run(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    session_id = await create_session(
        db_path,
        title="Metrics history session",
        source="metrics-history.wav",
    )

    run_id = await create_pipeline_run(
        db_path,
        session_id=session_id,
        job_id="metrics-history-job",
        status="completed",
        detected_key="F major",
        hvs_score=0.8065,
        metadata={"kind": "metrics-history-test"},
    )

    from app.db.database import (
        create_metric_record,
        get_metrics_for_run,
        list_metrics,
    )

    await create_metric_record(
        db_path,
        pipeline_run_id=run_id,
        metric_name="baseline_transcription_f1",
        metric_value=0.048951,
        metric_json={
            "precision": 0.063869,
            "recall": 0.039683,
            "f1": 0.048951,
            "overlap": 0.85949,
        },
    )

    await create_metric_record(
        db_path,
        pipeline_run_id=run_id,
        metric_name="baseline_transcription_overlap",
        metric_value=0.85949,
        metric_json={
            "overlap": 0.85949,
        },
    )

    metrics = await list_metrics(
        db_path,
        metric_name="baseline_transcription_f1",
        limit=10,
    )

    assert len(metrics) == 1
    assert metrics[0]["job_id"] == "metrics-history-job"
    assert metrics[0]["metric_name"] == "baseline_transcription_f1"
    assert metrics[0]["metric_value"] == 0.048951
    assert metrics[0]["metric_json"]["f1"] == 0.048951

    result = await get_metrics_for_run(
        db_path,
        job_id="metrics-history-job",
    )

    assert result is not None
    assert result["run"]["job_id"] == "metrics-history-job"
    assert result["run"]["detected_key"] == "F major"
    assert result["run"]["metadata"]["kind"] == "metrics-history-test"
    assert result["count"] == 2

    names = {metric["metric_name"] for metric in result["metrics"]}
    assert names == {
        "baseline_transcription_f1",
        "baseline_transcription_overlap",
    }


@pytest.mark.asyncio
async def test_get_metrics_for_run_returns_none_for_missing_job(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    from app.db.database import get_metrics_for_run

    result = await get_metrics_for_run(
        db_path,
        job_id="missing-metrics-job",
    )

    assert result is None


async def test_correction_tables_are_created(tmp_path):
    from app.db.database import initialize_database, list_tables

    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    tables = set(await list_tables(db_path))

    assert "correction_runs" in tables
    assert "correction_proposals" in tables
    assert "correction_validations" in tables


async def test_correction_tables_have_expected_foreign_keys(tmp_path):
    import aiosqlite

    from app.db.database import initialize_database

    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("PRAGMA foreign_key_list(correction_runs)")
        correction_run_fks = await cursor.fetchall()

        cursor = await db.execute("PRAGMA foreign_key_list(correction_proposals)")
        proposal_fks = await cursor.fetchall()

        cursor = await db.execute("PRAGMA foreign_key_list(correction_validations)")
        validation_fks = await cursor.fetchall()

    assert any(row[2] == "pipeline_runs" for row in correction_run_fks)
    assert any(row[2] == "correction_runs" for row in proposal_fks)
    assert any(row[2] == "correction_runs" for row in validation_fks)


async def test_correction_tables_can_store_minimal_records(tmp_path):
    import aiosqlite

    from app.db.database import create_pipeline_run, initialize_database, new_id

    db_path = tmp_path / "app.sqlite3"

    await initialize_database(db_path)

    pipeline_run_id = await create_pipeline_run(
        db_path,
        job_id="pytest-correction-job",
        status="completed",
    )

    correction_run_id = new_id("cor")

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")

        await db.execute(
            """
            INSERT INTO correction_runs (
                id,
                pipeline_run_id,
                job_id,
                status,
                harmony_path,
                mask_path,
                proposals_path,
                validation_path,
                mask_selected_count,
                proposal_count,
                approved_count,
                rejected_count,
                midi_mutated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                correction_run_id,
                pipeline_run_id,
                "pytest-correction-job",
                "completed",
                "artifacts/harmony/test.json",
                "artifacts/corrections/mask.json",
                "artifacts/corrections/proposals.json",
                "artifacts/corrections/validation.json",
                43,
                43,
                43,
                0,
                0,
            ),
        )

        await db.execute(
            """
            INSERT INTO correction_proposals (
                id,
                correction_run_id,
                proposal_id,
                candidate_id,
                action,
                original_pitch,
                proposed_pitch,
                status,
                reason,
                safety_notes_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("cpr"),
                correction_run_id,
                "prop_0000",
                "n87",
                "flag_for_review",
                47,
                None,
                "pending_validation",
                "selected_mask_candidate_requires_review:low_confidence_high_hvs",
                '["placeholder_proposal_no_midi_mutation"]',
            ),
        )

        await db.execute(
            """
            INSERT INTO correction_validations (
                id,
                correction_run_id,
                proposal_id,
                candidate_id,
                action,
                validation_status,
                approved,
                reasons_json,
                safety_notes_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("cvd"),
                correction_run_id,
                "prop_0000",
                "n87",
                "flag_for_review",
                "approved_for_review",
                1,
                "[]",
                '["safe_review_only_no_midi_mutation"]',
            ),
        )

        await db.commit()

        cursor = await db.execute(
            """
            SELECT
                correction_runs.job_id,
                correction_runs.mask_selected_count,
                correction_runs.proposal_count,
                correction_runs.approved_count,
                correction_runs.rejected_count,
                correction_runs.midi_mutated
            FROM correction_runs
            WHERE correction_runs.id = ?
            """,
            (correction_run_id,),
        )

        row = await cursor.fetchone()

    assert row == (
        "pytest-correction-job",
        43,
        43,
        43,
        0,
        0,
    )
