from pathlib import Path
from re import sub
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile


router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_ROOT = Path("data/uploads")
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3"}


def safe_name(value: str) -> str:
    cleaned = sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "audio"


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
