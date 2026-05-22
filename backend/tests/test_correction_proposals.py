from __future__ import annotations

import json

from app.pipeline.correction_proposals import (
    build_correction_proposals_from_mask,
    build_flag_for_review_proposal,
)


def test_build_flag_for_review_proposal_does_not_mutate_pitch_or_timing():
    proposal = build_flag_for_review_proposal(
        {
            "id": "n87",
            "pitch": 47,
            "pitch_name": "B2",
            "start": 11.465909,
            "end": 11.638636,
            "confidence": 0.629913,
            "hvs_score": 0.6,
            "reason": "low_confidence_high_hvs",
        },
        index=0,
    )

    data = proposal.to_dict()

    assert data["proposal_id"] == "prop_0000"
    assert data["candidate_id"] == "n87"
    assert data["action"] == "flag_for_review"

    assert data["original_pitch"] == 47
    assert data["proposed_pitch"] is None

    assert data["original_start"] == 11.465909
    assert data["proposed_start"] is None

    assert data["original_end"] == 11.638636
    assert data["proposed_end"] is None

    assert data["confidence"] == 0.629913
    assert data["hvs_score"] == 0.6
    assert data["status"] == "pending_validation"

    assert "placeholder_proposal_no_midi_mutation" in data["safety_notes"]
    assert "requires_validation_before_any_edit" in data["safety_notes"]


def test_build_correction_proposals_from_mask_uses_only_selected_candidates():
    batch = build_correction_proposals_from_mask(
        {
            "job_id": "pytest-job",
            "candidates": [
                {
                    "id": "n0",
                    "pitch": 60,
                    "start": 0.0,
                    "end": 1.0,
                    "confidence": 0.9,
                    "hvs_score": 0.0,
                    "selected": False,
                    "reason": "confidence_above_threshold",
                },
                {
                    "id": "n1",
                    "pitch": 61,
                    "start": 1.0,
                    "end": 2.0,
                    "confidence": 0.5,
                    "hvs_score": 0.6,
                    "selected": True,
                    "reason": "low_confidence_high_hvs",
                },
            ],
        },
        source_mask_path="mask.json",
    )

    data = batch.to_dict()

    assert data["status"] == "completed"
    assert data["job_id"] == "pytest-job"
    assert data["source_mask_path"] == "mask.json"
    assert data["candidate_count"] == 2
    assert data["selected_candidate_count"] == 1
    assert data["proposal_count"] == 1

    assert data["proposals"][0]["candidate_id"] == "n1"
    assert data["proposals"][0]["action"] == "flag_for_review"


def test_build_correction_proposals_respects_max_proposals():
    batch = build_correction_proposals_from_mask(
        {
            "job_id": "pytest-job",
            "candidates": [
                {"id": "n0", "pitch": 60, "selected": True},
                {"id": "n1", "pitch": 61, "selected": True},
                {"id": "n2", "pitch": 62, "selected": True},
            ],
        },
        max_proposals=2,
    )

    data = batch.to_dict()

    assert data["selected_candidate_count"] == 3
    assert data["proposal_count"] == 2
    assert [item["candidate_id"] for item in data["proposals"]] == ["n0", "n1"]


def test_correction_proposal_batch_is_json_serializable():
    batch = build_correction_proposals_from_mask(
        {
            "job_id": "pytest-job",
            "candidates": [
                {
                    "id": "n1",
                    "pitch": 61,
                    "start": 1.0,
                    "end": 2.0,
                    "confidence": 0.5,
                    "hvs_score": 0.6,
                    "selected": True,
                    "reason": "low_confidence_high_hvs",
                }
            ],
        },
    )

    encoded = json.dumps(batch.to_dict())
    decoded = json.loads(encoded)

    assert decoded["status"] == "completed"
    assert decoded["proposal_count"] == 1
