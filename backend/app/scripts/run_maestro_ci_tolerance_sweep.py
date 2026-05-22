from __future__ import annotations

import csv
import json
from pathlib import Path

from app.scripts.evaluate_midi_baseline import evaluate_midi_pair


def main() -> int:
    selection_path = Path("data/maestro/v3.0.0/selection/ci_pieces.csv")
    midi_root = Path("data/maestro/v3.0.0/maestro-v3.0.0")
    job_prefix = "day9-maestro-ci-persisted"
    output_path = Path("artifacts/metrics/day10_5_tolerance_sweep_report.json")

    onset_tolerances = [0.05, 0.10, 0.20]
    offset_ratios = [0.2]

    with selection_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    results = []

    for onset_tolerance in onset_tolerances:
        for offset_ratio in offset_ratios:
            run_results = []

            for index, row in enumerate(rows, start=1):
                job_id = f"{job_prefix}-{index:02d}-e2e"
                reference_midi = midi_root / row["midi_filename"]
                estimated_midi = Path("artifacts/tracer") / job_id / "output.mid"

                metrics = evaluate_midi_pair(
                    reference_midi=reference_midi,
                    estimated_midi=estimated_midi,
                    onset_tolerance=onset_tolerance,
                    offset_ratio=offset_ratio,
                )

                run_results.append({
                    "index": index,
                    "job_id": job_id,
                    "composer": row["canonical_composer"],
                    "title": row["canonical_title"],
                    **metrics,
                })

            completed = [item for item in run_results if item["status"] == "completed"]

            summary = {
                "onset_tolerance": onset_tolerance,
                "offset_ratio": offset_ratio,
                "completed_count": len(completed),
                "average_precision": round(sum(item["precision"] for item in completed) / len(completed), 6),
                "average_recall": round(sum(item["recall"] for item in completed) / len(completed), 6),
                "average_f1": round(sum(item["f1"] for item in completed) / len(completed), 6),
                "average_overlap": round(sum(item["overlap"] for item in completed) / len(completed), 6),
                "results": run_results,
            }

            results.append(summary)

    report = {
        "status": "completed",
        "job_prefix": job_prefix,
        "count": len(results),
        "sweeps": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "output": str(output_path),
        "summary": [
            {
                "onset_tolerance": item["onset_tolerance"],
                "offset_ratio": item["offset_ratio"],
                "average_f1": item["average_f1"],
                "average_precision": item["average_precision"],
                "average_recall": item["average_recall"],
                "average_overlap": item["average_overlap"],
            }
            for item in results
        ],
    }, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
