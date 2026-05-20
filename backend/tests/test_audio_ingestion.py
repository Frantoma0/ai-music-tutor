from __future__ import annotations

import numpy as np
import soundfile as sf

from app.pipeline.audio_ingestion import extract_audio


def test_extract_audio_normalizes_local_wav(tmp_path):
    sample_rate = 16_000
    duration_seconds = 1.0

    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )

    audio = 0.2 * np.sin(2 * np.pi * 440.0 * t)

    source_path = tmp_path / "source.wav"
    sf.write(source_path, audio, sample_rate)

    result = extract_audio(
        source=source_path,
        output_dir=tmp_path / "processed",
        job_id="pytest-audio",
    )

    assert result.status == "completed"
    assert result.input_type == "file"
    assert result.wav_path.endswith("input.wav")
    assert result.sample_rate == 44100
    assert result.channels == 1
    assert result.duration_seconds is not None
    assert result.error is None


def test_extract_audio_returns_error_for_missing_file(tmp_path):
    result = extract_audio(
        source=tmp_path / "missing.wav",
        output_dir=tmp_path / "processed",
        job_id="pytest-missing",
    )

    assert result.status == "error"
    assert result.error is not None
    assert "FileNotFoundError" in result.error


def test_extract_audio_url_input_with_mocked_download(tmp_path, monkeypatch):
    sample_rate = 16_000
    duration_seconds = 1.0

    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )

    audio = 0.2 * np.sin(2 * np.pi * 440.0 * t)

    downloaded_path = tmp_path / "downloaded.wav"
    sf.write(downloaded_path, audio, sample_rate)

    def fake_download(source_url, output_dir):
        return downloaded_path

    monkeypatch.setattr(
        "app.pipeline.audio_ingestion._download_with_ytdlp",
        fake_download,
    )

    result = extract_audio(
        source="https://example.com/audio.wav",
        output_dir=tmp_path / "processed",
        job_id="pytest-url",
    )

    assert result.status == "completed"
    assert result.input_type == "url"
    assert result.sample_rate == 44100
    assert result.channels == 1
    assert result.wav_path.endswith("input.wav")
    assert result.error is None
