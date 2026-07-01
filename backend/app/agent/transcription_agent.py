from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_AGENT_MODEL = "qwen3:8b"
DEFAULT_OLLAMA_BASE_URL = "http://ollama:11434"

MAX_AGENT_CANDIDATES = 24
MAX_SAFE_PITCH_SHIFT = 2
PIANO_MIN_MIDI = 21
PIANO_MAX_MIDI = 108


def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)

        if number != number:
            return fallback

        return number
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _read_json(path: str | Path | None, default: Any) -> Any:
    if not path:
        return default

    target = Path(path)

    if not target.exists():
        return default

    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: str | Path, data: dict[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(target)


def _strip_qwen_think_blocks(value: str) -> str:
    return re.sub(r"<think>.*?</think>", "", value or "", flags=re.DOTALL).strip()


def _extract_json_object(value: str) -> dict[str, Any]:
    cleaned = _strip_qwen_think_blocks(value)

    try:
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:
        parsed = json.loads(cleaned[start : end + 1])

        if isinstance(parsed, dict):
            return parsed

    raise ValueError("LLM response does not contain a JSON object.")


def _candidate_from_note(note: dict[str, Any], index: int) -> dict[str, Any]:
    start = _safe_float(note.get("start"))
    end = _safe_float(note.get("end"), start)
    pitch = _safe_int(note.get("pitch"))
    confidence = note.get("confidence")

    return {
        "candidate_id": f"cand_{index:04d}",
        "note_id": str(note.get("id") or f"n{index}"),
        "pitch": pitch,
        "pitch_name": note.get("pitch_name"),
        "start": start,
        "end": end,
        "duration": max(0.0, end - start),
        "confidence": confidence,
        "in_correction_mask": bool(note.get("inCorrectionMask") or note.get("in_correction_mask")),
    }


def select_agent_candidates(
    notes: list[dict[str, Any]],
    *,
    max_candidates: int = MAX_AGENT_CANDIDATES,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for index, note in enumerate(notes):
      confidence = note.get("confidence")
      confidence_value = None if confidence is None else _safe_float(confidence, 1.0)
      is_low_confidence = confidence_value is None or confidence_value <= 0.62
      in_mask = bool(note.get("inCorrectionMask") or note.get("in_correction_mask"))

      if is_low_confidence or in_mask:
          candidates.append(_candidate_from_note(note, index))

      if len(candidates) >= max_candidates:
          break

    return candidates


def build_agent_prompt(candidates: list[dict[str, Any]], analysis: dict[str, Any]) -> str:
    key = analysis.get("detected_key") or "unknown"

    return f"""
You are a bounded piano transcription correction agent.

Task:
Review only the provided candidate notes and propose pitch-only corrections when clearly justified.

Hard constraints:
- Return JSON only.
- Do not add notes.
- Do not delete notes.
- Do not change start time.
- Do not change end time.
- Do not change duration.
- Allowed actions: "keep" or "shift_pitch".
- For "shift_pitch", proposed_pitch must be an integer.
- proposed_pitch may differ from original pitch by at most {MAX_SAFE_PITCH_SHIFT} semitones.
- proposed_pitch must stay inside piano range {PIANO_MIN_MIDI}-{PIANO_MAX_MIDI}.
- Every candidate_id must appear exactly once.

Musical context:
Detected key: {key}

Return format:
{{
  "corrections": [
    {{
      "candidate_id": "cand_0000",
      "action": "keep",
      "proposed_pitch": null,
      "reason": "short explanation"
    }}
  ]
}}

Candidates:
{json.dumps(candidates, ensure_ascii=False)}
""".strip()


def call_ollama_json(
    prompt: str,
    *,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    model: str = DEFAULT_AGENT_MODEL,
    timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
    }

    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_data = json.loads(response.read().decode("utf-8"))

    raw_response = response_data.get("response") or ""
    return _extract_json_object(raw_response)


def validate_llm_corrections(
    llm_data: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_by_id = {candidate["candidate_id"]: candidate for candidate in candidates}
    raw_items = llm_data.get("corrections")

    if not isinstance(raw_items, list):
        raise ValueError("LLM output must contain corrections list.")

    seen_ids: set[str] = set()
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for item in raw_items:
        if not isinstance(item, dict):
            rejected.append({"reason": "Correction item is not an object.", "item": item})
            continue

        candidate_id = str(item.get("candidate_id") or "")

        if candidate_id not in candidate_by_id:
            rejected.append({
                "candidate_id": candidate_id,
                "reason": "Unknown candidate_id.",
                "item": item,
            })
            continue

        if candidate_id in seen_ids:
            rejected.append({
                "candidate_id": candidate_id,
                "reason": "Duplicate candidate_id.",
                "item": item,
            })
            continue

        seen_ids.add(candidate_id)

        candidate = candidate_by_id[candidate_id]
        action = str(item.get("action") or "").strip()
        reason = str(item.get("reason") or "").strip()[:240]

        if action == "keep":
            accepted.append({
                "candidate_id": candidate_id,
                "note_id": candidate["note_id"],
                "action": "keep",
                "original_pitch": candidate["pitch"],
                "proposed_pitch": None,
                "start": candidate["start"],
                "end": candidate["end"],
                "reason": reason or "LLM kept the original pitch.",
            })
            continue

        if action != "shift_pitch":
            rejected.append({
                "candidate_id": candidate_id,
                "reason": f"Unsupported action: {action}",
                "item": item,
            })
            continue

        proposed_pitch = item.get("proposed_pitch")

        if proposed_pitch is None:
            rejected.append({
                "candidate_id": candidate_id,
                "reason": "shift_pitch requires proposed_pitch.",
                "item": item,
            })
            continue

        proposed_pitch_int = _safe_int(proposed_pitch, -9999)
        original_pitch = _safe_int(candidate["pitch"], -9999)
        shift = proposed_pitch_int - original_pitch

        if proposed_pitch_int < PIANO_MIN_MIDI or proposed_pitch_int > PIANO_MAX_MIDI:
            rejected.append({
                "candidate_id": candidate_id,
                "reason": "proposed_pitch outside piano range.",
                "item": item,
            })
            continue

        if abs(shift) > MAX_SAFE_PITCH_SHIFT:
            rejected.append({
                "candidate_id": candidate_id,
                "reason": "Pitch shift exceeds ±2 semitones.",
                "item": item,
            })
            continue

        accepted.append({
            "candidate_id": candidate_id,
            "note_id": candidate["note_id"],
            "action": "shift_pitch",
            "original_pitch": original_pitch,
            "proposed_pitch": proposed_pitch_int,
            "pitch_shift": shift,
            "start": candidate["start"],
            "end": candidate["end"],
            "reason": reason or "LLM proposed a bounded pitch correction.",
        })

    missing_ids = sorted(set(candidate_by_id) - seen_ids)

    for candidate_id in missing_ids:
        candidate = candidate_by_id[candidate_id]
        accepted.append({
            "candidate_id": candidate_id,
            "note_id": candidate["note_id"],
            "action": "keep",
            "original_pitch": candidate["pitch"],
            "proposed_pitch": None,
            "start": candidate["start"],
            "end": candidate["end"],
            "reason": "Candidate was missing from LLM output, so deterministic fallback kept it unchanged.",
        })

    return {
        "status": "validated",
        "accepted": accepted,
        "rejected": rejected,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "shift_pitch_count": sum(1 for item in accepted if item["action"] == "shift_pitch"),
        "keep_count": sum(1 for item in accepted if item["action"] == "keep"),
        "coverage_count": len(accepted),
        "expected_coverage_count": len(candidates),
    }


def build_empty_agent_trace(job_id: str, *, reason: str = "Agent was not reached.") -> dict[str, Any]:
    return {
        "status": "not_started",
        "agent_type": "bounded_transcription_agent",
        "job_id": job_id,
        "reason": reason,
        "trace_path": None,
    }


def run_bounded_transcription_agent(
    *,
    job_id: str,
    artifacts_dir: str | Path,
    transcription: dict[str, Any],
    analysis: dict[str, Any],
    separation_quality: dict[str, Any],
    enable_llm_correction: bool | None = None,
    ollama_base_url: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    started_at_ms = _now_ms()
    job_dir = Path(artifacts_dir) / job_id
    trace_path = job_dir / "agent_trace.json"

    notes = transcription.get("notes")

    if not isinstance(notes, list):
        notes = _read_json(transcription.get("notes_path"), default=[])

    if not isinstance(notes, list):
        notes = []

    candidates = select_agent_candidates(notes)
    correction_needed = len(candidates) > 0

    if enable_llm_correction is None:
        enable_llm_correction = os.getenv("AMT_AGENT_ENABLE_LLM_CORRECTION", "0").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
    selected_model = model or os.getenv("OLLAMA_MODEL", DEFAULT_AGENT_MODEL)

    trace: dict[str, Any] = {
        "status": "completed",
        "agent_type": "bounded_transcription_agent",
        "job_id": job_id,
        "model": selected_model,
        "constraints": {
            "max_pitch_shift_semitones": MAX_SAFE_PITCH_SHIFT,
            "allow_add_notes": False,
            "allow_delete_notes": False,
            "allow_timing_changes": False,
            "allow_duration_changes": False,
            "requires_candidate_coverage": True,
            "deterministic_validation": True,
        },
        "decisions": {
            "source_separation_decision": separation_quality.get("decision") or "unknown",
            "likely_solo_piano": separation_quality.get("likely_solo_piano"),
            "correction_needed": correction_needed,
            "llm_correction_enabled": bool(enable_llm_correction),
            "final_midi_choice": "raw_transcription",
            "final_midi_reason": "The current implementation stores bounded correction proposals as an explainable agent trace and keeps the raw MIDI as the safe playback artifact.",
        },
        "input_summary": {
            "note_count": len(notes),
            "candidate_count": len(candidates),
            "detected_key": analysis.get("detected_key"),
            "hvs_score": analysis.get("hvs_score"),
            "midi_path": transcription.get("midi_path") or analysis.get("midi_path"),
        },
        "tool_plan": [
            {
                "tool": "separate_sources",
                "status": "already_executed_or_skipped",
                "decision": separation_quality.get("decision") or "unknown",
            },
            {
                "tool": "transcribe_audio",
                "status": transcription.get("status") or "unknown",
                "method": transcription.get("transcription_method"),
            },
            {
                "tool": "bounded_llm_pitch_review",
                "status": "pending" if enable_llm_correction and correction_needed else "skipped",
            },
            {
                "tool": "deterministic_correction_validator",
                "status": "pending" if enable_llm_correction and correction_needed else "skipped",
            },
        ],
        "candidates": candidates,
        "llm": {
            "status": "skipped",
            "base_url": base_url,
            "error": None,
            "raw_validated": None,
        },
        "correction_summary": {
            "status": "not_needed" if not correction_needed else "not_attempted",
            "accepted_count": 0,
            "rejected_count": 0,
            "shift_pitch_count": 0,
            "keep_count": 0,
        },
        "started_at_ms": started_at_ms,
        "finished_at_ms": None,
        "duration_ms": None,
        "trace_path": str(trace_path),
    }

    if enable_llm_correction and correction_needed:
        prompt = build_agent_prompt(candidates, analysis)

        try:
            llm_data = call_ollama_json(
                prompt,
                base_url=base_url,
                model=selected_model,
            )
            validated = validate_llm_corrections(llm_data, candidates)

            trace["llm"] = {
                "status": "completed",
                "base_url": base_url,
                "error": None,
                "raw_validated": validated,
            }
            trace["correction_summary"] = {
                "status": "validated",
                "accepted_count": validated["accepted_count"],
                "rejected_count": validated["rejected_count"],
                "shift_pitch_count": validated["shift_pitch_count"],
                "keep_count": validated["keep_count"],
            }
            trace["tool_plan"][2]["status"] = "completed"
            trace["tool_plan"][3]["status"] = "completed"
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
            trace["llm"] = {
                "status": "fallback_to_raw",
                "base_url": base_url,
                "error": f"{type(exc).__name__}: {exc}",
                "raw_validated": None,
            }
            trace["correction_summary"] = {
                "status": "fallback_to_raw",
                "accepted_count": 0,
                "rejected_count": 0,
                "shift_pitch_count": 0,
                "keep_count": 0,
            }
            trace["tool_plan"][2]["status"] = "failed_safe"
            trace["tool_plan"][3]["status"] = "skipped"
            trace["decisions"]["final_midi_reason"] = (
                "LLM correction failed or was unavailable, so the agent kept the raw MIDI artifact."
            )

    finished_at_ms = _now_ms()
    trace["finished_at_ms"] = finished_at_ms
    trace["duration_ms"] = finished_at_ms - started_at_ms

    _write_json(trace_path, trace)

    return trace
