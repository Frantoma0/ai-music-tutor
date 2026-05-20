from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app
from app.mcp_tools.registry import registry


def _write_demo_wav(path: Path) -> None:
    sample_rate = 44_100
    duration_seconds = 1.0

    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )

    audio = 0.2 * np.sin(2 * np.pi * 440.0 * t)
    sf.write(path, audio, sample_rate)


def test_registry_contains_real_separate_sources_tool():
    tool = registry.get("separate_sources")

    assert tool.contract.name == "separate_sources"
    assert tool.contract.category == "audio"
    assert tool.contract.uses_gpu is True
    assert "wav_path" in tool.contract.input_schema["properties"]


def test_separate_sources_tool_returns_error_when_wav_path_is_missing():
    client = TestClient(app)

    response = client.post(
        "/api/tools/separate_sources/execute",
        json={"payload": {}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "separate_sources"
    assert body["status"] == "error"
    assert body["data"] == {}
    assert body["error"] == "Missing required field: wav_path"


def test_separate_sources_tool_via_api(tmp_path, monkeypatch):
    audio_path = tmp_path / "input.wav"
    _write_demo_wav(audio_path)

    def fake_separate_sources(
        wav_path,
        output_dir="data/stems",
        job_id=None,
        model_name="htdemucs",
        selected_stem="other",
    ):
        from app.pipeline.source_separation import SourceSeparationResult

        output_root = Path(output_dir) / (job_id or "fake-job")
        track_dir = output_root / "demucs" / model_name / "input"
        track_dir.mkdir(parents=True, exist_ok=True)

        stems = {}

        for stem_name in ["vocals", "drums", "bass", "other"]:
            stem_path = track_dir / f"{stem_name}.wav"
            _write_demo_wav(stem_path)
            stems[stem_name] = str(stem_path)

        return SourceSeparationResult(
            job_id=job_id or "fake-job",
            input_wav=str(wav_path),
            output_dir=str(output_root),
            model_name=model_name,
            stems=stems,
            selected_stem=selected_stem,
            selected_stem_path=stems[selected_stem],
            status="completed",
            error=None,
        )

    monkeypatch.setattr(
        "app.mcp_tools.tools.separate_sources",
        fake_separate_sources,
    )

    client = TestClient(app)

    response = client.post(
        "/api/tools/separate_sources/execute",
        json={
            "payload": {
                "wav_path": str(audio_path),
                "output_dir": str(tmp_path / "stems"),
                "job_id": "api-demucs-demo",
                "selected_stem": "other",
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "separate_sources"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "api-demucs-demo"
    assert data["status"] == "completed"
    assert data["selected_stem"] == "other"
    assert data["selected_stem_path"].endswith("other.wav")
    assert set(data["stems"]) == {"vocals", "drums", "bass", "other"}
