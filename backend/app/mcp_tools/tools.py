from typing import Any

from app.mcp_tools.base import MCPTool
from app.mcp_tools.schemas import ToolCategory, ToolContract, ToolResult, ToolStatus
from app.pipeline.audio_ingestion import extract_audio
from app.pipeline.source_separation import separate_sources
from app.pipeline.transcription import transcribe_audio
from app.pipeline.orchestrator import run_audio_to_analysis_pipeline
from app.pipeline.persistence import persist_audio_to_analysis_result
from app.pipeline.correction_mask import build_correction_mask
from app.pipeline.harmony_analysis import analyze_notes_harmony, merge_hvs_into_notes
from app.db.database import (
    get_metrics_for_run,
    get_pipeline_run,
    list_metrics,
    list_pipeline_runs,
)
from app.pipeline.tracer import run_tracer_bullet


class TranscribeAudioTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="transcribe_audio",
            description=(
                "Transcribe an audio file into MIDI and structured note events "
                "using Basic Pitch with placeholder fallback."
            ),
            category=ToolCategory.TRANSCRIPTION,
            status=ToolStatus.READY,
            deterministic=False,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "audio_path": {
                        "type": "string",
                        "description": "Path to the audio file inside the backend container.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory where MIDI transcription artifacts should be written.",
                        "default": "artifacts/transcription",
                    },
                    "job_id": {
                        "type": ["string", "null"],
                        "description": "Optional stable job id for transcription artifacts.",
                    },
                    "use_basic_pitch": {
                        "type": "boolean",
                        "description": "Use real Basic Pitch transcription when true.",
                        "default": True,
                    },
                },
                "required": ["audio_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "input_audio": {"type": "string"},
                    "midi_path": {"type": ["string", "null"]},
                    "status": {"type": "string"},
                    "transcription_method": {"type": "string"},
                    "note_count": {"type": "integer"},
                    "notes": {"type": "array"},
                    "transcription_error": {"type": ["string", "null"]},
                    "error": {"type": ["string", "null"]},
                    "persistence": {"type": ["object", "null"]},
                    "persistence_error": {"type": ["string", "null"]},
                },
                "required": [
                    "job_id",
                    "input_audio",
                    "status",
                    "transcription_method",
                    "note_count",
                    "notes",
                ],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        audio_path = payload.get("audio_path")

        if not audio_path:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={},
                error="Missing required field: audio_path",
            )

        result = transcribe_audio(
            audio_path=audio_path,
            output_dir=payload.get("output_dir", "artifacts/transcription"),
            job_id=payload.get("job_id"),
            use_basic_pitch=bool(payload.get("use_basic_pitch", True)),
        )

        return ToolResult(
            tool_name=self.contract.name,
            status="success" if result.status == "completed" else "error",
            data=result.to_dict(),
            error=result.error,
        )


class SeparateSourcesTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="separate_sources",
            description=(
                "Separate a normalized WAV file into Demucs stems and select "
                "the most suitable piano/instrumental stem."
            ),
            category=ToolCategory.AUDIO,
            status=ToolStatus.READY,
            deterministic=False,
            uses_gpu=True,
            input_schema={
                "type": "object",
                "properties": {
                    "wav_path": {
                        "type": "string",
                        "description": "Path to a normalized WAV file inside the backend container.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory where stem artifacts should be written.",
                        "default": "data/stems",
                    },
                    "job_id": {
                        "type": ["string", "null"],
                        "description": "Optional stable job id for separation artifacts.",
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Demucs model name.",
                        "default": "htdemucs",
                    },
                    "selected_stem": {
                        "type": "string",
                        "description": "Stem to use as piano/instrumental candidate.",
                        "default": "other",
                    },
                },
                "required": ["wav_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "input_wav": {"type": "string"},
                    "output_dir": {"type": "string"},
                    "model_name": {"type": "string"},
                    "stems": {"type": "object"},
                    "selected_stem": {"type": "string"},
                    "selected_stem_path": {"type": ["string", "null"]},
                    "status": {"type": "string"},
                    "error": {"type": ["string", "null"]},
                },
                "required": [
                    "job_id",
                    "input_wav",
                    "output_dir",
                    "model_name",
                    "stems",
                    "selected_stem",
                    "status",
                ],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        wav_path = payload.get("wav_path")

        if not wav_path:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={},
                error="Missing required field: wav_path",
            )

        result = separate_sources(
            wav_path=wav_path,
            output_dir=payload.get("output_dir", "data/stems"),
            job_id=payload.get("job_id"),
            model_name=payload.get("model_name", "htdemucs"),
            selected_stem=payload.get("selected_stem", "other"),
        )

        return ToolResult(
            tool_name=self.contract.name,
            status="success" if result.status == "completed" else "error",
            data=result.to_dict(),
            error=result.error,
        )


class ExtractAudioTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="extract_audio",
            description=(
                "Extract or normalize audio from a local file or URL into a "
                "16-bit 44.1kHz mono WAV file ready for transcription."
            ),
            category=ToolCategory.INGESTION,
            status=ToolStatus.READY,
            deterministic=True,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Local file path or HTTP/HTTPS URL.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory where processed audio should be written.",
                        "default": "data/processed",
                    },
                    "job_id": {
                        "type": ["string", "null"],
                        "description": "Optional stable job id for the extraction artifacts.",
                    },
                },
                "required": ["source"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "source": {"type": "string"},
                    "input_type": {"type": "string"},
                    "original_path": {"type": "string"},
                    "wav_path": {"type": "string"},
                    "duration_seconds": {"type": ["number", "null"]},
                    "sample_rate": {"type": ["integer", "null"]},
                    "channels": {"type": ["integer", "null"]},
                    "status": {"type": "string"},
                    "error": {"type": ["string", "null"]},
                },
                "required": [
                    "job_id",
                    "source",
                    "input_type",
                    "wav_path",
                    "status",
                ],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        source = payload.get("source")

        if not source:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={},
                error="Missing required field: source",
            )

        result = extract_audio(
            source=source,
            output_dir=payload.get("output_dir", "data/processed"),
            job_id=payload.get("job_id"),
        )

        return ToolResult(
            tool_name=self.contract.name,
            status="success" if result.status == "completed" else "error",
            data=result.to_dict(),
            error=result.error,
        )


