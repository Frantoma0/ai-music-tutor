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
