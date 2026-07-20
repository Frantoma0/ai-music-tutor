from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _fmt_rate(value: float | None) -> str:
    if value is None:
        return "n/a"

    return f"{value:.4f}"


def build_pitch_correction_report_markdown(data: dict[str, Any]) -> str:
    pitch_safety = data.get("pitch_safety") or {}
    coverage = data.get("coverage") or {}
    locked = data.get("locked") or {}

    approved = pitch_safety.get("approved") or []
    rejected = pitch_safety.get("rejected") or []
    action_distribution = pitch_safety.get("action_distribution") or {}

    approved_pitch_shifts = [
        item for item in approved if item.get("action") == "propose_pitch_shift"
    ]

    lines: list[str] = []

    lines.append("# Day 14 Qwen3 8B Pitch Correction Report")
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
    lines.append(f"| Coverage OK | `{str(bool(coverage.get('ok'))).lower()}` |")
    lines.append(f"| Approved pitch shifts | `{pitch_safety.get('approved_pitch_shift_count')}` |")
    lines.append(f"| Rejected pitch shifts | `{pitch_safety.get('rejected_pitch_shift_count')}` |")
    lines.append(f"| CAR | `{_fmt_rate(pitch_safety.get('correction_acceptance_rate'))}` |")
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

    for action, count in sorted(action_distribution.items()):
        lines.append(f"| `{action}` | `{count}` |")

    lines.append("")

    lines.append("## 4. Approved Pitch Shifts")
    lines.append("")
    lines.append("| # | Candidate ID | Original | Proposed | Confidence | HVS | Reason |")
    lines.append("|---:|---|---:|---:|---:|---:|---|")

    for index, item in enumerate(approved_pitch_shifts, start=1):
        lines.append(
            "| "
            f"{index} | "
            f"`{item.get('candidate_id')}` | "
            f"`{item.get('original_pitch')}` | "
            f"`{item.get('proposed_pitch')}` | "
            f"`{item.get('confidence')}` | "
            f"`{item.get('hvs_score')}` | "
            f"`{item.get('reason')}` |"
        )

    lines.append("")

    lines.append("## 5. Rejected Pitch Shifts")
    lines.append("")
    lines.append("| # | Candidate ID | Original | Proposed | Reasons |")
    lines.append("|---:|---|---:|---:|---|")

    for index, item in enumerate(rejected, start=1):
        lines.append(
            "| "
            f"{index} | "
            f"`{item.get('candidate_id')}` | "
            f"`{item.get('original_pitch')}` | "
            f"`{item.get('proposed_pitch')}` | "
            f"`{item.get('pitch_safety_reasons')}` |"
        )

    lines.append("")

    lines.append("## 6. Interpretation")
    lines.append("")
    lines.append(
        "This run is the first full-set pitch correction attempt using `qwen3:8b` "
        "with JSON mode enabled, chunk size 5, metadata locking, coverage validation, "
        "and post-hoc pitch safety validation."
    )
    lines.append("")
    lines.append(
        "The model proposed concrete pitch shifts instead of only classifying candidates. "
        "Unsafe large jumps were rejected by the pitch safety layer before any MIDI mutation."
    )
    lines.append("")
    lines.append(
        "The reported CAR value measures how many proposed pitch shifts passed deterministic "
        "safety constraints. It does not yet prove musical correctness; that requires applying "
        "approved corrections to a MIDI copy and measuring corrected F1."
    )
    lines.append("")

    return "\n".join(lines)


def generate_report(*, input_path: str, output: str) -> dict[str, Any]:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    markdown = build_pitch_correction_report_markdown(data)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    pitch_safety = data.get("pitch_safety") or {}

    return {
        "status": "completed",
        "input_path": input_path,
        "output": str(output_path),
        "candidate_count": data.get("candidate_count"),
        "approved_pitch_shift_count": pitch_safety.get("approved_pitch_shift_count"),
        "rejected_pitch_shift_count": pitch_safety.get("rejected_pitch_shift_count"),
        "correction_acceptance_rate": pitch_safety.get("correction_acceptance_rate"),
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Markdown report for Qwen pitch correction run."
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