class StubTool(MCPTool):
    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        *,
        deterministic: bool = False,
        uses_gpu: bool = False,
        status: ToolStatus = ToolStatus.READY,
    ) -> None:
        self._contract = ToolContract(
            name=name,
            description=description,
            category=category,
            status=status,
            deterministic=deterministic,
            uses_gpu=uses_gpu,
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["job_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "status": {"type": "string"},
                    "data": {"type": "object"},
                    "error": {"type": ["string", "null"]},
                },
                "required": ["tool_name", "status", "data"],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        return ToolResult(
            tool_name=self.contract.name,
            status="skipped",
            data={"reason": "stub_only", "received_payload": payload},
            error=None,
        )


class RunAudioToAnalysisTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="run_audio_to_analysis",
            description=(
                "Run the end-to-end audio analysis pipeline: extract audio, "
                "separate sources, transcribe selected stem and return MIDI, "
                "key detection and HVS score."
            ),
            category=ToolCategory.SYSTEM,
            status=ToolStatus.READY,
            deterministic=False,
            uses_gpu=True,
            input_schema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Local file path or HTTP/HTTPS URL.",
                    },
                    "job_id": {
                        "type": ["string", "null"],
                        "description": "Optional stable job id for all pipeline artifacts.",
                    },
                    "processed_dir": {
                        "type": "string",
                        "description": "Directory for normalized audio artifacts.",
                        "default": "data/processed",
                    },
                    "stems_dir": {
                        "type": "string",
                        "description": "Directory for source separation artifacts.",
                        "default": "data/stems",
                    },
                    "artifacts_dir": {
                        "type": "string",
                        "description": "Directory for tracer/MIDI artifacts.",
                        "default": "artifacts/tracer",
                    },
                    "use_basic_pitch": {
                        "type": "boolean",
                        "description": "Use real Basic Pitch transcription.",
                        "default": True,
                    },
                    "selected_stem": {
                        "type": "string",
                        "description": "Stem to pass to the transcription stage.",
                        "default": "other",
                    },
                    "persist": {
                        "type": "boolean",
                        "description": "Persist the completed pipeline result to SQLite.",
                        "default": False,
                    },
                    "db_path": {
                        "type": "string",
                        "description": "SQLite database path used when persist is true.",
                        "default": "data/app.sqlite3",
                    },
                    "session_title": {
                        "type": ["string", "null"],
                        "description": "Optional session title used when persisting the run.",
                    },
                },
                "required": ["source"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "source": {"type": "string"},
                    "status": {"type": "string"},
                    "extract": {"type": "object"},
                    "separation": {"type": "object"},
                    "separation_quality": {"type": "object"},
                    "transcription": {"type": "object"},
                    "analysis": {"type": "object"},
                    "final_audio_path": {"type": ["string", "null"]},
                    "midi_path": {"type": ["string", "null"]},
                    "detected_key": {"type": ["string", "null"]},
                    "hvs_score": {"type": ["number", "null"]},
                    "error": {"type": ["string", "null"]},
                },
                "required": [
                    "job_id",
                    "source",
                    "status",
                    "extract",
                    "separation",
                    "separation_quality",
                    "transcription",
                    "analysis",
                ],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        source = payload.get("source")

        if not source:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={},
                error="Missing required field: source",
            )

        result = run_audio_to_analysis_pipeline(
            source=source,
            job_id=payload.get("job_id"),
            processed_dir=payload.get("processed_dir", "data/processed"),
            stems_dir=payload.get("stems_dir", "data/stems"),
            artifacts_dir=payload.get("artifacts_dir", "artifacts/tracer"),
            use_basic_pitch=bool(payload.get("use_basic_pitch", True)),
            selected_stem=payload.get("selected_stem", "other"),
        )

        data = result.to_dict()
        data["persistence"] = None
        data["persistence_error"] = None

        if bool(payload.get("persist", False)) and result.status == "completed":
            try:
                data["persistence"] = await persist_audio_to_analysis_result(
                    result,
                    db_path=payload.get("db_path", "data/app.sqlite3"),
                    session_title=payload.get("session_title"),
                )
            except Exception as exc:
                data["persistence_error"] = f"{type(exc).__name__}: {exc}"

                return ToolResult(
                    tool_name=self.contract.name,
                    status="error",
                    data=data,
                    error=data["persistence_error"],
                )

        return ToolResult(
            tool_name=self.contract.name,
            status="success" if result.status == "completed" else "error",
            data=data,
            error=result.error,
        )


class RunTracerBulletTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="run_tracer_bullet",
            description=(
                "Run the Day 3 tracer bullet pipeline: audio input to MIDI "
                "artifact, music21 key detection, placeholder HVS score and "
                "JSON-compatible result."
            ),
            category=ToolCategory.SYSTEM,
            status=ToolStatus.READY,
            deterministic=True,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "audio_path": {
                        "type": "string",
                        "description": "Path to input WAV/audio file inside the backend container.",
                    },
                    "job_id": {
                        "type": ["string", "null"],
                        "description": "Optional stable job id for artifacts.",
                    },
                    "artifacts_dir": {
                        "type": "string",
                        "description": "Directory where tracer artifacts will be written.",
                        "default": "artifacts/tracer",
                    },
                    "use_basic_pitch": {
                        "type": "boolean",
                        "description": "Try Basic Pitch before falling back to placeholder MIDI.",
                        "default": False,
                    },
                },
                "required": ["audio_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "input_audio": {"type": "string"},
                    "midi_path": {"type": "string"},
                    "detected_key": {"type": "string"},
                    "hvs_score": {"type": "number"},
                    "status": {"type": "string"},
                    "transcription_method": {"type": "string"},
                    "key_confidence": {"type": ["number", "null"]},
                    "transcription_error": {"type": ["string", "null"]},
                    "error": {"type": ["string", "null"]},
                },
                "required": [
                    "job_id",
                    "input_audio",
                    "midi_path",
                    "detected_key",
                    "hvs_score",
                    "status",
                    "transcription_method",
                ],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        try:
            audio_path = payload.get("audio_path")
            if not audio_path:
                raise ValueError("Missing required field: audio_path")

            result = run_tracer_bullet(
                audio_path=audio_path,
                artifacts_dir=payload.get("artifacts_dir", "artifacts/tracer"),
                job_id=payload.get("job_id"),
                use_basic_pitch=bool(payload.get("use_basic_pitch", False)),
            )

            return ToolResult(
                tool_name=self.contract.name,
                status="success",
                data=result.to_dict(),
                error=None,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={},
                error=str(exc),
            )








class AnalyzeHarmonyTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="analyze_harmony",
            description="Analyze persisted transcription notes and assign per-note harmony violation scores.",
            category=ToolCategory.MUSIC_THEORY,
            status=ToolStatus.READY,
            deterministic=True,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Persisted pipeline job id.",
                    },
                    "db_path": {
                        "type": "string",
                        "description": "SQLite database path.",
                        "default": "data/app.sqlite3",
                    },
                    "output_path": {
                        "type": ["string", "null"],
                        "description": "Optional path where the full harmony analysis JSON should be written.",
                        "default": None,
                    },
                    "include_notes": {
                        "type": "boolean",
                        "description": "Include analyzed notes in the API response. Full notes are still written to output_path when provided.",
                        "default": False,
                    },
                    "max_notes": {
                        "type": "integer",
                        "description": "Maximum number of analyzed notes to include in the API response when include_notes is true.",
                        "default": 50,
                    },
                },
                "required": ["job_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "pipeline_run_id": {"type": ["string", "null"]},
                    "detected_key": {"type": ["string", "null"]},
                    "global_hvs_score": {"type": ["number", "null"]},
                    "transcription_method": {"type": ["string", "null"]},
                    "midi_path": {"type": ["string", "null"]},
                    "note_count": {"type": "integer"},
                    "hvs_distribution": {"type": "object"},
                    "label_distribution": {"type": "object"},
                    "notes": {"type": "array"},
                    "notes_included": {"type": "boolean"},
                    "returned_note_count": {"type": "integer"},
                    "output_path": {"type": ["string", "null"]},
                    "error": {"type": ["string", "null"]},
                },
                "required": [
                    "job_id",
                    "note_count",
                    "hvs_distribution",
                    "label_distribution",
                    "notes",
                    "notes_included",
                    "returned_note_count",
                ],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        job_id = payload.get("job_id")

        if not job_id:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={
                    "job_id": "",
                    "pipeline_run_id": None,
                    "detected_key": None,
                    "global_hvs_score": None,
                    "transcription_method": None,
                    "midi_path": None,
                    "note_count": 0,
                    "hvs_distribution": {},
                    "label_distribution": {},
                    "notes": [],
                    "notes_included": False,
                    "returned_note_count": 0,
                    "output_path": payload.get("output_path"),
                    "error": "Missing required field: job_id",
                },
                error="Missing required field: job_id",
            )

        try:
            run = await get_pipeline_run(
                payload.get("db_path", "data/app.sqlite3"),
                job_id=job_id,
            )

            if run is None:
                message = f"Pipeline run not found: {job_id}"

                return ToolResult(
                    tool_name=self.contract.name,
                    status="error",
                    data={
                        "job_id": job_id,
                        "pipeline_run_id": None,
                        "detected_key": None,
                        "global_hvs_score": None,
                        "transcription_method": None,
                        "midi_path": None,
                        "note_count": 0,
                        "hvs_distribution": {},
                        "label_distribution": {},
                        "notes": [],
                        "notes_included": False,
                        "returned_note_count": 0,
                        "output_path": payload.get("output_path"),
                        "error": message,
                    },
                    error=message,
                )

            transcription = run.get("transcription") or {}
            notes = transcription.get("notes") or []

            harmony = analyze_notes_harmony(
                notes,
                detected_key=run.get("detected_key"),
            )

            notes_with_hvs = merge_hvs_into_notes(notes, harmony)

            hvs_distribution: dict[str, int] = {}
            label_distribution: dict[str, int] = {}

            for note in notes_with_hvs:
                hvs_key = str(note.get("hvs_score"))
                label_key = str(note.get("hvs_label"))

                hvs_distribution[hvs_key] = hvs_distribution.get(hvs_key, 0) + 1
                label_distribution[label_key] = label_distribution.get(label_key, 0) + 1

            include_notes = bool(payload.get("include_notes", False))

            try:
                max_notes = int(payload.get("max_notes", 50))
            except (TypeError, ValueError):
                max_notes = 50

            max_notes = max(0, min(max_notes, 1000))

            response_notes = notes_with_hvs[:max_notes] if include_notes else []

            harmony_data = harmony.to_dict()
            harmony_summary = {
                **harmony_data,
                "notes": response_notes,
            }

            full_data = {
                "job_id": job_id,
                "pipeline_run_id": run.get("id"),
                "detected_key": run.get("detected_key"),
                "global_hvs_score": run.get("hvs_score"),
                "transcription_method": transcription.get("transcription_method"),
                "midi_path": transcription.get("midi_path") or run.get("midi_path"),
                "status": harmony.status,
                "note_count": harmony.note_count,
                "harmony": harmony_data,
                "hvs_distribution": hvs_distribution,
                "label_distribution": label_distribution,
                "notes": notes_with_hvs,
                "notes_included": True,
                "returned_note_count": len(notes_with_hvs),
                "output_path": payload.get("output_path"),
                "error": harmony.error,
            }

            data = {
                **full_data,
                "harmony": harmony_summary,
                "notes": response_notes,
                "notes_included": include_notes,
                "returned_note_count": len(response_notes),
            }

            output_path = payload.get("output_path")
            if output_path:
                import json
                from pathlib import Path

                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(full_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            return ToolResult(
                tool_name=self.contract.name,
                status="success",
                data=data,
                error=None,
            )

        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"

            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={
                    "job_id": job_id,
                    "pipeline_run_id": None,
                    "detected_key": None,
                    "global_hvs_score": None,
                    "transcription_method": None,
                    "midi_path": None,
                    "note_count": 0,
                    "hvs_distribution": {},
                    "label_distribution": {},
                    "notes": [],
                    "notes_included": False,
                    "returned_note_count": 0,
                    "output_path": payload.get("output_path"),
                    "error": message,
                },
                error=message,
            )

class GenerateMaskTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="generate_mask",
            description="Generate deterministic correction mask candidates from a persisted pipeline run.",
            category=ToolCategory.CORRECTION,
            status=ToolStatus.READY,
            deterministic=True,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Persisted pipeline job id.",
                    },
                    "db_path": {
                        "type": "string",
                        "description": "SQLite database path.",
                        "default": "data/app.sqlite3",
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "description": "Select notes with confidence below this threshold.",
                        "default": 0.7,
                    },
                    "hvs_threshold": {
                        "type": "number",
                        "description": "Select notes only when HVS is above this threshold.",
                        "default": 0.6,
                    },
                    "allow_hvs_only_fallback": {
                        "type": "boolean",
                        "description": "Allow HVS-only candidate selection when note confidence is missing.",
                        "default": True,
                    },
                    "output_path": {
                        "type": ["string", "null"],
                        "description": "Optional path where the generated mask JSON should be written.",
                        "default": None,
                    },
                    "harmony_path": {
                        "type": ["string", "null"],
                        "description": "Optional harmony analysis JSON path containing notes with per-note hvs_score.",
                        "default": None,
                    },
                    "include_candidates": {
                        "type": "boolean",
                        "description": "Include correction candidates in the API response. Full candidates are still written to output_path when provided.",
                        "default": False,
                    },
                    "max_candidates": {
                        "type": "integer",
                        "description": "Maximum number of candidates to include in the API response when include_candidates is true.",
                        "default": 50,
                    },
                },
                "required": ["job_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "pipeline_run_id": {"type": ["string", "null"]},
                    "detected_key": {"type": ["string", "null"]},
                    "hvs_score": {"type": ["number", "null"]},
                    "transcription_method": {"type": ["string", "null"]},
                    "note_count": {"type": "integer"},
                    "selected_count": {"type": "integer"},
                    "confidence_threshold": {"type": "number"},
                    "hvs_threshold": {"type": "number"},
                    "candidates": {"type": "array"},
                    "candidate_count": {"type": "integer"},
                    "candidates_included": {"type": "boolean"},
                    "returned_candidate_count": {"type": "integer"},
                    "output_path": {"type": ["string", "null"]},
                    "error": {"type": ["string", "null"]},
                },
                "required": [
                    "job_id",
                    "note_count",
                    "selected_count",
                    "confidence_threshold",
                    "hvs_threshold",
                    "candidates",
                ],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        job_id = payload.get("job_id")

        if not job_id:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={
                    "job_id": "",
                    "pipeline_run_id": None,
                    "detected_key": None,
                    "hvs_score": None,
                    "transcription_method": None,
                    "note_count": 0,
                    "selected_count": 0,
                    "confidence_threshold": float(payload.get("confidence_threshold", 0.7)),
                    "hvs_threshold": float(payload.get("hvs_threshold", 0.6)),
                    "candidates": [],
                    "output_path": payload.get("output_path"),
                    "error": "Missing required field: job_id",
                },
                error="Missing required field: job_id",
            )

        try:
            run = await get_pipeline_run(
                payload.get("db_path", "data/app.sqlite3"),
                job_id=job_id,
            )

            if run is None:
                message = f"Pipeline run not found: {job_id}"

                return ToolResult(
                    tool_name=self.contract.name,
                    status="error",
                    data={
                        "job_id": job_id,
                        "pipeline_run_id": None,
                        "detected_key": None,
                        "hvs_score": None,
                        "transcription_method": None,
                        "note_count": 0,
                        "selected_count": 0,
                        "confidence_threshold": float(payload.get("confidence_threshold", 0.7)),
                        "hvs_threshold": float(payload.get("hvs_threshold", 0.6)),
                        "candidates": [],
                        "output_path": payload.get("output_path"),
                        "error": message,
                    },
                    error=message,
                )

            transcription = run.get("transcription") or {}
            notes = transcription.get("notes") or []

            harmony_path = payload.get("harmony_path")
            harmony_source = "none"

            if harmony_path:
                import json
                from pathlib import Path

                path = Path(harmony_path)
                harmony_data = json.loads(path.read_text(encoding="utf-8"))

                harmony_notes = harmony_data.get("notes") or []
                hvs_by_id = {
                    note.get("id"): note
                    for note in harmony_notes
                    if note.get("id") is not None
                }

                merged_notes = []

                for note in notes:
                    item = dict(note)
                    harmony_note = hvs_by_id.get(item.get("id"))

                    if harmony_note is not None:
                        item["hvs_score"] = harmony_note.get("hvs_score")
                        item["hvs_label"] = harmony_note.get("hvs_label")
                        item["hvs_reason"] = harmony_note.get("hvs_reason") or harmony_note.get("reason")

                    merged_notes.append(item)

                notes = merged_notes
                harmony_source = str(path)

            mask = build_correction_mask(
                notes,
                global_hvs_score=run.get("hvs_score"),
                confidence_threshold=float(payload.get("confidence_threshold", 0.7)),
                hvs_threshold=float(payload.get("hvs_threshold", 0.6)),
                allow_hvs_only_fallback=bool(payload.get("allow_hvs_only_fallback", True)),
            )

            mask_data = mask.to_dict()
            all_candidates = mask_data.get("candidates", [])

            include_candidates = bool(payload.get("include_candidates", False))

            try:
                max_candidates = int(payload.get("max_candidates", 50))
            except (TypeError, ValueError):
                max_candidates = 50

            max_candidates = max(0, min(max_candidates, 1000))

            response_candidates = (
                all_candidates[:max_candidates]
                if include_candidates
                else []
            )

            full_data = {
                "job_id": job_id,
                "pipeline_run_id": run.get("id"),
                "detected_key": run.get("detected_key"),
                "hvs_score": run.get("hvs_score"),
                "transcription_method": transcription.get("transcription_method"),
                "midi_path": transcription.get("midi_path") or run.get("midi_path"),
                "harmony_path": payload.get("harmony_path"),
                "harmony_source": harmony_source,
                **mask_data,
                "candidate_count": len(all_candidates),
                "candidates_included": True,
                "returned_candidate_count": len(all_candidates),
                "output_path": payload.get("output_path"),
            }

            data = {
                **full_data,
                "candidates": response_candidates,
                "candidates_included": include_candidates,
                "returned_candidate_count": len(response_candidates),
            }

            output_path = payload.get("output_path")
            if output_path:
                import json
                from pathlib import Path

                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(full_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            return ToolResult(
                tool_name=self.contract.name,
                status="success",
                data=data,
                error=None,
            )

        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"

            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={
                    "job_id": job_id,
                    "pipeline_run_id": None,
                    "detected_key": None,
                    "hvs_score": None,
                    "transcription_method": None,
                    "note_count": 0,
                    "selected_count": 0,
                    "confidence_threshold": float(payload.get("confidence_threshold", 0.7)),
                    "hvs_threshold": float(payload.get("hvs_threshold", 0.6)),
                    "candidates": [],
                    "output_path": payload.get("output_path"),
                    "error": message,
                },
                error=message,
            )

class ListPipelineRunsTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="list_pipeline_runs",
            description="List recent persisted audio-to-analysis pipeline runs from SQLite.",
            category=ToolCategory.SYSTEM,
            status=ToolStatus.READY,
            deterministic=True,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "db_path": {
                        "type": "string",
                        "description": "SQLite database path.",
                        "default": "data/app.sqlite3",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of runs to return.",
                        "default": 20,
                    },
                },
                "required": [],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "runs": {"type": "array"},
                    "count": {"type": "integer"},
                },
                "required": ["runs", "count"],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        try:
            limit = int(payload.get("limit", 20))
            limit = max(1, min(limit, 100))

            runs = await list_pipeline_runs(
                payload.get("db_path", "data/app.sqlite3"),
                limit=limit,
            )

            return ToolResult(
                tool_name=self.contract.name,
                status="success",
                data={
                    "runs": runs,
                    "count": len(runs),
                },
                error=None,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={
                    "runs": [],
                    "count": 0,
                },
                error=f"{type(exc).__name__}: {exc}",
            )


class GetPipelineRunTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="get_pipeline_run",
            description="Get one persisted audio-to-analysis pipeline run by job_id from SQLite.",
            category=ToolCategory.SYSTEM,
            status=ToolStatus.READY,
            deterministic=True,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Pipeline job id to retrieve.",
                    },
                    "db_path": {
                        "type": "string",
                        "description": "SQLite database path.",
                        "default": "data/app.sqlite3",
                    },
                },
                "required": ["job_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "run": {"type": ["object", "null"]},
                },
                "required": ["run"],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        job_id = payload.get("job_id")

        if not job_id:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={"run": None},
                error="Missing required field: job_id",
            )

        try:
            run = await get_pipeline_run(
                payload.get("db_path", "data/app.sqlite3"),
                job_id=job_id,
            )

            if run is None:
                return ToolResult(
                    tool_name=self.contract.name,
                    status="error",
                    data={"run": None},
                    error=f"Pipeline run not found: {job_id}",
                )

            return ToolResult(
                tool_name=self.contract.name,
                status="success",
                data={"run": run},
                error=None,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={"run": None},
                error=f"{type(exc).__name__}: {exc}",
            )



class ListMetricsTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="list_metrics",
            description="List persisted evaluation metrics from SQLite.",
            category=ToolCategory.SYSTEM,
            status=ToolStatus.READY,
            deterministic=True,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "db_path": {
                        "type": "string",
                        "description": "SQLite database path.",
                        "default": "data/app.sqlite3",
                    },
                    "metric_name": {
                        "type": ["string", "null"],
                        "description": "Optional metric name filter.",
                        "default": None,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of metrics to return.",
                        "default": 50,
                    },
                },
                "required": [],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "metrics": {"type": "array"},
                    "count": {"type": "integer"},
                },
                "required": ["metrics", "count"],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        try:
            metrics = await list_metrics(
                payload.get("db_path", "data/app.sqlite3"),
                metric_name=payload.get("metric_name"),
                limit=int(payload.get("limit", 50)),
            )

            return ToolResult(
                tool_name=self.contract.name,
                status="success",
                data={
                    "metrics": metrics,
                    "count": len(metrics),
                },
                error=None,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={
                    "metrics": [],
                    "count": 0,
                },
                error=f"{type(exc).__name__}: {exc}",
            )


class GetMetricsForRunTool(MCPTool):
    def __init__(self) -> None:
        self._contract = ToolContract(
            name="get_metrics_for_run",
            description="Get all persisted metrics for one pipeline run by job_id.",
            category=ToolCategory.SYSTEM,
            status=ToolStatus.READY,
            deterministic=True,
            uses_gpu=False,
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Pipeline job id.",
                    },
                    "db_path": {
                        "type": "string",
                        "description": "SQLite database path.",
                        "default": "data/app.sqlite3",
                    },
                },
                "required": ["job_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "run": {"type": ["object", "null"]},
                    "metrics": {"type": "array"},
                    "count": {"type": "integer"},
                },
                "required": ["run", "metrics", "count"],
            },
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        job_id = payload.get("job_id")

        if not job_id:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={
                    "run": None,
                    "metrics": [],
                    "count": 0,
                },
                error="Missing required field: job_id",
            )

        try:
            result = await get_metrics_for_run(
                payload.get("db_path", "data/app.sqlite3"),
                job_id=job_id,
            )

            if result is None:
                return ToolResult(
                    tool_name=self.contract.name,
                    status="error",
                    data={
                        "run": None,
                        "metrics": [],
                        "count": 0,
                    },
                    error=f"Pipeline run not found: {job_id}",
                )

            return ToolResult(
                tool_name=self.contract.name,
                status="success",
                data=result,
                error=None,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.contract.name,
                status="error",
                data={
                    "run": None,
                    "metrics": [],
                    "count": 0,
                },
                error=f"{type(exc).__name__}: {exc}",
            )

def build_default_tools() -> list[MCPTool]:
    return [
        ExtractAudioTool(),
        SeparateSourcesTool(),
        TranscribeAudioTool(),
        AnalyzeHarmonyTool(),
        GenerateMaskTool(),
        StubTool("correct_midi", "Ask the local LLM to propose constrained MIDI corrections.", ToolCategory.CORRECTION, uses_gpu=True),
        StubTool("validate_corrections", "Deterministically validate proposed corrections and reject harmful edits.", ToolCategory.CORRECTION, deterministic=True),
        StubTool("prepare_lesson", "Generate a learner-friendly lesson plan from the validated MIDI.", ToolCategory.LESSON, uses_gpu=True),
        RunTracerBulletTool(),
        RunAudioToAnalysisTool(),
        ListPipelineRunsTool(),
        GetPipelineRunTool(),
        ListMetricsTool(),
        GetMetricsForRunTool(),
        StubTool("separate_lass", "Language-queried audio source separation using AudioSep or a compatible LASS model.", ToolCategory.AUDIO, uses_gpu=True, status=ToolStatus.EXPERIMENTAL),
    ]
