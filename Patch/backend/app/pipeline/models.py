from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class TracerBulletResult:
    job_id: str
    input_audio: str
    midi_path: str
    detected_key: str
    hvs_score: float
    status: str
    transcription_method: str
    key_confidence: float | None = None
    transcription_error: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
