from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


MAX_FILE_SIZE_MB = 50
MAX_DURATION_SECONDS = 10 * 60


@dataclass
class AudioExtractionResult:
    job_id: str
    source: str
    input_type: str
    original_path: str
    wav_path: str
    duration_seconds: float | None
    sample_rate: int | None
    channels: int | None
    status: str
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _is_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"}


def _run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )


def _probe_audio(path: Path) -> tuple[float | None, int | None, int | None]:
    try:
        completed = _run_command(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=sample_rate,channels",
                "-of",
                "json",
                str(path),
            ]
        )

        data = json.loads(completed.stdout)

        duration = None
        sample_rate = None
        channels = None

        if "format" in data and data["format"].get("duration") is not None:
            duration = float(data["format"]["duration"])

        streams = data.get("streams", [])
        if streams:
            first_stream = streams[0]
            if first_stream.get("sample_rate") is not None:
                sample_rate = int(first_stream["sample_rate"])
            if first_stream.get("channels") is not None:
                channels = int(first_stream["channels"])

        return duration, sample_rate, channels

    except Exception:
        return None, None, None


def _validate_local_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"Input file is too large: {size_mb:.2f} MB > {MAX_FILE_SIZE_MB} MB"
        )

    duration, _, _ = _probe_audio(path)
    if duration is not None and duration > MAX_DURATION_SECONDS:
        raise ValueError(
            f"Input audio is too long: {duration:.2f}s > {MAX_DURATION_SECONDS}s"
        )


def _download_with_ytdlp(source_url: str, output_dir: Path) -> Path:
    try:
        import yt_dlp
    except Exception as exc:
        raise RuntimeError("yt-dlp is not installed, cannot download URL input.") from exc

    output_template = str(output_dir / "downloaded.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(source_url, download=True)
        downloaded_path = Path(ydl.prepare_filename(info))

    if not downloaded_path.exists():
        candidates = list(output_dir.glob("downloaded.*"))
        if not candidates:
            raise FileNotFoundError("yt-dlp finished but no downloaded file was found.")
        downloaded_path = candidates[0]

    return downloaded_path


def _normalize_to_wav(input_path: Path, wav_path: Path) -> None:
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    _run_command(
        [
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
            str(wav_path),
        ]
    )


def extract_audio(
    source: str | Path,
    output_dir: str | Path = "data/processed",
    job_id: str | None = None,
) -> AudioExtractionResult:
    """
    T1 extract_audio.

    Converts a local audio file or URL input into a normalized WAV file:
    16-bit PCM, 44.1kHz, mono.
    """
    job_id = job_id or uuid.uuid4().hex[:12]
    source_str = str(source)

    job_dir = Path(output_dir) / job_id
    raw_dir = job_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    wav_path = job_dir / "input.wav"

    try:
        if _is_url(source_str):
            input_type = "url"
            original_path = _download_with_ytdlp(source_str, raw_dir)
        else:
            input_type = "file"
            source_path = Path(source_str)
            _validate_local_file(source_path)

            original_path = raw_dir / source_path.name
            if source_path.resolve() != original_path.resolve():
                shutil.copyfile(source_path, original_path)

        _normalize_to_wav(original_path, wav_path)

        duration, sample_rate, channels = _probe_audio(wav_path)

        return AudioExtractionResult(
            job_id=job_id,
            source=source_str,
            input_type=input_type,
            original_path=str(original_path),
            wav_path=str(wav_path),
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels,
            status="completed",
            error=None,
        )

    except Exception as exc:
        return AudioExtractionResult(
            job_id=job_id,
            source=source_str,
            input_type="url" if _is_url(source_str) else "file",
            original_path="",
            wav_path=str(wav_path),
            duration_seconds=None,
            sample_rate=None,
            channels=None,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )
