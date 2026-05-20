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


def test_registry_contains_real_extract_audio_tool():
    tool = registry.get("extract_audio")

    assert tool.contract.name == "extract_audio"
    assert tool.contract.category == "ingestion"
    assert tool.contract.deterministic is True
    assert tool.contract.uses_gpu is False
    assert "source" in tool.contract.input_schema["properties"]


def test_extract_audio_tool_via_api(tmp_path):
    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    client = TestClient(app)

    response = client.post(
        "/api/tools/extract_audio/execute",
        json={
            "payload": {
                "source": str(audio_path),
                "output_dir": str(tmp_path / "processed"),
                "job_id": "api-extract-demo",
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "extract_audio"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "api-extract-demo"
    assert data["input_type"] == "file"
    assert data["status"] == "completed"
    assert data["sample_rate"] == 44100
    assert data["channels"] == 1
    assert data["wav_path"].endswith("input.wav")
