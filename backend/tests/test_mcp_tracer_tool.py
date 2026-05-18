from __future__ import annotations

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app
from app.mcp_tools.registry import registry


def _write_demo_wav(path):
    sample_rate = 16_000
    duration_seconds = 1.0

    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )

    audio = 0.2 * np.sin(2 * np.pi * 440.0 * t)
    sf.write(path, audio, sample_rate)


def test_registry_contains_run_tracer_bullet_tool():
    assert "run_tracer_bullet" in registry.names()
    assert registry.count() == 10


def test_run_tracer_bullet_tool_via_api(tmp_path):
    audio_path = tmp_path / "demo.wav"
    _write_demo_wav(audio_path)

    client = TestClient(app)

    response = client.post(
        "/api/tools/run_tracer_bullet/execute",
        json={
            "payload": {
                "audio_path": str(audio_path),
                "artifacts_dir": str(tmp_path / "artifacts"),
                "job_id": "api-demo",
                "use_basic_pitch": False,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "run_tracer_bullet"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "api-demo"
    assert data["status"] == "completed"
    assert data["transcription_method"] == "placeholder_midi"
    assert data["midi_path"].endswith("output.mid")
    assert "major" in data["detected_key"].lower()
