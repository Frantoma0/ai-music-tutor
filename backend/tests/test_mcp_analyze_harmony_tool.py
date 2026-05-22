from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_analyze_harmony_tool_requires_job_id():
    response = client.post(
        "/api/tools/analyze_harmony/execute",
        json={"payload": {}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "analyze_harmony"
    assert body["status"] == "error"
    assert body["error"] == "Missing required field: job_id"


def test_analyze_harmony_tool_returns_compact_summary_with_mocked_run(monkeypatch):
    async def fake_get_pipeline_run(db_path, *, job_id):
        assert job_id == "pytest-harmony-job"

        return {
            "id": "run_test",
            "job_id": job_id,
            "detected_key": "C major",
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
                        "confidence": 0.5,
                    },
                    {
                        "id": "n1",
                        "pitch": 61,
                        "pitch_name": "C#4",
                        "confidence": 0.4,
                    },
                ],
            },
        }

    monkeypatch.setattr(
        "app.mcp_tools.tools.get_pipeline_run",
        fake_get_pipeline_run,
    )

    response = client.post(
        "/api/tools/analyze_harmony/execute",
        json={
            "payload": {
                "job_id": "pytest-harmony-job",
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "analyze_harmony"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "pytest-harmony-job"
    assert data["pipeline_run_id"] == "run_test"
    assert data["detected_key"] == "C major"
    assert data["global_hvs_score"] == 0.8
    assert data["transcription_method"] == "basic_pitch"
    assert data["note_count"] == 2

    assert data["hvs_distribution"] == {
        "0.0": 1,
        "0.6": 1,
    }

    assert data["label_distribution"] == {
        "stable_chord_tone": 1,
        "chromatic_neighbor": 1,
    }

    assert data["notes_included"] is False
    assert data["returned_note_count"] == 0
    assert data["notes"] == []


def test_analyze_harmony_tool_can_include_limited_notes(monkeypatch):
    async def fake_get_pipeline_run(db_path, *, job_id):
        return {
            "id": "run_test",
            "job_id": job_id,
            "detected_key": "C major",
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
                        "confidence": 0.5,
                    },
                    {
                        "id": "n1",
                        "pitch": 62,
                        "pitch_name": "D4",
                        "confidence": 0.4,
                    },
                ],
            },
        }

    monkeypatch.setattr(
        "app.mcp_tools.tools.get_pipeline_run",
        fake_get_pipeline_run,
    )

    response = client.post(
        "/api/tools/analyze_harmony/execute",
        json={
            "payload": {
                "job_id": "pytest-harmony-job",
                "include_notes": True,
                "max_notes": 1,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"

    data = body["data"]

    assert data["notes_included"] is True
    assert data["returned_note_count"] == 1
    assert len(data["notes"]) == 1
    assert data["notes"][0]["id"] == "n0"
    assert data["notes"][0]["hvs_score"] == 0.0
    assert data["notes"][0]["hvs_label"] == "stable_chord_tone"


def test_analyze_harmony_tool_omits_nested_harmony_notes_by_default(monkeypatch):
    async def fake_get_pipeline_run(db_path, *, job_id):
        return {
            "id": "run_test",
            "job_id": job_id,
            "detected_key": "C major",
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
                        "confidence": 0.5,
                    }
                ],
            },
        }

    monkeypatch.setattr(
        "app.mcp_tools.tools.get_pipeline_run",
        fake_get_pipeline_run,
    )

    response = client.post(
        "/api/tools/analyze_harmony/execute",
        json={
            "payload": {
                "job_id": "pytest-harmony-job",
            }
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]

    assert body["status"] == "success"
    assert data["notes_included"] is False
    assert data["returned_note_count"] == 0
    assert data["notes"] == []
    assert data["harmony"]["notes"] == []
