from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _fmt_bool(value: bool) -> str:
    return "true" if value else "false"


def _action_distribution(corrections: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(item.get("action", "unknown") for item in corrections))


def build_llm_correction_report_markdown(data: dict[str, Any]) -> str:
    locked = data.get("locked") or {}
    coverage = data.get("coverage") or {}
    chunks = data.get("chunks") or []
    corrections = locked.get("corrections") or []

    actions = _action_distribution(corrections)

    lines: list[str] = []

    lines.append("# Day 13 LLM Correction Report")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Status | `{data.get('status')}` |")
    lines.append(f"| Model | `{data.get('model')}` |")
    lines.append(f"| Candidate count | `{data.get('candidate_count')}` |")
    lines.append(f"| Chunk size | `{data.get('chunk_size')}` |")
    lines.append(f"| Chunk count | `{data.get('chunk_count')}` |")
    lines.append(f"| Completed chunks | `{data.get('completed_chunk_count')}` |")
    lines.append(f"| Failed chunks | `{data.get('failed_chunk_count')}` |")
    lines.append(f"| Locked correction count | `{locked.get('correction_count')}` |")
    lines.append(f"| Metadata locked | `{_fmt_bool(bool(locked.get('metadata_locked')))}` |")
    lines.append(f"| Coverage OK | `{_fmt_bool(bool(coverage.get('ok')))}` |")
    lines.append("")

    lines.append("## 2. Coverage")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Expected candidate count | `{coverage.get('expected_candidate_count')}` |")
    lines.append(f"| Locked candidate count | `{coverage.get('locked_candidate_count')}` |")
    lines.append(f"| Missing candidate IDs | `{coverage.get('missing_candidate_ids')}` |")
    lines.append(f"| Duplicate candidate IDs | `{coverage.get('duplicate_candidate_ids')}` |")
    lines.append("")

    lines.append("## 3. Action Distribution")
    lines.append("")
    lines.append("| Action | Count |")
    lines.append("|---|---:|")

    for action, count in sorted(actions.items()):
        lines.append(f"| `{action}` | `{count}` |")

    lines.append("")

    lines.append("## 4. Chunk Results")
    lines.append("")
    lines.append("| Chunk | Status | Candidates | Error |")
    lines.append("|---:|---|---:|---|")

    for chunk in chunks:
        lines.append(
            "| "
            f"{chunk.get('chunk_index')} | "
            f"`{chunk.get('status')}` | "
            f"`{chunk.get('candidate_count')}` | "
            f"`{chunk.get('error')}` |"
        )

    lines.append("")

    lines.append("## 5. First Locked Corrections")
    lines.append("")
    lines.append("| # | Candidate ID | Action | Pitch | Confidence | HVS | Metadata Source |")
    lines.append("|---:|---|---|---|---:|---:|---|")

    for index, item in enumerate(corrections[:10], start=1):
        lines.append(
            "| "
            f"{index} | "
            f"`{item.get('candidate_id')}` | "
            f"`{item.get('action')}` | "
            f"`{item.get('pitch_name')}` | "
            f"`{item.get('confidence')}` | "
            f"`{item.get('hvs_score')}` | "
            f"`{item.get('metadata_source')}` |"
        )

    lines.append("")

    lines.append("## 6. Interpretation")
    lines.append("")
    lines.append(
        "The direct 43-candidate Qwen run failed to produce valid JSON, "
        "but chunked processing with chunk size 10 completed successfully."
    )
    lines.append("")
    lines.append(
        "This confirms that LLM-based correction should be processed in bounded chunks, "
        "with schema validation, metadata locking, and coverage validation."
    )
    lines.append("")
    lines.append(
        "The system does not trust the LLM as a source of numeric metadata. "
        "The LLM decides only the correction action and reason, while pitch, timing, "
        "confidence, and HVS values are restored from the original system candidates."
    )
    lines.append("")

    return "\n".join(lines)


def generate_report(*, input_path: str, output: str) -> dict[str, Any]:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    markdown = build_llm_correction_report_markdown(data)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    return {
        "status": "completed",
        "input_path": input_path,
        "output": str(output_path),
        "candidate_count": data.get("candidate_count"),
        "chunk_count": data.get("chunk_count"),
        "locked_correction_count": (data.get("locked") or {}).get("correction_count"),
        "coverage_ok": (data.get("coverage") or {}).get("ok"),
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Markdown report for chunked LLM correction run."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    try:
        result = generate_report(
            input_path=args.input,
            output=args.output,
        )
    except Exception as exc:
        result = {
            "status": "error",
            "input_path": args.input,
            "output": args.output,
            "error": f"{type(exc).__name__}: {exc}",
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
