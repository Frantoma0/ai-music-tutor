from __future__ import annotations

import pytest

from app.pipeline.llm_correction_batch import validate_correction_batch_json
from app.pipeline.llm_metadata_locking import (
    MetadataLockingError,
    lock_correction_batch_metadata,
)


def test_lock_correction_batch_metadata_preserves_candidate_values():
    batch = validate_correction_batch_json(
        {
            "status": "completed",
            "corrections": [
                {
                    "candidate_id": "n87",
                    "action": "keep",
                    "reason": "model says keep",
                    "confidence": 0.6,
                    "hvs_score": 0.6,
                }
            ],
        }
    )

    locked = lock_correction_batch_metadata(
        batch,
        candidates=[
            {
                "id": "n87",
                "pitch": 47,
                "pitch_name": "B2",
                "start": 11.465909,
                "end": 11.638636,
                "confidence": 0.629913,
                "hvs_score": 0.6,
                "reason": "low_confidence_high_hvs",
            }
        ],
    )

    correction = locked["corrections"][0]

    assert locked["metadata_locked"] is True
    assert correction["candidate_id"] == "n87"
    assert correction["action"] == "keep"
    assert correction["reason"] == "model says keep"

    assert correction["original_pitch"] == 47
    assert correction["pitch_name"] == "B2"
    assert correction["original_start"] == 11.465909
    assert correction["original_end"] == 11.638636

    # Important: system keeps original candidate metadata,
    # not rounded/rewritten LLM metadata.
    assert correction["confidence"] == 0.629913
    assert correction["hvs_score"] == 0.6
    assert correction["mask_reason"] == "low_confidence_high_hvs"

    assert correction["metadata_source"] == "system_candidate_locked"
    assert correction["llm_metadata_ignored"] is True


def test_lock_correction_batch_metadata_rejects_unknown_candidate_id():
    batch = validate_correction_batch_json(
        {
            "status": "completed",
            "corrections": [
                {
                    "candidate_id": "missing",
                    "action": "keep",
                    "reason": "unknown",
                }
            ],
        }
    )

    with pytest.raises(MetadataLockingError, match="unknown candidate_id"):
        lock_correction_batch_metadata(
            batch,
            candidates=[
                {
                    "id": "n87",
                    "pitch": 47,
                }
            ],
        )


def test_lock_correction_batch_metadata_preserves_llm_proposed_pitch():
    batch = validate_correction_batch_json(
        {
            "status": "completed",
            "corrections": [
                {
                    "candidate_id": "n87",
                    "action": "propose_pitch_shift",
                    "original_pitch": 47,
                    "proposed_pitch": 48,
                    "reason": "safe semitone correction",
                }
            ],
        }
    )

    locked = lock_correction_batch_metadata(
        batch,
        candidates=[
            {
                "id": "n87",
                "pitch": 47,
                "pitch_name": "B2",
                "start": 11.465909,
                "end": 11.638636,
                "confidence": 0.629913,
                "hvs_score": 0.6,
            }
        ],
    )

    correction = locked["corrections"][0]

    assert correction["original_pitch"] == 47
    assert correction["proposed_pitch"] == 48
    assert correction["confidence"] == 0.629913
    assert correction["metadata_source"] == "system_candidate_locked"
