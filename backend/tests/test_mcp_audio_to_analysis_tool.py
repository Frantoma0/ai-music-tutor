from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.mcp_tools.registry import registry


def test_registry_contains_run_audio_to_analysis_tool():
    tool = registry.get("run_audio_to_analysis")

    assert tool.contract.name == "run_audio_to_analysis"
    assert tool.contract.uses_gpu is True
    assert "source" in tool.contract.input_schema["properties"]


def test_run_audio_to_analysis_tool_returns_error_when_source_is_missing():
    client = TestClient(app)

    response = client.post(
        "/api/tools/run_audio_to_analysis/execute",
        json={"payload": {}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "run_audio_to_analysis"
    assert body["status"] == "error"
    assert body["data"] == {}
    assert body["error"] == "Missing required field: source"


def test_run_audio_to_analysis_tool_via_api(monkeypatch):
    from app.pipeline.orchestrator import AudioToAnalysisPipelineResult

    def fake_pipeline(
        source,
        job_id=None,
        processed_dir="data/processed",
        stems_dir="data/stems",
        artifacts_dir="artifacts/tracer",
        use_basic_pitch=True,
        selected_stem="other",
        skip_separation=False,
        **kwargs,
    ):
        return AudioToAnalysisPipelineResult(
            job_id=job_id or "fake-job",
            source=str(source),
            status="completed",
            extract={"status": "completed", "wav_path": "data/processed/fake/input.wav"},
            separation={
                "status": "completed",
                "selected_stem": selected_stem,
                "selected_stem_path": "data/stems/fake/other.wav",
            },
            separation_quality={
                "status": "completed",
                "decision": "use_selected_stem",
                "likely_solo_piano": False,
            },
            transcription={
                "status": "completed",
                "transcription_method": "basic_pitch",
                "note_count": 1,
                "notes": [],
            },
            analysis={
                "status": "completed",
                "midi_path": "artifacts/tracer/fake/output.mid",
                "detected_key": "C major",
                "hvs_score": 1.0,
            },
            final_audio_path="data/stems/fake/other.wav",
            midi_path="artifacts/tracer/fake/output.mid",
            detected_key="C major",
            hvs_score=1.0,
            error=None,
        )

    monkeypatch.setattr(
        "app.mcp_tools.tools.run_audio_to_analysis_pipeline",
        fake_pipeline,
    )

    client = TestClient(app)

    response = client.post(
        "/api/tools/run_audio_to_analysis/execute",
        json={
            "payload": {
                "source": "data/samples/source.wav",
                "job_id": "api-full-pipeline",
                "use_basic_pitch": True,
                "selected_stem": "other",
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "run_audio_to_analysis"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "api-full-pipeline"
    assert data["status"] == "completed"
    assert data["final_audio_path"].endswith("other.wav")
    assert data["midi_path"].endswith("output.mid")
    assert data["detected_key"] == "C major"
    assert data["hvs_score"] == 1.0


def test_run_audio_to_analysis_tool_can_persist_result(tmp_path, monkeypatch):
    from app.pipeline.orchestrator import AudioToAnalysisPipelineResult

    db_path = tmp_path / "app.sqlite3"

    def fake_run_audio_to_analysis_pipeline(**kwargs):
        return AudioToAnalysisPipelineResult(
            job_id=kwargs["job_id"] or "pytest-api-persist",
            source=kwargs["source"],
            status="completed",
            extract={"status": "completed"},
            separation={"status": "completed"},
            separation_quality={"status": "completed"},
            transcription={
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
            analysis={
                "status": "completed",
                "detected_key": "D major",
                "hvs_score": 0.81,
            },
            final_audio_path="data/processed/pytest/input.wav",
            midi_path="artifacts/tracer/pytest/output.mid",
            detected_key="D major",
            hvs_score=0.81,
            error=None,
        )

    monkeypatch.setattr(
        "app.mcp_tools.tools.run_audio_to_analysis_pipeline",
        fake_run_audio_to_analysis_pipeline,
    )

    client = TestClient(app)

    response = client.post(
        "/api/tools/run_audio_to_analysis/execute",
        json={
            "payload": {
                "source": "data/samples/source.wav",
                "job_id": "pytest-api-persist",
                "persist": True,
                "db_path": str(db_path),
                "session_title": "Pytest API persisted run",
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "run_audio_to_analysis"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["status"] == "completed"
    assert data["persistence"] is not None
    assert data["persistence"]["session_id"].startswith("sess_")
    assert data["persistence"]["pipeline_run_id"].startswith("run_")
    assert data["persistence"]["transcription_id"].startswith("trn_")
    assert data["persistence_error"] is None
