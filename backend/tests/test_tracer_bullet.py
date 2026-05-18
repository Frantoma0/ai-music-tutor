from __future__ import annotations

import numpy as np
import soundfile as sf

from app.pipeline.tracer import run_tracer_bullet


def test_tracer_bullet_creates_midi_and_detects_key(tmp_path):
    sample_rate = 16_000
    duration_seconds = 1.0

    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )

    # Simple A4 sine wave. The current tracer does not perform real AMT yet;
    # it only requires a valid audio file as pipeline input.
    audio = 0.2 * np.sin(2 * np.pi * 440.0 * t)

    audio_path = tmp_path / "demo.wav"
    sf.write(audio_path, audio, sample_rate)

    result = run_tracer_bullet(
        audio_path=audio_path,
        artifacts_dir=tmp_path / "artifacts",
        job_id="pytest-demo",
        use_basic_pitch=False,
    )

    assert result.status == "completed"
    assert result.input_audio.endswith("demo.wav")
    assert result.midi_path.endswith("output.mid")
    assert result.hvs_score == 0.0
    assert result.transcription_method == "placeholder_midi"
    assert "major" in result.detected_key.lower()
