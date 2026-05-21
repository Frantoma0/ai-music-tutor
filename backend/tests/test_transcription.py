from __future__ import annotations

from pathlib import Path

import numpy as np
import pretty_midi
import soundfile as sf

from app.pipeline.transcription import transcribe_audio


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

    piano.notes.append(
        pretty_midi.Note(
            velocity=90,
            pitch=60,
            start=0.0,
            end=0.5,
        )
    )

    piano.notes.append(
        pretty_midi.Note(
            velocity=80,
            pitch=64,
            start=0.5,
            end=1.0,
        )
    )

    midi.instruments.append(piano)
    midi.write(str(path))


def test_transcribe_audio_placeholder_path(tmp_path):
    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    result = transcribe_audio(
        audio_path=audio_path,
        output_dir=tmp_path / "transcription",
        job_id="pytest-placeholder",
        use_basic_pitch=False,
    )

    assert result.status == "completed"
    assert result.transcription_method == "placeholder_midi"
    assert result.midi_path is not None
    assert result.midi_path.endswith("output.mid")
    assert result.note_count == 1
    assert len(result.notes) == 1
    assert result.notes[0]["pitch"] == 60
    assert result.notes[0]["pitch_name"] == "C4"


def test_transcribe_audio_basic_pitch_path_with_mock(tmp_path, monkeypatch):
    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    def fake_try_basic_pitch(audio_path, raw_output_dir, normalized_midi_path):
        _write_demo_midi(normalized_midi_path)
        return normalized_midi_path, [(0.0, 0.5, 60, 0.91, None), (0.5, 1.0, 64, 0.87, None)], None

    monkeypatch.setattr(
        "app.pipeline.transcription._try_basic_pitch",
        fake_try_basic_pitch,
    )

    result = transcribe_audio(
        audio_path=audio_path,
        output_dir=tmp_path / "transcription",
        job_id="pytest-basic-pitch",
        use_basic_pitch=True,
    )

    assert result.status == "completed"
    assert result.transcription_method == "basic_pitch"
    assert result.transcription_error is None
    assert result.note_count == 2
    assert [note["pitch"] for note in result.notes] == [60, 64]
    assert result.notes[0]["confidence"] == 0.91
    assert result.notes[1]["confidence"] == 0.87


def test_transcribe_audio_falls_back_when_basic_pitch_fails(tmp_path, monkeypatch):
    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    def fake_try_basic_pitch(audio_path, raw_output_dir, normalized_midi_path):
        return None, None, "RuntimeError: fake basic pitch failure"

    monkeypatch.setattr(
        "app.pipeline.transcription._try_basic_pitch",
        fake_try_basic_pitch,
    )

    result = transcribe_audio(
        audio_path=audio_path,
        output_dir=tmp_path / "transcription",
        job_id="pytest-fallback",
        use_basic_pitch=True,
    )

    assert result.status == "completed"
    assert result.transcription_method == "placeholder_midi_after_basic_pitch_fallback"
    assert result.transcription_error == "RuntimeError: fake basic pitch failure"
    assert result.note_count == 1


def test_transcribe_audio_returns_error_for_missing_input(tmp_path):
    result = transcribe_audio(
        audio_path=tmp_path / "missing.wav",
        output_dir=tmp_path / "transcription",
        job_id="pytest-missing",
        use_basic_pitch=False,
    )

    assert result.status == "error"
    assert result.error is not None
    assert "FileNotFoundError" in result.error
    assert result.midi_path is None
    assert result.note_count == 0
    assert result.notes == []


def test_transcription_result_is_json_serializable(tmp_path):
    import json

    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    result = transcribe_audio(
        audio_path=audio_path,
        output_dir=tmp_path / "transcription",
        job_id="pytest-json",
        use_basic_pitch=False,
    )

    encoded = json.dumps(result.to_dict())

    assert "placeholder_midi" in encoded


def test_transcribe_audio_writes_result_and_notes_json(tmp_path):
    import json
    from pathlib import Path

    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    result = transcribe_audio(
        audio_path=audio_path,
        output_dir=tmp_path / "transcription",
        job_id="pytest-artifacts",
        use_basic_pitch=False,
    )

    job_dir = Path(tmp_path / "transcription" / "pytest-artifacts")
    result_path = job_dir / "result.json"
    notes_path = job_dir / "notes.json"

    assert result.status == "completed"
    assert result_path.exists()
    assert notes_path.exists()

    result_data = json.loads(result_path.read_text(encoding="utf-8"))
    notes_data = json.loads(notes_path.read_text(encoding="utf-8"))

    assert result_data["job_id"] == "pytest-artifacts"
    assert result_data["midi_path"].endswith("output.mid")
    assert result_data["note_count"] == 1

    assert isinstance(notes_data, list)
    assert notes_data[0]["pitch"] == 60
    assert notes_data[0]["pitch_name"] == "C4"


def test_transcribe_audio_writes_error_result_json(tmp_path):
    import json
    from pathlib import Path

    result = transcribe_audio(
        audio_path=tmp_path / "missing.wav",
        output_dir=tmp_path / "transcription",
        job_id="pytest-error-artifacts",
        use_basic_pitch=False,
    )

    job_dir = Path(tmp_path / "transcription" / "pytest-error-artifacts")
    result_path = job_dir / "result.json"
    notes_path = job_dir / "notes.json"

    assert result.status == "error"
    assert result_path.exists()
    assert notes_path.exists()

    result_data = json.loads(result_path.read_text(encoding="utf-8"))
    notes_data = json.loads(notes_path.read_text(encoding="utf-8"))

    assert result_data["status"] == "error"
    assert "FileNotFoundError" in result_data["error"]
    assert notes_data == []


def test_transcribe_audio_mirrors_output_to_data_midi(tmp_path, monkeypatch):
    import json
    from pathlib import Path

    monkeypatch.chdir(tmp_path)

    audio_path = tmp_path / "source.wav"
    _write_demo_wav(audio_path)

    result = transcribe_audio(
        audio_path=audio_path,
        output_dir=tmp_path / "transcription",
        job_id="pytest-data-midi",
        use_basic_pitch=False,
    )

    mirror_dir = Path("data/midi/pytest-data-midi")

    assert result.status == "completed"
    assert (mirror_dir / "output.mid").exists()
    assert (mirror_dir / "notes.json").exists()
    assert (mirror_dir / "result.json").exists()

    notes = json.loads((mirror_dir / "notes.json").read_text(encoding="utf-8"))
    assert notes[0]["pitch_name"] == "C4"
