from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


class CorrectionBatchValidationError(ValueError):
    pass


ALLOWED_ACTIONS = {
    "keep",
    "flag_for_review",
    "propose_pitch_shift",
    "propose_timing_adjustment",
}

PIANO_MIDI_MIN = 21
PIANO_MIDI_MAX = 108
MAX_ABS_PITCH_SHIFT = 2
MAX_ABS_TIMING_SHIFT_SECONDS = 0.25
MAX_CORRECTIONS = 100


@dataclass(frozen=True)
class LLMCorrectionItem:
    candidate_id: str
    action: str
    reason: str
    proposed_pitch: int | None = None
    proposed_start: float | None = None
    proposed_end: float | None = None
    confidence: float | None = None
    hvs_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LLMCorrectionBatch:
    status: str
    corrections: list[LLMCorrectionItem]
    correction_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "correction_count": self.correction_count,
            "corrections": [item.to_dict() for item in self.corrections],
        }


def _require_dict(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CorrectionBatchValidationError(f"{name} must be an object")

    return value


def _require_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CorrectionBatchValidationError(f"{name} must be a non-empty string")

    return value.strip()


def _optional_int(value: Any, *, name: str) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise CorrectionBatchValidationError(f"{name} must be an integer")

    try:
        return int(value)
    except (TypeError, ValueError):
        raise CorrectionBatchValidationError(f"{name} must be an integer") from None


def _optional_float(value: Any, *, name: str) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise CorrectionBatchValidationError(f"{name} must be a number")

    try:
        return float(value)
    except (TypeError, ValueError):
        raise CorrectionBatchValidationError(f"{name} must be a number") from None


def _validate_no_mutation_fields(
    *,
    action: str,
    proposed_pitch: int | None,
    proposed_start: float | None,
    proposed_end: float | None,
) -> None:
    if proposed_pitch is not None or proposed_start is not None or proposed_end is not None:
        raise CorrectionBatchValidationError(
            f"{action} must not include proposed_pitch/proposed_start/proposed_end"
        )


def _validate_pitch_shift(item: dict[str, Any], proposed_pitch: int | None) -> None:
    if proposed_pitch is None:
        raise CorrectionBatchValidationError("propose_pitch_shift requires proposed_pitch")

    if not (PIANO_MIDI_MIN <= proposed_pitch <= PIANO_MIDI_MAX):
        raise CorrectionBatchValidationError("proposed_pitch outside piano MIDI range")

    original_pitch = _optional_int(item.get("original_pitch"), name="original_pitch")

    if original_pitch is not None:
        if abs(proposed_pitch - original_pitch) > MAX_ABS_PITCH_SHIFT:
            raise CorrectionBatchValidationError("pitch shift exceeds safe limit")


def _validate_timing_adjustment(
    item: dict[str, Any],
    proposed_start: float | None,
    proposed_end: float | None,
) -> None:
    if proposed_start is None and proposed_end is None:
        raise CorrectionBatchValidationError(
            "propose_timing_adjustment requires proposed_start or proposed_end"
        )

    if proposed_start is not None and proposed_start < 0:
        raise CorrectionBatchValidationError("proposed_start before zero")

    if proposed_start is not None and proposed_end is not None and proposed_end <= proposed_start:
        raise CorrectionBatchValidationError("proposed_end must be after proposed_start")

    original_start = _optional_float(item.get("original_start"), name="original_start")
    original_end = _optional_float(item.get("original_end"), name="original_end")

    if original_start is not None and proposed_start is not None:
        if abs(proposed_start - original_start) > MAX_ABS_TIMING_SHIFT_SECONDS:
            raise CorrectionBatchValidationError("start timing shift exceeds safe limit")

    if original_end is not None and proposed_end is not None:
        if abs(proposed_end - original_end) > MAX_ABS_TIMING_SHIFT_SECONDS:
            raise CorrectionBatchValidationError("end timing shift exceeds safe limit")


def validate_correction_item_json(item: dict[str, Any]) -> LLMCorrectionItem:
    item = _require_dict(item, name="correction item")

    candidate_id = _require_string(item.get("candidate_id"), name="candidate_id")
    action = _require_string(item.get("action"), name="action")

    if action not in ALLOWED_ACTIONS:
        raise CorrectionBatchValidationError(f"unsupported action: {action}")

    reason = item.get("reason")
    if reason is None:
        reason = ""
    reason = _require_string(reason or "no_reason_provided", name="reason")

    proposed_pitch = _optional_int(item.get("proposed_pitch"), name="proposed_pitch")
    proposed_start = _optional_float(item.get("proposed_start"), name="proposed_start")
    proposed_end = _optional_float(item.get("proposed_end"), name="proposed_end")

    confidence = _optional_float(item.get("confidence"), name="confidence")
    hvs_score = _optional_float(item.get("hvs_score"), name="hvs_score")

    if action in {"keep", "flag_for_review"}:
        _validate_no_mutation_fields(
            action=action,
            proposed_pitch=proposed_pitch,
            proposed_start=proposed_start,
            proposed_end=proposed_end,
        )

    if action == "propose_pitch_shift":
        _validate_pitch_shift(item, proposed_pitch)

    if action == "propose_timing_adjustment":
        _validate_timing_adjustment(
            item,
            proposed_start=proposed_start,
            proposed_end=proposed_end,
        )

    return LLMCorrectionItem(
        candidate_id=candidate_id,
        action=action,
        reason=reason,
        proposed_pitch=proposed_pitch,
        proposed_start=proposed_start,
        proposed_end=proposed_end,
        confidence=confidence,
        hvs_score=hvs_score,
    )


def validate_correction_batch_json(data: dict[str, Any]) -> LLMCorrectionBatch:
    data = _require_dict(data, name="CorrectionBatch")

    status = _require_string(data.get("status", "completed"), name="status")

    corrections = data.get("corrections")

    if not isinstance(corrections, list):
        raise CorrectionBatchValidationError("corrections must be a list")

    if len(corrections) > MAX_CORRECTIONS:
        raise CorrectionBatchValidationError("corrections exceeds maximum allowed size")

    parsed = [validate_correction_item_json(item) for item in corrections]

    return LLMCorrectionBatch(
        status=status,
        corrections=parsed,
        correction_count=len(parsed),
    )
