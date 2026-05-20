from __future__ import annotations

from app.pipeline.audio_ingestion import AudioExtractionResult
from app.pipeline.models import TracerBulletResult
from app.pipeline.orchestrator import run_audio_to_analysis_pipeline
from app.pipeline.source_separation import SourceSeparationResult


def test_audio_to_analysis_pipeline_success(monkeypatch):
    def fake_extract_audio(source, output_dir="data/processed", job_id=None):
        return AudioExtractionResult(
            job_id=job_id or "fake-job",
            source=str(source),
            input_type="file",
            original_path="data/processed/fake-job/raw/source.wav",
            wav_path="data/processed/fake-job/input.wav",
            duration_seconds=1.0,
            sample_rate=44100,
            channels=1,
            status="completed",
            error=None,
        )

    def fake_separate_sources(
        wav_path,
        output_dir="data/stems",
        job_id=None,
        model_name="htdemucs",
        selected_stem="other",
    ):
        return SourceSeparationResult(
            job_id=job_id or "fake-job",
            input_wav=str(wav_path),
            output_dir="data/stems/fake-job",
            model_name=model_name,
            stems={
                "vocals": "data/stems/fake-job/vocals.wav",
                "drums": "data/stems/fake-job/drums.wav",
                "bass": "data/stems/fake-job/bass.wav",
                "other": "data/stems/fake-job/other.wav",
            },
            selected_stem=selected_stem,
            selected_stem_path="data/stems/fake-job/other.wav",
            status="completed",
            error=None,
        )

    def fake_run_tracer_bullet(
        audio_path,
        artifacts_dir="artifacts/tracer",
        job_id=None,
        use_basic_pitch=False,
    ):
        return TracerBulletResult(
            job_id=job_id or "fake-job",
            input_audio=str(audio_path),
            midi_path="artifacts/tracer/fake-job/output.mid",
            detected_key="C major",
            hvs_score=1.0,
            status="completed",
            transcription_method="basic_pitch",
            key_confidence=0.9,
            transcription_error=None,
            error=None,
        )

    monkeypatch.setattr("app.pipeline.orchestrator.extract_audio", fake_extract_audio)
    monkeypatch.setattr("app.pipeline.orchestrator.separate_sources", fake_separate_sources)
    monkeypatch.setattr("app.pipeline.orchestrator.run_tracer_bullet", fake_run_tracer_bullet)

    result = run_audio_to_analysis_pipeline(
        source="data/samples/source.wav",
        job_id="pytest-pipeline",
    )

    assert result.status == "completed"
    assert result.job_id == "pytest-pipeline"
    assert result.final_audio_path == "data/stems/fake-job/other.wav"
    assert result.midi_path == "artifacts/tracer/fake-job/output.mid"
    assert result.detected_key == "C major"
    assert result.hvs_score == 1.0
    assert result.error is None
    assert result.extract["status"] == "completed"
    assert result.separation["status"] == "completed"
    assert "status" in result.separation_quality
    assert result.analysis["status"] == "completed"


def test_audio_to_analysis_pipeline_stops_on_extract_error(monkeypatch):
    def fake_extract_audio(source, output_dir="data/processed", job_id=None):
        return AudioExtractionResult(
            job_id=job_id or "fake-job",
            source=str(source),
            input_type="file",
            original_path="",
            wav_path="data/processed/fake-job/input.wav",
            duration_seconds=None,
            sample_rate=None,
            channels=None,
            status="error",
            error="FileNotFoundError: missing input",
        )

    monkeypatch.setattr("app.pipeline.orchestrator.extract_audio", fake_extract_audio)

    result = run_audio_to_analysis_pipeline(
        source="missing.wav",
        job_id="pytest-extract-error",
    )

    assert result.status == "error"
    assert result.error == "FileNotFoundError: missing input"
    assert result.extract["status"] == "error"
    assert result.separation == {}
    assert result.separation_quality == {}
    assert result.analysis == {}
    assert result.midi_path is None


