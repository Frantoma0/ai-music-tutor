from __future__ import annotations

import json

from app.scripts.qwen_candidate_chunks_smoke import run_qwen_candidate_chunks_smoke


class FakeResponse:
    def __init__(self, candidate_ids):
        self.candidate_ids = candidate_ids

    def raise_for_status(self):
        return None

    def json(self):
        corrections = [
            {
                "candidate_id": candidate_id,
                "action": "flag_for_review",
                "reason": "mocked chunk response",
            }
            for candidate_id in self.candidate_ids
        ]

        return {
            "response": json.dumps(
                {
                    "status": "completed",
                    "corrections": corrections,
                }
            )
        }


def test_qwen_candidate_chunks_smoke_merges_chunks_and_validates_coverage(
    tmp_path,
    monkeypatch,
):
    mask_path = tmp_path / "mask.json"
    output_path = tmp_path / "chunks.json"

    candidates = [
        {
            "id": f"n{index}",
            "pitch": 60 + index,
            "pitch_name": f"N{index}",
            "start": float(index),
            "end": float(index) + 0.5,
            "confidence": 0.6,
            "hvs_score": 0.6,
            "selected": True,
            "reason": "low_confidence_high_hvs",
        }
        for index in range(5)
    ]

    mask_path.write_text(
        json.dumps({"candidates": candidates}),
        encoding="utf-8",
    )

    def fake_post(url, json, timeout):
        prompt = json["prompt"]

        candidate_ids = [candidate["id"] for candidate in candidates if candidate["id"] in prompt]

        return FakeResponse(candidate_ids)

    monkeypatch.setattr(
        "app.scripts.qwen_candidate_chunks_smoke.httpx.post",
        fake_post,
    )

    result = run_qwen_candidate_chunks_smoke(
        base_url="http://ollama.test",
        model="qwen3:test",
        mask_path=str(mask_path),
        output=str(output_path),
        candidate_limit=5,
        chunk_size=2,
    )

    assert result["status"] == "completed"
    assert result["candidate_count"] == 5
    assert result["chunk_count"] == 3
    assert result["completed_chunk_count"] == 3
    assert result["failed_chunk_count"] == 0
    assert result["locked_correction_count"] == 5

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["coverage"]["ok"] is True
    assert artifact["coverage"]["expected_candidate_count"] == 5
    assert artifact["coverage"]["locked_candidate_count"] == 5
    assert artifact["coverage"]["missing_candidate_ids"] == []
    assert artifact["coverage"]["duplicate_candidate_ids"] == []
    assert artifact["locked"]["correction_count"] == 5


def test_qwen_candidate_chunks_smoke_marks_missing_candidates_as_error(
    tmp_path,
    monkeypatch,
):
    mask_path = tmp_path / "mask.json"
    output_path = tmp_path / "chunks_missing.json"

    candidates = [
        {
            "id": "n1",
            "pitch": 60,
            "pitch_name": "C4",
            "start": 1.0,
            "end": 1.5,
            "confidence": 0.6,
            "hvs_score": 0.6,
            "selected": True,
            "reason": "low_confidence_high_hvs",
        },
        {
            "id": "n2",
            "pitch": 61,
            "pitch_name": "C#4",
            "start": 2.0,
            "end": 2.5,
            "confidence": 0.6,
            "hvs_score": 0.6,
            "selected": True,
            "reason": "low_confidence_high_hvs",
        },
    ]

    mask_path.write_text(
        json.dumps({"candidates": candidates}),
        encoding="utf-8",
    )

    class MissingResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": json.dumps(
                    {
                        "status": "completed",
                        "corrections": [
                            {
                                "candidate_id": "n1",
                                "action": "flag_for_review",
                                "reason": "mocked incomplete response",
                            }
                        ],
                    }
                )
            }

    def fake_post(url, json, timeout):
        return MissingResponse()

    monkeypatch.setattr(
        "app.scripts.qwen_candidate_chunks_smoke.httpx.post",
        fake_post,
    )

    result = run_qwen_candidate_chunks_smoke(
        base_url="http://ollama.test",
        model="qwen3:test",
        mask_path=str(mask_path),
        output=str(output_path),
        candidate_limit=2,
        chunk_size=2,
    )

    assert result["status"] == "error"
    assert result["locked_correction_count"] == 1

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["coverage"]["ok"] is False
    assert artifact["coverage"]["missing_candidate_ids"] == ["n2"]
    assert artifact["locked"]["status"] == "partial"
