from __future__ import annotations

import pytest

from app.pipeline.llm_json import (
    LLMJsonExtractionError,
    extract_first_json_object,
    require_json_fields,
    strip_think_blocks,
)


def test_strip_think_blocks_removes_qwen_reasoning():
    text = """<think>
internal reasoning
</think>

{"status":"ok","message":"hello"}"""

    cleaned = strip_think_blocks(text)

    assert "<think>" not in cleaned
    assert "</think>" not in cleaned
    assert cleaned == '{"status":"ok","message":"hello"}'


def test_extract_first_json_object_after_think_block():
    text = """<think>
internal reasoning
</think>

{"status":"ok","message":"hello"}"""

    data = extract_first_json_object(text)

    assert data == {
        "status": "ok",
        "message": "hello",
    }


def test_extract_first_json_object_ignores_prefix_text():
    text = """
Sure, here is the JSON:

{"status":"ok","message":"hello"}

Done.
"""

    data = extract_first_json_object(text)

    assert data["status"] == "ok"
    assert data["message"] == "hello"


def test_extract_first_json_object_raises_for_missing_json():
    with pytest.raises(LLMJsonExtractionError):
        extract_first_json_object("no json here")


def test_require_json_fields_accepts_present_fields():
    require_json_fields(
        {"status": "ok", "message": "hello"},
        ["status", "message"],
    )


def test_require_json_fields_rejects_missing_fields():
    with pytest.raises(LLMJsonExtractionError, match="Missing required JSON fields"):
        require_json_fields(
            {"status": "ok"},
            ["status", "message"],
        )
