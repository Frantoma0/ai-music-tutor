from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import aiosqlite


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: str | None) -> Any:
    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _read_json_file(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


async def init_correction_schema(db_path: str | Path) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS correction_runs (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                pipeline_run_id TEXT,
                status TEXT NOT NULL,
                source_mask_path TEXT,
                source_proposals_path TEXT,
                source_validation_path TEXT,
                note_count INTEGER NOT NULL DEFAULT 0,
                candidate_count INTEGER NOT NULL DEFAULT 0,
                selected_count INTEGER NOT NULL DEFAULT 0,
                proposal_count INTEGER NOT NULL DEFAULT 0,
                approved_count INTEGER NOT NULL DEFAULT 0,
                rejected_count INTEGER NOT NULL DEFAULT 0,
                midi_mutation_allowed INTEGER NOT NULL DEFAULT 0,
                midi_mutated INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS correction_proposals (
                id TEXT PRIMARY KEY,
                correction_run_id TEXT NOT NULL,
                proposal_id TEXT,
                candidate_id TEXT,
                action TEXT,
                original_pitch INTEGER,
                proposed_pitch INTEGER,
                original_start REAL,
                proposed_start REAL,
                original_end REAL,
                proposed_end REAL,
                confidence REAL,
                hvs_score REAL,
                reason TEXT,
                status TEXT,
                safety_notes_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (correction_run_id)
                    REFERENCES correction_runs(id)
                    ON DELETE CASCADE
            )
            """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS correction_validations (
                id TEXT PRIMARY KEY,
                correction_run_id TEXT NOT NULL,
                proposal_id TEXT,
                candidate_id TEXT,
                action TEXT,
                validation_status TEXT,
                approved INTEGER NOT NULL DEFAULT 0,
                reasons_json TEXT,
                safety_notes_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (correction_run_id)
                    REFERENCES correction_runs(id)
                    ON DELETE CASCADE
            )
            """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_correction_runs_job_id
            ON correction_runs(job_id)
            """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_correction_runs_pipeline_run_id
            ON correction_runs(pipeline_run_id)
            """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_correction_proposals_run
            ON correction_proposals(correction_run_id)
            """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_correction_validations_run
            ON correction_validations(correction_run_id)
            """)

        await db.commit()


async def persist_correction_artifacts(
    db_path: str | Path,
    *,
    mask_path: str | Path,
    proposals_path: str | Path,
    validation_path: str | Path,
) -> dict[str, Any]:
    await init_correction_schema(db_path)

    mask_data = _read_json_file(mask_path)
    proposals_data = _read_json_file(proposals_path)
    validation_data = _read_json_file(validation_path)

    correction_run_id = _new_id("crun")

    job_id = (
        validation_data.get("job_id") or proposals_data.get("job_id") or mask_data.get("job_id")
    )

    pipeline_run_id = mask_data.get("pipeline_run_id")

    note_count = int(mask_data.get("note_count") or 0)
    candidate_count = int(mask_data.get("candidate_count") or note_count or 0)
    selected_count = int(
        mask_data.get("selected_count") or proposals_data.get("selected_candidate_count") or 0
    )
    proposal_count = int(
        proposals_data.get("proposal_count") or validation_data.get("proposal_count") or 0
    )
    approved_count = int(validation_data.get("approved_count") or 0)
    rejected_count = int(validation_data.get("rejected_count") or 0)
    midi_mutation_allowed = bool(validation_data.get("midi_mutation_allowed"))
    midi_mutated = bool(proposals_data.get("midi_mutated"))

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        await db.execute(
            """
            INSERT INTO correction_runs (
                id,
                job_id,
                pipeline_run_id,
                status,
                source_mask_path,
                source_proposals_path,
                source_validation_path,
                note_count,
                candidate_count,
                selected_count,
                proposal_count,
                approved_count,
                rejected_count,
                midi_mutation_allowed,
                midi_mutated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                correction_run_id,
                job_id,
                pipeline_run_id,
                validation_data.get("status")
                or proposals_data.get("status")
                or mask_data.get("status")
                or "completed",
                str(mask_path),
                str(proposals_path),
                str(validation_path),
                note_count,
                candidate_count,
                selected_count,
                proposal_count,
                approved_count,
                rejected_count,
                1 if midi_mutation_allowed else 0,
                1 if midi_mutated else 0,
            ),
        )

        for proposal in proposals_data.get("proposals") or []:
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
                    original_start,
                    proposed_start,
                    original_end,
                    proposed_end,
                    confidence,
                    hvs_score,
                    reason,
                    status,
                    safety_notes_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("cprop"),
                    correction_run_id,
                    proposal.get("proposal_id"),
                    proposal.get("candidate_id"),
                    proposal.get("action"),
                    proposal.get("original_pitch"),
                    proposal.get("proposed_pitch"),
                    proposal.get("original_start"),
                    proposal.get("proposed_start"),
                    proposal.get("original_end"),
                    proposal.get("proposed_end"),
                    proposal.get("confidence"),
                    proposal.get("hvs_score"),
                    proposal.get("reason"),
                    proposal.get("status"),
                    _dump_json(proposal.get("safety_notes") or []),
                ),
            )

        for validation in validation_data.get("validations") or []:
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
                    _new_id("cval"),
                    correction_run_id,
                    validation.get("proposal_id"),
                    validation.get("candidate_id"),
                    validation.get("action"),
                    validation.get("validation_status"),
                    1 if validation.get("approved") else 0,
                    _dump_json(validation.get("reasons") or []),
                    _dump_json(validation.get("safety_notes") or []),
                ),
            )

        await db.commit()

    return {
        "status": "completed",
        "correction_run_id": correction_run_id,
        "job_id": job_id,
        "pipeline_run_id": pipeline_run_id,
        "note_count": note_count,
        "candidate_count": candidate_count,
        "selected_count": selected_count,
        "proposal_count": proposal_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "midi_mutation_allowed": midi_mutation_allowed,
        "midi_mutated": midi_mutated,
    }


async def list_correction_runs(
    db_path: str | Path,
    *,
    job_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    await init_correction_schema(db_path)

    query = """
        SELECT
            id,
            job_id,
            pipeline_run_id,
            status,
            source_mask_path,
            source_proposals_path,
            source_validation_path,
            note_count,
            candidate_count,
            selected_count,
            proposal_count,
            approved_count,
            rejected_count,
            midi_mutation_allowed,
            midi_mutated,
            created_at
        FROM correction_runs
    """

    params: list[Any] = []

    if job_id:
        query += " WHERE job_id = ?"
        params.append(job_id)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "job_id": row[1],
            "pipeline_run_id": row[2],
            "status": row[3],
            "source_mask_path": row[4],
            "source_proposals_path": row[5],
            "source_validation_path": row[6],
            "note_count": row[7],
            "candidate_count": row[8],
            "selected_count": row[9],
            "proposal_count": row[10],
            "approved_count": row[11],
            "rejected_count": row[12],
            "midi_mutation_allowed": bool(row[13]),
            "midi_mutated": bool(row[14]),
            "created_at": row[15],
        }
        for row in rows
    ]


async def get_correction_run(
    db_path: str | Path,
    *,
    correction_run_id: str,
) -> dict[str, Any] | None:
    await init_correction_schema(db_path)

    async with aiosqlite.connect(db_path) as db:
        run_cursor = await db.execute(
            """
            SELECT
                id,
                job_id,
                pipeline_run_id,
                status,
                source_mask_path,
                source_proposals_path,
                source_validation_path,
                note_count,
                candidate_count,
                selected_count,
                proposal_count,
                approved_count,
                rejected_count,
                midi_mutation_allowed,
                midi_mutated,
                created_at
            FROM correction_runs
            WHERE id = ?
            """,
            (correction_run_id,),
        )

        run = await run_cursor.fetchone()

        if run is None:
            return None

        proposal_cursor = await db.execute(
            """
            SELECT
                proposal_id,
                candidate_id,
                action,
                original_pitch,
                proposed_pitch,
                original_start,
                proposed_start,
                original_end,
                proposed_end,
                confidence,
                hvs_score,
                reason,
                status,
                safety_notes_json
            FROM correction_proposals
            WHERE correction_run_id = ?
            ORDER BY created_at ASC
            """,
            (correction_run_id,),
        )

        proposal_rows = await proposal_cursor.fetchall()

        validation_cursor = await db.execute(
            """
            SELECT
                proposal_id,
                candidate_id,
                action,
                validation_status,
                approved,
                reasons_json,
                safety_notes_json
            FROM correction_validations
            WHERE correction_run_id = ?
            ORDER BY created_at ASC
            """,
            (correction_run_id,),
        )

        validation_rows = await validation_cursor.fetchall()

    return {
        "id": run[0],
        "job_id": run[1],
        "pipeline_run_id": run[2],
        "status": run[3],
        "source_mask_path": run[4],
        "source_proposals_path": run[5],
        "source_validation_path": run[6],
        "note_count": run[7],
        "candidate_count": run[8],
        "selected_count": run[9],
        "proposal_count": run[10],
        "approved_count": run[11],
        "rejected_count": run[12],
        "midi_mutation_allowed": bool(run[13]),
        "midi_mutated": bool(run[14]),
        "created_at": run[15],
        "proposals": [
            {
                "proposal_id": row[0],
                "candidate_id": row[1],
                "action": row[2],
                "original_pitch": row[3],
                "proposed_pitch": row[4],
                "original_start": row[5],
                "proposed_start": row[6],
                "original_end": row[7],
                "proposed_end": row[8],
                "confidence": row[9],
                "hvs_score": row[10],
                "reason": row[11],
                "status": row[12],
                "safety_notes": _load_json(row[13]) or [],
            }
            for row in proposal_rows
        ],
        "validations": [
            {
                "proposal_id": row[0],
                "candidate_id": row[1],
                "action": row[2],
                "validation_status": row[3],
                "approved": bool(row[4]),
                "reasons": _load_json(row[5]) or [],
                "safety_notes": _load_json(row[6]) or [],
            }
            for row in validation_rows
        ],
    }
