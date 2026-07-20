from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

ALLOWED_PROPOSAL_ACTIONS = {
    "keep",
    "flag_for_review",
    "propose_pitch_shift",
    "propose_timing_adjustment",
    "propose_delete",
}


@dataclass(frozen=True)
class CorrectionProposal:
    proposal_id: str
    candidate_id: str | None
    action: str

    original_pitch: int | None
    proposed_pitch: int | None

    original_start: float | None
    proposed_start: float | None

    original_end: float | None
    proposed_end: float | None

    confidence: float | None
    hvs_score: float | None

    reason: str
    status: str
    safety_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CorrectionProposalBatch:
    status: str
    job_id: str | None
    source_mask_path: str | None
    candidate_count: int
    selected_candidate_count: int
    proposal_count: int
    proposals: list[CorrectionProposal]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "job_id": self.job_id,
            "source_mask_path": self.source_mask_path,
            "candidate_count": self.candidate_count,
            "selected_candidate_count": self.selected_candidate_count,
            "proposal_count": self.proposal_count,
            "proposals": [proposal.to_dict() for proposal in self.proposals],
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


def _validate_action(action: str) -> None:
    if action not in ALLOWED_PROPOSAL_ACTIONS:
        allowed = ", ".join(sorted(ALLOWED_PROPOSAL_ACTIONS))
        raise ValueError(f"Unsupported correction proposal action: {action}. Allowed: {allowed}")


def build_flag_for_review_proposal(
    candidate: dict[str, Any],
    *,
    index: int,
) -> CorrectionProposal:
    """
    Build a safe placeholder correction proposal.

    This does not mutate pitch or timing. It only marks a selected mask candidate
    for later review/correction by T6.
    """
    action = "flag_for_review"
    _validate_action(action)

    candidate_id = candidate.get("id")

    return CorrectionProposal(
        proposal_id=f"prop_{index:04d}",
        candidate_id=str(candidate_id) if candidate_id is not None else None,
        action=action,
        original_pitch=_as_int(candidate.get("pitch")),
        proposed_pitch=None,
        original_start=_as_float(candidate.get("start")),
        proposed_start=None,
        original_end=_as_float(candidate.get("end")),
        proposed_end=None,
        confidence=_as_float(candidate.get("confidence")),
        hvs_score=_as_float(candidate.get("hvs_score")),
        reason=(
            "selected_mask_candidate_requires_review:"
            f"{candidate.get('reason') or 'unknown_reason'}"
        ),
        status="pending_validation",
        safety_notes=[
            "placeholder_proposal_no_midi_mutation",
            "requires_validation_before_any_edit",
        ],
    )


def build_correction_proposals_from_mask(
    mask_data: dict[str, Any],
    *,
    source_mask_path: str | None = None,
    max_proposals: int | None = None,
) -> CorrectionProposalBatch:
    """
    Convert selected correction mask candidates into safe correction proposals.

    Current Day 11 behavior:
        selected candidate -> flag_for_review

    Future behavior:
        selected candidate -> constrained pitch/timing proposal
    """
    candidates = mask_data.get("candidates") or []
    selected_candidates = [candidate for candidate in candidates if bool(candidate.get("selected"))]

    if max_proposals is not None:
        selected_candidates = selected_candidates[: max(0, int(max_proposals))]

    proposals = [
        build_flag_for_review_proposal(candidate, index=index)
        for index, candidate in enumerate(selected_candidates)
    ]

    return CorrectionProposalBatch(
        status="completed",
        job_id=mask_data.get("job_id"),
        source_mask_path=source_mask_path,
        candidate_count=len(candidates),
        selected_candidate_count=sum(
            1 for candidate in candidates if bool(candidate.get("selected"))
        ),
        proposal_count=len(proposals),
        proposals=proposals,
        error=None,
    )
