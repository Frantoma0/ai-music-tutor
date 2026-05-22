from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import aiosqlite


DEFAULT_DB_PATH = Path("data/app.sqlite3")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def initialize_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.executescript(schema)
        await db.commit()

    return db_path


async def list_tables(db_path: str | Path = DEFAULT_DB_PATH) -> list[str]:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        )
        rows = await cursor.fetchall()

    return [row[0] for row in rows]


async def create_session(
    db_path: str | Path,
    *,
    title: str | None = None,
    source: str | None = None,
    session_id: str | None = None,
) -> str:
    session_id = session_id or new_id("sess")

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute(
            """
            INSERT INTO sessions (id, title, source)
            VALUES (?, ?, ?)
            """,
            (session_id, title, source),
        )
        await db.commit()

    return session_id


async def create_pipeline_run(
    db_path: str | Path,
    *,
    job_id: str,
    status: str,
    session_id: str | None = None,
    source: str | None = None,
    final_audio_path: str | None = None,
    midi_path: str | None = None,
    detected_key: str | None = None,
    hvs_score: float | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> str:
    run_id = run_id or new_id("run")
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute(
            """
            INSERT INTO pipeline_runs (
                id,
                session_id,
                job_id,
                status,
                source,
                final_audio_path,
                midi_path,
                detected_key,
                hvs_score,
                error,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                session_id,
                job_id,
                status,
                source,
                final_audio_path,
                midi_path,
                detected_key,
                hvs_score,
                error,
                metadata_json,
            ),
        )
        await db.commit()

    return run_id


async def create_transcription_record(
    db_path: str | Path,
    *,
    job_id: str,
    input_audio: str,
    transcription_method: str,
    status: str,
    pipeline_run_id: str | None = None,
    midi_path: str | None = None,
    notes: list[dict[str, Any]] | None = None,
    error: str | None = None,
    transcription_id: str | None = None,
) -> str:
    transcription_id = transcription_id or new_id("trn")
    notes = notes or []

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute(
            """
            INSERT INTO transcriptions (
                id,
                pipeline_run_id,
                job_id,
                input_audio,
                midi_path,
                transcription_method,
                note_count,
                notes_json,
                status,
                error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transcription_id,
                pipeline_run_id,
                job_id,
                input_audio,
                midi_path,
                transcription_method,
                len(notes),
                json.dumps(notes, ensure_ascii=False),
                status,
                error,
            ),
        )
        await db.commit()

    return transcription_id


async def list_pipeline_runs(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                pipeline_runs.id,
                pipeline_runs.job_id,
                pipeline_runs.status,
                pipeline_runs.source,
                pipeline_runs.final_audio_path,
                pipeline_runs.midi_path,
                pipeline_runs.detected_key,
                pipeline_runs.hvs_score,
                pipeline_runs.error,
                pipeline_runs.started_at,
                pipeline_runs.completed_at,
                sessions.id AS session_id,
                sessions.title AS session_title,
                transcriptions.transcription_method,
                transcriptions.note_count
            FROM pipeline_runs
            LEFT JOIN sessions ON pipeline_runs.session_id = sessions.id
            LEFT JOIN transcriptions ON transcriptions.pipeline_run_id = pipeline_runs.id
            ORDER BY pipeline_runs.started_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = await cursor.fetchall()

    return [dict(row) for row in rows]


async def get_pipeline_run(
    db_path: str | Path,
    *,
    job_id: str,
) -> dict[str, Any] | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                pipeline_runs.*,
                sessions.title AS session_title,
                sessions.source AS session_source
            FROM pipeline_runs
            LEFT JOIN sessions ON pipeline_runs.session_id = sessions.id
            WHERE pipeline_runs.job_id = ?
            """,
            (job_id,),
        )

        run_row = await cursor.fetchone()

        if run_row is None:
            return None

        cursor = await db.execute(
            """
            SELECT *
            FROM transcriptions
            WHERE pipeline_run_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (run_row["id"],),
        )

        transcription_row = await cursor.fetchone()

    result = dict(run_row)

    if transcription_row is not None:
        transcription = dict(transcription_row)
        transcription["notes"] = json.loads(transcription.get("notes_json") or "[]")
        result["transcription"] = transcription
    else:
        result["transcription"] = None

    result["metadata"] = json.loads(result.get("metadata_json") or "{}")

    return result


async def create_metric_record(
    db_path: str | Path,
    *,
    metric_name: str,
    metric_value: float | None = None,
    metric_json: dict[str, Any] | None = None,
    pipeline_run_id: str | None = None,
    metric_id: str | None = None,
) -> str:
    metric_id = metric_id or new_id("met")

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute(
            """
            INSERT INTO metrics (
                id,
                pipeline_run_id,
                metric_name,
                metric_value,
                metric_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                metric_id,
                pipeline_run_id,
                metric_name,
                metric_value,
                json.dumps(metric_json or {}, ensure_ascii=False),
            ),
        )
        await db.commit()

    return metric_id
