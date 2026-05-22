from __future__ import annotations

import csv
import json
from pathlib import Path

from app.scripts.evaluate_midi_baseline import evaluate_midi_pair


def main() -> int:
    selection_path = Path("data/maestro/v3.0.0/selection/ci_pieces.csv")
    midi_root = Path("data/maestro/v3.0.0/maestro-v3.0.0")
    report_path = Path("artifacts/metrics/day9_maestro_ci_baseline_report.json")

    with selection_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    results = []

    for index, row in enumerate(rows, start=1):
        job_id = f"day8-maestro-ci-{index:02d}-e2e"

        reference_midi = midi_root / row["midi_filename"]
        estimated_midi = Path("artifacts/tracer") / job_id / "output.mid"

        print(f"\n=== Baseline CI {index}/{len(rows)} ===")
        print("Composer:", row["canonical_composer"])
        print("Title:", row["canonical_title"])
        print("Reference:", reference_midi)
        print("Estimated:", estimated_midi)

        if not reference_midi.exists():
            item = {
                "index": index,
                "job_id": job_id,
                "status": "error",
                "error": f"Reference MIDI not found: {reference_midi}",
            }
            print(json.dumps(item, indent=2, ensure_ascii=False))
            results.append(item)
            continue

        if not estimated_midi.exists():
            item = {
                "index": index,
                "job_id": job_id,
                "status": "error",
                "error": f"Estimated MIDI not found: {estimated_midi}",
            }
            print(json.dumps(item, indent=2, ensure_ascii=False))
            results.append(item)
            continue

        metrics = evaluate_midi_pair(
            reference_midi=reference_midi,
            estimated_midi=estimated_midi,
            onset_tolerance=0.05,
            offset_ratio=0.2,
        )

        item = {
            "index": index,
            "job_id": job_id,
            "composer": row["canonical_composer"],
            "title": row["canonical_title"],
            "duration": float(row["duration"]),
            "reference_midi": str(reference_midi),
            "estimated_midi": str(estimated_midi),
            **metrics,
        }

        print(json.dumps(item, indent=2, ensure_ascii=False))
        results.append(item)

    completed = [item for item in results if item.get("status") == "completed"]

    if completed:
        avg_precision = sum(item["precision"] for item in completed) / len(completed)
        avg_recall = sum(item["recall"] for item in completed) / len(completed)
        avg_f1 = sum(item["f1"] for item in completed) / len(completed)
        avg_overlap = sum(item["overlap"] for item in completed) / len(completed)
    else:
        avg_precision = avg_recall = avg_f1 = avg_overlap = 0.0

    report = {
        "status": "completed" if len(completed) == len(results) else "error",
        "count": len(results),
        "completed_count": len(completed),
        "averages": {
            "precision": round(avg_precision, 6),
            "recall": round(avg_recall, 6),
            "f1": round(avg_f1, 6),
            "overlap": round(avg_overlap, 6),
        },
        "results": results,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n=== BASELINE REPORT ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
