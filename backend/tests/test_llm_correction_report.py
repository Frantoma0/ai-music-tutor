from __future__ import annotations

import json

from app.scripts.generate_llm_correction_report import (
    build_llm_correction_report_markdown,
    generate_report,
)


def test_build_llm_correction_report_markdown_summarizes_chunked_run():
    markdown = build_llm_correction_report_markdown(
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
                "metadata_locked": True,
                "correction_count": 2,
                "corrections": [
                    {
                        "candidate_id": "n1",
                        "action": "keep",
                        "pitch_name": "C4",
                        "confidence": 0.7,
                        "hvs_score": 0.6,
                        "metadata_source": "system_candidate_locked",
                    },
                    {
                        "candidate_id": "n2",
                        "action": "flag_for_review",
                        "pitch_name": "D4",
                        "confidence": 0.5,
                        "hvs_score": 0.6,
                        "metadata_source": "system_candidate_locked",
                    },
                ],
            },
            "chunks": [
                {
                    "chunk_index": 1,
                    "status": "completed",
                    "candidate_count": 1,
                    "error": None,
                },
                {
                    "chunk_index": 2,
                    "status": "completed",
                    "candidate_count": 1,
                    "error": None,
                },
            ],
        }
    )

    assert "# Day 13 LLM Correction Report" in markdown
    assert "| Candidate count | `2` |" in markdown
    assert "| Metadata locked | `true` |" in markdown
    assert "| Coverage OK | `true` |" in markdown
    assert "| `flag_for_review` | `1` |" in markdown
    assert "| `keep` | `1` |" in markdown
    assert "\\n" not in markdown


def test_generate_llm_correction_report_writes_markdown(tmp_path):
    input_path = tmp_path / "llm.json"
    output_path = tmp_path / "report.md"

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
                    "metadata_locked": True,
                    "correction_count": 1,
                    "corrections": [],
                },
                "chunks": [],
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
    assert result["chunk_count"] == 1
    assert result["locked_correction_count"] == 1
    assert result["coverage_ok"] is True
    assert output_path.exists()
