from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app
from app.mcp_tools.registry import registry


def _write_demo_wav(path: Path) -> None:
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


def test_registry_contains_real_transcribe_audio_tool():
    tool = registry.get("transcribe_audio")

    assert tool.contract.name == "transcribe_audio"
    assert tool.contract.category == "transcription"
    assert "audio_path" in tool.contract.input_schema["properties"]


def test_transcribe_audio_tool_returns_error_when_audio_path_is_missing():
    client = TestClient(app)

    response = client.post(
        "/api/tools/transcribe_audio/execute",
        json={"payload": {}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "transcribe_audio"
    assert body["status"] == "error"
    assert body["data"] == {}
    assert body["error"] == "Missing required field: audio_path"


def test_transcribe_audio_tool_via_api_placeholder(tmp_path):
    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    client = TestClient(app)

    response = client.post(
        "/api/tools/transcribe_audio/execute",
        json={
            "payload": {
                "audio_path": str(audio_path),
                "output_dir": str(tmp_path / "transcription"),
                "job_id": "api-transcribe-placeholder",
                "use_basic_pitch": False,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "transcribe_audio"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "api-transcribe-placeholder"
    assert data["status"] == "completed"
    assert data["transcription_method"] == "placeholder_midi"
    assert data["note_count"] == 1
    assert data["notes"][0]["pitch"] == 60
    assert data["notes"][0]["pitch_name"] == "C4"
