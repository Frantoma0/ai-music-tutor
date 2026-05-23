from __future__ import annotations

from app.pipeline.llm_pitch_safety import validate_locked_pitch_corrections


def test_validate_locked_pitch_corrections_approves_non_pitch_actions():
    result = validate_locked_pitch_corrections(
        {
            "corrections": [
                {
                    "candidate_id": "n1",
                    "action": "keep",
                    "original_pitch": 60,
                    "proposed_pitch": None,
                },
                {
                    "candidate_id": "n2",
                    "action": "flag_for_review",
                    "original_pitch": 61,
                    "proposed_pitch": None,
                },
            ]
        }
    )

    assert result["status"] == "completed"
    assert result["approved_count"] == 2
    assert result["rejected_count"] == 0
    assert result["correction_acceptance_rate"] is None


def test_validate_locked_pitch_corrections_approves_safe_pitch_shift():
    result = validate_locked_pitch_corrections(
        {
            "corrections": [
                {
                    "candidate_id": "n1",
                    "action": "propose_pitch_shift",
                    "original_pitch": 59,
                    "proposed_pitch": 60,
                }
            ]
        }
    )

    assert result["status"] == "completed"
    assert result["approved_count"] == 1
    assert result["rejected_count"] == 0
    assert result["approved_pitch_shift_count"] == 1
    assert result["correction_acceptance_rate"] == 1.0


def test_validate_locked_pitch_corrections_rejects_large_pitch_shift():
    result = validate_locked_pitch_corrections(
        {
            "corrections": [
                {
                    "candidate_id": "n1",
                    "action": "propose_pitch_shift",
                    "original_pitch": 47,
                    "proposed_pitch": 60,
                }
            ]
        }
    )

    assert result["status"] == "partial"
    assert result["approved_count"] == 0
    assert result["rejected_count"] == 1
    assert result["correction_acceptance_rate"] == 0.0
    assert "pitch_shift_exceeds_safe_limit" in result["rejected"][0]["pitch_safety_reasons"]


def test_validate_locked_pitch_corrections_rejects_out_of_range_pitch():
    result = validate_locked_pitch_corrections(
        {
            "corrections": [
                {
                    "candidate_id": "n1",
                    "action": "propose_pitch_shift",
                    "original_pitch": 107,
                    "proposed_pitch": 109,
                }
            ]
        }
    )

    assert result["status"] == "partial"
    assert result["rejected_count"] == 1
    assert "proposed_pitch_outside_piano_range" in result["rejected"][0]["pitch_safety_reasons"]


def test_validate_locked_pitch_corrections_rejects_same_pitch_noop():
    result = validate_locked_pitch_corrections(
        {
            "corrections": [
                {
                    "candidate_id": "n1",
                    "action": "propose_pitch_shift",
                    "original_pitch": 60,
                    "proposed_pitch": 60,
                }
            ]
        }
    )

    assert result["status"] == "partial"
    assert result["rejected_count"] == 1
    assert "proposed_pitch_same_as_original" in result["rejected"][0]["pitch_safety_reasons"]
