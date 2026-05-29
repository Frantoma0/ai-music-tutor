from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, median
from typing import Any


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def local_features(note: dict[str, Any], notes: list[dict[str, Any]], window: float) -> dict[str, Any]:
    start = note["start"]
    pitch = note["pitch"]

    nearby = [
        other for other in notes
        if other["id"] != note["id"]
        and abs(other["start"] - start) <= window
    ]

    overlapping = [
        other for other in notes
        if other["id"] != note["id"]
        and other["start"] <= start <= other["end"]
    ]

    before = [
        other for other in notes
        if other["end"] <= start
    ]

    after = [
        other for other in notes
        if other["start"] >= start
        and other["id"] != note["id"]
    ]

    prev_note = max(before, key=lambda x: x["end"], default=None)
    next_note = min(after, key=lambda x: x["start"], default=None)

    prev_interval = None if prev_note is None else pitch - prev_note["pitch"]
    next_interval = None if next_note is None else next_note["pitch"] - pitch

    return {
        "nearby_count": len(nearby),
        "overlap_count": len(overlapping),
        "prev_interval": prev_interval,
        "next_interval": next_interval,
        "abs_prev_interval": None if prev_interval is None else abs(prev_interval),
        "abs_next_interval": None if next_interval is None else abs(next_interval),
    }


def safe_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "min": None, "max": None}

    return {
        "mean": mean(values),
        "median": median(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes-path", required=True)
    parser.add_argument("--mask-path", required=True)
    parser.add_argument("--correctable-path", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--window", type=float, default=0.25)

    args = parser.parse_args()

    notes = load_json(args.notes_path)
    mask = load_json(args.mask_path)
    correctable = load_json(args.correctable_path)

    candidates_by_id = {
        item["id"]: item
        for item in mask["candidates"]
    }

    bucket_by_id = {
        item["candidate_id"]: item["bucket"]
        for item in correctable.get("selected_items", [])
    }

    rows = []

    for note in notes:
        candidate = candidates_by_id.get(note["id"], {})
        features = local_features(note, notes, args.window)

        confidence = note.get("confidence")
        duration = note.get("duration")
        overlap_count = features["overlap_count"]
        abs_prev_interval = features["abs_prev_interval"]

        rule_conf_lt_050 = confidence is not None and confidence < 0.50
        rule_duration_gt_019 = duration is not None and duration > 0.19
        rule_overlap_ge_4 = overlap_count >= 4
        rule_abs_prev_ge_12 = abs_prev_interval is not None and abs_prev_interval >= 12

        rule_conf_and_overlap = rule_conf_lt_050 and rule_overlap_ge_4
        three_signal_rule = (
            rule_conf_lt_050
            and rule_duration_gt_019
            and (rule_overlap_ge_4 or rule_abs_prev_ge_12)
        )

        rows.append({
            "id": note["id"],
            "pitch": note["pitch"],
            "pitch_name": note.get("pitch_name"),
            "start": note["start"],
            "end": note["end"],
            "duration": duration,
            "velocity": note.get("velocity"),
            "confidence": confidence,
            "hvs_score": candidate.get("hvs_score"),
            "selected": bool(candidate.get("selected", False)),
            "mask_reason": candidate.get("reason"),
            "selected_bucket": bucket_by_id.get(note["id"], "not_selected_or_unlabeled"),
            **features,
            "rule_conf_lt_050": rule_conf_lt_050,
            "rule_duration_gt_019": rule_duration_gt_019,
            "rule_overlap_ge_4": rule_overlap_ge_4,
            "rule_abs_prev_ge_12": rule_abs_prev_ge_12,
            "rule_conf_and_overlap": rule_conf_and_overlap,
            "three_signal_rule": three_signal_rule,
        })

    summary: dict[str, Any] = {
        "status": "completed",
        "note_count": len(rows),
        "selected_count": sum(1 for row in rows if row["selected"]),
        "rule_counts": {
            "rule_conf_lt_050": sum(1 for row in rows if row["rule_conf_lt_050"]),
            "rule_duration_gt_019": sum(1 for row in rows if row["rule_duration_gt_019"]),
            "rule_overlap_ge_4": sum(1 for row in rows if row["rule_overlap_ge_4"]),
            "rule_abs_prev_ge_12": sum(1 for row in rows if row["rule_abs_prev_ge_12"]),
            "rule_conf_and_overlap": sum(1 for row in rows if row["rule_conf_and_overlap"]),
            "three_signal_rule": sum(1 for row in rows if row["three_signal_rule"]),
        },
        "selected_bucket_counts": {},
        "stats_by_selected": {},
        "rows": rows,
    }

    for row in rows:
        bucket = row["selected_bucket"]
        summary["selected_bucket_counts"][bucket] = summary["selected_bucket_counts"].get(bucket, 0) + 1

    for selected_value in [True, False]:
        group = [row for row in rows if row["selected"] is selected_value]
        key = "selected" if selected_value else "not_selected"

        summary["stats_by_selected"][key] = {
            "count": len(group),
            "confidence": safe_stats([row["confidence"] for row in group if row["confidence"] is not None]),
            "duration": safe_stats([row["duration"] for row in group if row["duration"] is not None]),
            "overlap_count": safe_stats([row["overlap_count"] for row in group]),
            "nearby_count": safe_stats([row["nearby_count"] for row in group]),
        }

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "status": "completed",
        "note_count": summary["note_count"],
        "selected_count": summary["selected_count"],
        "rule_counts": summary["rule_counts"],
        "selected_bucket_counts": summary["selected_bucket_counts"],
        "output_json": str(output_json),
        "output_csv": str(output_csv),
    }, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
