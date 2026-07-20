from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_validate_corrections_tool_requires_proposals_path():
    response = client.post(
        "/api/tools/validate_corrections/execute",
        json={"payload": {}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "validate_corrections"
    assert body["status"] == "error"
    assert body["error"] == "Missing required field: proposals_path"


def test_validate_corrections_tool_returns_compact_summary(tmp_path):
    proposals_path = tmp_path / "proposals.json"
    proposals_path.write_text(
        json.dumps(
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
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/api/tools/validate_corrections/execute",
        json={
            "payload": {
                "proposals_path": str(proposals_path),
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "validate_corrections"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["job_id"] == "pytest-job"
    assert data["source_proposals_path"] == str(proposals_path)
    assert data["proposal_count"] == 1
    assert data["approved_count"] == 1
    assert data["rejected_count"] == 0
    assert data["midi_mutation_allowed"] is False

    assert data["validations_included"] is False
    assert data["returned_validation_count"] == 0
    assert data["validations"] == []


def test_validate_corrections_tool_can_include_limited_validations(tmp_path):
    proposals_path = tmp_path / "proposals.json"
    proposals_path.write_text(
        json.dumps(
            {
                "job_id": "pytest-job",
                "proposals": [
                    {
                        "proposal_id": "prop_0000",
                        "candidate_id": "n0",
                        "action": "flag_for_review",
                    },
                    {
                        "proposal_id": "prop_0001",
                        "candidate_id": "n1",
                        "action": "flag_for_review",
                        "proposed_pitch": 61,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/api/tools/validate_corrections/execute",
        json={
            "payload": {
                "proposals_path": str(proposals_path),
                "include_validations": True,
                "max_response_validations": 1,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]

    assert body["status"] == "success"
    assert data["proposal_count"] == 2
    assert data["approved_count"] == 1
    assert data["rejected_count"] == 1
    assert data["validations_included"] is True
    assert data["returned_validation_count"] == 1
    assert len(data["validations"]) == 1

    validation = data["validations"][0]

    assert validation["proposal_id"] == "prop_0000"
    assert validation["validation_status"] == "approved_for_review"
    assert validation["approved"] is True


def test_validate_corrections_tool_writes_full_output_artifact(tmp_path):
    proposals_path = tmp_path / "proposals.json"
    output_path = tmp_path / "validation.json"

    proposals_path.write_text(
        json.dumps(
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
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/api/tools/validate_corrections/execute",
        json={
            "payload": {
                "proposals_path": str(proposals_path),
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
    assert artifact["approved_count"] == 1
    assert artifact["rejected_count"] == 0
    assert artifact["midi_mutation_allowed"] is False
    assert len(artifact["validations"]) == 1
