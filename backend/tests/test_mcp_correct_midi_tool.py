from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_correct_midi_tool_requires_mask_path():
    response = client.post(
        "/api/tools/correct_midi/execute",
        json={"payload": {}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "correct_midi"
    assert body["status"] == "error"
    assert body["error"] == "Missing required field: mask_path"


def test_correct_midi_tool_returns_compact_proposal_summary(tmp_path):
    mask_path = tmp_path / "mask.json"
    mask_path.write_text(
        json.dumps(
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
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/api/tools/correct_midi/execute",
        json={
            "payload": {
                "mask_path": str(mask_path),
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "correct_midi"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "pytest-job"
    assert data["source_mask_path"] == str(mask_path)
    assert data["candidate_count"] == 2
    assert data["selected_candidate_count"] == 1
    assert data["proposal_count"] == 1

    assert data["midi_mutated"] is False
    assert data["proposals_included"] is False
    assert data["returned_proposal_count"] == 0
    assert data["proposals"] == []


def test_correct_midi_tool_can_include_limited_proposals(tmp_path):
    mask_path = tmp_path / "mask.json"
    mask_path.write_text(
        json.dumps(
            {
                "job_id": "pytest-job",
                "candidates": [
                    {
                        "id": "n0",
                        "pitch": 60,
                        "start": 0.0,
                        "end": 1.0,
                        "confidence": 0.5,
                        "hvs_score": 0.6,
                        "selected": True,
                        "reason": "low_confidence_high_hvs",
                    },
                    {
                        "id": "n1",
                        "pitch": 61,
                        "start": 1.0,
                        "end": 2.0,
                        "confidence": 0.4,
                        "hvs_score": 0.6,
                        "selected": True,
                        "reason": "low_confidence_high_hvs",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/api/tools/correct_midi/execute",
        json={
            "payload": {
                "mask_path": str(mask_path),
                "include_proposals": True,
                "max_response_proposals": 1,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]

    assert body["status"] == "success"
    assert data["proposal_count"] == 2
    assert data["proposals_included"] is True
    assert data["returned_proposal_count"] == 1
    assert len(data["proposals"]) == 1

    proposal = data["proposals"][0]

    assert proposal["candidate_id"] == "n0"
    assert proposal["action"] == "flag_for_review"
    assert proposal["proposed_pitch"] is None
    assert proposal["proposed_start"] is None
    assert proposal["proposed_end"] is None
    assert "placeholder_proposal_no_midi_mutation" in proposal["safety_notes"]


def test_correct_midi_tool_writes_full_output_artifact(tmp_path):
    mask_path = tmp_path / "mask.json"
    output_path = tmp_path / "proposals.json"

    mask_path.write_text(
        json.dumps(
            {
                "job_id": "pytest-job",
                "candidates": [
                    {
                        "id": "n0",
                        "pitch": 60,
                        "confidence": 0.5,
                        "hvs_score": 0.6,
                        "selected": True,
                        "reason": "low_confidence_high_hvs",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/api/tools/correct_midi/execute",
        json={
            "payload": {
                "mask_path": str(mask_path),
                "output_path": str(output_path),
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert output_path.exists()

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["job_id"] == "pytest-job"
    assert artifact["proposal_count"] == 1
    assert artifact["midi_mutated"] is False
    assert len(artifact["proposals"]) == 1
