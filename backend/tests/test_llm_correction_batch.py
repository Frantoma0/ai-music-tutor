from __future__ import annotations

import pytest

from app.pipeline.llm_correction_batch import (
    CorrectionBatchValidationError,
    validate_correction_batch_json,
    validate_correction_item_json,
)


def test_validate_correction_batch_accepts_keep_and_flag_for_review():
    batch = validate_correction_batch_json(
        {
            "status": "completed",
            "corrections": [
                {
                    "candidate_id": "n1",
                    "action": "keep",
                    "reason": "already stable",
                },
                {
                    "candidate_id": "n2",
                    "action": "flag_for_review",
                    "reason": "low confidence high hvs",
                    "confidence": 0.61,
                    "hvs_score": 0.6,
                },
            ],
        }
    )

    data = batch.to_dict()

    assert data["status"] == "completed"
    assert data["correction_count"] == 2
    assert data["corrections"][0]["candidate_id"] == "n1"
    assert data["corrections"][1]["action"] == "flag_for_review"


def test_validate_correction_item_accepts_safe_pitch_shift():
    item = validate_correction_item_json(
        {
            "candidate_id": "n1",
            "action": "propose_pitch_shift",
            "original_pitch": 59,
            "proposed_pitch": 60,
            "reason": "likely neighbor correction",
        }
    )

    assert item.candidate_id == "n1"
    assert item.action == "propose_pitch_shift"
    assert item.proposed_pitch == 60


def test_validate_correction_item_rejects_large_pitch_shift():
    with pytest.raises(CorrectionBatchValidationError, match="pitch shift exceeds safe limit"):
        validate_correction_item_json(
            {
                "candidate_id": "n1",
                "action": "propose_pitch_shift",
                "original_pitch": 47,
                "proposed_pitch": 60,
                "reason": "too large",
            }
        )


def test_validate_correction_item_rejects_pitch_outside_piano_range():
    with pytest.raises(CorrectionBatchValidationError, match="outside piano MIDI range"):
        validate_correction_item_json(
            {
                "candidate_id": "n1",
                "action": "propose_pitch_shift",
                "original_pitch": 107,
                "proposed_pitch": 109,
                "reason": "outside range",
            }
        )


def test_validate_correction_item_accepts_safe_timing_adjustment():
    item = validate_correction_item_json(
        {
            "candidate_id": "n1",
            "action": "propose_timing_adjustment",
            "original_start": 1.0,
            "proposed_start": 1.05,
            "original_end": 1.5,
            "proposed_end": 1.55,
            "reason": "small onset correction",
        }
    )

    assert item.action == "propose_timing_adjustment"
    assert item.proposed_start == 1.05
    assert item.proposed_end == 1.55


def test_validate_correction_item_rejects_negative_timing():
    with pytest.raises(CorrectionBatchValidationError, match="before zero"):
        validate_correction_item_json(
            {
                "candidate_id": "n1",
                "action": "propose_timing_adjustment",
                "proposed_start": -0.1,
                "reason": "invalid",
            }
        )


def test_validate_correction_item_rejects_unknown_action():
    with pytest.raises(CorrectionBatchValidationError, match="unsupported action"):
        validate_correction_item_json(
            {
                "candidate_id": "n1",
                "action": "delete",
                "reason": "not allowed",
            }
        )


def test_validate_correction_batch_rejects_missing_corrections_list():
    with pytest.raises(CorrectionBatchValidationError, match="corrections must be a list"):
        validate_correction_batch_json(
            {
                "status": "completed",
            }
        )


def test_keep_rejects_hidden_mutation_fields():
    with pytest.raises(CorrectionBatchValidationError, match="keep must not include"):
        validate_correction_item_json(
            {
                "candidate_id": "n1",
                "action": "keep",
                "proposed_pitch": 61,
                "reason": "hidden mutation",
            }
        )
