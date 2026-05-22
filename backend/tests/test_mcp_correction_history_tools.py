from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_correction_runs_tool_returns_runs(monkeypatch):
    async def fake_list_correction_runs(db_path, *, job_id=None, limit=50):
        assert job_id == "pytest-job"
        assert limit == 5

        return [
            {
                "id": "crun_test",
                "job_id": "pytest-job",
                "pipeline_run_id": "run_test",
                "status": "completed",
                "note_count": 2,
                "candidate_count": 2,
                "selected_count": 1,
                "proposal_count": 1,
                "approved_count": 1,
                "rejected_count": 0,
                "midi_mutation_allowed": False,
                "midi_mutated": False,
            }
        ]

    monkeypatch.setattr(
        "app.mcp_tools.tools.db_list_correction_runs",
        fake_list_correction_runs,
    )

    response = client.post(
        "/api/tools/list_correction_runs/execute",
        json={
            "payload": {
                "db_path": "data/app.sqlite3",
                "job_id": "pytest-job",
                "limit": 5,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "list_correction_runs"
    assert body["status"] == "success"
    assert body["error"] is None

    data = body["data"]

    assert data["count"] == 1
    assert data["runs"][0]["id"] == "crun_test"
    assert data["runs"][0]["job_id"] == "pytest-job"
    assert data["runs"][0]["proposal_count"] == 1
    assert data["runs"][0]["approved_count"] == 1


def test_get_correction_run_tool_requires_correction_run_id():
    response = client.post(
        "/api/tools/get_correction_run/execute",
        json={"payload": {}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "get_correction_run"
    assert body["status"] == "error"
    assert body["error"] == "Missing required field: correction_run_id"


def test_get_correction_run_tool_returns_limited_details(monkeypatch):
    async def fake_get_correction_run(db_path, *, correction_run_id):
        assert correction_run_id == "crun_test"

        return {
            "id": "crun_test",
            "job_id": "pytest-job",
            "pipeline_run_id": "run_test",
            "status": "completed",
            "note_count": 2,
            "candidate_count": 2,
            "selected_count": 1,
            "proposal_count": 2,
            "approved_count": 2,
            "rejected_count": 0,
            "midi_mutation_allowed": False,
            "midi_mutated": False,
            "proposals": [
                {"proposal_id": "prop_0000", "candidate_id": "n0"},
                {"proposal_id": "prop_0001", "candidate_id": "n1"},
            ],
            "validations": [
                {"proposal_id": "prop_0000", "approved": True},
                {"proposal_id": "prop_0001", "approved": True},
            ],
        }

    monkeypatch.setattr(
        "app.mcp_tools.tools.db_get_correction_run",
        fake_get_correction_run,
    )

    response = client.post(
        "/api/tools/get_correction_run/execute",
        json={
            "payload": {
                "db_path": "data/app.sqlite3",
                "correction_run_id": "crun_test",
                "include_details": True,
                "max_items": 1,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_name"] == "get_correction_run"
    assert body["status"] == "success"

    data = body["data"]

    assert data["found"] is True
    assert data["details_included"] is True
    assert data["returned_proposal_count"] == 1
    assert data["returned_validation_count"] == 1

    run = data["correction_run"]

    assert run["id"] == "crun_test"
    assert run["proposal_count"] == 2
    assert len(run["proposals"]) == 1
    assert len(run["validations"]) == 1


def test_get_correction_run_tool_can_omit_details(monkeypatch):
    async def fake_get_correction_run(db_path, *, correction_run_id):
        return {
            "id": "crun_test",
            "job_id": "pytest-job",
            "proposal_count": 2,
            "approved_count": 2,
            "rejected_count": 0,
            "proposals": [
                {"proposal_id": "prop_0000"},
                {"proposal_id": "prop_0001"},
            ],
            "validations": [
                {"proposal_id": "prop_0000"},
                {"proposal_id": "prop_0001"},
            ],
        }

    monkeypatch.setattr(
        "app.mcp_tools.tools.db_get_correction_run",
        fake_get_correction_run,
    )

    response = client.post(
        "/api/tools/get_correction_run/execute",
        json={
            "payload": {
                "correction_run_id": "crun_test",
                "include_details": False,
            }
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]

    assert body["status"] == "success"
    assert data["found"] is True
    assert data["details_included"] is False
    assert data["returned_proposal_count"] == 0
    assert data["returned_validation_count"] == 0
    assert data["correction_run"]["proposals"] == []
    assert data["correction_run"]["validations"] == []


def test_get_correction_run_tool_returns_not_found(monkeypatch):
    async def fake_get_correction_run(db_path, *, correction_run_id):
        return None

    monkeypatch.setattr(
        "app.mcp_tools.tools.db_get_correction_run",
        fake_get_correction_run,
    )

    response = client.post(
        "/api/tools/get_correction_run/execute",
        json={
            "payload": {
                "correction_run_id": "missing",
            }
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]

    assert body["status"] == "success"
    assert data["found"] is False
    assert data["correction_run"] is None
    assert data["error"] is None
