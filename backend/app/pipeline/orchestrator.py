from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.pipeline.audio_ingestion import AudioExtractionResult, extract_audio
from app.pipeline.models import TracerBulletResult
from app.pipeline.separation_quality import analyze_separation_quality
from app.pipeline.resource_guard import gpu_sequential_guard
from app.pipeline.source_separation import SourceSeparationResult, separate_sources
from app.pipeline.tracer import run_tracer_bullet
from app.pipeline.audio_preprocess import preprocess_audio_for_transcription
from app.agent.transcription_agent import build_empty_agent_trace, run_bounded_transcription_agent


@dataclass
class AudioToAnalysisPipelineResult:
    job_id: str
    source: str
    status: str
    extract: dict[str, Any]
    separation: dict[str, Any]
    separation_quality: dict[str, Any]
    preprocessing: dict[str, Any]
    transcription: dict[str, Any]
    analysis: dict[str, Any]
    final_audio_path: str | None
    midi_path: str | None
    detected_key: str | None
    hvs_score: float | None
    error: str | None = None
    agent: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return asdict(self)



def _empty_transcription() -> dict[str, Any]:
    return {}


def _load_transcription_metadata(
    tracer_result: TracerBulletResult,
    artifacts_dir: str | Path,
    job_id: str,
) -> dict[str, Any]:
    """
    Load transcription metadata produced by transcribe_audio() inside tracer.

    The tracer now routes through the Day 7 transcription layer, which writes
    notes.json next to output.mid. We expose that metadata in the orchestrator
    result without running transcription a second time.
    """
    job_dir = Path(artifacts_dir) / job_id
    notes_path = job_dir / "notes.json"

    notes: list[dict[str, Any]] = []

    if notes_path.exists():
        notes = json.loads(notes_path.read_text(encoding="utf-8"))

    return {
        "status": "completed" if tracer_result.status == "completed" else "error",
        "input_audio": tracer_result.input_audio,
        "midi_path": tracer_result.midi_path,
        "transcription_method": tracer_result.transcription_method,
        "note_count": len(notes),
        "notes": notes,
        "notes_path": str(notes_path) if notes_path.exists() else None,
        "transcription_error": tracer_result.transcription_error,
        "error": tracer_result.error,
    }


def _empty_quality() -> dict[str, Any]:
    return {}

def _empty_preprocessing() -> dict[str, Any]:
    return {
        "status": "skipped",
        "enabled": False,
        "filters": [],
        "error": None,
    }

def _analyze_separation_quality_safely(
    extract_result: AudioExtractionResult,
    separation_result: SourceSeparationResult,
) -> dict[str, Any]:
    try:
        quality = analyze_separation_quality(
            input_wav=extract_result.wav_path,
            stems=separation_result.stems,
            selected_stem=separation_result.selected_stem,
        )

        return {
            "status": "completed",
            **quality.to_dict(),
        }

    except Exception as exc:
        return {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "decision": "use_selected_stem",
            "recommended_audio_path": separation_result.selected_stem_path,
            "reason": "Separation quality analysis failed, so the pipeline falls back to the selected stem.",
        }


def _choose_transcription_audio_path(
    separation_result: SourceSeparationResult,
    separation_quality_data: dict[str, Any],
) -> str:
    """
    Choose which audio file should be transcribed.

    If separation quality says the input is likely solo piano, use the original
    normalized WAV. Otherwise, use the selected Demucs stem.
    """
    decision = separation_quality_data.get("decision")
    recommended_audio_path = separation_quality_data.get("recommended_audio_path")

    if decision == "prefer_original_wav" and recommended_audio_path:
        return str(recommended_audio_path)

    if separation_result.selected_stem_path is None:
        raise ValueError("Source separation completed but selected_stem_path is missing.")

    return separation_result.selected_stem_path


