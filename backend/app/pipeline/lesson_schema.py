from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


HvsLabel = Literal[
    "stable_chord_tone",
    "diatonic_non_chord_tone",
    "chromatic_neighbor",
    "strong_out_of_key_tone",
    "unknown_key",
    "unknown_pitch",
]

Hand = Literal["left", "right", "unknown"]

CorrectionStatus = Literal["none", "proposed", "approved", "rejected"]

LessonStatus = Literal["pending", "running", "completed", "error"]


class LessonNote(BaseModel):
    id: str = Field(description="Stable note identifier shared across transcription, harmony, mask and correction stages")
    pitch: int = Field(description="MIDI pitch number, piano range 21-108")
    pitch_name: str = Field(description="Human-readable pitch name such as C4")
    start: float = Field(description="Note onset in seconds from the start of the audio")
    end: float = Field(description="Note offset in seconds from the start of the audio")
    duration: float = Field(description="Note duration in seconds")
    velocity: int = Field(description="MIDI velocity 0-127")
    confidence: float | None = Field(
        default=None,
        description="Basic Pitch confidence in 0-1, null when unavailable",
    )
    hvs_score: float = Field(description="Harmonic violation score in 0-1")
    hvs_label: HvsLabel = Field(description="Categorical harmonic classification")
    hvs_reason: str = Field(description="Deterministic reason for the HVS classification")
    hand: Hand = Field(default="unknown", description="left/right from C4 split, unknown when not assignable")
    in_correction_mask: bool = Field(default=False, description="True when selected by generate_mask")
    correction_status: CorrectionStatus = Field(default="none", description="Correction lifecycle status")
    original_pitch: int | None = Field(default=None, description="Original pitch when a validated pitch shift is displayed")
    correction_reason: str | None = Field(default=None, description="Correction or review rationale")


class LessonMeta(BaseModel):
    id: str = Field(description="Lesson identifier, derived from the pipeline job_id")
    job_id: str = Field(description="Source pipeline job_id")
    title: str | None = Field(default=None, description="Human-readable lesson title")
    detected_key: str | None = Field(default=None, description="Detected key")
    tempo_bpm: float | None = Field(default=None, description="Estimated tempo in BPM")
    time_signature: str | None = Field(default=None, description="Detected time signature")
    duration_s: float | None = Field(default=None, description="Total duration in seconds")
    transcription_method: str | None = Field(default=None, description="Transcription method")
    status: LessonStatus = Field(description="Lesson availability status")


class LessonVersions(BaseModel):
    raw_midi_url: str | None = Field(default=None, description="REST path to raw MIDI")
    corrected_midi_url: str | None = Field(default=None, description="REST path to corrected MIDI")


class LessonResponse(BaseModel):
    meta: LessonMeta
    notes: list[LessonNote]
    versions: LessonVersions
    note_count: int = Field(description="Total note count")
    masked_count: int = Field(description="Notes selected by correction mask")
    correction_count: int = Field(description="Notes with non-none correction status")
