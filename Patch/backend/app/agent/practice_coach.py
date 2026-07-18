"""
Practice Coach agent.

Turns REAL practice data (misses and wrong notes recorded by the player)
into an actionable plan: which sections to loop, at what tempo, with
which hand — plus short coaching tips.

Same bounded-agent pattern as the transcription agent:

    deterministic core  – sections, tempos and hands are computed from
                          the weak-spot data with plain arithmetic; the
                          plan is complete and useful without any model.
    LLM enrichment      – the local model may only REWRITE the tip texts
                          (strict JSON, validated, length-capped). It can
                          never change sections, tempos or hands.
    trace               – every run writes coach_trace.json next to the
                          lesson artifacts and a row in practice_plans.
    failed_safe         – any model problem falls back to canned tips.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agent.transcription_agent import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_OLLAMA_BASE_URL,
    call_ollama_json,
)
from app.db.database import DEFAULT_DB_PATH
from app.db.progress import list_sessions_for_job

MAX_SECTIONS = 3
SECTION_MERGE_GAP_SECONDS = 2.0
SECTION_PADDING_SECONDS = 1.2
MIN_SECTION_LENGTH_SECONDS = 3.0
MAX_TIP_LENGTH = 220


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round_tempo(value: float) -> float:
    clamped = max(0.5, min(1.0, value))
    return round(clamped * 20) / 20  # steps of 0.05


CANNED = {
    "en": {
        "overall_good": "Solid run! Push the tempo up a step and keep the flow.",
        "overall_mixed": "Good progress — the plan below targets exactly where notes slip.",
        "overall_hard": "Slow everything down first; accuracy before speed, always.",
        "section_wrong": "Watch WHICH keys you press here — name the notes out loud before playing.",
        "section_miss": "Notes are slipping past — slow down and use Wait mode until it feels easy.",
        "section_mixed": "Loop this slowly with one hand until every note lands, then add the other.",
        "hand_left": "left hand",
        "hand_right": "right hand",
        "hand_both": "both hands",
    },
    "bg": {
        "overall_good": "Стабилно изпълнение! Вдигни темпото с една стъпка и запази потока.",
        "overall_mixed": "Добър напредък — планът долу цели точно местата, където нотите се изплъзват.",
        "overall_hard": "Първо забави всичко; точност преди скорост, винаги.",
        "section_wrong": "Внимавай КОИ клавиши натискаш тук — кажи имената на нотите на глас, преди да свириш.",
        "section_miss": "Нотите ти убягват — забави и ползвай режим Изчакване, докато стане лесно.",
        "section_mixed": "Върти този пасаж бавно с една ръка, докато всяка нота уцелва, после добави другата.",
        "hand_left": "лява ръка",
        "hand_right": "дясна ръка",
        "hand_both": "двете ръце",
    },
}


def _normalize_weak_spots(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest session with weak spots wins; older ones only add context."""
    spots: list[dict[str, Any]] = []

    for session in sessions:  # sessions come newest-first
        raw = session.get("weak_spots_json")
        if not raw:
            continue

        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            continue

        if isinstance(parsed, list) and parsed:
            for item in parsed:
                if not isinstance(item, dict):
                    continue

                start = item.get("start", item.get("t"))
                if start is None:
                    continue

                try:
                    start = float(start)
                except (TypeError, ValueError):
                    continue

                spots.append(
                    {
                        "start": start,
                        "end": float(item.get("end", start)),
                        "hand": item.get("hand")
                        if item.get("hand") in ("left", "right")
                        else None,
                        "kind": "wrong" if item.get("kind") == "wrong" else "miss",
                    }
                )

            break  # only the most recent session that has spots

    spots.sort(key=lambda spot: spot["start"])
    return spots[:300]


