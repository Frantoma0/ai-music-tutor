from __future__ import annotations

import json

from app.pipeline.correction_validation import (
    validate_correction_proposal,
    validate_correction_proposals,
)


def test_validate_flag_for_review_proposal_is_approved_without_midi_mutation():
    validation = validate_correction_proposal(
        {
            "proposal_id": "prop_0000",
            "candidate_id": "n87",
            "action": "flag_for_review",
            "original_pitch": 47,
            "proposed_pitch": None,
            "original_start": 11.465909,
            "proposed_start": None,
            "original_end": 11.638636,
            "proposed_end": None,
        }
    )

    data = validation.__dict__

    assert data["proposal_id"] == "prop_0000"
    assert data["candidate_id"] == "n87"
    assert data["action"] == "flag_for_review"
    assert data["approved"] is True
    assert data["validation_status"] == "approved_for_review"
    assert data["reasons"] == []
    assert "safe_review_only_no_midi_mutation" in data["safety_notes"]


def test_validate_flag_for_review_rejects_hidden_pitch_mutation():
    validation = validate_correction_proposal(
        {
            "proposal_id": "prop_0000",
            "candidate_id": "n87",
            "action": "flag_for_review",
            "original_pitch": 47,
            "proposed_pitch": 48,
        }
    )

    data = validation.__dict__

    assert data["approved"] is False
    assert data["validation_status"] == "rejected"
    assert "flag_for_review_must_not_set_proposed_pitch" in data["reasons"]


def test_validate_pitch_shift_rejects_large_pitch_jump():
    validation = validate_correction_proposal(
        {
            "proposal_id": "prop_0000",
            "candidate_id": "n87",
            "action": "propose_pitch_shift",
            "original_pitch": 47,
            "proposed_pitch": 60,
        }
    )

    data = validation.__dict__

    assert data["approved"] is False
    assert data["validation_status"] == "rejected"
    assert "pitch_shift_exceeds_safe_limit" in data["reasons"]


def test_validate_timing_adjustment_rejects_negative_start():
    validation = validate_correction_proposal(
        {
            "proposal_id": "prop_0000",
            "candidate_id": "n87",
            "action": "propose_timing_adjustment",
            "original_start": 0.1,
            "proposed_start": -0.1,
            "original_end": 0.5,
            "proposed_end": 0.6,
        }
    )

    data = validation.__dict__

    assert data["approved"] is False
    assert "proposed_start_before_zero" in data["reasons"]


def test_validate_correction_proposals_batch_counts_approved_and_rejected():
    batch = validate_correction_proposals(
        {
            "job_id": "pytest-job",
            "proposals": [
                {
                    "proposal_id": "prop_0000",
                    "candidate_id": "n0",
                    "action": "flag_for_review",
                    "proposed_pitch": None,
                    "proposed_start": None,
                    "proposed_end": None,
                },
                {
                    "proposal_id": "prop_0001",
                    "candidate_id": "n1",
                    "action": "flag_for_review",
                    "proposed_pitch": 61,
                },
            ],
        },
        source_proposals_path="proposals.json",
    )

    data = batch.to_dict()

    assert data["status"] == "completed"
    assert data["job_id"] == "pytest-job"
    assert data["source_proposals_path"] == "proposals.json"
    assert data["proposal_count"] == 2
    assert data["approved_count"] == 1
    assert data["rejected_count"] == 1
    assert data["midi_mutation_allowed"] is False


def test_validation_batch_is_json_serializable():
    batch = validate_correction_proposals(
        {
            "job_id": "pytest-job",
            "proposals": [
                {
                    "proposal_id": "prop_0000",
                    "candidate_id": "n0",
                    "action": "flag_for_review",
                }
            ],
        }
    )

    encoded = json.dumps(batch.to_dict())
    decoded = json.loads(encoded)

    assert decoded["status"] == "completed"
    assert decoded["proposal_count"] == 1
    assert decoded["approved_count"] == 1
