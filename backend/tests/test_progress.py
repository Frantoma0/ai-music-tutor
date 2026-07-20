from __future__ import annotations

import pytest

from app.db.progress import (
    init_progress_schema,
    list_sessions_for_job,
    progress_summary,
    save_position,
    save_practice_session,
)


@pytest.mark.asyncio
async def test_progress_schema_creates_tables(tmp_path):
    db_path = tmp_path / "progress.sqlite3"

    await init_progress_schema(db_path)

    sessions = await list_sessions_for_job("missing-job", db_path=db_path)
    summary = await progress_summary(db_path=db_path)

    assert sessions == []
    assert summary == {}


@pytest.mark.asyncio
async def test_save_session_updates_summary_bests(tmp_path):
    db_path = tmp_path / "progress.sqlite3"
    await init_progress_schema(db_path)

    await save_practice_session(
        "job-a",
        hits=10,
        missed=5,
        wrong=3,
        accuracy=55,
        stars=1,
        mode="flow",
        note_view="practice",
        duration_seconds=90,
        db_path=db_path,
    )
    await save_practice_session(
        "job-a",
        hits=16,
        missed=2,
        wrong=1,
        accuracy=84,
        stars=3,
        mode="wait",
        note_view="beginner",
        db_path=db_path,
    )

    summary = await progress_summary(db_path=db_path)

    assert summary["job-a"]["attempts"] == 2
    assert summary["job-a"]["best_accuracy"] == 84
    assert summary["job-a"]["best_stars"] == 3
    assert summary["job-a"]["last_note_view"] == "beginner"

    sessions = await list_sessions_for_job("job-a", db_path=db_path)

    assert len(sessions) == 2
    assert sessions[0]["accuracy"] == 84  # newest first


@pytest.mark.asyncio
async def test_save_position_upserts_without_touching_bests(tmp_path):
    db_path = tmp_path / "progress.sqlite3"
    await init_progress_schema(db_path)

    await save_practice_session(
        "job-b",
        hits=8,
        missed=1,
        wrong=1,
        accuracy=80,
        stars=2,
        db_path=db_path,
    )
    await save_position("job-b", 42.5, "practice", db_path=db_path)

    summary = await progress_summary(db_path=db_path)

    assert summary["job-b"]["last_position_seconds"] == 42.5
    assert summary["job-b"]["best_accuracy"] == 80
    assert summary["job-b"]["attempts"] == 1


@pytest.mark.asyncio
async def test_weak_spots_are_persisted_with_session(tmp_path):
    db_path = tmp_path / "progress.sqlite3"
    await init_progress_schema(db_path)

    spots = [{"start": 1.0, "end": 1.2, "hand": "right", "kind": "miss"}]

    await save_practice_session(
        "job-c",
        hits=1,
        missed=1,
        wrong=0,
        accuracy=50,
        stars=0,
        weak_spots=spots,
        db_path=db_path,
    )

    sessions = await list_sessions_for_job("job-c", db_path=db_path)

    assert sessions[0]["weak_spots_json"] is not None
    assert "miss" in sessions[0]["weak_spots_json"]
