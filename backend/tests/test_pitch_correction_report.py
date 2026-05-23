from __future__ import annotations

import json

from app.scripts.generate_pitch_correction_report import (
    build_pitch_correction_report_markdown,
    generate_report,
)


def test_build_pitch_correction_report_markdown_summarizes_pitch_run():
    markdown = build_pitch_correction_report_markdown(
        {
            "status": "completed",
            "model": "qwen3:test",
            "candidate_count": 2,
            "chunk_size": 1,
            "chunk_count": 2,
            "completed_chunk_count": 2,
            "failed_chunk_count": 0,
            "coverage": {
                "ok": True,
                "expected_candidate_count": 2,
                "locked_candidate_count": 2,
                "missing_candidate_ids": [],
                "duplicate_candidate_ids": [],
            },
            "locked": {
                "correction_count": 2,
            },
            "pitch_safety": {
                "action_distribution": {
                    "propose_pitch_shift": 1,
                    "flag_for_review": 1,
                },
                "approved_pitch_shift_count": 1,
                "rejected_pitch_shift_count": 0,
                "correction_acceptance_rate": 1.0,
                "approved": [
                    {
                        "candidate_id": "n117",
                        "action": "propose_pitch_shift",
                        "original_pitch": 59,
                        "proposed_pitch": 60,
                        "confidence": 0.617295,
                        "hvs_score": 0.6,
                        "reason": "nearby diatonic option",
                    },
                    {
                        "candidate_id": "n120",
                        "action": "flag_for_review",
                        "original_pitch": 78,
                        "proposed_pitch": None,
                        "confidence": 0.63612,
                        "hvs_score": 0.6,
                        "reason": "uncertain",
                    },
                ],
                "rejected": [],
            },
        }
    )

    assert "# Day 14 Qwen3 8B Pitch Correction Report" in markdown
    assert "| Candidate count | `2` |" in markdown
    assert "| Approved pitch shifts | `1` |" in markdown
    assert "| Rejected pitch shifts | `0` |" in markdown
    assert "| CAR | `1.0000` |" in markdown
    assert "| `propose_pitch_shift` | `1` |" in markdown
    assert "| `flag_for_review` | `1` |" in markdown
    assert "`n117`" in markdown
    assert "`59`" in markdown
    assert "`60`" in markdown
    assert "\\n" not in markdown


def test_generate_pitch_correction_report_writes_markdown(tmp_path):
    input_path = tmp_path / "pitch.json"
    output_path = tmp_path / "pitch_report.md"

    input_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "model": "qwen3:test",
                "candidate_count": 1,
                "chunk_size": 1,
                "chunk_count": 1,
                "completed_chunk_count": 1,
                "failed_chunk_count": 0,
                "coverage": {
                    "ok": True,
                    "expected_candidate_count": 1,
                    "locked_candidate_count": 1,
                    "missing_candidate_ids": [],
                    "duplicate_candidate_ids": [],
                },
                "locked": {
                    "correction_count": 1,
                },
                "pitch_safety": {
                    "action_distribution": {
                        "propose_pitch_shift": 1,
                    },
                    "approved_pitch_shift_count": 1,
                    "rejected_pitch_shift_count": 0,
                    "correction_acceptance_rate": 1.0,
                    "approved": [],
                    "rejected": [],
                },
            }
        ),
        encoding="utf-8",
    )

    result = generate_report(
        input_path=str(input_path),
        output=str(output_path),
    )

    assert result["status"] == "completed"
    assert result["candidate_count"] == 1
    assert result["approved_pitch_shift_count"] == 1
    assert result["rejected_pitch_shift_count"] == 0
    assert result["correction_acceptance_rate"] == 1.0
    assert output_path.exists()
