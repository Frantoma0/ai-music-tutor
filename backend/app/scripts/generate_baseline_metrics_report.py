from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "n/a"

    if isinstance(value, float):
        return f"{value:.{digits}f}"

    return str(value)


async def load_baseline_metrics(
    db_path: str | Path,
    *,
    metric_name: str = "baseline_transcription_f1",
    job_prefix: str = "day9-maestro-ci-persisted",
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                metrics.id AS metric_id,
                metrics.metric_name,
                metrics.metric_value AS f1,
                metrics.metric_json,
                metrics.created_at AS metric_created_at,
                pipeline_runs.id AS pipeline_run_id,
                pipeline_runs.job_id,
                pipeline_runs.detected_key,
                pipeline_runs.hvs_score,
                pipeline_runs.status AS pipeline_status
            FROM metrics
            JOIN pipeline_runs ON metrics.pipeline_run_id = pipeline_runs.id
            WHERE metrics.metric_name = ?
              AND pipeline_runs.job_id LIKE ?
            ORDER BY pipeline_runs.job_id
            """,
            (metric_name, f"{job_prefix}-%"),
        )

        rows = await cursor.fetchall()

    results = []

    import json

    for row in rows:
        item = dict(row)
        metric_json = json.loads(item.get("metric_json") or "{}")

        item["precision"] = metric_json.get("precision")
        item["recall"] = metric_json.get("recall")
        item["overlap"] = metric_json.get("overlap")
        item["reference_note_count"] = metric_json.get("reference_note_count")
        item["estimated_note_count"] = metric_json.get("estimated_note_count")
        item["composer"] = metric_json.get("composer")
        item["title"] = metric_json.get("title")
        item["duration"] = metric_json.get("duration")
        item["onset_tolerance"] = metric_json.get("onset_tolerance")
        item["offset_ratio"] = metric_json.get("offset_ratio")

        results.append(item)

    return results


def build_markdown_report(
    rows: list[dict[str, Any]],
    *,
    title: str = "Baseline Metrics Report",
    db_path: str | Path = "data/app.sqlite3",
    job_prefix: str = "day9-maestro-ci-persisted",
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    completed = [row for row in rows if row.get("pipeline_status") == "completed"]

    if completed:
        avg_precision = sum(float(row["precision"] or 0) for row in completed) / len(completed)
        avg_recall = sum(float(row["recall"] or 0) for row in completed) / len(completed)
        avg_f1 = sum(float(row["f1"] or 0) for row in completed) / len(completed)
        avg_overlap = sum(float(row["overlap"] or 0) for row in completed) / len(completed)
    else:
        avg_precision = avg_recall = avg_f1 = avg_overlap = 0.0

    lines: list[str] = []

    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> Generated at: `{now}`")
    lines.append(f"> Database: `{db_path}`")
    lines.append(f"> Job prefix: `{job_prefix}`")
    lines.append("")

    lines.append("## 1. Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Completed runs | `{len(completed)}/{len(rows)}` |")
    lines.append(f"| Average precision | `{avg_precision:.6f}` |")
    lines.append(f"| Average recall | `{avg_recall:.6f}` |")
    lines.append(f"| Average F1 | `{avg_f1:.6f}` |")
    lines.append(f"| Average overlap | `{avg_overlap:.6f}` |")
    lines.append("")

    lines.append("## 2. Per-piece metrics")
    lines.append("")
    lines.append(
        "| # | Job ID | Piece | Key | HVS | Precision | Recall | F1 | Overlap | Ref notes | Est notes |"
    )
    lines.append("|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|")

    for index, row in enumerate(rows, start=1):
        piece = f"{row.get('composer') or 'Unknown'} — {row.get('title') or 'Unknown'}"
        lines.append(
            "| "
            f"{index} | "
            f"`{row.get('job_id')}` | "
            f"{piece} | "
            f"{row.get('detected_key') or 'n/a'} | "
            f"`{_fmt(row.get('hvs_score'), 4)}` | "
            f"`{_fmt(row.get('precision'))}` | "
            f"`{_fmt(row.get('recall'))}` | "
            f"`{_fmt(row.get('f1'))}` | "
            f"`{_fmt(row.get('overlap'))}` | "
            f"`{row.get('reference_note_count')}` | "
            f"`{row.get('estimated_note_count')}` |"
        )

    lines.append("")

    lines.append("## 3. Interpretation")
    lines.append("")
    lines.append(
        "The baseline scores represent raw Basic Pitch transcription quality before "
        "any correction, masking, validation, or HVS-aware repair layer is applied."
    )
    lines.append("")
    lines.append(
        f"The average F1 score is `{avg_f1:.6f}`, which should be treated as the "
        "initial baseline for later correction experiments."
    )
    lines.append("")
    lines.append(
        f"The average overlap is `{avg_overlap:.6f}`. This suggests that when note "
        "matches are found, their temporal overlap is relatively stronger than the "
        "overall note matching rate."
    )
    lines.append("")

    lines.append("## 4. Traceability")
    lines.append("")
    lines.append("Each metric row is linked to a persisted pipeline run:")
    lines.append("")
    lines.append("```text")
    lines.append("metric")
    lines.append("→ pipeline_run_id")
    lines.append("→ job_id")
    lines.append("→ transcription")
    lines.append("→ notes/confidence")
    lines.append("```")
    lines.append("")

    lines.append("## 5. Metric IDs")
    lines.append("")
    lines.append("| Job ID | Metric ID | Pipeline Run ID |")
    lines.append("|---|---|---|")

    for row in rows:
        lines.append(
            f"| `{row.get('job_id')}` | `{row.get('metric_id')}` | `{row.get('pipeline_run_id')}` |"
        )

    lines.append("")

    return "\n".join(lines)


async def generate_report(
    db_path: str | Path,
    output: str | Path,
    *,
    job_prefix: str = "day9-maestro-ci-persisted",
    title: str = "Day 10 Baseline Metrics Report",
) -> dict[str, Any]:
    rows = await load_baseline_metrics(
        db_path,
        job_prefix=job_prefix,
    )

    markdown = build_markdown_report(
        rows,
        title=title,
        db_path=db_path,
        job_prefix=job_prefix,
    )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    return {
        "status": "completed",
        "db_path": str(db_path),
        "output": str(output_path),
        "count": len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown report from persisted baseline metrics."
    )
    parser.add_argument("--db-path", default="data/app.sqlite3")
    parser.add_argument("--job-prefix", default="day9-maestro-ci-persisted")
    parser.add_argument("--output", default="artifacts/reports/day10_baseline_metrics_report.md")
    parser.add_argument("--title", default="Day 10 Baseline Metrics Report")

    args = parser.parse_args()

    result = asyncio.run(
        generate_report(
            db_path=args.db_path,
            output=args.output,
            job_prefix=args.job_prefix,
            title=args.title,
        )
    )

    import json

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
