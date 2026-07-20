from __future__ import annotations

import json
import sqlite3

import pytest

from app.agent.practice_coach import (
    build_deterministic_plan,
    get_latest_plan,
    run_practice_coach,
)
from app.db.progress import init_progress_schema, save_practice_session


def _session(accuracy: int, weak_spots: list[dict], duration: float = 120.0) -> dict:
    return {
        "accuracy": accuracy,
        "duration_seconds": duration,
        "weak_spots_json": json.dumps(weak_spots),
    }


def test_plan_clusters_nearby_spots_into_one_section():
    spots = [
        {"start": 10.0 + i * 0.4, "end": 10.2 + i * 0.4, "hand": "right", "kind": "wrong"}
        for i in range(6)
    ]

    plan = build_deterministic_plan([_session(60, spots)], language="en")

    assert len(plan["sections"]) == 1

    section = plan["sections"][0]

    assert section["start"] < 10.0
    assert section["end"] > 12.2
    assert section["hand"] == "right"
    assert section["errors"] == 6


def test_plan_caps_sections_and_orders_them_by_time():
    spots = []

    for base in (10.0, 40.0, 70.0, 100.0):
        spots.extend(
            {"start": base + i * 0.3, "end": base + 0.2 + i * 0.3, "hand": "left", "kind": "miss"}
            for i in range(3)
        )

    plan = build_deterministic_plan([_session(60, spots)], language="en")

    assert len(plan["sections"]) == 3

    starts = [section["start"] for section in plan["sections"]]

    assert starts == sorted(starts)


def test_plan_slows_tempo_where_errors_are_dense():
    dense = [
        {"start": 20.0 + i * 0.2, "end": 20.1 + i * 0.2, "hand": "right", "kind": "wrong"}
        for i in range(10)
    ]

    plan = build_deterministic_plan([_session(50, dense)], language="en")

    assert plan["sections"][0]["tempo"] < 0.8
    assert plan["sections"][0]["tempo"] >= 0.5


def test_low_accuracy_recommends_beginner_view():
    plan = build_deterministic_plan([_session(30, [])], language="en")

    assert plan["recommended_view"] == "beginner"

    plan = build_deterministic_plan([_session(60, [])], language="en")

    assert plan["recommended_view"] == "practice"

    plan = build_deterministic_plan([_session(90, [])], language="en")

    assert plan["recommended_view"] is None


def test_plan_uses_requested_language_for_tips():
    spots = [{"start": 5.0, "end": 5.2, "hand": "right", "kind": "wrong"}]

    plan = build_deterministic_plan([_session(60, spots)], language="bg")

    assert plan["language"] == "bg"
    assert len(plan["sections"]) == 1
    assert plan["sections"][0]["tip"]


@pytest.mark.asyncio
async def test_run_practice_coach_persists_and_reloads_plan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # coach_trace.json lands in the temp dir
    db_path = tmp_path / "coach.sqlite3"

    with sqlite3.connect(db_path) as connection:
        connection.execute("""
            CREATE TABLE practice_plans (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                plan_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

    await init_progress_schema(db_path)

    spots = [
        {"start": 12.0 + i * 0.4, "end": 12.3 + i * 0.4, "hand": "right", "kind": "wrong"}
        for i in range(5)
    ]

    await save_practice_session(
        "job-coach",
        hits=20,
        missed=3,
        wrong=5,
        accuracy=62,
        stars=1,
        note_view="practice",
        duration_seconds=100,
        weak_spots=spots,
        db_path=db_path,
    )

    result = await run_practice_coach("job-coach", language="en", use_llm=False, db_path=db_path)

    assert result["status"] == "ok"
    assert result["llm"]["status"] == "skipped"
    assert len(result["plan"]["sections"]) == 1

    stored = await get_latest_plan("job-coach", db_path=db_path)

    assert stored is not None
    assert stored["plan"]["sections"] == result["plan"]["sections"]


@pytest.mark.asyncio
async def test_run_practice_coach_without_sessions_reports_no_data(tmp_path):
    db_path = tmp_path / "coach.sqlite3"
    await init_progress_schema(db_path)

    result = await run_practice_coach("job-empty", language="en", use_llm=False, db_path=db_path)

    assert result["status"] == "no_data"
    assert result["plan"] is None
