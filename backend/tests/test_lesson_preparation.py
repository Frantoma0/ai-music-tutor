from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.database import create_pipeline_run, create_transcription_record, initialize_database
from app.main import app
from app.pipeline.lesson_preparation import prepare_lesson_for_job


@pytest.mark.asyncio
async def test_prepare_lesson_maps_notes_hvs_mask_and_hands(tmp_path: Path) -> None:
    db_path = tmp_path / "app.sqlite3"
    await initialize_database(db_path)

    run_id = await create_pipeline_run(
        db_path,
        job_id="job_lesson_test",
        status="completed",
        detected_key="C major",
        hvs_score=0.8,
        metadata={"tempo_bpm": 100, "time_signature": "4/4", "duration_s": 2.0},
    )

    await create_transcription_record(
        db_path,
        job_id="job_lesson_test",
        input_audio="input.wav",
        transcription_method="basic_pitch",
        status="completed",
        pipeline_run_id=run_id,
        midi_path="data/midi/job_lesson_test/raw.mid",
        notes=[
            {
                "id": "n0",
                "pitch": 48,
                "pitch_name": "C3",
                "start": 0.0,
                "end": 0.5,
                "duration": 0.5,
                "velocity": 80,
                "confidence": 0.95,
            },
            {
                "id": "n1",
                "pitch": 61,
                "pitch_name": "C#4",
                "start": 0.5,
                "end": 1.0,
                "duration": 0.5,
                "velocity": 90,
                "confidence": 0.4,
            },
        ],
    )

    lesson = await prepare_lesson_for_job("job_lesson_test", db_path=db_path)

    assert lesson is not None
    assert lesson.meta.job_id == "job_lesson_test"
    assert lesson.meta.status == "completed"
    assert lesson.meta.tempo_bpm == 100
    assert lesson.meta.time_signature == "4/4"
    assert lesson.note_count == 2

    assert lesson.notes[0].id == "n0"
    assert lesson.notes[0].hand == "left"
    assert lesson.notes[0].hvs_label == "stable_chord_tone"
    assert lesson.notes[0].in_correction_mask is False

    assert lesson.notes[1].id == "n1"
    assert lesson.notes[1].hand == "right"
    assert lesson.notes[1].in_correction_mask is True

    assert lesson.masked_count == 1
    assert lesson.correction_count == 0


def test_lesson_endpoint_returns_404_for_missing_job() -> None:
    client = TestClient(app)

    response = client.get("/api/lessons/missing-job")

    assert response.status_code == 404
