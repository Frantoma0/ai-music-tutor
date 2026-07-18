"""
Per-lesson practice progress and sessions.

Matches the tables declared in schema.sql:

    practice_sessions – one row per finished practice run (the results card)
    lesson_progress   – one summary row per lesson: best scores, attempt
                        count, and the last playback position for resume.
"""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .database import DEFAULT_DB_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_progress_schema(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    def _init() -> None:
        with sqlite3.connect(str(db_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS lesson_progress (
                    job_id TEXT PRIMARY KEY,
                    last_position_seconds REAL NOT NULL DEFAULT 0,
                    best_accuracy INTEGER,
                    best_stars INTEGER NOT NULL DEFAULT 0,
                    total_attempts INTEGER NOT NULL DEFAULT 0,
                    last_note_view TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS practice_sessions (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    mode TEXT,
                    note_view TEXT,
                    hits INTEGER NOT NULL DEFAULT 0,
                    missed INTEGER NOT NULL DEFAULT 0,
                    wrong INTEGER NOT NULL DEFAULT 0,
                    accuracy INTEGER,
                    stars INTEGER NOT NULL DEFAULT 0,
                    duration_seconds REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_practice_sessions_job
                ON practice_sessions (job_id, created_at);
                """
            )
            connection.commit()

    await asyncio.to_thread(_init)


async def save_practice_session(
    job_id: str,
    hits: int,
    missed: int,
    wrong: int,
    accuracy: int,
    stars: int,
    mode: str | None = None,
    note_view: str | None = None,
    duration_seconds: float | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    record = {
        "id": f"ps_{uuid.uuid4().hex[:12]}",
        "job_id": job_id,
        "mode": mode,
        "note_view": note_view,
        "hits": int(hits),
        "missed": int(missed),
        "wrong": int(wrong),
        "accuracy": int(accuracy),
        "stars": int(stars),
        "duration_seconds": duration_seconds,
        "created_at": _now_iso(),
    }

    def _write() -> None:
        with sqlite3.connect(str(db_path)) as connection:
            connection.execute(
                """
                INSERT INTO practice_sessions (
                    id, job_id, mode, note_view, hits, missed, wrong,
                    accuracy, stars, duration_seconds, created_at
                ) VALUES (
                    :id, :job_id, :mode, :note_view, :hits, :missed, :wrong,
                    :accuracy, :stars, :duration_seconds, :created_at
                )
                """,
                record,
            )

            connection.execute(
                """
                INSERT INTO lesson_progress (
                    job_id, best_accuracy, best_stars, total_attempts,
                    last_note_view, updated_at
                ) VALUES (:job_id, :accuracy, :stars, 1, :note_view, :created_at)
                ON CONFLICT(job_id) DO UPDATE SET
                    best_accuracy = MAX(COALESCE(best_accuracy, 0), :accuracy),
                    best_stars = MAX(best_stars, :stars),
                    total_attempts = total_attempts + 1,
                    last_note_view = COALESCE(:note_view, last_note_view),
                    updated_at = :created_at
                """,
                record,
            )
            connection.commit()

    await asyncio.to_thread(_write)

    return record


async def save_position(
    job_id: str,
    position_seconds: float,
    note_view: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    def _write() -> None:
        with sqlite3.connect(str(db_path)) as connection:
            connection.execute(
                """
                INSERT INTO lesson_progress (
                    job_id, last_position_seconds, last_note_view, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    last_position_seconds = excluded.last_position_seconds,
                    last_note_view = COALESCE(excluded.last_note_view, last_note_view),
                    updated_at = excluded.updated_at
                """,
                (job_id, float(position_seconds), note_view, _now_iso()),
            )
            connection.commit()

    await asyncio.to_thread(_write)


async def list_sessions_for_job(
    job_id: str,
    limit: int = 50,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    def _query() -> list[dict[str, Any]]:
        with sqlite3.connect(str(db_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT * FROM practice_sessions
                WHERE job_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()

            return [dict(row) for row in rows]

    return await asyncio.to_thread(_query)


async def progress_summary(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, dict[str, Any]]:
    def _query() -> dict[str, dict[str, Any]]:
        with sqlite3.connect(str(db_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT * FROM lesson_progress").fetchall()

            return {
                row["job_id"]: {
                    "attempts": row["total_attempts"],
                    "best_accuracy": row["best_accuracy"],
                    "best_stars": row["best_stars"],
                    "last_position_seconds": row["last_position_seconds"],
                    "last_note_view": row["last_note_view"],
                    "last_played": row["updated_at"],
                }
                for row in rows
            }

    return await asyncio.to_thread(_query)
