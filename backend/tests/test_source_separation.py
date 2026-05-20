from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from app.pipeline.source_separation import separate_sources


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


def test_separate_sources_collects_demucs_stems(tmp_path, monkeypatch):
    input_wav = tmp_path / "input.wav"
    _write_demo_wav(input_wav)

    def fake_run_command(command):
        output_dir = Path(command[command.index("-o") + 1])
        model_name = command[command.index("-n") + 1]
        track_dir = output_dir / model_name / input_wav.stem
        track_dir.mkdir(parents=True, exist_ok=True)

        for stem_name in ["vocals", "drums", "bass", "other"]:
            _write_demo_wav(track_dir / f"{stem_name}.wav")

        class FakeCompletedProcess:
            stdout = "fake demucs success"
            stderr = ""

        return FakeCompletedProcess()

    monkeypatch.setattr(
        "app.pipeline.source_separation._run_command",
        fake_run_command,
    )

    result = separate_sources(
        wav_path=input_wav,
        output_dir=tmp_path / "stems",
        job_id="pytest-demucs",
    )

    assert result.status == "completed"
    assert result.job_id == "pytest-demucs"
    assert result.selected_stem == "other"
    assert result.selected_stem_path is not None
    assert result.selected_stem_path.endswith("other.wav")
    assert set(result.stems) == {"vocals", "drums", "bass", "other"}


def test_separate_sources_returns_error_for_missing_input(tmp_path):
    result = separate_sources(
        wav_path=tmp_path / "missing.wav",
        output_dir=tmp_path / "stems",
        job_id="pytest-missing-demucs",
    )

    assert result.status == "error"
    assert result.error is not None
    assert "FileNotFoundError" in result.error
    assert result.selected_stem_path is None
    assert result.stems == {}
