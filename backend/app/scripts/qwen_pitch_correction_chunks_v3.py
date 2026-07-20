from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx

from app.pipeline.llm_correction_batch import validate_correction_batch_json
from app.pipeline.llm_json import extract_first_json_object
from app.pipeline.llm_metadata_locking import lock_correction_batch_metadata
from app.pipeline.llm_pitch_safety import validate_locked_pitch_corrections
from app.scripts.qwen_candidate_chunks_smoke import _chunks
from app.scripts.qwen_three_candidate_smoke import (
    _compact_candidate,
    _load_selected_candidates,
)

PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _pitch_name(pitch: int) -> str:
    octave = pitch // 12 - 1
    return f"{PITCH_CLASS_NAMES[pitch % 12]}{octave}"


def _safe_pitch_options(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    pitch = candidate.get("pitch")

    if not isinstance(pitch, int):
        return []

    options: list[dict[str, Any]] = []

    for delta in [-2, -1, 1, 2]:
        proposed = pitch + delta

        if 21 <= proposed <= 108:
            options.append(
                {
                    "proposed_pitch": proposed,
                    "pitch_name": _pitch_name(proposed),
                    "semitone_delta": delta,
                }
            )

    return options


def _compact_pitch_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    compact = _compact_candidate(candidate)
    compact["safe_pitch_options"] = _safe_pitch_options(candidate)
    return compact


def _load_notes_context(notes_path: str | None) -> list[dict[str, Any]]:
    if not notes_path:
        return []

    path = Path(notes_path)

    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        notes = data.get("notes") or data.get("items") or []
    elif isinstance(data, list):
        notes = data
    else:
        notes = []

    normalized: list[dict[str, Any]] = []

    for index, note in enumerate(notes):
        pitch = note.get("pitch")
        start = note.get("start")
        end = note.get("end")

        if not isinstance(pitch, int):
            continue

        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue

        normalized.append(
            {
                "id": note.get("id") or f"note_{index}",
                "pitch": pitch,
                "pitch_name": note.get("pitch_name") or _pitch_name(pitch),
                "start": round(float(start), 6),
                "end": round(float(end), 6),
                "confidence": note.get("confidence"),
            }
        )

    return sorted(normalized, key=lambda item: (item["start"], item["pitch"]))


def _local_note_context(
    *,
    candidate: dict[str, Any],
    notes: list[dict[str, Any]],
    context_window: float,
) -> dict[str, Any]:
    candidate_start = candidate.get("start")

    if not isinstance(candidate_start, (int, float)):
        return {
            "previous_notes": [],
            "next_notes": [],
            "simultaneous_or_overlapping_notes": [],
        }

    start = float(candidate_start)

    previous_notes = []
    next_notes = []
    overlapping_notes = []

    for note in notes:
        note_start = float(note["start"])
        note_end = float(note["end"])

        if note.get("id") == candidate.get("id"):
            continue

        if note_end <= start and start - note_end <= context_window:
            previous_notes.append(note)

        elif note_start >= start and note_start - start <= context_window:
            next_notes.append(note)

        elif note_start <= start <= note_end:
            overlapping_notes.append(note)

    previous_notes = sorted(
        previous_notes,
        key=lambda item: abs(start - float(item["end"])),
    )[:2]

    next_notes = sorted(
        next_notes,
        key=lambda item: abs(float(item["start"]) - start),
    )[:2]

    overlapping_notes = sorted(
        overlapping_notes,
        key=lambda item: (item["start"], item["pitch"]),
    )[:2]

    return {
        "previous_notes": previous_notes,
        "next_notes": next_notes,
        "simultaneous_or_overlapping_notes": overlapping_notes,
    }


def _compact_pitch_candidate_with_context(
    candidate: dict[str, Any],
    *,
    notes: list[dict[str, Any]],
    context_window: float,
) -> dict[str, Any]:
    compact = _compact_pitch_candidate(candidate)

    compact["local_context"] = _local_note_context(
        candidate=candidate,
        notes=notes,
        context_window=context_window,
    )

    return compact


def build_pitch_correction_prompt(
    candidates: list[dict[str, Any]],
    *,
    notes: list[dict[str, Any]] | None = None,
    context_window: float = 0.35,
) -> str:
    notes = notes or []

    compact_candidates = [
        _compact_pitch_candidate_with_context(
            item,
            notes=notes,
            context_window=context_window,
        )
        for item in candidates
    ]

    return (
        "You are a conservative music transcription correction assistant.\n"
        "Return ONLY valid JSON. Do not use markdown.\n"
        "Do not include explanations outside JSON.\n"
        "\n"
        "Piece context:\n"
        "- detected_key: F major\n"
        "- Chromatic notes can be intentional in real classical music.\n"
        "- Do not change a note only because it is chromatic against the detected key.\n"
        "- hvs_score 0.6 means suspicious, not automatically wrong.\n"
        "\n"
        "You must return exactly one correction object for every input candidate_id.\n"
        "Never invent candidate_id values.\n"
        "Use only candidate_id values from the provided candidates.\n"
        "\n"
        "Allowed actions:\n"
        "- keep\n"
        "- flag_for_review\n"
        "- propose_pitch_shift\n"
        "\n"
        "Do NOT propose timing edits.\n"
        "Do NOT include original_pitch, original_start, or original_end in the output.\n"
        "The system owns original metadata.\n"
        "\n"
        "Pitch correction rules:\n"
        "- Chromatic notes may be intentional.\n"
        "- Do not shift only to make a note diatonic.\n"
        "- Prefer keep when local_context supports the current pitch.\n"
        "- Use propose_pitch_shift only with strong local_context support.\n"
        "- Only choose proposed_pitch from safe_pitch_options.\n"
        "- If unsure, choose flag_for_review.\n"
        "\n"
        "Return exactly this JSON shape:\n"
        "{\n"
        '  "status": "completed",\n'
        '  "corrections": [\n'
        "    {\n"
        '      "candidate_id": "n_example",\n'
        '      "action": "keep",\n'
        '      "reason": "short reason"\n'
        "    },\n"
        "    {\n"
        '      "candidate_id": "n_example_2",\n'
        '      "action": "propose_pitch_shift",\n'
        '      "proposed_pitch": 60,\n'
        '      "reason": "short reason"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "\n"
        "Candidates:\n"
        f"{json.dumps(compact_candidates, ensure_ascii=False, indent=2)}"
    )


def _call_qwen_pitch(
    *,
    base_url: str,
    model: str,
    candidates: list[dict[str, Any]],
    notes: list[dict[str, Any]] | None = None,
    context_window: float = 0.35,
) -> dict[str, Any]:
    prompt = build_pitch_correction_prompt(
        candidates,
        notes=notes,
        context_window=context_window,
    )

    response = httpx.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=300,
    )

    response.raise_for_status()

    ollama_data = response.json()
    raw_response = ollama_data.get("response") or ""

    parsed = extract_first_json_object(raw_response)
    validated = validate_correction_batch_json(parsed)
    locked = lock_correction_batch_metadata(
        validated,
        candidates=candidates,
    )

    return {
        "prompt": prompt,
        "raw_response": raw_response,
        "parsed": parsed,
        "validated": validated.to_dict(),
        "locked": locked,
    }


