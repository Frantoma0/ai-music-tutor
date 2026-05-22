from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CorrectionMaskCandidate:
    id: str | None
    pitch: int | None
    pitch_name: str | None
    start: float | None
    end: float | None
    confidence: float | None
    hvs_score: float | None
    selected: bool
    reason: str


@dataclass(frozen=True)
class CorrectionMaskResult:
    status: str
    note_count: int
    selected_count: int
    confidence_threshold: float
    hvs_threshold: float
    global_hvs_score: float | None
    allow_hvs_only_fallback: bool
    candidates: list[CorrectionMaskCandidate]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "note_count": self.note_count,
            "selected_count": self.selected_count,
            "confidence_threshold": self.confidence_threshold,
            "hvs_threshold": self.hvs_threshold,
            "global_hvs_score": self.global_hvs_score,
            "allow_hvs_only_fallback": self.allow_hvs_only_fallback,
            "candidates": [asdict(candidate) for candidate in self.candidates],
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


def build_correction_mask(
    notes: list[dict[str, Any]],
    *,
    global_hvs_score: float | None,
    confidence_threshold: float = 0.7,
    hvs_threshold: float = 0.6,
    allow_hvs_only_fallback: bool = True,
) -> CorrectionMaskResult:
    """
    Build deterministic correction mask candidates for T5.

    Primary rule:
        M(n) = 1 iff confidence < confidence_threshold AND hvs(n) >= hvs_threshold

    Current bridge:
        If per-note hvs_score is missing, global pipeline hvs_score is used.

    Fallback:
        If confidence is missing, optionally select by HVS only. This keeps the
        pipeline usable for placeholder/non-Basic-Pitch transcriptions.
    """
    candidates: list[CorrectionMaskCandidate] = []

    global_hvs = _as_float(global_hvs_score)

    for index, note in enumerate(notes):
        confidence = _as_float(note.get("confidence"))
        hvs_score = _as_float(note.get("hvs_score"))
        effective_hvs = hvs_score if hvs_score is not None else global_hvs

        has_hvs_signal = effective_hvs is not None and effective_hvs >= hvs_threshold

        if confidence is None:
            selected = bool(allow_hvs_only_fallback and has_hvs_signal)
            reason = (
                "confidence_missing_hvs_only_fallback"
                if selected
                else "confidence_missing_not_selected"
            )
        elif confidence < confidence_threshold and has_hvs_signal:
            selected = True
            reason = "low_confidence_high_hvs"
        elif confidence >= confidence_threshold:
            selected = False
            reason = "confidence_above_threshold"
        else:
            selected = False
            reason = "hvs_below_threshold_or_missing"

        candidates.append(
            CorrectionMaskCandidate(
                id=note.get("id") or f"n{index}",
                pitch=_as_int(note.get("pitch")),
                pitch_name=note.get("pitch_name"),
                start=_as_float(note.get("start")),
                end=_as_float(note.get("end")),
                confidence=confidence,
                hvs_score=effective_hvs,
                selected=selected,
                reason=reason,
            )
        )

    selected_count = sum(1 for candidate in candidates if candidate.selected)

    return CorrectionMaskResult(
        status="completed",
        note_count=len(notes),
        selected_count=selected_count,
        confidence_threshold=confidence_threshold,
        hvs_threshold=hvs_threshold,
        global_hvs_score=global_hvs,
        allow_hvs_only_fallback=allow_hvs_only_fallback,
        candidates=candidates,
        error=None,
    )
