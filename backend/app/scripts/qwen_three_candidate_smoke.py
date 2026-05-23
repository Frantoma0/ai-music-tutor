from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx

from app.pipeline.llm_correction_batch import validate_correction_batch_json
from app.pipeline.llm_json import extract_first_json_object
from app.pipeline.llm_metadata_locking import lock_correction_batch_metadata


def _load_selected_candidates(mask_path: str | Path, limit: int) -> list[dict[str, Any]]:
    data = json.loads(Path(mask_path).read_text(encoding="utf-8"))

    candidates = data.get("candidates") or []
    selected = [item for item in candidates if item.get("selected")]

    return selected[:limit]


def _compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("id"),
        "pitch": candidate.get("pitch"),
        "pitch_name": candidate.get("pitch_name"),
        "start": candidate.get("start"),
        "end": candidate.get("end"),
        "confidence": candidate.get("confidence"),
        "hvs_score": candidate.get("hvs_score"),
        "reason": candidate.get("reason"),
    }


def build_prompt(candidates: list[dict[str, Any]]) -> str:
    compact_candidates = [_compact_candidate(item) for item in candidates]

    return (
        "You are a conservative music transcription correction assistant.\\n"
        "Return ONLY valid JSON. Do not use markdown.\\n"
        "For this smoke test, do NOT propose pitch shifts or timing edits.\\n"
        "For each candidate, choose only one action: keep or flag_for_review.\\n"
        "Return exactly this JSON shape:\\n"
        "{\\n"
        '  "status": "completed",\\n'
        '  "corrections": [\\n'
        "    {\\n"
        '      "candidate_id": "n_example",\\n'
        '      "action": "keep",\\n'
        '      "reason": "short reason",\\n'
        '      "confidence": 0.5,\\n'
        '      "hvs_score": 0.6\\n'
        "    }\\n"
        "  ]\\n"
        "}\\n"
        "Candidates:\\n"
        f"{json.dumps(compact_candidates, ensure_ascii=False, indent=2)}"
    )


def run_qwen_three_candidate_smoke(
    *,
    base_url: str,
    model: str,
    mask_path: str,
    output: str,
    candidate_limit: int = 3,
) -> dict[str, Any]:
    candidates = _load_selected_candidates(mask_path, candidate_limit)
    prompt = build_prompt(candidates)

    response = httpx.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
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

    result = {
        "status": "completed",
        "model": model,
        "mask_path": mask_path,
        "candidate_count": len(candidates),
        "candidates": [_compact_candidate(item) for item in candidates],
        "prompt": prompt,
        "raw_response": raw_response,
        "parsed": parsed,
        "validated": validated.to_dict(),
        "locked": locked,
        "error": None,
    }

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "status": "completed",
        "output": str(output_path),
        "candidate_count": len(candidates),
        "correction_count": validated.correction_count,
        "actions": [item.action for item in validated.corrections],
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Qwen smoke test on 3 selected mask candidates.")
    parser.add_argument("--base-url", default="http://host.docker.internal:11434")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--mask-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--candidate-limit", type=int, default=3)

    args = parser.parse_args()

    try:
        result = run_qwen_three_candidate_smoke(
            base_url=args.base_url,
            model=args.model,
            mask_path=args.mask_path,
            output=args.output,
            candidate_limit=args.candidate_limit,
        )
    except Exception as exc:
        result = {
            "status": "error",
            "output": args.output,
            "candidate_count": 0,
            "correction_count": 0,
            "actions": [],
            "error": f"{type(exc).__name__}: {exc}",
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
