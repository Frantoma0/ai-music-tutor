from __future__ import annotations

from typing import Any

from app.pipeline.llm_correction_batch import (
    CorrectionBatchValidationError,
    LLMCorrectionBatch,
)


class MetadataLockingError(ValueError):
    pass


def _candidate_id(candidate: dict[str, Any]) -> str | None:
    value = candidate.get("id") or candidate.get("candidate_id")

    if value is None:
        return None

    return str(value)


def _candidate_index(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}

    for candidate in candidates:
        candidate_id = _candidate_id(candidate)

        if not candidate_id:
            continue

        indexed[candidate_id] = candidate

    return indexed


def lock_correction_batch_metadata(
    batch: LLMCorrectionBatch,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    indexed_candidates = _candidate_index(candidates)

    locked_corrections: list[dict[str, Any]] = []

    for correction in batch.corrections:
        candidate = indexed_candidates.get(correction.candidate_id)

        if candidate is None:
            raise MetadataLockingError(
                f"Correction references unknown candidate_id: {correction.candidate_id}"
            )

        locked_corrections.append(
            {
                "candidate_id": correction.candidate_id,
                "action": correction.action,
                "reason": correction.reason,
                # System-owned original metadata.
                "original_pitch": candidate.get("pitch"),
                "pitch_name": candidate.get("pitch_name"),
                "original_start": candidate.get("start"),
                "original_end": candidate.get("end"),
                "confidence": candidate.get("confidence"),
                "hvs_score": candidate.get("hvs_score"),
                "mask_reason": candidate.get("reason"),
                # LLM-owned proposed fields.
                "proposed_pitch": correction.proposed_pitch,
                "proposed_start": correction.proposed_start,
                "proposed_end": correction.proposed_end,
                # Traceability.
                "metadata_source": "system_candidate_locked",
                "llm_metadata_ignored": True,
            }
        )

    return {
        "status": batch.status,
        "correction_count": len(locked_corrections),
        "metadata_locked": True,
        "corrections": locked_corrections,
    }


def validate_and_lock_correction_batch(
    *,
    batch: LLMCorrectionBatch,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    if batch.correction_count != len(batch.corrections):
        raise CorrectionBatchValidationError(
            "Correction batch count does not match corrections length"
        )

    return lock_correction_batch_metadata(
        batch=batch,
        candidates=candidates,
    )
