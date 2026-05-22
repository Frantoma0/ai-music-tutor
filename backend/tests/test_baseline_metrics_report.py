from __future__ import annotations

from app.scripts.generate_baseline_metrics_report import build_markdown_report


def test_build_markdown_report_contains_summary_and_traceability():
    markdown = build_markdown_report(
        [
            {
                "metric_id": "met_test",
                "pipeline_run_id": "run_test",
                "metric_name": "baseline_transcription_f1",
                "f1": 0.5,
                "precision": 0.6,
                "recall": 0.4,
                "overlap": 0.8,
                "job_id": "job_test",
                "pipeline_status": "completed",
                "detected_key": "C major",
                "hvs_score": 0.75,
                "composer": "Composer",
                "title": "Piece",
                "reference_note_count": 10,
                "estimated_note_count": 8,
            }
        ],
        title="Test Report",
        db_path="test.sqlite3",
        job_prefix="job",
    )

    assert "# Test Report" in markdown
    assert "Average F1" in markdown
    assert "`0.500000`" in markdown
    assert "Composer — Piece" in markdown
    assert "metric" in markdown
    assert "pipeline_run_id" in markdown
    assert "`met_test`" in markdown
    assert "`run_test`" in markdown
