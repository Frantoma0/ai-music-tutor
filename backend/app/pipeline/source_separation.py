from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_DEMUCS_MODEL = "htdemucs"
DEFAULT_SELECTED_STEM = "other"


@dataclass
class SourceSeparationResult:
    job_id: str
    input_wav: str
    output_dir: str
    model_name: str
    stems: dict[str, str]
    selected_stem: str
    selected_stem_path: str | None
    status: str
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )


def _find_demucs_track_dir(
    demucs_output_dir: Path,
    model_name: str,
    input_wav: Path,
) -> Path:
    expected = demucs_output_dir / model_name / input_wav.stem

    if expected.exists():
        return expected

    candidates = []

    for directory in demucs_output_dir.rglob("*"):
        if not directory.is_dir():
            continue

        wav_names = {path.name for path in directory.glob("*.wav")}

        if {"vocals.wav", "drums.wav", "bass.wav", "other.wav"}.issubset(wav_names):
            candidates.append(directory)

    if candidates:
        return sorted(candidates)[0]

    raise FileNotFoundError(
        f"Could not find Demucs output stems under: {demucs_output_dir}"
    )


def _collect_stems(track_dir: Path) -> dict[str, str]:
    stems = {}

    for stem_name in ["vocals", "drums", "bass", "other"]:
        stem_path = track_dir / f"{stem_name}.wav"

        if stem_path.exists():
            stems[stem_name] = str(stem_path)

    return stems


def separate_sources(
    wav_path: str | Path,
    output_dir: str | Path = "data/stems",
    job_id: str | None = None,
    model_name: str = DEFAULT_DEMUCS_MODEL,
    selected_stem: str = DEFAULT_SELECTED_STEM,
) -> SourceSeparationResult:
    """
    T2 separate_sources.

    Runs Demucs 4-stem separation and selects the 'other' stem by default,
    which is the closest available stem for piano/instrumental material in
    standard htdemucs output.
    """
    job_id = job_id or uuid.uuid4().hex[:12]
    wav_path = Path(wav_path)

    job_dir = Path(output_dir) / job_id
    demucs_output_dir = job_dir / "demucs"

    try:
        if not wav_path.exists():
            raise FileNotFoundError(f"Input WAV not found: {wav_path}")

        if not wav_path.is_file():
            raise ValueError(f"Input WAV path is not a file: {wav_path}")

        if demucs_output_dir.exists():
            shutil.rmtree(demucs_output_dir)

        demucs_output_dir.mkdir(parents=True, exist_ok=True)

        _run_command(
            [
                "demucs",
                "-n",
                model_name,
                "-o",
                str(demucs_output_dir),
                str(wav_path),
            ]
        )

        track_dir = _find_demucs_track_dir(demucs_output_dir, model_name, wav_path)
        stems = _collect_stems(track_dir)

        if selected_stem not in stems:
            raise FileNotFoundError(
                f"Selected stem '{selected_stem}' not found. Available stems: {sorted(stems)}"
            )

        return SourceSeparationResult(
            job_id=job_id,
            input_wav=str(wav_path),
            output_dir=str(job_dir),
            model_name=model_name,
            stems=stems,
            selected_stem=selected_stem,
            selected_stem_path=stems[selected_stem],
            status="completed",
            error=None,
        )

    except Exception as exc:
        return SourceSeparationResult(
            job_id=job_id,
            input_wav=str(wav_path),
            output_dir=str(job_dir),
            model_name=model_name,
            stems={},
            selected_stem=selected_stem,
            selected_stem_path=None,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )
