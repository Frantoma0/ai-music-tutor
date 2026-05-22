from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import aiosqlite

from app.db.database import create_metric_record, initialize_database


async def _find_pipeline_run_id(db_path: str | Path, job_id: str) -> str | None:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT id
            FROM pipeline_runs
            WHERE job_id = ?
            """,
            (job_id,),
        )
        row = await cursor.fetchone()

    return row[0] if row else None


async def persist_baseline_report(
    report_path: str | Path,
    db_path: str | Path = "data/app.sqlite3",
) -> dict:
    await initialize_database(db_path)

    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    created = []

    for item in report.get("results", []):
        if item.get("status") != "completed":
            continue

        pipeline_run_id = await _find_pipeline_run_id(
            db_path,
            item["job_id"],
        )

        metric_id = await create_metric_record(
            db_path,
            pipeline_run_id=pipeline_run_id,
            metric_name="baseline_transcription_f1",
            metric_value=item.get("f1"),
            metric_json=item,
        )

        created.append(
            {
                "metric_id": metric_id,
                "job_id": item["job_id"],
                "pipeline_run_id": pipeline_run_id,
                "f1": item.get("f1"),
            }
        )

    average_metric_id = await create_metric_record(
        db_path,
        pipeline_run_id=None,
        metric_name="baseline_transcription_f1_average",
        metric_value=report.get("averages", {}).get("f1"),
        metric_json={
            "averages": report.get("averages", {}),
            "count": report.get("count"),
            "completed_count": report.get("completed_count"),
            "source_report": str(report_path),
        },
    )

    return {
        "status": "completed",
        "report_path": str(report_path),
        "db_path": str(db_path),
        "created_count": len(created) + 1,
        "average_metric_id": average_metric_id,
        "metrics": created,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist baseline evaluation metrics into SQLite.")
    parser.add_argument(
        "--report",
        default="artifacts/metrics/day9_maestro_ci_baseline_report.json",
    )
    parser.add_argument("--db-path", default="data/app.sqlite3")

    args = parser.parse_args()

    result = asyncio.run(
        persist_baseline_report(
            report_path=args.report,
            db_path=args.db_path,
        )
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