def test_audio_to_analysis_pipeline_stops_on_separation_error(monkeypatch):
    def fake_extract_audio(source, output_dir="data/processed", job_id=None):
        return AudioExtractionResult(
            job_id=job_id or "fake-job",
            source=str(source),
            input_type="file",
            original_path="data/processed/fake-job/raw/source.wav",
            wav_path="data/processed/fake-job/input.wav",
            duration_seconds=1.0,
            sample_rate=44100,
            channels=1,
            status="completed",
            error=None,
        )

    def fake_separate_sources(
        wav_path,
        output_dir="data/stems",
        job_id=None,
        model_name="htdemucs",
        selected_stem="other",
    ):
        return SourceSeparationResult(
            job_id=job_id or "fake-job",
            input_wav=str(wav_path),
            output_dir="data/stems/fake-job",
            model_name=model_name,
            stems={},
            selected_stem=selected_stem,
            selected_stem_path=None,
            status="error",
            error="RuntimeError: demucs failed",
        )

    monkeypatch.setattr("app.pipeline.orchestrator.extract_audio", fake_extract_audio)
    monkeypatch.setattr("app.pipeline.orchestrator.separate_sources", fake_separate_sources)

    result = run_audio_to_analysis_pipeline(
        source="data/samples/source.wav",
        job_id="pytest-separation-error",
    )

    assert result.status == "error"
    assert result.error == "RuntimeError: demucs failed"
    assert result.extract["status"] == "completed"
    assert result.separation["status"] == "error"
    assert result.separation_quality == {}
    assert result.analysis == {}
    assert result.midi_path is None


def test_audio_to_analysis_pipeline_uses_original_wav_when_quality_prefers_it(monkeypatch):
    class FakeQuality:
        def to_dict(self):
            return {
                "input_wav": "data/processed/fake-job/input.wav",
                "selected_stem": "other",
                "selected_stem_path": "data/stems/fake-job/other.wav",
                "decision": "prefer_original_wav",
                "recommended_audio_path": "data/processed/fake-job/input.wav",
                "likely_solo_piano": True,
                "total_energy": 1.0,
                "selected_stem_energy": 0.99,
                "non_selected_energy": 0.01,
                "non_selected_energy_ratio": 0.01,
                "stem_energies": {"other": 0.99, "vocals": 0.01},
                "reason": "Fake solo piano decision.",
            }

    def fake_extract_audio(source, output_dir="data/processed", job_id=None):
        return AudioExtractionResult(
            job_id=job_id or "fake-job",
            source=str(source),
            input_type="file",
            original_path="data/processed/fake-job/raw/source.wav",
            wav_path="data/processed/fake-job/input.wav",
            duration_seconds=1.0,
            sample_rate=44100,
            channels=1,
            status="completed",
            error=None,
        )

    def fake_separate_sources(
        wav_path,
        output_dir="data/stems",
        job_id=None,
        model_name="htdemucs",
        selected_stem="other",
    ):
        return SourceSeparationResult(
            job_id=job_id or "fake-job",
            input_wav=str(wav_path),
            output_dir="data/stems/fake-job",
            model_name=model_name,
            stems={
                "vocals": "data/stems/fake-job/vocals.wav",
                "drums": "data/stems/fake-job/drums.wav",
                "bass": "data/stems/fake-job/bass.wav",
                "other": "data/stems/fake-job/other.wav",
            },
            selected_stem=selected_stem,
            selected_stem_path="data/stems/fake-job/other.wav",
            status="completed",
            error=None,
        )

    def fake_analyze_separation_quality(input_wav, stems, selected_stem="other"):
        return FakeQuality()

    def fake_run_tracer_bullet(
        audio_path,
        artifacts_dir="artifacts/tracer",
        job_id=None,
        use_basic_pitch=False,
    ):
        assert audio_path == "data/processed/fake-job/input.wav"

        return TracerBulletResult(
            job_id=job_id or "fake-job",
            input_audio=str(audio_path),
            midi_path="artifacts/tracer/fake-job/output.mid",
            detected_key="C major",
            hvs_score=1.0,
            status="completed",
            transcription_method="basic_pitch",
            key_confidence=0.9,
            transcription_error=None,
            error=None,
        )

    monkeypatch.setattr("app.pipeline.orchestrator.extract_audio", fake_extract_audio)
    monkeypatch.setattr("app.pipeline.orchestrator.separate_sources", fake_separate_sources)
    monkeypatch.setattr(
        "app.pipeline.orchestrator.analyze_separation_quality",
        fake_analyze_separation_quality,
    )
    monkeypatch.setattr("app.pipeline.orchestrator.run_tracer_bullet", fake_run_tracer_bullet)

    result = run_audio_to_analysis_pipeline(
        source="data/samples/source.wav",
        job_id="pytest-adaptive-audio-selection",
    )

    assert result.status == "completed"
    assert result.final_audio_path == "data/processed/fake-job/input.wav"
    assert result.analysis["input_audio"] == "data/processed/fake-job/input.wav"
    assert result.separation_quality["decision"] == "prefer_original_wav"
    assert result.separation_quality["likely_solo_piano"] is True
