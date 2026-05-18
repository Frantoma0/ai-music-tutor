from __future__ import annotations

import numpy as np
import soundfile as sf

from app.pipeline.tracer import run_tracer_bullet


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


def test_tracer_bullet_creates_midi_and_detects_key(tmp_path):
    audio_path = tmp_path / "demo.wav"
    _write_demo_wav(audio_path)

    result = run_tracer_bullet(
        audio_path=audio_path,
        artifacts_dir=tmp_path / "artifacts",
        job_id="pytest-demo",
        use_basic_pitch=False,
    )

    assert result.status == "completed"
    assert result.input_audio.endswith("demo.wav")
    assert result.midi_path.endswith("output.mid")
    assert 0.0 <= result.hvs_score <= 1.0
    assert result.hvs_score > 0.0
    assert result.transcription_method == "placeholder_midi"
    assert result.transcription_error is None
    assert "major" in result.detected_key.lower()


def test_tracer_bullet_basic_pitch_success_path_is_reported(tmp_path, monkeypatch):
    audio_path = tmp_path / "demo.wav"
    _write_demo_wav(audio_path)

    def fake_try_basic_pitch(audio_path, job_dir):
        from app.pipeline.tracer import _create_placeholder_midi

        midi_path = job_dir / "output.mid"
        _create_placeholder_midi(midi_path)
        return midi_path, None

    monkeypatch.setattr(
        "app.pipeline.tracer._try_basic_pitch",
        fake_try_basic_pitch,
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


def test_tracer_bullet_basic_pitch_fallback_exposes_reason(tmp_path, monkeypatch):
    audio_path = tmp_path / "demo.wav"
    _write_demo_wav(audio_path)

    def fake_try_basic_pitch(audio_path, job_dir):
        return None, "RuntimeError: simulated Basic Pitch failure"

    monkeypatch.setattr(
        "app.pipeline.tracer._try_basic_pitch",
        fake_try_basic_pitch,
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
