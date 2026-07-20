from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

NOTE_TO_PC = {
    "C": 0,
    "C#": 1,
    "D-": 1,
    "D": 2,
    "D#": 3,
    "E-": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "G-": 6,
    "G": 7,
    "G#": 8,
    "A-": 8,
    "A": 9,
    "A#": 10,
    "B-": 10,
    "B": 11,
}

MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}
MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10}

MAJOR_TONIC_TRIAD = {0, 4, 7}
MINOR_TONIC_TRIAD = {0, 3, 7}


@dataclass(frozen=True)
class HarmonyNoteAnalysis:
    id: str | None
    pitch: int | None
    pitch_name: str | None
    start: float | None
    end: float | None
    confidence: float | None
    hvs_score: float
    hvs_label: str
    reason: str


@dataclass(frozen=True)
class HarmonyAnalysisResult:
    status: str
    detected_key: str | None
    tonic: str | None
    mode: str | None
    note_count: int
    notes: list[HarmonyNoteAnalysis]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "detected_key": self.detected_key,
            "tonic": self.tonic,
            "mode": self.mode,
            "note_count": self.note_count,
            "notes": [asdict(note) for note in self.notes],
            "error": self.error,
        }


def _as_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_key_name(key_name: str | None) -> tuple[str | None, str | None]:
    if not key_name:
        return None, None

    parts = key_name.strip().split()

    if not parts:
        return None, None

    tonic = parts[0]
    mode = parts[1].lower() if len(parts) > 1 else "major"

    if mode not in {"major", "minor"}:
        mode = "major"

    return tonic, mode


def _pitch_class_distance_to_scale(relative_pc: int, scale: set[int]) -> int:
    distances = []

    for scale_pc in scale:
        upward = (relative_pc - scale_pc) % 12
        downward = (scale_pc - relative_pc) % 12
        distances.append(min(upward, downward))

    return min(distances) if distances else 12


def classify_note_hvs(
    pitch: int | None,
    *,
    detected_key: str | None,
) -> tuple[float, str, str]:
    tonic, mode = _parse_key_name(detected_key)

    if pitch is None:
        return 1.0, "unknown_pitch", "missing_pitch"

    if tonic not in NOTE_TO_PC:
        return 0.6, "unknown_key", "could_not_parse_detected_key"

    tonic_pc = NOTE_TO_PC[tonic]
    relative_pc = (pitch % 12 - tonic_pc) % 12

    if mode == "minor":
        scale = MINOR_SCALE
        tonic_triad = MINOR_TONIC_TRIAD
    else:
        scale = MAJOR_SCALE
        tonic_triad = MAJOR_TONIC_TRIAD

    if relative_pc in tonic_triad:
        return 0.0, "stable_chord_tone", "pitch_class_in_tonic_triad"

    if relative_pc in scale:
        return 0.3, "diatonic_non_chord_tone", "pitch_class_in_key_scale"

    distance = _pitch_class_distance_to_scale(relative_pc, scale)

    if distance == 1:
        return 0.6, "chromatic_neighbor", "pitch_class_one_semitone_from_scale"

    return 1.0, "strong_out_of_key_tone", "pitch_class_far_from_scale"


def analyze_notes_harmony(
    notes: list[dict[str, Any]],
    *,
    detected_key: str | None,
) -> HarmonyAnalysisResult:
    tonic, mode = _parse_key_name(detected_key)
    analyzed_notes: list[HarmonyNoteAnalysis] = []

    for index, note in enumerate(notes):
        pitch = _as_int(note.get("pitch"))
        hvs_score, hvs_label, reason = classify_note_hvs(
            pitch,
            detected_key=detected_key,
        )

        analyzed_notes.append(
            HarmonyNoteAnalysis(
                id=note.get("id") or f"n{index}",
                pitch=pitch,
                pitch_name=note.get("pitch_name"),
                start=_as_float(note.get("start")),
                end=_as_float(note.get("end")),
                confidence=_as_float(note.get("confidence")),
                hvs_score=hvs_score,
                hvs_label=hvs_label,
                reason=reason,
            )
        )

    return HarmonyAnalysisResult(
        status="completed",
        detected_key=detected_key,
        tonic=tonic,
        mode=mode,
        note_count=len(analyzed_notes),
        notes=analyzed_notes,
        error=None,
    )


def merge_hvs_into_notes(
    notes: list[dict[str, Any]],
    harmony_result: HarmonyAnalysisResult,
) -> list[dict[str, Any]]:
    merged = []

    for original, analyzed in zip(notes, harmony_result.notes, strict=False):
        item = dict(original)
        item["hvs_score"] = analyzed.hvs_score
        item["hvs_label"] = analyzed.hvs_label
        item["hvs_reason"] = analyzed.reason
        merged.append(item)

    return merged
