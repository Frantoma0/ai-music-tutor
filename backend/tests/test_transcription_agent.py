from pathlib import Path

from app.agent.transcription_agent import (
    run_bounded_transcription_agent,
    select_agent_candidates,
    validate_llm_corrections,
)


def test_select_agent_candidates_prefers_low_confidence_notes():
    notes = [
        {
            "id": "n0",
            "pitch": 60,
            "pitch_name": "C4",
            "start": 0.0,
            "end": 0.5,
            "confidence": 0.91,
        },
        {
            "id": "n1",
            "pitch": 61,
            "pitch_name": "C#4",
            "start": 0.6,
            "end": 0.9,
            "confidence": 0.41,
        },
    ]

    candidates = select_agent_candidates(notes)

    assert len(candidates) == 1
    assert candidates[0]["note_id"] == "n1"
    assert candidates[0]["pitch"] == 61


def test_validate_llm_corrections_accepts_safe_pitch_shift():
    candidates = [
        {
            "candidate_id": "cand_0000",
            "note_id": "n0",
            "pitch": 60,
            "start": 0.0,
            "end": 0.5,
        }
    ]

    result = validate_llm_corrections(
        {
            "corrections": [
                {
                    "candidate_id": "cand_0000",
                    "action": "shift_pitch",
                    "proposed_pitch": 62,
                    "reason": "Likely D4 in context.",
                }
            ]
        },
        candidates,
    )

    assert result["status"] == "validated"
    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 0
    assert result["shift_pitch_count"] == 1
    assert result["accepted"][0]["pitch_shift"] == 2


def test_validate_llm_corrections_rejects_unsafe_pitch_shift():
    candidates = [
        {
            "candidate_id": "cand_0000",
            "note_id": "n0",
            "pitch": 60,
            "start": 0.0,
            "end": 0.5,
        }
    ]

    result = validate_llm_corrections(
        {
            "corrections": [
                {
                    "candidate_id": "cand_0000",
                    "action": "shift_pitch",
                    "proposed_pitch": 67,
                    "reason": "Too large.",
                }
            ]
        },
        candidates,
    )

    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 1
    assert "exceeds" in result["rejected"][0]["reason"]


def test_run_bounded_transcription_agent_writes_trace_without_llm(tmp_path):
    result = run_bounded_transcription_agent(
        job_id="pytest-agent",
        artifacts_dir=tmp_path,
        transcription={
            "status": "completed",
            "midi_path": "artifacts/tracer/pytest-agent/output.mid",
            "notes": [
                {
                    "id": "n0",
                    "pitch": 60,
                    "pitch_name": "C4",
                    "start": 0.0,
                    "end": 0.5,
                    "confidence": 0.42,
                }
            ],
        },
        analysis={
            "detected_key": "C major",
            "hvs_score": 0.8,
            "midi_path": "artifacts/tracer/pytest-agent/output.mid",
        },
        separation_quality={
            "decision": "prefer_original_wav",
            "likely_solo_piano": True,
        },
        enable_llm_correction=False,
    )

    trace_path = Path(result["trace_path"])

    assert result["status"] == "completed"
    assert result["decisions"]["correction_needed"] is True
    assert result["decisions"]["llm_correction_enabled"] is False
    assert trace_path.exists()
