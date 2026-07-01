import json
import shutil
import subprocess
from pathlib import Path
from re import sub
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile


router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_ROOT = Path("data/uploads")
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3"}
MAX_UPLOAD_BYTES = 80 * 1024 * 1024
MAX_YOUTUBE_URL_LENGTH = 2048

YTDLP_BIN = "/usr/local/bin/yt-dlp"
YTDLP_FORMAT = "140/251/139/249/bestaudio/best/18"
YTDLP_PLAYER_CLIENTS = "youtube:player_client=web,android,mweb"

PROTECTED_MARKERS = [
    "drm",
    "private video",
    "sign in",
    "copyright",
    "not available",
    "unavailable",
    "members-only",
    "age-restricted",
    "this video is not available",
    "requested format is not available",
    "only images are available",
    "po token",
    "http error 403",
]

ALLOWED_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}


def safe_name(value: str) -> str:
    cleaned = sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip("-") or "audio"
    return cleaned[:96]


def raise_bad_request(message: str) -> None:
    raise HTTPException(status_code=400, detail=message)


def validate_youtube_url(value: str) -> str:
    url = str(value or "").strip()

    if not url:
        raise_bad_request("Missing YouTube URL.")

    if len(url) > MAX_YOUTUBE_URL_LENGTH:
        raise_bad_request("The YouTube URL is too long.")

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise_bad_request("Only http or https YouTube links are supported.")

    if "@" in parsed.netloc:
        raise_bad_request("Invalid YouTube URL.")

    host = parsed.hostname.lower() if parsed.hostname else ""

    if host not in ALLOWED_YOUTUBE_HOSTS:
        raise_bad_request("Only public YouTube links from youtube.com or youtu.be are supported.")

    video_id = ""

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    else:
        path = parsed.path.rstrip("/")

        if path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif path.startswith("/shorts/"):
            video_id = path.split("/shorts/", 1)[1].split("/")[0]
        elif path.startswith("/embed/"):
            video_id = path.split("/embed/", 1)[1].split("/")[0]

    if not video_id or not sub(r"^[a-zA-Z0-9_-]{11}$", "", video_id) == "":
        raise_bad_request("Invalid YouTube video link. Please paste a normal public video URL.")

    return f"https://www.youtube.com/watch?v={video_id}"


def run_ytdlp_command(command: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def read_youtube_metadata(url: str) -> dict[str, str | None]:
    metadata_command = [
        YTDLP_BIN,
        "--js-runtimes",
        "deno",
        "--skip-download",
        "--no-playlist",
        "--dump-single-json",
        "--extractor-args",
        YTDLP_PLAYER_CLIENTS,
        url,
    ]

    try:
        result = run_ytdlp_command(metadata_command, timeout=30)

        if result.returncode != 0:
            return {
                "title": None,
                "thumbnail_url": None,
            }

        data = json.loads(result.stdout or "{}")

        thumbnail_url = data.get("thumbnail")
        thumbnails = data.get("thumbnails") or []

        if thumbnails:
            best_thumbnail = thumbnails[-1]
            thumbnail_url = best_thumbnail.get("url") or thumbnail_url

        return {
            "title": data.get("title"),
            "thumbnail_url": thumbnail_url,
        }
    except Exception:
        return {
            "title": None,
            "thumbnail_url": None,
        }


@router.post("/audio")
async def upload_audio_file(
    job_id: str = Form(...),
    file: UploadFile = File(...),
):
    original_name = file.filename or "audio"
    suffix = Path(original_name).suffix.lower()

    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio file. Please upload .wav or .mp3.",
        )

    safe_job_id = safe_name(job_id)

    if not safe_job_id:
        raise HTTPException(status_code=400, detail="Missing job_id.")

    safe_filename = safe_name(Path(original_name).stem)
    target_dir = UPLOAD_ROOT / safe_job_id
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{safe_filename}-{uuid4().hex[:8]}{suffix}"

    content = await file.read(MAX_UPLOAD_BYTES + 1)

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Audio file is too large. Please upload a file up to 80 MB.",
        )

    target_path.write_bytes(content)

    return {
        "status": "success",
        "filename": original_name,
        "path": str(target_path),
        "content_type": file.content_type,
        "size_bytes": len(content),
    }


@router.post("/youtube")
async def upload_youtube_audio(payload: dict[str, Any]):
    raw_url = str(payload.get("url") or "").strip()
    job_id = str(payload.get("job_id") or "").strip()

    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id.")

    safe_job_id = safe_name(job_id)
    url = validate_youtube_url(raw_url)

    youtube_metadata = read_youtube_metadata(url)
    youtube_title = youtube_metadata.get("title")
    youtube_thumbnail_url = youtube_metadata.get("thumbnail_url")

    work_dir = Path("data/processed") / safe_job_id
    raw_dir = work_dir / "raw"

    if work_dir.exists():
        shutil.rmtree(work_dir)

    raw_dir.mkdir(parents=True, exist_ok=True)

    output_template = raw_dir / "downloaded.%(ext)s"

    download_command = [
        YTDLP_BIN,
        "--js-runtimes",
        "deno",
        "-f",
        YTDLP_FORMAT,
        "--extractor-args",
        YTDLP_PLAYER_CLIENTS,
        "--no-playlist",
        "-o",
        str(output_template),
        url,
    ]

    try:
        download_result = run_ytdlp_command(download_command, timeout=300)
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail="YouTube download timed out. Try a shorter video or another source.",
        )

    combined_output = f"{download_result.stdout}\n{download_result.stderr}".lower()

    if download_result.returncode != 0:
        if any(marker in combined_output for marker in PROTECTED_MARKERS):
            raise HTTPException(
                status_code=400,
                detail=(
                    "This YouTube video cannot be processed. It may be private, "
                    "DRM/copyright protected, age-restricted, region-blocked, or unavailable."
                ),
            )

        raise HTTPException(
            status_code=400,
            detail=f"YouTube download failed: {download_result.stderr[-800:]}",
        )

    downloaded_files = list(raw_dir.glob("downloaded.*"))

    if not downloaded_files:
        raise HTTPException(
            status_code=500,
            detail="YouTube download finished, but no audio file was created.",
        )

    downloaded_file = downloaded_files[0]
    wav_path = work_dir / "input.wav"

    convert_command = [
        "ffmpeg",
        "-y",
        "-i",
        str(downloaded_file),
        "-ac",
        "1",
        "-ar",
        "44100",
        "-sample_fmt",
        "s16",
        str(wav_path),
    ]

    try:
        convert_result = subprocess.run(
            convert_command,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail="Audio conversion timed out. Try a shorter video or another source.",
        )

    if convert_result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Audio conversion to WAV failed: {convert_result.stderr[-800:]}",
        )

    if not wav_path.exists():
        raise HTTPException(
            status_code=500,
            detail="Audio conversion finished, but input.wav was not created.",
        )

    return {
        "status": "success",
        "url": url,
        "job_id": safe_job_id,
        "title": youtube_title,
        "thumbnail_url": youtube_thumbnail_url,
        "downloaded_path": str(downloaded_file),
        "path": str(wav_path),
        "size_bytes": wav_path.stat().st_size,
    }
