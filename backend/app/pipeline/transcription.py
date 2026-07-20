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


def _match_basic_pitch_confidence(
    note_start: float,
    note_end: float,
    note_pitch: int,
    basic_pitch_note_events: list[tuple] | None,
) -> float | None:
    if not basic_pitch_note_events:
        return None

    candidates = []

    for event in basic_pitch_note_events:
        if len(event) < 4:
            continue

        event_start, event_end, event_pitch, event_amplitude = event[:4]

        if int(event_pitch) != int(note_pitch):
            continue

        distance = abs(float(event_start) - note_start) + abs(float(event_end) - note_end)
        candidates.append((distance, float(event_amplitude)))

    if not candidates:
        return None

    _, confidence = min(candidates, key=lambda item: item[0])

    return round(confidence, 6)


def _extract_note_events(
    midi_path: str | Path,
    basic_pitch_note_events: list[tuple] | None = None,
) -> list[dict[str, Any]]:
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
                    "confidence": _match_basic_pitch_confidence(
                        note_start=float(note.start),
                        note_end=float(note.end),
                        note_pitch=int(note.pitch),
                        basic_pitch_note_events=basic_pitch_note_events,
                    ),
                }
            )

            note_id += 1

    return notes


def _env_float(name: str, default: float) -> float:
    import os

    raw = os.environ.get(name)

    if raw is None or raw.strip() == "":
        return default

    try:
        return float(raw)
    except ValueError:
        return default


def _basic_pitch_settings() -> dict:
    """
    Detection thresholds for Basic Pitch, tunable via environment.

    The defaults are intentionally stricter than the library defaults
    (onset 0.5 / frame 0.3 / min length ~58 ms): real-world YouTube audio
    with reverb, sustain pedal and compression produces a large number of
    weak false positives at the library defaults. Raising the thresholds
    keeps the confident, audible notes and drops overtone ghosts and
    reverb tails at the source, before any downstream filtering.

        DAITUNE_BP_ONSET_THRESHOLD    default 0.60  (higher = fewer note starts)
        DAITUNE_BP_FRAME_THRESHOLD    default 0.40  (higher = fewer weak sustains)
        DAITUNE_BP_MIN_NOTE_LENGTH_MS default 110   (drop sub-110 ms blips)
        DAITUNE_BP_MIN_FREQUENCY_HZ   default 30    (below piano range = rumble)
        DAITUNE_BP_MAX_FREQUENCY_HZ   default 4200  (above piano range = hiss)
    """
    return {
        "onset_threshold": _env_float("DAITUNE_BP_ONSET_THRESHOLD", 0.60),
        "frame_threshold": _env_float("DAITUNE_BP_FRAME_THRESHOLD", 0.40),
        "minimum_note_length": _env_float("DAITUNE_BP_MIN_NOTE_LENGTH_MS", 110.0),
        "minimum_frequency": _env_float("DAITUNE_BP_MIN_FREQUENCY_HZ", 30.0),
        "maximum_frequency": _env_float("DAITUNE_BP_MAX_FREQUENCY_HZ", 4200.0),
    }


def _try_basic_pitch(
    audio_path: Path,
    raw_output_dir: Path,
    normalized_midi_path: Path,
) -> tuple[Path | None, list[tuple] | None, str | None]:
    """
    Run Basic Pitch and normalize its generated MIDI path to output.mid.

    Uses predict() instead of predict_and_save() so we can keep note_events,
    including the Basic Pitch amplitude/confidence-like value per note.

    Returns:
        (midi_path, note_events, None) on success
        (None, None, error_message) on failure
    """
    try:
        from basic_pitch import ICASSP_2022_MODEL_PATH
        from basic_pitch.inference import predict

        if raw_output_dir.exists():
            shutil.rmtree(raw_output_dir)

        raw_output_dir.mkdir(parents=True, exist_ok=True)
        normalized_midi_path.parent.mkdir(parents=True, exist_ok=True)

        settings = _basic_pitch_settings()

        try:
            _model_output, midi_data, note_events = predict(
                audio_path,
                model_or_model_path=ICASSP_2022_MODEL_PATH,
                **settings,
            )
        except TypeError:
            # Older basic_pitch versions without these keyword arguments.
            _model_output, midi_data, note_events = predict(
                audio_path,
                model_or_model_path=ICASSP_2022_MODEL_PATH,
            )

        midi_data.write(str(normalized_midi_path))

        raw_midi_path = raw_output_dir / f"{audio_path.stem}_basic_pitch.mid"

        # Basic Pitch can already write to the normalized output path depending
        # on the selected output directory. Avoid copying a file onto itself.
        if normalized_midi_path.resolve() != raw_midi_path.resolve():
            shutil.copyfile(normalized_midi_path, raw_midi_path)

        return normalized_midi_path, note_events, None

    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def _mirror_transcription_to_data_midi(
    result: TranscriptionResult,
    job_id: str,
) -> None:
    """
    Compatibility mirror for roadmap wording:
    save MIDI and note list JSON under data/midi/{job_id}/.

    Primary artifacts remain in the configured output_dir.
    """
    mirror_dir = Path("data/midi") / job_id
    mirror_dir.mkdir(parents=True, exist_ok=True)

    if result.midi_path is not None:
        source_midi = Path(result.midi_path)
        target_midi = mirror_dir / "output.mid"

        if source_midi.exists() and source_midi.resolve() != target_midi.resolve():
            shutil.copyfile(source_midi, target_midi)

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
            generated_midi, basic_pitch_note_events, transcription_error = _try_basic_pitch(
                audio_path=audio_path,
                raw_output_dir=raw_output_dir,
                normalized_midi_path=midi_path,
            )

            if generated_midi is not None:
                notes = _extract_note_events(
                    generated_midi,
                    basic_pitch_note_events=basic_pitch_note_events,
                )

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
                _mirror_transcription_to_data_midi(result, job_id)

                return result

        _write_placeholder_midi(midi_path)
        notes = _extract_note_events(midi_path)

        method = (
            "placeholder_midi_after_basic_pitch_fallback" if use_basic_pitch else "placeholder_midi"
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
