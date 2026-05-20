from __future__ import annotations

from pathlib import Path

import numpy as np
import pretty_midi
import soundfile as sf

from app.pipeline.models import TracerBulletResult
from app.pipeline.transcription import TranscriptionResult
from app.pipeline.tracer import run_tracer_bullet


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


def _write_c_major_midi(path: Path) -> None:
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


def test_run_tracer_bullet_uses_transcription_layer(tmp_path, monkeypatch):
    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    def fake_transcribe_audio(
        audio_path,
        output_dir="artifacts/transcription",
        job_id=None,
        use_basic_pitch=True,
    ):
        midi_path = Path(output_dir) / (job_id or "fake-job") / "output.mid"
        _write_c_major_midi(midi_path)

        return TranscriptionResult(
            job_id=job_id or "fake-job",
            input_audio=str(audio_path),
            midi_path=str(midi_path),
            status="completed",
            transcription_method="fake_transcription_layer",
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
        artifacts_dir=tmp_path / "tracer",
        job_id="pytest-tracer-transcription",
        use_basic_pitch=True,
    )

    assert isinstance(result, TracerBulletResult)
    assert result.status == "completed"
    assert result.transcription_method == "fake_transcription_layer"
    assert result.midi_path.endswith("output.mid")
    assert result.detected_key
    assert 0.0 <= result.hvs_score <= 1.0
