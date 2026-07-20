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


def build_pitch_correction_prompt(candidates: list[dict[str, Any]]) -> str:
    compact_candidates = [_compact_pitch_candidate(item) for item in candidates]

    return (
        "You are a conservative music transcription correction assistant.\n"
        "Return ONLY valid JSON. Do not use markdown.\n"
        "Do not include explanations outside JSON.\n"
        "\n"
        "Piece context:\n"
        "- detected_key: F major\n"
        "- In F major, Bb/A# is diatonic, while B natural is chromatic.\n"
        "- hvs_score 0.6 means the note is harmonically suspicious or chromatic.\n"
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
        "- Use propose_pitch_shift when a low-confidence chromatic note has a nearby musically plausible pitch.\n"
        "- Only choose proposed_pitch values from the candidate safe_pitch_options list.\n"
        "- Do not propose a pitch outside safe_pitch_options.\n"
        "- If unsure between two possible pitches, choose flag_for_review.\n"
        "- If the current pitch is likely correct, choose keep.\n"
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
) -> dict[str, Any]:
    prompt = build_pitch_correction_prompt(candidates)

    response = httpx.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=180,
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


def run_qwen_pitch_correction_chunks(
    *,
    base_url: str,
    model: str,
    mask_path: str,
    output: str,
    candidate_limit: int = 43,
    chunk_size: int = 5,
) -> dict[str, Any]:
    candidates = _load_selected_candidates(mask_path, candidate_limit)
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
            errors.append(message)

            chunk_results.append(
                {
                    "chunk_index": chunk_index,
                    "status": "error",
                    "candidate_count": len(chunk_candidates),
                    "candidate_ids": [
                        _compact_candidate(item)["candidate_id"] for item in chunk_candidates
                    ],
                    "validated": None,
                    "locked": None,
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
        "candidate_count": len(candidates),
        "chunk_size": chunk_size,
        "chunk_count": len(candidate_chunks),
        "completed_chunk_count": sum(1 for item in chunk_results if item["status"] == "completed"),
        "failed_chunk_count": sum(1 for item in chunk_results if item["status"] == "error"),
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

    args = parser.parse_args()

    result = run_qwen_pitch_correction_chunks(
        base_url=args.base_url,
        model=args.model,
        mask_path=args.mask_path,
        output=args.output,
        candidate_limit=args.candidate_limit,
        chunk_size=args.chunk_size,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
