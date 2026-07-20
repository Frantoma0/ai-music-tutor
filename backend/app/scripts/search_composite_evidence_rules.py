from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

TARGET_BUCKET = "spurious_or_timing_fp"


def load_rows(audit_path: str, labels_path: str) -> list[dict[str, Any]]:
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    labels = json.loads(Path(labels_path).read_text(encoding="utf-8"))

    label_by_id = {row["id"]: row["bucket"] for row in labels["rows"]}

    rows = []

    for row in audit["rows"]:
        rows.append(
            {
                **row,
                "bucket": label_by_id[row["id"]],
            }
        )

    return rows


def clause_passes(row: dict[str, Any], clause: dict[str, Any]) -> bool:
    value = row.get(clause["field"])

    if value is None:
        return False

    op = clause["op"]
    threshold = clause["threshold"]

    if op == "<":
        return value < threshold

    if op == "<=":
        return value <= threshold

    if op == ">":
        return value > threshold

    if op == ">=":
        return value >= threshold

    raise ValueError(f"Unsupported op: {op}")


def rule_passes(row: dict[str, Any], clauses: tuple[dict[str, Any], ...]) -> bool:
    return all(clause_passes(row, clause) for clause in clauses)


def evaluate_rule(
    *,
    rows: list[dict[str, Any]],
    clauses: tuple[dict[str, Any], ...],
    target_bucket: str,
) -> dict[str, Any]:
    hits = [row for row in rows if rule_passes(row, clauses)]

    target_count = sum(1 for row in rows if row["bucket"] == target_bucket)

    tp = sum(1 for row in hits if row["bucket"] == target_bucket)
    fp = sum(1 for row in hits if row["bucket"] != target_bucket)
    fn = target_count - tp
    tn = len(rows) - tp - fp - fn

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    bucket_counts: dict[str, int] = {}

    for row in hits:
        bucket = row["bucket"]
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    return {
        "clauses": list(clauses),
        "rule": " AND ".join(
            f'{clause["field"]} {clause["op"]} {clause["threshold"]}' for clause in clauses
        ),
        "hits": len(hits),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "hit_bucket_counts": bucket_counts,
        "hit_ids": [row["id"] for row in hits],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-path", required=True)
    parser.add_argument("--labels-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-clauses", type=int, default=3)
    parser.add_argument("--min-hits", type=int, default=3)

    args = parser.parse_args()

    rows = load_rows(args.audit_path, args.labels_path)

    clause_space = [
        {"field": "confidence", "op": "<", "threshold": 0.35},
        {"field": "confidence", "op": "<", "threshold": 0.40},
        {"field": "confidence", "op": "<", "threshold": 0.45},
        {"field": "confidence", "op": "<", "threshold": 0.50},
        {"field": "confidence", "op": "<", "threshold": 0.55},
        {"field": "duration", "op": ">", "threshold": 0.15},
        {"field": "duration", "op": ">", "threshold": 0.19},
        {"field": "duration", "op": ">", "threshold": 0.23},
        {"field": "duration", "op": ">", "threshold": 0.27},
        {"field": "overlap_count", "op": ">=", "threshold": 2},
        {"field": "overlap_count", "op": ">=", "threshold": 3},
        {"field": "overlap_count", "op": ">=", "threshold": 4},
        {"field": "overlap_count", "op": ">=", "threshold": 5},
        {"field": "nearby_count", "op": ">=", "threshold": 3},
        {"field": "nearby_count", "op": ">=", "threshold": 4},
        {"field": "nearby_count", "op": ">=", "threshold": 5},
        {"field": "abs_prev_interval", "op": ">=", "threshold": 8},
        {"field": "abs_prev_interval", "op": ">=", "threshold": 12},
        {"field": "abs_prev_interval", "op": ">=", "threshold": 16},
        {"field": "abs_next_interval", "op": ">=", "threshold": 8},
        {"field": "abs_next_interval", "op": ">=", "threshold": 12},
    ]

    results = []

    for size in range(1, args.max_clauses + 1):
        for clauses in itertools.combinations(clause_space, size):
            fields = [clause["field"] for clause in clauses]

            if len(fields) != len(set(fields)):
                continue

            result = evaluate_rule(
                rows=rows,
                clauses=clauses,
                target_bucket=TARGET_BUCKET,
            )

            if result["hits"] >= args.min_hits:
                results.append(result)

    top_by_f1 = sorted(
        results,
        key=lambda item: (item["f1"], item["precision"], item["recall"]),
        reverse=True,
    )[:25]

    top_by_precision = sorted(
        results,
        key=lambda item: (item["precision"], item["recall"], item["f1"]),
        reverse=True,
    )[:25]

    top_by_recall = sorted(
        results,
        key=lambda item: (item["recall"], item["precision"], item["f1"]),
        reverse=True,
    )[:25]

    report = {
        "status": "completed",
        "target_bucket": TARGET_BUCKET,
        "row_count": len(rows),
        "target_count": sum(1 for row in rows if row["bucket"] == TARGET_BUCKET),
        "candidate_rule_count": len(results),
        "top_by_f1": top_by_f1,
        "top_by_precision": top_by_precision,
        "top_by_recall": top_by_recall,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": report["status"],
                "target_bucket": report["target_bucket"],
                "row_count": report["row_count"],
                "target_count": report["target_count"],
                "candidate_rule_count": report["candidate_rule_count"],
                "best_f1_rule": top_by_f1[0] if top_by_f1 else None,
                "output": str(output),
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
