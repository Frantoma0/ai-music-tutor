from __future__ import annotations

import json
import re
from typing import Any


class LLMJsonExtractionError(ValueError):
    pass


def strip_think_blocks(text: str) -> str:
    return re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()


def extract_first_json_object(text: str) -> dict[str, Any]:
    cleaned = strip_think_blocks(text)

    decoder = json.JSONDecoder()

    for index, char in enumerate(cleaned):
        if char != "{":
            continue

        try:
            obj, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(obj, dict):
            return obj

    raise LLMJsonExtractionError("No valid JSON object found in LLM response.")


def require_json_fields(data: dict[str, Any], required_fields: list[str]) -> None:
    missing = [field for field in required_fields if field not in data]

    if missing:
        raise LLMJsonExtractionError(
            "Missing required JSON fields: " + ", ".join(missing)
        )