def run_audio_to_analysis_pipeline(
    source: str | Path,
    job_id: str | None = None,
    processed_dir: str | Path = "data/processed",
    stems_dir: str | Path = "data/stems",
    artifacts_dir: str | Path = "artifacts/tracer",
    use_basic_pitch: bool = True,
    selected_stem: str = "other",
    skip_separation: bool = False,
    preprocess_audio: bool = True,
    trim_silence: bool = True,
    normalize_audio: bool = True,
    highpass_filter: bool = True,
) -> AudioToAnalysisPipelineResult:
    """
    Day 6 orchestrator:

    source audio
    -> T1 extract_audio
    -> optional T2 separate_sources
    -> optional separation quality analysis
    -> adaptive transcription audio selection
    -> T3 tracer analysis
    -> final JSON-compatible result
    """
    job_id = job_id or uuid.uuid4().hex[:12]
    source_str = str(source)

    empty_extract: dict[str, Any] = {}
    empty_separation: dict[str, Any] = {}
    empty_transcription: dict[str, Any] = {}
    empty_analysis: dict[str, Any] = {}
    empty_preprocessing: dict[str, Any] = _empty_preprocessing()

    try:
        extract_result: AudioExtractionResult = extract_audio(
            source=source,
            output_dir=processed_dir,
            job_id=job_id,
        )

        extract_data = extract_result.to_dict()

        if extract_result.status != "completed":
            return AudioToAnalysisPipelineResult(
                job_id=job_id,
                source=source_str,
                status="error",
                extract=extract_data,
                separation=empty_separation,
                separation_quality=_empty_quality(),
                preprocessing=empty_preprocessing,
                transcription=empty_transcription,
                analysis=empty_analysis,
                final_audio_path=None,
                midi_path=None,
                detected_key=None,
                hvs_score=None,
                error=extract_result.error,
            )

        if skip_separation:
            transcription_audio_path = str(extract_result.wav_path)

            separation_data = {
                "job_id": job_id,
                "input_wav": str(extract_result.wav_path),
                "output_dir": str(stems_dir),
                "model_name": None,
                "stems": {},
                "selected_stem": "original",
                "selected_stem_path": str(extract_result.wav_path),
                "status": "skipped",
                "error": None,
            }

            separation_quality_data = {
                "status": "skipped",
                "input_wav": str(extract_result.wav_path),
                "selected_stem": "original",
                "selected_stem_path": str(extract_result.wav_path),
                "decision": "prefer_original_wav",
                "recommended_audio_path": str(extract_result.wav_path),
                "likely_solo_piano": True,
                "reason": "Source separation skipped for piano-focused transcription.",
            }
        else:
            separation_result: SourceSeparationResult = separate_sources(
                wav_path=extract_result.wav_path,
                output_dir=stems_dir,
                job_id=job_id,
                selected_stem=selected_stem,
            )

            separation_data = separation_result.to_dict()

            if separation_result.status != "completed":
                return AudioToAnalysisPipelineResult(
                    job_id=job_id,
                    source=source_str,
                    status="error",
                    extract=extract_data,
                    separation=separation_data,
                    separation_quality=_empty_quality(),
                    preprocessing=empty_preprocessing,
                    transcription=empty_transcription,
                    analysis=empty_analysis,
                    final_audio_path=None,
                    midi_path=None,
                    detected_key=None,
                    hvs_score=None,
                    error=separation_result.error,
                )

            separation_quality_data = _analyze_separation_quality_safely(
                extract_result=extract_result,
                separation_result=separation_result,
            )

            transcription_audio_path = _choose_transcription_audio_path(
                separation_result=separation_result,
                separation_quality_data=separation_quality_data,
            )

        preprocessing_data = _empty_preprocessing()

        if preprocess_audio:
            preprocessed_audio_path = Path(processed_dir) / job_id / "preprocessed.wav"

            preprocess_result = preprocess_audio_for_transcription(
                transcription_audio_path,
                preprocessed_audio_path,
                trim_silence=trim_silence,
                normalize_audio=normalize_audio,
                highpass_filter=highpass_filter,
            )

            preprocessing_data = {
                "status": preprocess_result.status,
                "input_path": preprocess_result.input_path,
                "output_path": preprocess_result.output_path,
                "enabled": preprocess_result.enabled,
                "filters": preprocess_result.filters,
                "error": preprocess_result.error,
            }

            if preprocess_result.status == "completed":
                transcription_audio_path = str(preprocessed_audio_path)    

        tracer_result: TracerBulletResult = run_tracer_bullet(
            audio_path=transcription_audio_path,
            artifacts_dir=artifacts_dir,
            job_id=job_id,
            use_basic_pitch=use_basic_pitch,
        )

        transcription_data = _load_transcription_metadata(
            tracer_result=tracer_result,
            artifacts_dir=artifacts_dir,
            job_id=job_id,
        )

        analysis_data = tracer_result.to_dict()

        try:
            agent_data = run_bounded_transcription_agent(
                job_id=job_id,
                artifacts_dir=artifacts_dir,
                transcription=transcription_data,
                analysis=analysis_data,
                separation_quality=separation_quality_data,
            )
        except Exception as agent_error:
            agent_data = build_empty_agent_trace(
                job_id=job_id,
                reason=(
                    "Bounded transcription agent failed safely; "
                    "pipeline kept the raw transcription artifact."
                ),
            )
            agent_data["status"] = "failed_safe"
            agent_data["error"] = f"{type(agent_error).__name__}: {agent_error}"

        if tracer_result.status != "completed":
            return AudioToAnalysisPipelineResult(
                job_id=job_id,
                source=source_str,
                status="error",
                extract=extract_data,
                separation=separation_data,
                separation_quality=separation_quality_data,
                preprocessing=preprocessing_data,
                transcription=transcription_data,
                analysis=analysis_data,
                final_audio_path=transcription_audio_path,
                midi_path=tracer_result.midi_path,
                detected_key=tracer_result.detected_key,
                hvs_score=tracer_result.hvs_score,
                error=tracer_result.error,
                    agent=agent_data,
            )

        return AudioToAnalysisPipelineResult(
            job_id=job_id,
            source=source_str,
            status="completed",
            extract=extract_data,
            separation=separation_data,
            separation_quality=separation_quality_data,
            preprocessing=preprocessing_data,
            transcription=transcription_data,
            analysis=analysis_data,
            final_audio_path=transcription_audio_path,
            midi_path=tracer_result.midi_path,
            detected_key=tracer_result.detected_key,
            hvs_score=tracer_result.hvs_score,
            error=None,
                agent=agent_data,
        )

    except Exception as exc:
        return AudioToAnalysisPipelineResult(
            job_id=job_id,
            source=source_str,
            status="error",
            extract=empty_extract,
            separation=empty_separation,
            separation_quality=_empty_quality(),
            preprocessing=empty_preprocessing,
            transcription=_empty_transcription(),
            analysis=empty_analysis,
            final_audio_path=None,
            midi_path=None,
            detected_key=None,
            hvs_score=None,
            error=f"{type(exc).__name__}: {exc}",
        )