from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

from app.db.database import DEFAULT_DB_PATH, get_pipeline_run
from app.pipeline.correction_mask import build_correction_mask
from app.pipeline.harmony_analysis import analyze_notes_harmony, merge_hvs_into_notes
from app.pipeline.lesson_schema import LessonMeta, LessonNote, LessonResponse, LessonVersions


NOTE_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_pitch_name(pitch: int | None) -> str:
    if pitch is None:
        return "Unknown"

    octave = (int(pitch) // 12) - 1
    name = NOTE_NAMES_SHARP[int(pitch) % 12]
    return f"{name}{octave}"


def as_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def note_hand_from_c4_split(pitch: int | None) -> str:
    if pitch is None:
        return "unknown"

    return "left" if int(pitch) < 60 else "right"


def lesson_status_from_run(status: str | None) -> str:
    normalized = (status or "").lower()

    if normalized in {"completed", "success"}:
        return "completed"

    if normalized in {"running", "processing", "started"}:
        return "running"

    if normalized in {"failed", "error"}:
        return "error"

    return "pending"


async def latest_correction_details_for_job(
    db_path: str | Path,
    *,
    job_id: str,
) -> dict[str, Any] | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM correction_runs
            WHERE job_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (job_id,),
        )
        run = await cursor.fetchone()

        if run is None:
            return None

        correction_run_id = run["id"]

        cursor = await db.execute(
            """
            SELECT *
            FROM correction_proposals
            WHERE correction_run_id = ?
            """,
            (correction_run_id,),
        )
        proposals = await cursor.fetchall()

        cursor = await db.execute(
            """
            SELECT *
            FROM correction_validations
            WHERE correction_run_id = ?
            """,
            (correction_run_id,),
        )
        validations = await cursor.fetchall()

    return {
        "run": dict(run),
        "proposals": [dict(row) for row in proposals],
        "validations": [dict(row) for row in validations],
    }


def load_json_list(value: str | None) -> list[Any]:
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []

    return parsed if isinstance(parsed, list) else []


def build_correction_maps(correction_details: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if correction_details is None:
        return {}

    proposals_by_candidate = {
        proposal.get("candidate_id"): proposal
        for proposal in correction_details.get("proposals", [])
        if proposal.get("candidate_id")
    }

    validations_by_candidate = {
        validation.get("candidate_id"): validation
        for validation in correction_details.get("validations", [])
        if validation.get("candidate_id")
    }

    result: dict[str, dict[str, Any]] = {}

    for candidate_id, proposal in proposals_by_candidate.items():
        result[candidate_id] = {
            "status": "proposed",
            "proposal": proposal,
            "validation": None,
        }

    for candidate_id, validation in validations_by_candidate.items():
        existing = result.setdefault(
            candidate_id,
            {
                "status": "proposed",
                "proposal": proposals_by_candidate.get(candidate_id),
                "validation": None,
            },
        )

        existing["validation"] = validation
        existing["status"] = "approved" if validation.get("approved") else "rejected"

    return result


def correction_reason_for(
    proposal: dict[str, Any] | None,
    validation: dict[str, Any] | None,
) -> str | None:
    if proposal and proposal.get("reason"):
        return str(proposal["reason"])

    if validation:
        reasons = load_json_list(validation.get("reasons_json"))
        if reasons:
            return "; ".join(str(reason) for reason in reasons)

    return None


def build_lesson_notes(
    notes: list[dict[str, Any]],
    *,
    detected_key: str | None,
    global_hvs_score: float | None,
    correction_details: dict[str, Any] | None,
) -> tuple[list[LessonNote], int, int]:
    harmony = analyze_notes_harmony(notes, detected_key=detected_key)
    notes_with_hvs = merge_hvs_into_notes(notes, harmony)

    mask = build_correction_mask(
        notes_with_hvs,
        global_hvs_score=global_hvs_score,
        confidence_threshold=0.7,
        hvs_threshold=0.6,
    )

    selected_ids = {
        candidate.id
        for candidate in mask.candidates
        if candidate.selected and candidate.id is not None
    }

    correction_maps = build_correction_maps(correction_details)

    lesson_notes: list[LessonNote] = []

    for index, note in enumerate(notes_with_hvs):
        note_id = str(note.get("id") or f"n{index}")
        pitch = as_int(note.get("pitch"))
        correction = correction_maps.get(note_id, {})
        proposal = correction.get("proposal")
        validation = correction.get("validation")
        correction_status = correction.get("status", "none")

        display_pitch = pitch
        original_pitch = None

        if (
            correction_status == "approved"
            and proposal
            and proposal.get("proposed_pitch") is not None
            and proposal.get("original_pitch") is not None
            and int(proposal["proposed_pitch"]) != int(proposal["original_pitch"])
        ):
            original_pitch = int(proposal["original_pitch"])
            display_pitch = int(proposal["proposed_pitch"])

        duration = as_float(note.get("duration"))
        start = as_float(note.get("start")) or 0.0
        end = as_float(note.get("end")) or start

        if duration is None:
            duration = max(end - start, 0.0)

        lesson_notes.append(
            LessonNote(
                id=note_id,
                pitch=display_pitch if display_pitch is not None else 0,
                pitch_name=midi_pitch_name(display_pitch),
                start=start,
                end=end,
                duration=duration,
                velocity=as_int(note.get("velocity")) or 0,
                confidence=as_float(note.get("confidence")),
                hvs_score=as_float(note.get("hvs_score")) or 0.0,
                hvs_label=note.get("hvs_label") or "unknown_pitch",
                hvs_reason=note.get("hvs_reason") or "missing_hvs_reason",
                hand=note_hand_from_c4_split(display_pitch),
                in_correction_mask=note_id in selected_ids,
                correction_status=correction_status,
                original_pitch=original_pitch,
                correction_reason=correction_reason_for(proposal, validation),
            )
        )

    correction_count = sum(1 for note in lesson_notes if note.correction_status != "none")

    return lesson_notes, mask.selected_count, correction_count


async def prepare_lesson_for_job(
    job_id: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> LessonResponse | None:
    run = await get_pipeline_run(db_path, job_id=job_id)

    if run is None:
        return None

    transcription = run.get("transcription")

    if not transcription:
        return None

    notes = transcription.get("notes") or []
    metadata = run.get("metadata") or {}
    correction_details = await latest_correction_details_for_job(db_path, job_id=job_id)

    lesson_notes, masked_count, correction_count = build_lesson_notes(
        notes,
        detected_key=run.get("detected_key"),
        global_hvs_score=run.get("hvs_score"),
        correction_details=correction_details,
    )

    midi_path = transcription.get("midi_path") or run.get("midi_path")

    meta = LessonMeta(
        id=job_id,
        job_id=job_id,
        title=run.get("session_title"),
        detected_key=run.get("detected_key"),
        tempo_bpm=as_float(metadata.get("tempo_bpm") or metadata.get("tempo")),
        time_signature=metadata.get("time_signature") or metadata.get("time_sig"),
        duration_s=as_float(metadata.get("duration_s") or metadata.get("duration")),
        transcription_method=transcription.get("transcription_method"),
        status=lesson_status_from_run(run.get("status")),
    )

    versions = LessonVersions(
        raw_midi_url=f"/api/lessons/{job_id}/midi/raw" if midi_path else None,
        corrected_midi_url=None,
    )

    return LessonResponse(
        meta=meta,
        notes=lesson_notes,
        versions=versions,
        note_count=len(lesson_notes),
        masked_count=masked_count,
        correction_count=correction_count,
    )
