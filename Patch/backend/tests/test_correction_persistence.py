from __future__ import annotations

import asyncio
import json

from app.db.correction_persistence import (
    get_correction_run,
    init_correction_schema,
    list_correction_runs,
    persist_correction_artifacts,
)


def test_init_correction_schema_creates_tables(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    async def run():
        await init_correction_schema(db_path)

        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name IN (
                    'correction_runs',
                    'correction_proposals',
                    'correction_validations'
                  )
                ORDER BY name
                """)
            rows = await cursor.fetchall()

        return [row[0] for row in rows]

    tables = asyncio.run(run())

    assert tables == [
        "correction_proposals",
        "correction_runs",
        "correction_validations",
    ]


def test_persist_correction_artifacts_and_read_back(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    mask_path = tmp_path / "mask.json"
    proposals_path = tmp_path / "proposals.json"
    validation_path = tmp_path / "validation.json"

    mask_path.write_text(
        json.dumps(
            {
                "job_id": "pytest-job",
                "pipeline_run_id": "run_test",
                "status": "completed",
                "note_count": 2,
                "candidate_count": 2,
                "selected_count": 1,
            }
        ),
        encoding="utf-8",
    )

    proposals_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "job_id": "pytest-job",
                "candidate_count": 2,
                "selected_candidate_count": 1,
                "proposal_count": 1,
                "midi_mutated": False,
                "proposals": [
                    {
                        "proposal_id": "prop_0000",
                        "candidate_id": "n1",
                        "action": "flag_for_review",
                        "original_pitch": 61,
                        "proposed_pitch": None,
                        "original_start": 1.0,
                        "proposed_start": None,
                        "original_end": 2.0,
                        "proposed_end": None,
                        "confidence": 0.5,
                        "hvs_score": 0.6,
                        "reason": "selected_mask_candidate_requires_review:low_confidence_high_hvs",
                        "status": "pending_validation",
                        "safety_notes": [
                            "placeholder_proposal_no_midi_mutation",
                            "requires_validation_before_any_edit",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    validation_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "job_id": "pytest-job",
                "proposal_count": 1,
                "approved_count": 1,
                "rejected_count": 0,
                "midi_mutation_allowed": False,
                "validations": [
                    {
                        "proposal_id": "prop_0000",
                        "candidate_id": "n1",
                        "action": "flag_for_review",
                        "validation_status": "approved_for_review",
                        "approved": True,
                        "reasons": [],
                        "safety_notes": ["safe_review_only_no_midi_mutation"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    async def run():
        persisted = await persist_correction_artifacts(
            db_path,
            mask_path=mask_path,
            proposals_path=proposals_path,
            validation_path=validation_path,
        )

        listed = await list_correction_runs(db_path)

        loaded = await get_correction_run(
            db_path,
            correction_run_id=persisted["correction_run_id"],
        )

        return persisted, listed, loaded

    persisted, listed, loaded = asyncio.run(run())

    assert persisted["status"] == "completed"
    assert persisted["job_id"] == "pytest-job"
    assert persisted["pipeline_run_id"] == "run_test"
    assert persisted["candidate_count"] == 2
    assert persisted["selected_count"] == 1
    assert persisted["proposal_count"] == 1
    assert persisted["approved_count"] == 1
    assert persisted["rejected_count"] == 0
    assert persisted["midi_mutation_allowed"] is False
    assert persisted["midi_mutated"] is False

    assert len(listed) == 1
    assert listed[0]["job_id"] == "pytest-job"

    assert loaded is not None
    assert loaded["job_id"] == "pytest-job"
    assert loaded["pipeline_run_id"] == "run_test"
    assert loaded["proposal_count"] == 1
    assert loaded["approved_count"] == 1
    assert loaded["rejected_count"] == 0

    assert len(loaded["proposals"]) == 1
    assert loaded["proposals"][0]["proposal_id"] == "prop_0000"
    assert loaded["proposals"][0]["candidate_id"] == "n1"
    assert loaded["proposals"][0]["action"] == "flag_for_review"
    assert "placeholder_proposal_no_midi_mutation" in loaded["proposals"][0]["safety_notes"]

    assert len(loaded["validations"]) == 1
    assert loaded["validations"][0]["proposal_id"] == "prop_0000"
    assert loaded["validations"][0]["approved"] is True
    assert loaded["validations"][0]["reasons"] == []


def test_list_correction_runs_filters_by_job_id(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    async def run():
        await init_correction_schema(db_path)

        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT INTO correction_runs (
                    id,
                    job_id,
                    status
                )
                VALUES (?, ?, ?)
                """,
                ("crun_1", "job-a", "completed"),
            )

            await db.execute(
                """
                INSERT INTO correction_runs (
                    id,
                    job_id,
                    status
                )
                VALUES (?, ?, ?)
                """,
                ("crun_2", "job-b", "completed"),
            )

            await db.commit()

        return await list_correction_runs(db_path, job_id="job-a")

    rows = asyncio.run(run())

    assert len(rows) == 1
    assert rows[0]["id"] == "crun_1"
    assert rows[0]["job_id"] == "job-a"


def test_get_correction_run_returns_none_for_missing_id(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    async def run():
        await init_correction_schema(db_path)
        return await get_correction_run(db_path, correction_run_id="missing")

    result = asyncio.run(run())

    assert result is None
