from __future__ import annotations

import json

import aiosqlite
import pytest

from app.pipeline.persistence import persist_audio_to_analysis_result


class FakeAudioToAnalysisResult:
    def to_dict(self):
        return {
            "job_id": "pytest-persist-job",
            "source": "data/samples/source.wav",
            "status": "completed",
            "extract": {"status": "completed"},
            "separation": {"status": "completed"},
            "separation_quality": {"status": "completed"},
            "transcription": {
                "status": "completed",
                "input_audio": "data/processed/pytest/input.wav",
                "midi_path": "artifacts/tracer/pytest/output.mid",
                "transcription_method": "basic_pitch",
                "note_count": 1,
                "notes": [
                    {
                        "id": "n0",
                        "pitch": 69,
                        "pitch_name": "A4",
                        "confidence": 0.629446,
                    }
                ],
                "error": None,
            },
            "analysis": {
                "status": "completed",
                "detected_key": "D major",
                "hvs_score": 0.81,
            },
            "final_audio_path": "data/processed/pytest/input.wav",
            "midi_path": "artifacts/tracer/pytest/output.mid",
            "detected_key": "D major",
            "hvs_score": 0.81,
            "error": None,
        }


@pytest.mark.asyncio
async def test_persist_audio_to_analysis_result_stores_run_and_transcription(tmp_path):
    db_path = tmp_path / "app.sqlite3"

    ids = await persist_audio_to_analysis_result(
        FakeAudioToAnalysisResult(),
        db_path=db_path,
        session_title="Pytest persisted run",
    )

    assert ids["session_id"].startswith("sess_")
    assert ids["pipeline_run_id"].startswith("run_")
    assert ids["transcription_id"].startswith("trn_")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT
                sessions.title,
                pipeline_runs.job_id,
                pipeline_runs.detected_key,
                pipeline_runs.hvs_score,
                transcriptions.transcription_method,
                transcriptions.note_count,
                transcriptions.notes_json
            FROM transcriptions
            JOIN pipeline_runs ON transcriptions.pipeline_run_id = pipeline_runs.id
            JOIN sessions ON pipeline_runs.session_id = sessions.id
            WHERE pipeline_runs.job_id = ?
            """,
            ("pytest-persist-job",),
        )

        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "Pytest persisted run"
    assert row[1] == "pytest-persist-job"
    assert row[2] == "D major"
    assert row[3] == 0.81
    assert row[4] == "basic_pitch"
    assert row[5] == 1

    notes = json.loads(row[6])
    assert notes[0]["confidence"] == 0.629446
