from typing import Any

from app.mcp_tools.base import MCPTool
from app.mcp_tools.schemas import ToolCategory, ToolContract, ToolResult, ToolStatus
from app.pipeline.audio_ingestion import extract_audio
from app.pipeline.source_separation import separate_sources
from app.pipeline.transcription import transcribe_audio
from app.pipeline.orchestrator import run_audio_to_analysis_pipeline
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

        return ToolResult(
            tool_name=self.contract.name,
            status="success" if result.status == "completed" else "error",
            data=result.to_dict(),
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


def build_default_tools() -> list[MCPTool]:
    return [
        ExtractAudioTool(),
        SeparateSourcesTool(),
        TranscribeAudioTool(),
        StubTool("analyze_harmony", "Analyze key, harmonic context and chord-level information using music21.", ToolCategory.MUSIC_THEORY, deterministic=True),
        StubTool("generate_mask", "Generate confidence and harmony weighted correction mask.", ToolCategory.CORRECTION, deterministic=True),
        StubTool("correct_midi", "Ask the local LLM to propose constrained MIDI corrections.", ToolCategory.CORRECTION, uses_gpu=True),
        StubTool("validate_corrections", "Deterministically validate proposed corrections and reject harmful edits.", ToolCategory.CORRECTION, deterministic=True),
        StubTool("prepare_lesson", "Generate a learner-friendly lesson plan from the validated MIDI.", ToolCategory.LESSON, uses_gpu=True),
        RunTracerBulletTool(),
        RunAudioToAnalysisTool(),
        StubTool("separate_lass", "Language-queried audio source separation using AudioSep or a compatible LASS model.", ToolCategory.AUDIO, uses_gpu=True, status=ToolStatus.EXPERIMENTAL),
    ]
