from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

from app.pipeline.llm_json import extract_first_json_object, require_json_fields


def run_qwen_json_smoke(
    *,
    base_url: str,
    model: str,
    output: str,
) -> dict:
    prompt = (
        'Return only valid JSON with these exact fields: '
        '{"status":"ok","message":"hello"}. '
        'Do not include markdown.'
    )

    response = httpx.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=90,
    )

    response.raise_for_status()

    ollama_data = response.json()
    raw_response = ollama_data.get("response") or ""

    parsed = extract_first_json_object(raw_response)
    require_json_fields(parsed, ["status", "message"])

    result = {
        "status": "completed",
        "base_url": base_url,
        "model": model,
        "raw_response": raw_response,
        "parsed": parsed,
        "error": None,
    }

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "status": "completed",
        "output": str(output_path),
        "parsed": parsed,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Qwen JSON extraction smoke test.")
    parser.add_argument("--base-url", default="http://host.docker.internal:11434")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    try:
        result = run_qwen_json_smoke(
            base_url=args.base_url,
            model=args.model,
            output=args.output,
        )
    except Exception as exc:
        result = {
            "status": "error",
            "output": args.output,
            "parsed": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
