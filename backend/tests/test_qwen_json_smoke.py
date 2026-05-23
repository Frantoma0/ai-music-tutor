from __future__ import annotations

import json

from app.scripts.qwen_json_smoke import run_qwen_json_smoke


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "response": """<think>
internal reasoning
</think>

{"status":"ok","message":"hello"}"""
        }


def test_run_qwen_json_smoke_extracts_json_and_writes_artifact(tmp_path, monkeypatch):
    def fake_post(url, json, timeout):
        assert url == "http://ollama.test/api/generate"
        assert json["model"] == "qwen3:test"
        assert json["stream"] is False
        assert timeout == 90

        return FakeResponse()

    monkeypatch.setattr(
        "app.scripts.qwen_json_smoke.httpx.post",
        fake_post,
    )

    output_path = tmp_path / "qwen_smoke.json"

    result = run_qwen_json_smoke(
        base_url="http://ollama.test",
        model="qwen3:test",
        output=str(output_path),
    )

    assert result["status"] == "completed"
    assert result["parsed"] == {
        "status": "ok",
        "message": "hello",
    }
    assert result["error"] is None
    assert output_path.exists()

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["status"] == "completed"
    assert artifact["model"] == "qwen3:test"
    assert artifact["parsed"]["status"] == "ok"
    assert artifact["parsed"]["message"] == "hello"
    assert "<think>" in artifact["raw_response"]
