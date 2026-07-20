from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

ALLOWED_ACTIONS = {
    "keep",
    "flag_for_review",
    "propose_pitch_shift",
    "propose_timing_adjustment",
    "propose_delete",
}

PIANO_MIDI_MIN = 21
PIANO_MIDI_MAX = 108
MAX_ABS_PITCH_SHIFT = 2
MAX_ABS_TIMING_SHIFT_SECONDS = 0.25


@dataclass(frozen=True)
class CorrectionValidationItem:
    proposal_id: str | None
    candidate_id: str | None
    action: str | None
    validation_status: str
    approved: bool
    reasons: list[str]
    safety_notes: list[str]


@dataclass(frozen=True)
class CorrectionValidationBatch:
    status: str
    job_id: str | None
    source_proposals_path: str | None
    proposal_count: int
    approved_count: int
    rejected_count: int
    validations: list[CorrectionValidationItem]
    midi_mutation_allowed: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "job_id": self.job_id,
            "source_proposals_path": self.source_proposals_path,
            "proposal_count": self.proposal_count,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "validations": [asdict(item) for item in self.validations],
            "midi_mutation_allowed": self.midi_mutation_allowed,
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


def validate_correction_proposal(proposal: dict[str, Any]) -> CorrectionValidationItem:
    proposal_id = proposal.get("proposal_id")
    candidate_id = proposal.get("candidate_id")
    action = proposal.get("action")

    reasons: list[str] = []
    safety_notes: list[str] = []

    if action not in ALLOWED_ACTIONS:
        reasons.append(f"unsupported_action:{action}")

    original_pitch = _as_int(proposal.get("original_pitch"))
    proposed_pitch = _as_int(proposal.get("proposed_pitch"))

    original_start = _as_float(proposal.get("original_start"))
    proposed_start = _as_float(proposal.get("proposed_start"))

    original_end = _as_float(proposal.get("original_end"))
    proposed_end = _as_float(proposal.get("proposed_end"))

    if action == "flag_for_review":
        if proposed_pitch is not None:
            reasons.append("flag_for_review_must_not_set_proposed_pitch")

        if proposed_start is not None:
            reasons.append("flag_for_review_must_not_set_proposed_start")

        if proposed_end is not None:
            reasons.append("flag_for_review_must_not_set_proposed_end")

        safety_notes.append("safe_review_only_no_midi_mutation")

    if action == "keep":
        if proposed_pitch is not None or proposed_start is not None or proposed_end is not None:
            reasons.append("keep_action_must_not_set_proposed_changes")

        safety_notes.append("safe_keep_no_midi_mutation")

    if action == "propose_pitch_shift":
        if original_pitch is None:
            reasons.append("missing_original_pitch")

        if proposed_pitch is None:
            reasons.append("missing_proposed_pitch")

        if proposed_pitch is not None and not (PIANO_MIDI_MIN <= proposed_pitch <= PIANO_MIDI_MAX):
            reasons.append("proposed_pitch_outside_piano_range")

        if original_pitch is not None and proposed_pitch is not None:
            shift = abs(proposed_pitch - original_pitch)

            if shift > MAX_ABS_PITCH_SHIFT:
                reasons.append("pitch_shift_exceeds_safe_limit")

        safety_notes.append("requires_explicit_pitch_validation_before_midi_mutation")

    if action == "propose_timing_adjustment":
        if original_start is None or proposed_start is None:
            reasons.append("missing_start_timing_for_adjustment")

        if original_end is None or proposed_end is None:
            reasons.append("missing_end_timing_for_adjustment")

        if proposed_start is not None and proposed_start < 0:
            reasons.append("proposed_start_before_zero")

        if (
            proposed_end is not None
            and proposed_start is not None
            and proposed_end <= proposed_start
        ):
            reasons.append("proposed_end_must_be_after_proposed_start")

        if original_start is not None and proposed_start is not None:
            if abs(proposed_start - original_start) > MAX_ABS_TIMING_SHIFT_SECONDS:
                reasons.append("start_timing_shift_exceeds_safe_limit")

        if original_end is not None and proposed_end is not None:
            if abs(proposed_end - original_end) > MAX_ABS_TIMING_SHIFT_SECONDS:
                reasons.append("end_timing_shift_exceeds_safe_limit")

        safety_notes.append("requires_explicit_timing_validation_before_midi_mutation")

    if action == "propose_delete":
        safety_notes.append("delete_action_requires_human_or_strict_validator_approval")
        reasons.append("delete_action_not_allowed_in_day11_safe_mode")

    approved = len(reasons) == 0

    if approved and action in {"flag_for_review", "keep"}:
        validation_status = "approved_for_review"
    elif approved:
        validation_status = "approved_pending_midi_validator"
    else:
        validation_status = "rejected"

    return CorrectionValidationItem(
        proposal_id=str(proposal_id) if proposal_id is not None else None,
        candidate_id=str(candidate_id) if candidate_id is not None else None,
        action=str(action) if action is not None else None,
        validation_status=validation_status,
        approved=approved,
        reasons=reasons,
        safety_notes=safety_notes,
    )


def validate_correction_proposals(
    proposals_data: dict[str, Any],
    *,
    source_proposals_path: str | None = None,
    midi_mutation_allowed: bool = False,
) -> CorrectionValidationBatch:
    proposals = proposals_data.get("proposals") or []

    validations = [validate_correction_proposal(proposal) for proposal in proposals]

    approved_count = sum(1 for item in validations if item.approved)
    rejected_count = len(validations) - approved_count

    return CorrectionValidationBatch(
        status="completed",
        job_id=proposals_data.get("job_id"),
        source_proposals_path=source_proposals_path,
        proposal_count=len(proposals),
        approved_count=approved_count,
        rejected_count=rejected_count,
        validations=validations,
        midi_mutation_allowed=midi_mutation_allowed,
        error=None,
    )
