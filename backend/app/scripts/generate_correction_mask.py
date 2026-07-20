from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.database import get_pipeline_run
from app.pipeline.correction_mask import build_correction_mask


async def generate_correction_mask_for_run(
    *,
    db_path: str | Path,
    job_id: str,
    output: str | Path,
    confidence_threshold: float = 0.7,
    hvs_threshold: float = 0.6,
    allow_hvs_only_fallback: bool = True,
) -> dict:
    run = await get_pipeline_run(
        db_path,
        job_id=job_id,
    )

    if run is None:
        result = {
            "status": "error",
            "job_id": job_id,
            "error": f"Pipeline run not found: {job_id}",
        }
    else:
        transcription = run.get("transcription") or {}
        notes = transcription.get("notes") or []

        mask = build_correction_mask(
            notes,
            global_hvs_score=run.get("hvs_score"),
            confidence_threshold=confidence_threshold,
            hvs_threshold=hvs_threshold,
            allow_hvs_only_fallback=allow_hvs_only_fallback,
        )

        result = {
            "status": mask.status,
            "job_id": job_id,
            "pipeline_run_id": run.get("id"),
            "detected_key": run.get("detected_key"),
            "hvs_score": run.get("hvs_score"),
            "transcription_method": transcription.get("transcription_method"),
            "midi_path": transcription.get("midi_path") or run.get("midi_path"),
            **mask.to_dict(),
        }

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "status": result["status"],
        "job_id": job_id,
        "output": str(output_path),
        "note_count": result.get("note_count"),
        "selected_count": result.get("selected_count"),
        "error": result.get("error"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate correction mask candidates for a persisted pipeline run."
    )
    parser.add_argument("--db-path", default="data/app.sqlite3")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--confidence-threshold", type=float, default=0.7)
    parser.add_argument("--hvs-threshold", type=float, default=0.6)
    parser.add_argument(
        "--disable-hvs-only-fallback",
        action="store_true",
        help="Do not select notes when confidence is missing.",
    )

    args = parser.parse_args()

    result = asyncio.run(
        generate_correction_mask_for_run(
            db_path=args.db_path,
            job_id=args.job_id,
            output=args.output,
            confidence_threshold=args.confidence_threshold,
            hvs_threshold=args.hvs_threshold,
            allow_hvs_only_fallback=not args.disable_hvs_only_fallback,
        )
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
