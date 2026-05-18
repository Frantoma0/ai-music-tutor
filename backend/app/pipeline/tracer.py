from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Optional

import pretty_midi
from music21 import converter

from app.pipeline.models import TracerBulletResult


def _create_placeholder_midi(output_path: Path) -> Path:
    """
    Create a tiny valid MIDI file for the Day 3 tracer bullet.

    This is not the final AMT step. It only proves that the pipeline can produce
    a MIDI artifact and pass it to music21 for symbolic analysis.
    """
    midi = pretty_midi.PrettyMIDI()
    piano = pretty_midi.Instrument(program=0, name="Tracer Piano")

    # C major triad: C4, E4, G4, C5
    notes = [
        (60, 0.0, 0.8),
        (64, 0.8, 1.6),
        (67, 1.6, 2.4),
        (72, 2.4, 3.2),
    ]

    for pitch, start, end in notes:
        piano.notes.append(
            pretty_midi.Note(
                velocity=90,
                pitch=pitch,
                start=start,
                end=end,
            )
        )

    midi.instruments.append(piano)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(output_path))
    return output_path


def _try_basic_pitch(audio_path: Path, job_dir: Path) -> tuple[Optional[Path], Optional[str]]:
    """
    Try to run Basic Pitch.

    Basic Pitch refuses to overwrite existing output files, so each run writes
    into a clean raw subdirectory and then normalizes the selected MIDI artifact
    to job_dir/output.mid.
    """
    try:
        from basic_pitch import ICASSP_2022_MODEL_PATH
        from basic_pitch.inference import predict_and_save

        raw_dir = job_dir / "basic_pitch_raw"

        if raw_dir.exists():
            shutil.rmtree(raw_dir)

        raw_dir.mkdir(parents=True, exist_ok=True)

        predict_and_save(
            [str(audio_path)],
            str(raw_dir),
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
        )

        midi_candidates = sorted(
            list(raw_dir.glob("*.mid")) + list(raw_dir.glob("*.midi"))
        )

        if not midi_candidates:
            return None, "Basic Pitch finished but did not create a MIDI file."

        generated_midi = midi_candidates[0]
        normalized_midi = job_dir / "output.mid"

        if normalized_midi.exists():
            normalized_midi.unlink()

        shutil.copyfile(generated_midi, normalized_midi)

        return normalized_midi, None

    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def detect_key_from_midi(midi_path: Path) -> tuple[str, Optional[float]]:
    """
    Detect musical key from a MIDI file using music21.
    """
    score = converter.parse(str(midi_path))
    detected = score.analyze("key")

    key_name = f"{detected.tonic.name} {detected.mode}"
    confidence = getattr(detected, "correlationCoefficient", None)

    if confidence is not None:
        confidence = float(confidence)

    return key_name, confidence


def run_tracer_bullet(
    audio_path: str | Path,
    artifacts_dir: str | Path = "artifacts/tracer",
    job_id: Optional[str] = None,
    use_basic_pitch: bool = False,
) -> TracerBulletResult:
    """
    Day 3 tracer bullet:

    WAV input -> MIDI artifact -> music21 key detection -> placeholder HVS score.
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Input audio not found: {audio_path}")

    job_id = job_id or uuid.uuid4().hex[:12]
    job_dir = Path(artifacts_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    midi_path = job_dir / "output.mid"
    transcription_method = "placeholder_midi"
    transcription_error = None

    if use_basic_pitch:
        generated_midi, transcription_error = _try_basic_pitch(audio_path, job_dir)

        if generated_midi is not None:
            midi_path = generated_midi
            transcription_method = "basic_pitch"
        else:
            _create_placeholder_midi(midi_path)
            transcription_method = "placeholder_midi_after_basic_pitch_fallback"
    else:
        _create_placeholder_midi(midi_path)

    detected_key, key_confidence = detect_key_from_midi(midi_path)

    result = TracerBulletResult(
        job_id=job_id,
        input_audio=str(audio_path),
        midi_path=str(midi_path),
        detected_key=detected_key,
        hvs_score=0.0,
        status="completed",
        transcription_method=transcription_method,
        key_confidence=key_confidence,
        transcription_error=transcription_error,
    )

    result_path = job_dir / "result.json"
    result_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Day 3 tracer bullet pipeline.")
    parser.add_argument("audio_path", help="Path to input WAV/audio file.")
    parser.add_argument("--artifacts-dir", default="artifacts/tracer")
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--basic-pitch", action="store_true")

    args = parser.parse_args()

    output = run_tracer_bullet(
        audio_path=args.audio_path,
        artifacts_dir=args.artifacts_dir,
        job_id=args.job_id,
        use_basic_pitch=args.basic_pitch,
    )

    print(json.dumps(output.to_dict(), indent=2, ensure_ascii=False))
