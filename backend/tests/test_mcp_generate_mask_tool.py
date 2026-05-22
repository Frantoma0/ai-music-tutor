from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generate_mask_tool_requires_job_id():
    response = client.post(
        "/api/tools/generate_mask/execute",
        json={"payload": {}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "generate_mask"
    assert body["status"] == "error"
    assert body["error"] == "Missing required field: job_id"


def test_generate_mask_tool_returns_candidates_with_mocked_run(monkeypatch):
    async def fake_get_pipeline_run(db_path, *, job_id):
        assert job_id == "pytest-mask-job"

        return {
            "id": "run_test",
            "job_id": job_id,
            "detected_key": "F major",
            "hvs_score": 0.8,
            "midi_path": "artifacts/tracer/pytest/output.mid",
            "transcription": {
                "transcription_method": "basic_pitch",
                "midi_path": "artifacts/tracer/pytest/output.mid",
                "notes": [
                    {
                        "id": "n0",
                        "pitch": 60,
                        "pitch_name": "C4",
                        "start": 0.0,
                        "end": 1.0,
                        "confidence": 0.5,
                    },
                    {
                        "id": "n1",
                        "pitch": 64,
                        "pitch_name": "E4",
                        "start": 1.0,
                        "end": 2.0,
                        "confidence": 0.9,
                    },
                ],
            },
        }

    monkeypatch.setattr(
        "app.mcp_tools.tools.get_pipeline_run",
        fake_get_pipeline_run,
    )

    response = client.post(
        "/api/tools/generate_mask/execute",
        json={
            "payload": {
                "job_id": "pytest-mask-job",
                "confidence_threshold": 0.7,
                "hvs_threshold": 0.6,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "generate_mask"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "pytest-mask-job"
    assert data["pipeline_run_id"] == "run_test"
    assert data["detected_key"] == "F major"
    assert data["hvs_score"] == 0.8
    assert data["transcription_method"] == "basic_pitch"
    assert data["note_count"] == 2
    assert data["selected_count"] == 1

    assert data["candidates"][0]["selected"] is True
    assert data["candidates"][0]["reason"] == "low_confidence_high_hvs"

    assert data["candidates"][1]["selected"] is False
    assert data["candidates"][1]["reason"] == "confidence_above_threshold"
