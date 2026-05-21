from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pretty_midi


@dataclass
class TranscriptionResult:
    job_id: str
    input_audio: str
    midi_path: str | None
    status: str
    transcription_method: str
    note_count: int
    notes: list[dict[str, Any]]
    transcription_error: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _write_placeholder_midi(midi_path: Path) -> None:
    midi_path.parent.mkdir(parents=True, exist_ok=True)

    midi = pretty_midi.PrettyMIDI()
    piano = pretty_midi.Instrument(program=0, name="Placeholder Piano")

    piano.notes.append(
        pretty_midi.Note(
            velocity=90,
            pitch=60,
            start=0.0,
            end=1.0,
        )
    )

    midi.instruments.append(piano)
    midi.write(str(midi_path))


def _extract_note_events(midi_path: str | Path) -> list[dict[str, Any]]:
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    notes: list[dict[str, Any]] = []

    note_id = 0

    for instrument_index, instrument in enumerate(midi.instruments):
        if instrument.is_drum:
            continue

        instrument_name = instrument.name or pretty_midi.program_to_instrument_name(
            instrument.program
        )

        for note in sorted(instrument.notes, key=lambda item: (item.start, item.pitch)):
            notes.append(
                {
                    "id": f"n{note_id}",
                    "instrument_index": instrument_index,
                    "instrument_name": instrument_name,
                    "program": int(instrument.program),
                    "pitch": int(note.pitch),
                    "pitch_name": pretty_midi.note_number_to_name(note.pitch),
                    "start": round(float(note.start), 6),
                    "end": round(float(note.end), 6),
                    "duration": round(float(note.end - note.start), 6),
                    "velocity": int(note.velocity),
                    "confidence": None,
                }
            )

            note_id += 1

    return notes


def _try_basic_pitch(audio_path: Path, raw_output_dir: Path, normalized_midi_path: Path) -> tuple[Path | None, str | None]:
    """
    Run Basic Pitch and normalize its generated MIDI path to output.mid.

    Returns:
        (midi_path, None) on success
        (None, error_message) on failure
    """
    try:
        from basic_pitch import ICASSP_2022_MODEL_PATH
        from basic_pitch.inference import predict_and_save

        if raw_output_dir.exists():
            shutil.rmtree(raw_output_dir)

        raw_output_dir.mkdir(parents=True, exist_ok=True)

        predict_and_save(
            [str(audio_path)],
            str(raw_output_dir),
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
        )

        midi_candidates = sorted(
            list(raw_output_dir.glob("*.mid")) + list(raw_output_dir.glob("*.midi"))
        )

        if not midi_candidates:
            return None, "Basic Pitch finished but did not create a MIDI file."

        generated_midi = midi_candidates[0]
        normalized_midi_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated_midi, normalized_midi_path)

        return normalized_midi_path, None

    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"




def _mirror_transcription_to_data_midi(
    result: TranscriptionResult,
    job_id: str,
) -> None:
    """
    Compatibility mirror for roadmap wording:
    save raw MIDI and note list JSON under data/midi/{job_id}/.

    Primary artifacts remain in the configured output_dir.
    """
    mirror_dir = Path("data/midi") / job_id
    mirror_dir.mkdir(parents=True, exist_ok=True)

    if result.midi_path is not None:
        source_midi = Path(result.midi_path)
        if source_midi.exists():
            shutil.copyfile(source_midi, mirror_dir / "output.mid")

    (mirror_dir / "notes.json").write_text(
        json.dumps(result.notes, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (mirror_dir / "result.json").write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_transcription_artifacts(
    result: TranscriptionResult,
    job_dir: Path,
) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)

    result_path = job_dir / "result.json"
    notes_path = job_dir / "notes.json"

    result_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    notes_path.write_text(
        json.dumps(result.notes, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def transcribe_audio(
    audio_path: str | Path,
    output_dir: str | Path = "artifacts/transcription",
    job_id: str | None = None,
    use_basic_pitch: bool = True,
) -> TranscriptionResult:
    """
    T3 transcribe_audio.

    Converts an audio file into MIDI and extracts structured note events.
    Basic Pitch is used when requested and available. If it fails, the function
    falls back to a deterministic placeholder MIDI so downstream pipeline steps
    can continue during development.
    """
    job_id = job_id or uuid.uuid4().hex[:12]
    audio_path = Path(audio_path)

    job_dir = Path(output_dir) / job_id
    midi_path = job_dir / "output.mid"
    raw_output_dir = job_dir / "basic_pitch_raw"

    try:
        if not audio_path.exists():
            raise FileNotFoundError(f"Input audio not found: {audio_path}")

        if not audio_path.is_file():
            raise ValueError(f"Input audio path is not a file: {audio_path}")

        transcription_error = None

        if use_basic_pitch:
            generated_midi, transcription_error = _try_basic_pitch(
                audio_path=audio_path,
                raw_output_dir=raw_output_dir,
                normalized_midi_path=midi_path,
            )

            if generated_midi is not None:
                notes = _extract_note_events(generated_midi)

                result = TranscriptionResult(
                    job_id=job_id,
                    input_audio=str(audio_path),
                    midi_path=str(generated_midi),
                    status="completed",
                    transcription_method="basic_pitch",
                    note_count=len(notes),
                    notes=notes,
                    transcription_error=None,
                    error=None,
                )

                _write_transcription_artifacts(result, job_dir)

                return result

        _write_placeholder_midi(midi_path)
        notes = _extract_note_events(midi_path)

        method = (
            "placeholder_midi_after_basic_pitch_fallback"
            if use_basic_pitch
            else "placeholder_midi"
        )

        result = TranscriptionResult(
            job_id=job_id,
            input_audio=str(audio_path),
            midi_path=str(midi_path),
            status="completed",
            transcription_method=method,
            note_count=len(notes),
            notes=notes,
            transcription_error=transcription_error,
            error=None,
        )

        _write_transcription_artifacts(result, job_dir)
        _mirror_transcription_to_data_midi(result, job_id)

        return result

    except Exception as exc:
        result = TranscriptionResult(
            job_id=job_id,
            input_audio=str(audio_path),
            midi_path=None,
            status="error",
            transcription_method="none",
            note_count=0,
            notes=[],
            transcription_error=None,
            error=f"{type(exc).__name__}: {exc}",
        )

        _write_transcription_artifacts(result, job_dir)
        _mirror_transcription_to_data_midi(result, job_id)

        return result
