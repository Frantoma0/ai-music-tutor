from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.pipeline.audio_ingestion import AudioExtractionResult, extract_audio
from app.pipeline.models import TracerBulletResult
from app.pipeline.separation_quality import analyze_separation_quality
from app.pipeline.source_separation import SourceSeparationResult, separate_sources
from app.pipeline.tracer import run_tracer_bullet


@dataclass
class AudioToAnalysisPipelineResult:
    job_id: str
    source: str
    status: str
    extract: dict[str, Any]
    separation: dict[str, Any]
    separation_quality: dict[str, Any]
    analysis: dict[str, Any]
    final_audio_path: str | None
    midi_path: str | None
    detected_key: str | None
    hvs_score: float | None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _empty_quality() -> dict[str, Any]:
    return {}


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
) -> AudioToAnalysisPipelineResult:
    """
    Day 6 orchestrator:

    source audio
    -> T1 extract_audio
    -> T2 separate_sources
    -> separation quality analysis
    -> adaptive transcription audio selection
    -> T3 tracer analysis
    -> final JSON-compatible result
    """
    job_id = job_id or uuid.uuid4().hex[:12]
    source_str = str(source)

    empty_extract: dict[str, Any] = {}
    empty_separation: dict[str, Any] = {}
    empty_analysis: dict[str, Any] = {}

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
                analysis=empty_analysis,
                final_audio_path=None,
                midi_path=None,
                detected_key=None,
                hvs_score=None,
                error=extract_result.error,
            )

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

        tracer_result: TracerBulletResult = run_tracer_bullet(
            audio_path=transcription_audio_path,
            artifacts_dir=artifacts_dir,
            job_id=job_id,
            use_basic_pitch=use_basic_pitch,
        )

        analysis_data = tracer_result.to_dict()

        if tracer_result.status != "completed":
            return AudioToAnalysisPipelineResult(
                job_id=job_id,
                source=source_str,
                status="error",
                extract=extract_data,
                separation=separation_data,
                separation_quality=separation_quality_data,
                analysis=analysis_data,
                final_audio_path=transcription_audio_path,
                midi_path=tracer_result.midi_path,
                detected_key=tracer_result.detected_key,
                hvs_score=tracer_result.hvs_score,
                error=tracer_result.error,
            )

        return AudioToAnalysisPipelineResult(
            job_id=job_id,
            source=source_str,
            status="completed",
            extract=extract_data,
            separation=separation_data,
            separation_quality=separation_quality_data,
            analysis=analysis_data,
            final_audio_path=transcription_audio_path,
            midi_path=tracer_result.midi_path,
            detected_key=tracer_result.detected_key,
            hvs_score=tracer_result.hvs_score,
            error=None,
        )

    except Exception as exc:
        return AudioToAnalysisPipelineResult(
            job_id=job_id,
            source=source_str,
            status="error",
            extract=empty_extract,
            separation=empty_separation,
            separation_quality=_empty_quality(),
            analysis=empty_analysis,
            final_audio_path=None,
            midi_path=None,
            detected_key=None,
            hvs_score=None,
            error=f"{type(exc).__name__}: {exc}",
        )
