from __future__ import annotations

import asyncio

from app.scripts.generate_correction_report import (
    build_correction_report_markdown,
    generate_report,
)


def test_build_correction_report_markdown_formats_real_newlines():
    markdown = build_correction_report_markdown(
        {
            "id": "crun_test",
            "job_id": "pytest-job",
            "pipeline_run_id": "run_test",
            "status": "completed",
            "note_count": 100,
            "candidate_count": 100,
            "selected_count": 10,
            "proposal_count": 10,
            "approved_count": 10,
            "rejected_count": 0,
            "midi_mutation_allowed": False,
            "midi_mutated": False,
            "source_mask_path": "mask.json",
            "source_proposals_path": "proposals.json",
            "source_validation_path": "validation.json",
            "proposals": [
                {
                    "proposal_id": "prop_0000",
                    "candidate_id": "n0",
                    "action": "flag_for_review",
                    "original_pitch": 60,
                    "confidence": 0.5,
                    "hvs_score": 0.6,
                    "status": "pending_validation",
                }
            ],
            "validations": [
                {
                    "proposal_id": "prop_0000",
                    "candidate_id": "n0",
                    "validation_status": "approved_for_review",
                    "approved": True,
                    "reasons": [],
                }
            ],
        }
    )

    assert "# Correction Run Report\n\n## 1. Summary" in markdown
    assert "\\n" not in markdown
    assert "| Mask ratio | `0.1000` |" in markdown
    assert "| Proposal count | `10` |" in markdown
    assert "| Approved count | `10` |" in markdown
    assert "| Rejected count | `0` |" in markdown


def test_generate_report_returns_error_for_missing_run(tmp_path):
    async def run():
        return await generate_report(
            db_path=str(tmp_path / "app.sqlite3"),
            correction_run_id="missing",
            output=str(tmp_path / "report.md"),
        )

    result = asyncio.run(run())

    assert result["status"] == "error"
    assert result["error"] == "Correction run not found: missing"
