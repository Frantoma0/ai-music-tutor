from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_tools_names_endpoint() -> None:
    response = client.get("/api/tools/names")

    assert response.status_code == 200
    assert response.json() == [
        "extract_audio",
        "separate_sources",
        "transcribe_audio",
        "analyze_harmony",
        "generate_mask",
        "correct_midi",
        "validate_corrections",
        "prepare_lesson",
        "run_tracer_bullet",
        "run_audio_to_analysis",
        "list_pipeline_runs",
        "get_pipeline_run",
        "list_metrics",
        "get_metrics_for_run",
        "list_correction_runs",
        "get_correction_run",
        "separate_lass",
        "practice_coach",
    ]


def test_tools_contracts_endpoint() -> None:
    response = client.get("/api/tools")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 18

    by_name = {contract["name"]: contract for contract in data}
    assert data[-1]["name"] == "practice_coach"
    assert by_name["practice_coach"]["status"] == "ready"
    assert by_name["practice_coach"]["category"] == "lesson"
    assert by_name["separate_lass"]["status"] == "experimental"


def test_pipeline_websocket_stub() -> None:
    with client.websocket_connect("/ws/pipeline/test-job") as websocket:
        first_message = websocket.receive_json()

        assert first_message["job_id"] == "test-job"
        assert first_message["status"] == "connected"

        websocket.send_text("ping")
        echo = websocket.receive_json()

        assert echo["job_id"] == "test-job"
        assert echo["status"] == "echo"
        assert echo["message"] == "ping"
