from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class TracerBulletResult:
    job_id: str
    input_audio: str
    midi_path: str
    detected_key: str
    hvs_score: float
    status: str
    transcription_method: str
    key_confidence: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
