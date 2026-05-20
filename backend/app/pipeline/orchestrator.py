from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.pipeline.audio_ingestion import AudioExtractionResult, extract_audio
from app.pipeline.source_separation import SourceSeparationResult, separate_sources
from app.pipeline.models import TracerBulletResult
from app.pipeline.tracer import run_tracer_bullet


@dataclass
class AudioToAnalysisPipelineResult:
    job_id: str
    source: str
    status: str
    extract: dict[str, Any]
    separation: dict[str, Any]
    analysis: dict[str, Any]
    final_audio_path: str | None
    midi_path: str | None
    detected_key: str | None
    hvs_score: float | None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


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
    Day 5 orchestrator:

    source audio
    -> T1 extract_audio
    -> T2 separate_sources
    -> T3 tracer analysis on selected stem
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
                analysis=empty_analysis,
                final_audio_path=None,
                midi_path=None,
                detected_key=None,
                hvs_score=None,
                error=separation_result.error,
            )

        if separation_result.selected_stem_path is None:
            return AudioToAnalysisPipelineResult(
                job_id=job_id,
                source=source_str,
                status="error",
                extract=extract_data,
                separation=separation_data,
                analysis=empty_analysis,
                final_audio_path=None,
                midi_path=None,
                detected_key=None,
                hvs_score=None,
                error="Source separation completed but selected_stem_path is missing.",
            )

        tracer_result: TracerBulletResult = run_tracer_bullet(
            audio_path=separation_result.selected_stem_path,
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
                analysis=analysis_data,
                final_audio_path=separation_result.selected_stem_path,
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
            analysis=analysis_data,
            final_audio_path=separation_result.selected_stem_path,
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
            analysis=empty_analysis,
            final_audio_path=None,
            midi_path=None,
            detected_key=None,
            hvs_score=None,
            error=f"{type(exc).__name__}: {exc}",
        )
