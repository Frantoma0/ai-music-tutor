from typing import Any

from app.mcp_tools.base import MCPTool
from app.mcp_tools.schemas import ToolCategory, ToolContract, ToolResult, ToolStatus
from app.pipeline.tracer import run_tracer_bullet


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
        StubTool("extract_audio", "Extract or normalize audio from uploaded file or YouTube source.", ToolCategory.INGESTION, deterministic=True),
        StubTool("separate_sources", "Separate audio sources using Demucs.", ToolCategory.AUDIO, uses_gpu=True),
        StubTool("transcribe_audio", "Transcribe piano audio to MIDI/note events using Basic Pitch ONNX backend.", ToolCategory.TRANSCRIPTION),
        StubTool("analyze_harmony", "Analyze key, harmonic context and chord-level information using music21.", ToolCategory.MUSIC_THEORY, deterministic=True),
        StubTool("generate_mask", "Generate confidence and harmony weighted correction mask.", ToolCategory.CORRECTION, deterministic=True),
        StubTool("correct_midi", "Ask the local LLM to propose constrained MIDI corrections.", ToolCategory.CORRECTION, uses_gpu=True),
        StubTool("validate_corrections", "Deterministically validate proposed corrections and reject harmful edits.", ToolCategory.CORRECTION, deterministic=True),
        StubTool("prepare_lesson", "Generate a learner-friendly lesson plan from the validated MIDI.", ToolCategory.LESSON, uses_gpu=True),
        RunTracerBulletTool(),
        StubTool("separate_lass", "Language-queried audio source separation using AudioSep or a compatible LASS model.", ToolCategory.AUDIO, uses_gpu=True, status=ToolStatus.EXPERIMENTAL),
    ]
