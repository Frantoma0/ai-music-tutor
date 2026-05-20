from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pretty_midi
import pytest
import soundfile as sf

from app.pipeline.tracer import run_tracer_bullet
from app.pipeline.transcription import TranscriptionResult


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


def _write_demo_midi(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    midi = pretty_midi.PrettyMIDI()
    piano = pretty_midi.Instrument(program=0, name="Test Piano")

    for pitch, start, end in [
        (60, 0.0, 0.5),
        (64, 0.5, 1.0),
        (67, 1.0, 1.5),
    ]:
        piano.notes.append(
            pretty_midi.Note(
                velocity=90,
                pitch=pitch,
                start=start,
                end=end,
            )
        )

    midi.instruments.append(piano)
    midi.write(str(path))


def test_tracer_bullet_creates_midi_and_result_json(tmp_path):
    audio_path = tmp_path / "demo.wav"
    _write_demo_wav(audio_path)

    result = run_tracer_bullet(
        audio_path=audio_path,
        artifacts_dir=tmp_path / "artifacts",
        job_id="pytest-tracer",
        use_basic_pitch=False,
    )

    assert result.status == "completed"
    assert result.transcription_method == "placeholder_midi"
    assert result.midi_path.endswith("output.mid")
    assert Path(result.midi_path).exists()
    assert result.detected_key
    assert 0.0 <= result.hvs_score <= 1.0

    result_json = tmp_path / "artifacts" / "pytest-tracer" / "result.json"
    assert result_json.exists()

    data = json.loads(result_json.read_text(encoding="utf-8"))
    assert data["job_id"] == "pytest-tracer"
    assert data["status"] == "completed"


def test_tracer_bullet_raises_for_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_tracer_bullet(
            audio_path=tmp_path / "missing.wav",
            artifacts_dir=tmp_path / "artifacts",
            job_id="pytest-missing",
        )


def test_tracer_bullet_basic_pitch_success_path_is_reported(tmp_path, monkeypatch):
    audio_path = tmp_path / "demo.wav"
    _write_demo_wav(audio_path)

    def fake_transcribe_audio(
        audio_path,
        output_dir="artifacts/transcription",
        job_id=None,
        use_basic_pitch=True,
    ):
        midi_path = Path(output_dir) / (job_id or "fake-job") / "output.mid"
        _write_demo_midi(midi_path)

        return TranscriptionResult(
            job_id=job_id or "fake-job",
            input_audio=str(audio_path),
            midi_path=str(midi_path),
            status="completed",
            transcription_method="basic_pitch",
            note_count=3,
            notes=[],
            transcription_error=None,
            error=None,
        )

    monkeypatch.setattr(
        "app.pipeline.tracer.transcribe_audio",
        fake_transcribe_audio,
    )

    result = run_tracer_bullet(
        audio_path=audio_path,
        artifacts_dir=tmp_path / "artifacts",
        job_id="pytest-basic-pitch-success",
        use_basic_pitch=True,
    )

    assert result.status == "completed"
    assert result.transcription_method == "basic_pitch"
    assert result.transcription_error is None
    assert result.midi_path.endswith("output.mid")
    assert result.detected_key
    assert 0.0 <= result.hvs_score <= 1.0


def test_tracer_bullet_basic_pitch_fallback_exposes_reason(tmp_path, monkeypatch):
    audio_path = tmp_path / "demo.wav"
    _write_demo_wav(audio_path)

    def fake_transcribe_audio(
        audio_path,
        output_dir="artifacts/transcription",
        job_id=None,
        use_basic_pitch=True,
    ):
        midi_path = Path(output_dir) / (job_id or "fake-job") / "output.mid"
        _write_demo_midi(midi_path)

        return TranscriptionResult(
            job_id=job_id or "fake-job",
            input_audio=str(audio_path),
            midi_path=str(midi_path),
            status="completed",
            transcription_method="placeholder_midi_after_basic_pitch_fallback",
            note_count=3,
            notes=[],
            transcription_error="RuntimeError: simulated Basic Pitch failure",
            error=None,
        )

    monkeypatch.setattr(
        "app.pipeline.tracer.transcribe_audio",
        fake_transcribe_audio,
    )

    result = run_tracer_bullet(
        audio_path=audio_path,
        artifacts_dir=tmp_path / "artifacts",
        job_id="pytest-basic-pitch-fallback",
        use_basic_pitch=True,
    )

    assert result.status == "completed"
    assert result.transcription_method == "placeholder_midi_after_basic_pitch_fallback"
    assert result.transcription_error == "RuntimeError: simulated Basic Pitch failure"
    assert result.midi_path.endswith("output.mid")


def test_tracer_bullet_returns_error_when_transcription_layer_fails(tmp_path, monkeypatch):
    audio_path = tmp_path / "demo.wav"
    _write_demo_wav(audio_path)

    def fake_transcribe_audio(
        audio_path,
        output_dir="artifacts/transcription",
        job_id=None,
        use_basic_pitch=True,
    ):
        return TranscriptionResult(
            job_id=job_id or "fake-job",
            input_audio=str(audio_path),
            midi_path=None,
            status="error",
            transcription_method="none",
            note_count=0,
            notes=[],
            transcription_error=None,
            error="RuntimeError: simulated transcription failure",
        )

    monkeypatch.setattr(
        "app.pipeline.tracer.transcribe_audio",
        fake_transcribe_audio,
    )

    result = run_tracer_bullet(
        audio_path=audio_path,
        artifacts_dir=tmp_path / "artifacts",
        job_id="pytest-transcription-error",
        use_basic_pitch=True,
    )

    assert result.status == "error"
    assert result.error == "RuntimeError: simulated transcription failure"
    assert result.transcription_method == "none"
