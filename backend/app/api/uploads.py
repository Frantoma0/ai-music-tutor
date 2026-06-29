import shutil
import subprocess
from typing import Any
from pathlib import Path
from re import sub
from uuid import uuid4
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile


router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_ROOT = Path("data/uploads")
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3"}


def safe_name(value: str) -> str:
    cleaned = sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "audio"

def read_youtube_metadata(url: str) -> dict[str, str | None]:
    metadata_command = [
        "/usr/local/bin/yt-dlp",
        "--js-runtimes",
        "deno",
        "--skip-download",
        "--no-playlist",
        "--dump-single-json",
        "--extractor-args",
        "youtube:player_client=web,android,mweb",
        url,
    ]

    try:
        result = subprocess.run(
            metadata_command,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

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
    safe_filename = safe_name(Path(original_name).stem)
    target_dir = UPLOAD_ROOT / safe_job_id
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{safe_filename}-{uuid4().hex[:8]}{suffix}"

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

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
    url = str(payload.get("url") or "").strip()
    job_id = str(payload.get("job_id") or "").strip()

    if not url:
        raise HTTPException(status_code=400, detail="Missing YouTube URL.")

    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id.")

    safe_job_id = safe_name(job_id)
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
        "/usr/local/bin/yt-dlp",
        "--js-runtimes",
        "deno",
        "-f",
        "140/251/139/249/bestaudio/best/18",
        "--extractor-args",
        "youtube:player_client=web,android,mweb",
        "--no-playlist",
        "-o",
        str(output_template),
        url,
    ]

    try:
        download_result = subprocess.run(
            download_command,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail="YouTube download timed out. Try a shorter video or another source.",
        )

    combined_output = f"{download_result.stdout}\n{download_result.stderr}".lower()

    if download_result.returncode != 0:
        protected_markers = [
            "drm",
            "private video",
            "sign in",
            "copyright",
            "not available",
            "unavailable",
            "members-only",
            "age-restricted",
            "this video is not available",
        ]

        if any(marker in combined_output for marker in protected_markers):
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

    convert_result = subprocess.run(
        convert_command,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
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