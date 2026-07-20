from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.correction_persistence import get_correction_run


def _fmt_bool(value: bool) -> str:
    return "true" if value else "false"


def build_correction_report_markdown(run: dict) -> str:
    proposals = run.get("proposals") or []
    validations = run.get("validations") or []

    selected_count = run.get("selected_count") or 0
    note_count = run.get("note_count") or 0

    mask_ratio = selected_count / note_count if note_count else 0.0

    lines: list[str] = []

    lines.append("# Correction Run Report")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Correction run ID | `{run.get('id')}` |")
    lines.append(f"| Job ID | `{run.get('job_id')}` |")
    lines.append(f"| Pipeline run ID | `{run.get('pipeline_run_id')}` |")
    lines.append(f"| Status | `{run.get('status')}` |")
    lines.append(f"| Note count | `{run.get('note_count')}` |")
    lines.append(f"| Candidate count | `{run.get('candidate_count')}` |")
    lines.append(f"| Selected count | `{run.get('selected_count')}` |")
    lines.append(f"| Mask ratio | `{mask_ratio:.4f}` |")
    lines.append(f"| Proposal count | `{run.get('proposal_count')}` |")
    lines.append(f"| Approved count | `{run.get('approved_count')}` |")
    lines.append(f"| Rejected count | `{run.get('rejected_count')}` |")
    lines.append(
        f"| MIDI mutation allowed | `{_fmt_bool(run.get('midi_mutation_allowed', False))}` |"
    )
    lines.append(f"| MIDI mutated | `{_fmt_bool(run.get('midi_mutated', False))}` |")
    lines.append("")

    lines.append("## 2. Artifact Trace")
    lines.append("")
    lines.append("| Artifact | Path |")
    lines.append("|---|---|")
    lines.append(f"| Mask | `{run.get('source_mask_path')}` |")
    lines.append(f"| Proposals | `{run.get('source_proposals_path')}` |")
    lines.append(f"| Validation | `{run.get('source_validation_path')}` |")
    lines.append("")

    lines.append("## 3. First Proposals")
    lines.append("")
    lines.append("| # | Proposal ID | Candidate ID | Action | Pitch | Confidence | HVS | Status |")
    lines.append("|---:|---|---|---|---:|---:|---:|---|")

    for index, proposal in enumerate(proposals[:10], start=1):
        lines.append(
            "| "
            f"{index} | "
            f"`{proposal.get('proposal_id')}` | "
            f"`{proposal.get('candidate_id')}` | "
            f"`{proposal.get('action')}` | "
            f"`{proposal.get('original_pitch')}` | "
            f"`{proposal.get('confidence')}` | "
            f"`{proposal.get('hvs_score')}` | "
            f"`{proposal.get('status')}` |"
        )

    lines.append("")

    lines.append("## 4. First Validations")
    lines.append("")
    lines.append("| # | Proposal ID | Candidate ID | Status | Approved | Reasons |")
    lines.append("|---:|---|---|---|---:|---|")

    for index, validation in enumerate(validations[:10], start=1):
        reasons = validation.get("reasons") or []
        reason_text = ", ".join(reasons) if reasons else "none"

        lines.append(
            "| "
            f"{index} | "
            f"`{validation.get('proposal_id')}` | "
            f"`{validation.get('candidate_id')}` | "
            f"`{validation.get('validation_status')}` | "
            f"`{_fmt_bool(validation.get('approved', False))}` | "
            f"`{reason_text}` |"
        )

    lines.append("")

    lines.append("## 5. Interpretation")
    lines.append("")
    lines.append(
        "This correction run represents a safe, non-destructive correction stage. "
        "The system generated correction proposals from selected mask candidates, "
        "validated them, and preserved the result without mutating MIDI data."
    )
    lines.append("")
    lines.append(
        "The current behavior is intentionally conservative: proposals are marked "
        "as `flag_for_review`, and MIDI mutation remains disabled."
    )
    lines.append("")

    return "\n".join(lines)


async def generate_report(
    *,
    db_path: str,
    correction_run_id: str,
    output: str,
) -> dict:
    run = await get_correction_run(
        db_path,
        correction_run_id=correction_run_id,
    )

    if run is None:
        return {
            "status": "error",
            "error": f"Correction run not found: {correction_run_id}",
        }

    markdown = build_correction_report_markdown(run)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    return {
        "status": "completed",
        "correction_run_id": correction_run_id,
        "output": str(output_path),
        "proposal_count": run.get("proposal_count"),
        "approved_count": run.get("approved_count"),
        "rejected_count": run.get("rejected_count"),
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Markdown correction report.")
    parser.add_argument("--db-path", default="data/app.sqlite3")
    parser.add_argument("--correction-run-id", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = asyncio.run(
        generate_report(
            db_path=args.db_path,
            correction_run_id=args.correction_run_id,
            output=args.output,
        )
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