def _fallback_locked_corrections(
    candidates: list[dict[str, Any]],
    *,
    reason: str,
) -> list[dict[str, Any]]:
    fallback = []

    for candidate in candidates:
        pitch = candidate.get("pitch")

        fallback.append(
            {
                "candidate_id": candidate.get("id"),
                "action": "flag_for_review",
                "reason": reason,
                "original_pitch": pitch,
                "proposed_pitch": None,
                "original_start": candidate.get("start"),
                "proposed_start": None,
                "original_end": candidate.get("end"),
                "proposed_end": None,
                "pitch_name": candidate.get("pitch_name") or _pitch_name(int(pitch)),
                "confidence": candidate.get("confidence"),
                "hvs_score": candidate.get("hvs_score"),
                "metadata_source": "system_candidate_locked",
            }
        )

    return fallback


def run_qwen_pitch_correction_chunks(
    *,
    base_url: str,
    model: str,
    mask_path: str,
    output: str,
    candidate_limit: int = 43,
    chunk_size: int = 5,
    notes_path: str | None = None,
    context_window: float = 0.35,
) -> dict[str, Any]:
    candidates = _load_selected_candidates(mask_path, candidate_limit)
    notes = _load_notes_context(notes_path)
    candidate_chunks = _chunks(candidates, chunk_size)

    chunk_results: list[dict[str, Any]] = []
    merged_locked_corrections: list[dict[str, Any]] = []
    errors: list[str] = []

    for chunk_index, chunk_candidates in enumerate(candidate_chunks, start=1):
        try:
            chunk_result = _call_qwen_pitch(
                base_url=base_url,
                model=model,
                candidates=chunk_candidates,
                notes=notes,
                context_window=context_window,
            )

            locked = chunk_result["locked"]
            merged_locked_corrections.extend(locked["corrections"])

            chunk_results.append(
                {
                    "chunk_index": chunk_index,
                    "status": "completed",
                    "candidate_count": len(chunk_candidates),
                    "candidate_ids": [
                        _compact_candidate(item)["candidate_id"] for item in chunk_candidates
                    ],
                    "validated": chunk_result["validated"],
                    "locked": chunk_result["locked"],
                    "raw_response": chunk_result["raw_response"],
                    "error": None,
                }
            )

        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"

            fallback_corrections = _fallback_locked_corrections(
                chunk_candidates,
                reason="llm_invalid_output_fallback",
            )

            merged_locked_corrections.extend(fallback_corrections)

            fallback_locked = {
                "status": "completed",
                "metadata_locked": True,
                "correction_count": len(fallback_corrections),
                "corrections": fallback_corrections,
                "fallback_reason": message,
            }

            chunk_results.append(
                {
                    "chunk_index": chunk_index,
                    "status": "fallback",
                    "candidate_count": len(chunk_candidates),
                    "candidate_ids": [
                        _compact_candidate(item)["candidate_id"] for item in chunk_candidates
                    ],
                    "validated": None,
                    "locked": fallback_locked,
                    "raw_response": None,
                    "error": message,
                }
            )

    expected_candidate_ids = [_compact_candidate(item)["candidate_id"] for item in candidates]

    locked_candidate_ids = [item["candidate_id"] for item in merged_locked_corrections]

    missing_candidate_ids = [
        candidate_id
        for candidate_id in expected_candidate_ids
        if candidate_id not in locked_candidate_ids
    ]

    duplicate_candidate_ids = sorted(
        {
            candidate_id
            for candidate_id in locked_candidate_ids
            if locked_candidate_ids.count(candidate_id) > 1
        }
    )

    coverage_ok = (
        len(missing_candidate_ids) == 0
        and len(duplicate_candidate_ids) == 0
        and len(locked_candidate_ids) == len(expected_candidate_ids)
    )

    if not coverage_ok:
        errors.append(
            "Correction coverage mismatch: "
            f"expected={len(expected_candidate_ids)}, "
            f"actual={len(locked_candidate_ids)}, "
            f"missing={missing_candidate_ids}, "
            f"duplicates={duplicate_candidate_ids}"
        )

    locked_batch = {
        "status": "completed" if coverage_ok and not errors else "partial",
        "metadata_locked": True,
        "correction_count": len(merged_locked_corrections),
        "corrections": merged_locked_corrections,
    }

    pitch_safety = validate_locked_pitch_corrections(locked_batch)

    status = "completed" if not errors else "error"

    result = {
        "status": status,
        "model": model,
        "mask_path": mask_path,
        "notes_path": notes_path,
        "context_window": context_window,
        "note_context_count": len(notes),
        "candidate_count": len(candidates),
        "chunk_size": chunk_size,
        "chunk_count": len(candidate_chunks),
        "completed_chunk_count": sum(1 for item in chunk_results if item["status"] == "completed"),
        "failed_chunk_count": sum(1 for item in chunk_results if item["status"] == "error"),
        "fallback_chunk_count": sum(1 for item in chunk_results if item["status"] == "fallback"),
        "coverage": {
            "ok": coverage_ok,
            "expected_candidate_count": len(expected_candidate_ids),
            "locked_candidate_count": len(locked_candidate_ids),
            "missing_candidate_ids": missing_candidate_ids,
            "duplicate_candidate_ids": duplicate_candidate_ids,
        },
        "locked": locked_batch,
        "pitch_safety": pitch_safety,
        "chunks": chunk_results,
        "errors": errors,
    }

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "status": status,
        "output": str(output_path),
        "candidate_count": len(candidates),
        "chunk_size": chunk_size,
        "chunk_count": len(candidate_chunks),
        "completed_chunk_count": result["completed_chunk_count"],
        "failed_chunk_count": result["failed_chunk_count"],
        "locked_correction_count": len(merged_locked_corrections),
        "coverage_ok": coverage_ok,
        "action_distribution": pitch_safety["action_distribution"],
        "approved_pitch_shift_count": pitch_safety["approved_pitch_shift_count"],
        "rejected_pitch_shift_count": pitch_safety["rejected_pitch_shift_count"],
        "correction_acceptance_rate": pitch_safety["correction_acceptance_rate"],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Qwen pitch correction on selected candidates in chunks."
    )
    parser.add_argument("--base-url", default="http://host.docker.internal:11434")
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--mask-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--candidate-limit", type=int, default=43)
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--notes-path", default=None)
    parser.add_argument("--context-window", type=float, default=0.35)

    args = parser.parse_args()

    result = run_qwen_pitch_correction_chunks(
        base_url=args.base_url,
        model=args.model,
        mask_path=args.mask_path,
        output=args.output,
        candidate_limit=args.candidate_limit,
        chunk_size=args.chunk_size,
        notes_path=args.notes_path,
        context_window=args.context_window,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
