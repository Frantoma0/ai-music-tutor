from __future__ import annotations

import json

from app.scripts.qwen_pitch_correction_chunks import (
    build_pitch_correction_prompt,
    run_qwen_pitch_correction_chunks,
)


class FakePitchResponse:
    def __init__(self, response):
        self.response = response

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "response": json.dumps(self.response),
        }


def test_build_pitch_correction_prompt_includes_json_mode_constraints():
    prompt = build_pitch_correction_prompt(
        [
            {
                "id": "n117",
                "pitch": 59,
                "pitch_name": "B3",
                "start": 14.370455,
                "end": 14.509091,
                "confidence": 0.617295,
                "hvs_score": 0.6,
                "selected": True,
                "reason": "low_confidence_high_hvs",
            }
        ]
    )

    assert "detected_key: F major" in prompt
    assert "safe_pitch_options" in prompt
    assert "propose_pitch_shift" in prompt
    assert "Never invent candidate_id values" in prompt
    assert "Do NOT propose timing edits" in prompt
    assert "n117" in prompt
    assert "B3" in prompt


def test_qwen_pitch_correction_chunks_accepts_safe_pitch_shift(
    tmp_path,
    monkeypatch,
):
    mask_path = tmp_path / "mask.json"
    output_path = tmp_path / "pitch_result.json"

    mask_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "id": "n117",
                        "pitch": 59,
                        "pitch_name": "B3",
                        "start": 14.370455,
                        "end": 14.509091,
                        "confidence": 0.617295,
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
        assert json["format"] == "json"
        assert timeout == 180

        return FakePitchResponse(
            {
                "status": "completed",
                "corrections": [
                    {
                        "candidate_id": "n117",
                        "action": "propose_pitch_shift",
                        "proposed_pitch": 60,
                        "reason": "nearby diatonic option",
                    }
                ],
            }
        )

    monkeypatch.setattr(
        "app.scripts.qwen_pitch_correction_chunks.httpx.post",
        fake_post,
    )

    result = run_qwen_pitch_correction_chunks(
        base_url="http://ollama.test",
        model="qwen3:test",
        mask_path=str(mask_path),
        output=str(output_path),
        candidate_limit=1,
        chunk_size=1,
    )

    assert result["status"] == "completed"
    assert result["coverage_ok"] is True
    assert result["action_distribution"] == {
        "propose_pitch_shift": 1,
    }
    assert result["approved_pitch_shift_count"] == 1
    assert result["rejected_pitch_shift_count"] == 0
    assert result["correction_acceptance_rate"] == 1.0

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["coverage"]["ok"] is True
    assert artifact["locked"]["correction_count"] == 1
    assert artifact["pitch_safety"]["approved_pitch_shift_count"] == 1
    assert artifact["pitch_safety"]["rejected_pitch_shift_count"] == 0
    assert artifact["pitch_safety"]["approved"][0]["original_pitch"] == 59
    assert artifact["pitch_safety"]["approved"][0]["proposed_pitch"] == 60


def test_qwen_pitch_correction_chunks_rejects_unsafe_pitch_shift(
    tmp_path,
    monkeypatch,
):
    mask_path = tmp_path / "mask.json"
    output_path = tmp_path / "pitch_result_rejected.json"

    mask_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "id": "n175",
                        "pitch": 71,
                        "pitch_name": "B4",
                        "start": 20.0,
                        "end": 20.5,
                        "confidence": 0.5,
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
        return FakePitchResponse(
            {
                "status": "completed",
                "corrections": [
                    {
                        "candidate_id": "n175",
                        "action": "propose_pitch_shift",
                        "proposed_pitch": 60,
                        "reason": "bad octave jump",
                    }
                ],
            }
        )

    monkeypatch.setattr(
        "app.scripts.qwen_pitch_correction_chunks.httpx.post",
        fake_post,
    )

    result = run_qwen_pitch_correction_chunks(
        base_url="http://ollama.test",
        model="qwen3:test",
        mask_path=str(mask_path),
        output=str(output_path),
        candidate_limit=1,
        chunk_size=1,
    )

    assert result["status"] == "completed"
    assert result["coverage_ok"] is True
    assert result["approved_pitch_shift_count"] == 0
    assert result["rejected_pitch_shift_count"] == 1
    assert result["correction_acceptance_rate"] == 0.0

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["pitch_safety"]["status"] == "partial"
    assert artifact["pitch_safety"]["rejected"][0]["candidate_id"] == "n175"
    assert "pitch_shift_exceeds_safe_limit" in artifact["pitch_safety"]["rejected"][0]["pitch_safety_reasons"]


def test_qwen_pitch_correction_chunks_marks_missing_coverage_as_error(
    tmp_path,
    monkeypatch,
):
    mask_path = tmp_path / "mask.json"
    output_path = tmp_path / "pitch_result_missing.json"

    mask_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "id": "n1",
                        "pitch": 59,
                        "pitch_name": "B3",
                        "start": 1.0,
                        "end": 1.5,
                        "confidence": 0.6,
                        "hvs_score": 0.6,
                        "selected": True,
                        "reason": "low_confidence_high_hvs",
                    },
                    {
                        "id": "n2",
                        "pitch": 78,
                        "pitch_name": "F#5",
                        "start": 2.0,
                        "end": 2.5,
                        "confidence": 0.6,
                        "hvs_score": 0.6,
                        "selected": True,
                        "reason": "low_confidence_high_hvs",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_post(url, json, timeout):
        return FakePitchResponse(
            {
                "status": "completed",
                "corrections": [
                    {
                        "candidate_id": "n1",
                        "action": "flag_for_review",
                        "reason": "mocked partial response",
                    }
                ],
            }
        )

    monkeypatch.setattr(
        "app.scripts.qwen_pitch_correction_chunks.httpx.post",
        fake_post,
    )

    result = run_qwen_pitch_correction_chunks(
        base_url="http://ollama.test",
        model="qwen3:test",
        mask_path=str(mask_path),
        output=str(output_path),
        candidate_limit=2,
        chunk_size=2,
    )

    assert result["status"] == "error"
    assert result["coverage_ok"] is False

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["coverage"]["ok"] is False
    assert artifact["coverage"]["missing_candidate_ids"] == ["n2"]
    assert artifact["locked"]["status"] == "partial"
