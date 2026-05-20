from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from app.pipeline.separation_quality import analyze_separation_quality


def _write_tone(path: Path, amplitude: float, sample_rate: int = 44_100) -> None:
    duration_seconds = 1.0

    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )

    audio = amplitude * np.sin(2 * np.pi * 440.0 * t)
    sf.write(path, audio, sample_rate)


def test_analyze_separation_quality_detects_likely_solo_piano(tmp_path):
    input_wav = tmp_path / "input.wav"
    _write_tone(input_wav, amplitude=0.2)

    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()

    stems = {
        "vocals": str(stems_dir / "vocals.wav"),
        "drums": str(stems_dir / "drums.wav"),
        "bass": str(stems_dir / "bass.wav"),
        "other": str(stems_dir / "other.wav"),
    }

    _write_tone(Path(stems["vocals"]), amplitude=0.001)
    _write_tone(Path(stems["drums"]), amplitude=0.001)
    _write_tone(Path(stems["bass"]), amplitude=0.001)
    _write_tone(Path(stems["other"]), amplitude=0.2)

    result = analyze_separation_quality(
        input_wav=input_wav,
        stems=stems,
        selected_stem="other",
    )

    assert result.likely_solo_piano is True
    assert result.decision == "prefer_original_wav"
    assert result.recommended_audio_path == str(input_wav)
    assert result.non_selected_energy_ratio <= 0.05


def test_analyze_separation_quality_uses_selected_stem_for_mixed_audio(tmp_path):
    input_wav = tmp_path / "input.wav"
    _write_tone(input_wav, amplitude=0.2)

    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()

    stems = {
        "vocals": str(stems_dir / "vocals.wav"),
        "drums": str(stems_dir / "drums.wav"),
        "bass": str(stems_dir / "bass.wav"),
        "other": str(stems_dir / "other.wav"),
    }

    _write_tone(Path(stems["vocals"]), amplitude=0.15)
    _write_tone(Path(stems["drums"]), amplitude=0.12)
    _write_tone(Path(stems["bass"]), amplitude=0.10)
    _write_tone(Path(stems["other"]), amplitude=0.2)

    result = analyze_separation_quality(
        input_wav=input_wav,
        stems=stems,
        selected_stem="other",
    )

    assert result.likely_solo_piano is False
    assert result.decision == "use_selected_stem"
    assert result.recommended_audio_path == stems["other"]
    assert result.non_selected_energy_ratio > 0.05
