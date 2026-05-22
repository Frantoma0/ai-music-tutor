from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.database import get_pipeline_run
from app.pipeline.harmony_analysis import analyze_notes_harmony, merge_hvs_into_notes


async def analyze_harmony_for_run(
    *,
    db_path: str | Path,
    job_id: str,
    output: str | Path,
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

        harmony = analyze_notes_harmony(
            notes,
            detected_key=run.get("detected_key"),
        )

        notes_with_hvs = merge_hvs_into_notes(notes, harmony)

        result = {
            "status": harmony.status,
            "job_id": job_id,
            "pipeline_run_id": run.get("id"),
            "detected_key": run.get("detected_key"),
            "global_hvs_score": run.get("hvs_score"),
            "transcription_method": transcription.get("transcription_method"),
            "midi_path": transcription.get("midi_path") or run.get("midi_path"),
            "note_count": harmony.note_count,
            "harmony": harmony.to_dict(),
            "notes": notes_with_hvs,
            "error": harmony.error,
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
        "error": result.get("error"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze per-note harmony/HVS for a persisted pipeline run.")
    parser.add_argument("--db-path", default="data/app.sqlite3")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = asyncio.run(
        analyze_harmony_for_run(
            db_path=args.db_path,
            job_id=args.job_id,
            output=args.output,
        )
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
