from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from app.pipeline.audio_ingestion import extract_audio
from app.pipeline.source_separation import separate_sources


def _write_demo_wav(path: Path, sample_rate: int = 16_000) -> None:
    duration_seconds = 1.0

    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )

    audio = 0.2 * np.sin(2 * np.pi * 440.0 * t)
    sf.write(path, audio, sample_rate)


def test_t1_extract_audio_feeds_t2_source_separation(tmp_path, monkeypatch):
    source_path = tmp_path / "source.wav"
    _write_demo_wav(source_path, sample_rate=16_000)

    def fake_run_command(command):
        output_dir = Path(command[command.index("-o") + 1])
        model_name = command[command.index("-n") + 1]
        input_wav = Path(command[-1])

        track_dir = output_dir / model_name / input_wav.stem
        track_dir.mkdir(parents=True, exist_ok=True)

        for stem_name in ["vocals", "drums", "bass", "other"]:
            _write_demo_wav(track_dir / f"{stem_name}.wav", sample_rate=44_100)

        class FakeCompletedProcess:
            stdout = "fake demucs success"
            stderr = ""

        return FakeCompletedProcess()

    monkeypatch.setattr(
        "app.pipeline.source_separation._run_command",
        fake_run_command,
    )

    extract_result = extract_audio(
        source=source_path,
        output_dir=tmp_path / "processed",
        job_id="pytest-t1-t2",
    )

    assert extract_result.status == "completed"
    assert extract_result.sample_rate == 44100
    assert extract_result.channels == 1

    separation_result = separate_sources(
        wav_path=extract_result.wav_path,
        output_dir=tmp_path / "stems",
        job_id="pytest-t1-t2",
    )

    assert separation_result.status == "completed"
    assert separation_result.input_wav == extract_result.wav_path
    assert separation_result.selected_stem == "other"
    assert separation_result.selected_stem_path is not None
    assert separation_result.selected_stem_path.endswith("other.wav")
    assert set(separation_result.stems) == {"vocals", "drums", "bass", "other"}
