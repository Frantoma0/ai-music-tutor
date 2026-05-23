from __future__ import annotations

import json

from app.scripts.qwen_three_candidate_smoke import (
    build_prompt,
    run_qwen_three_candidate_smoke,
)


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "response": """<think>
reasoning
</think>

{
  "status": "completed",
  "corrections": [
    {
      "candidate_id": "n87",
      "action": "keep",
      "reason": "safe smoke response",
      "confidence": 0.6,
      "hvs_score": 0.6
    }
  ]
}
"""
        }


def test_build_prompt_limits_actions_to_keep_or_flag_for_review():
    prompt = build_prompt(
        [
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
        ]
    )

    assert "choose only one action: keep or flag_for_review" in prompt
    assert "do NOT propose pitch shifts or timing edits" in prompt
    assert "n87" in prompt
    assert "B2" in prompt


def test_run_qwen_three_candidate_smoke_validates_batch_and_writes_artifact(
    tmp_path,
    monkeypatch,
):
    mask_path = tmp_path / "mask.json"
    output_path = tmp_path / "result.json"

    mask_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "id": "n87",
                        "pitch": 47,
                        "pitch_name": "B2",
                        "start": 11.465909,
                        "end": 11.638636,
                        "confidence": 0.629913,
                        "hvs_score": 0.6,
                        "selected": True,
                        "reason": "low_confidence_high_hvs",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_post(url, json, timeout):
        assert url == "http://ollama.test/api/generate"
        assert json["model"] == "qwen3:test"
        assert json["stream"] is False
        assert timeout == 120
        return FakeResponse()

    monkeypatch.setattr(
        "app.scripts.qwen_three_candidate_smoke.httpx.post",
        fake_post,
    )

    result = run_qwen_three_candidate_smoke(
        base_url="http://ollama.test",
        model="qwen3:test",
        mask_path=str(mask_path),
        output=str(output_path),
        candidate_limit=1,
    )

    assert result["status"] == "completed"
    assert result["candidate_count"] == 1
    assert result["correction_count"] == 1
    assert result["actions"] == ["keep"]

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["status"] == "completed"
    assert artifact["model"] == "qwen3:test"
    assert artifact["candidate_count"] == 1
    assert artifact["validated"]["correction_count"] == 1
    assert artifact["validated"]["corrections"][0]["candidate_id"] == "n87"

    assert artifact["locked"]["metadata_locked"] is True
    assert artifact["locked"]["correction_count"] == 1
    assert artifact["locked"]["corrections"][0]["candidate_id"] == "n87"
    assert artifact["locked"]["corrections"][0]["confidence"] == 0.629913
    assert artifact["locked"]["corrections"][0]["metadata_source"] == "system_candidate_locked"
