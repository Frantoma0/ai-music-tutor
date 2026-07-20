from __future__ import annotations

from collections import Counter
from typing import Any


class LLMPitchSafetyError(ValueError):
    pass


PIANO_MIDI_MIN = 21
PIANO_MIDI_MAX = 108
MAX_ABS_PITCH_SHIFT = 2


def validate_locked_pitch_corrections(
    locked_batch: dict[str, Any],
) -> dict[str, Any]:
    corrections = locked_batch.get("corrections") or []

    approved: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for correction in corrections:
        action = correction.get("action")

        if action != "propose_pitch_shift":
            approved.append(
                {
                    **correction,
                    "pitch_safety_status": "approved_no_pitch_change",
                    "pitch_safety_reasons": [],
                }
            )
            continue

        reasons: list[str] = []

        original_pitch = correction.get("original_pitch")
        proposed_pitch = correction.get("proposed_pitch")

        if not isinstance(original_pitch, int):
            reasons.append("missing_or_invalid_system_original_pitch")

        if not isinstance(proposed_pitch, int):
            reasons.append("missing_or_invalid_proposed_pitch")

        if isinstance(proposed_pitch, int):
            if not (PIANO_MIDI_MIN <= proposed_pitch <= PIANO_MIDI_MAX):
                reasons.append("proposed_pitch_outside_piano_range")

        if isinstance(original_pitch, int) and isinstance(proposed_pitch, int):
            if abs(proposed_pitch - original_pitch) > MAX_ABS_PITCH_SHIFT:
                reasons.append("pitch_shift_exceeds_safe_limit")

            if proposed_pitch == original_pitch:
                reasons.append("proposed_pitch_same_as_original")

        if reasons:
            rejected.append(
                {
                    **correction,
                    "pitch_safety_status": "rejected",
                    "pitch_safety_reasons": reasons,
                }
            )
        else:
            approved.append(
                {
                    **correction,
                    "pitch_safety_status": "approved_pitch_shift",
                    "pitch_safety_reasons": [],
                }
            )

    action_counts = Counter(item.get("action", "unknown") for item in corrections)

    approved_pitch_shifts = [
        item for item in approved if item.get("action") == "propose_pitch_shift"
    ]

    rejected_pitch_shifts = [
        item for item in rejected if item.get("action") == "propose_pitch_shift"
    ]

    proposed_pitch_shift_count = action_counts.get("propose_pitch_shift", 0)

    car = (
        len(approved_pitch_shifts) / proposed_pitch_shift_count
        if proposed_pitch_shift_count
        else None
    )

    return {
        "status": "completed" if not rejected else "partial",
        "input_correction_count": len(corrections),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "action_distribution": dict(action_counts),
        "approved_pitch_shift_count": len(approved_pitch_shifts),
        "rejected_pitch_shift_count": len(rejected_pitch_shifts),
        "correction_acceptance_rate": car,
        "approved": approved,
        "rejected": rejected,
    }