def _cluster_sections(
    spots: list[dict[str, Any]],
    duration_seconds: float,
) -> list[dict[str, Any]]:
    clusters: list[list[dict[str, Any]]] = []

    for spot in spots:
        if clusters and spot["start"] - clusters[-1][-1]["end"] <= SECTION_MERGE_GAP_SECONDS:
            clusters[-1].append(spot)
        else:
            clusters.append([spot])

    # Most error-dense clusters first, keep the top few, then back in time order.
    clusters.sort(key=len, reverse=True)
    clusters = clusters[:MAX_SECTIONS]
    clusters.sort(key=lambda cluster: cluster[0]["start"])

    sections = []

    for cluster in clusters:
        start = max(0.0, cluster[0]["start"] - SECTION_PADDING_SECONDS)
        end = min(
            duration_seconds if duration_seconds > 0 else cluster[-1]["end"] + 5,
            cluster[-1]["end"] + SECTION_PADDING_SECONDS,
        )

        if end - start < MIN_SECTION_LENGTH_SECONDS:
            end = start + MIN_SECTION_LENGTH_SECONDS

        left = sum(1 for spot in cluster if spot["hand"] == "left")
        right = sum(1 for spot in cluster if spot["hand"] == "right")
        wrong = sum(1 for spot in cluster if spot["kind"] == "wrong")
        miss = len(cluster) - wrong

        if left > right * 1.5:
            hand = "left"
        elif right > left * 1.5:
            hand = "right"
        else:
            hand = "both"

        errors_per_second = len(cluster) / max(end - start, 1.0)
        tempo = _round_tempo(1.05 - errors_per_second * 0.18)

        sections.append(
            {
                "start": round(start, 2),
                "end": round(end, 2),
                "hand": hand,
                "errors": len(cluster),
                "wrong": wrong,
                "miss": miss,
                "tempo": tempo,
            }
        )

    return sections


def _section_tip(section: dict[str, Any], language: str) -> str:
    copy = CANNED.get(language, CANNED["en"])

    if section["wrong"] > section["miss"] * 1.5:
        return copy["section_wrong"]
    if section["miss"] > section["wrong"] * 1.5:
        return copy["section_miss"]
    return copy["section_mixed"]


def build_deterministic_plan(
    sessions: list[dict[str, Any]],
    language: str = "en",
) -> dict[str, Any]:
    copy = CANNED.get(language, CANNED["en"])

    latest = sessions[0] if sessions else {}
    accuracy = latest.get("accuracy")
    duration = float(latest.get("duration_seconds") or 0)

    spots = _normalize_weak_spots(sessions)
    sections = _cluster_sections(spots, duration)

    for section in sections:
        section["tip"] = _section_tip(section, language)

    if accuracy is None:
        overall_tip = copy["overall_mixed"]
    elif accuracy >= 80 and not sections:
        overall_tip = copy["overall_good"]
    elif accuracy < 45:
        overall_tip = copy["overall_hard"]
    else:
        overall_tip = copy["overall_mixed"]

    if accuracy is not None and accuracy < 45:
        recommended_view = "beginner"
    elif accuracy is not None and accuracy < 75:
        recommended_view = "practice"
    else:
        recommended_view = None

    recommended_tempo = (
        min(section["tempo"] for section in sections) if sections else None
    )

    return {
        "generated_at": _now_iso(),
        "language": language,
        "based_on": {
            "attempts": len(sessions),
            "latest_accuracy": accuracy,
            "weak_spots": len(spots),
        },
        "recommended_view": recommended_view,
        "recommended_tempo": recommended_tempo,
        "overall_tip": overall_tip,
        "sections": sections,
    }


def _validate_llm_tips(
    llm_data: dict[str, Any],
    section_count: int,
) -> dict[str, Any]:
    overall = llm_data.get("overall_tip")
    tips = llm_data.get("section_tips")

    if not isinstance(overall, str) or not overall.strip():
        raise ValueError("overall_tip must be a non-empty string")

    if not isinstance(tips, list) or len(tips) != section_count:
        raise ValueError("section_tips must match the section count")

    for tip in tips:
        if not isinstance(tip, str) or not tip.strip():
            raise ValueError("Every section tip must be a non-empty string")

    return {
        "overall_tip": overall.strip()[:MAX_TIP_LENGTH],
        "section_tips": [tip.strip()[:MAX_TIP_LENGTH] for tip in tips],
    }


