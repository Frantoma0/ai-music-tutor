from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AudioPreprocessResult:
    status: str
    input_path: str
    output_path: str
    enabled: bool
    filters: list[str]
    error: str | None = None


def preprocess_audio_for_transcription(
    input_path: str | Path,
    output_path: str | Path,
    *,
    trim_silence: bool = True,
    normalize_audio: bool = True,
    highpass_filter: bool = True,
) -> AudioPreprocessResult:
    input_path = Path(input_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    filters: list[str] = []

    if highpass_filter:
        filters.append("highpass=f=25")

    if trim_silence:
        filters.append("silenceremove=start_periods=1:start_duration=0.12:start_threshold=-45dB")

    if normalize_audio:
        filters.append("loudnorm=I=-18:TP=-1.5:LRA=11")

    enabled = bool(filters)

    if not enabled:
        if input_path.resolve() != output_path.resolve():
            shutil.copyfile(input_path, output_path)

        return AudioPreprocessResult(
            status="skipped",
            input_path=str(input_path),
            output_path=str(output_path),
            enabled=False,
            filters=[],
        )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "44100",
        "-sample_fmt",
        "s16",
        "-af",
        ",".join(filters),
        str(output_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    if result.returncode != 0 or not output_path.exists():
        return AudioPreprocessResult(
            status="failed",
            input_path=str(input_path),
            output_path=str(output_path),
            enabled=True,
            filters=filters,
            error=result.stderr[-800:] if result.stderr else "Audio preprocessing failed.",
        )

    return AudioPreprocessResult(
        status="completed",
        input_path=str(input_path),
        output_path=str(output_path),
        enabled=True,
        filters=filters,
    )