def _enrich_with_llm(
    plan: dict[str, Any],
    base_url: str,
    model: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The model may ONLY rewrite tip texts. Structure stays deterministic."""
    language_name = "Bulgarian" if plan["language"] == "bg" else "English"

    prompt = (
        "You are a piano practice coach. Rewrite the coaching tips below to be "
        f"specific and encouraging, in {language_name}, max 2 sentences each.\n"
        "Respond ONLY with JSON exactly like: "
        '{"overall_tip": "...", "section_tips": ["...", ...]} '
        f"with exactly {len(plan['sections'])} section_tips.\n"
        f"Data: {json.dumps({'latest_accuracy': plan['based_on']['latest_accuracy'], 'sections': [{'seconds': [s['start'], s['end']], 'hand': s['hand'], 'wrong_notes': s['wrong'], 'missed_notes': s['miss'], 'draft_tip': s['tip']} for s in plan['sections']], 'overall_draft': plan['overall_tip']}, ensure_ascii=False)}"
    )

    llm_meta: dict[str, Any] = {"used": False, "model": model, "status": "skipped"}

    try:
        llm_data = call_ollama_json(prompt, base_url=base_url, model=model, timeout_seconds=12.0)
        validated = _validate_llm_tips(llm_data, len(plan["sections"]))

        plan = dict(plan)
        plan["overall_tip"] = validated["overall_tip"]
        plan["sections"] = [
            {**section, "tip": tip}
            for section, tip in zip(plan["sections"], validated["section_tips"])
        ]

        llm_meta = {"used": True, "model": model, "status": "ok"}
    except Exception as exc:  # noqa: BLE001 – any model problem is non-fatal
        llm_meta = {
            "used": False,
            "model": model,
            "status": "failed_safe",
            "error": f"{type(exc).__name__}: {exc}",
        }

    return plan, llm_meta


async def _store_plan(
    job_id: str,
    plan: dict[str, Any],
    db_path: str | Path,
) -> str:
    plan_id = f"plan_{uuid.uuid4().hex[:12]}"

    def _write() -> None:
        with sqlite3.connect(str(db_path)) as connection:
            try:
                connection.execute(
                    "ALTER TABLE practice_plans ADD COLUMN job_id TEXT"
                )
            except sqlite3.OperationalError:
                pass  # column already exists

            connection.execute(
                """
                INSERT INTO practice_plans (id, job_id, plan_json, status, created_at, updated_at)
                VALUES (?, ?, ?, 'active', ?, ?)
                """,
                (plan_id, job_id, json.dumps(plan, ensure_ascii=False), _now_iso(), _now_iso()),
            )
            connection.commit()

    await asyncio.to_thread(_write)
    return plan_id


def _write_trace(job_id: str, trace: dict[str, Any]) -> str | None:
    try:
        trace_dir = Path("data/midi") / job_id
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / "coach_trace.json"
        trace_path.write_text(
            json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return str(trace_path)
    except OSError:
        return None


async def run_practice_coach(
    job_id: str,
    language: str = "en",
    use_llm: bool | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    sessions = await list_sessions_for_job(job_id, limit=10, db_path=db_path)

    if not sessions:
        return {
            "job_id": job_id,
            "status": "no_data",
            "plan": None,
        }

    plan = build_deterministic_plan(sessions, language=language)

    if use_llm is None:
        use_llm = os.getenv("DAITUNE_COACH_USE_LLM", "1") != "0"

    base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
    model = os.getenv("OLLAMA_MODEL", DEFAULT_AGENT_MODEL)

    if use_llm and plan["sections"]:
        plan, llm_meta = await asyncio.to_thread(
            _enrich_with_llm, plan, base_url, model
        )
    else:
        llm_meta = {"used": False, "model": model, "status": "skipped"}

    trace = {
        "job_id": job_id,
        "generated_at": plan["generated_at"],
        "input_summary": plan["based_on"],
        "constraints": {
            "llm_may_change": ["overall_tip", "sections[].tip"],
            "llm_may_not_change": ["sections", "tempos", "hands", "recommendations"],
            "max_sections": MAX_SECTIONS,
        },
        "llm": llm_meta,
        "final_plan": plan,
    }

    trace_path = _write_trace(job_id, trace)
    plan_id = await _store_plan(job_id, plan, db_path)

    return {
        "job_id": job_id,
        "status": "ok",
        "plan_id": plan_id,
        "trace_path": trace_path,
        "llm": llm_meta,
        "plan": plan,
    }


async def get_latest_plan(
    job_id: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    def _query() -> dict[str, Any] | None:
        with sqlite3.connect(str(db_path)) as connection:
            connection.row_factory = sqlite3.Row

            try:
                row = connection.execute(
                    """
                    SELECT * FROM practice_plans
                    WHERE job_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (job_id,),
                ).fetchone()
            except sqlite3.OperationalError:
                return None  # job_id column not there yet → no plans

            if not row:
                return None

            try:
                plan = json.loads(row["plan_json"])
            except (TypeError, ValueError):
                return None

            return {"plan_id": row["id"], "created_at": row["created_at"], "plan": plan}

    return await asyncio.to_thread(_query)
