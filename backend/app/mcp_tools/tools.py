from typing import Any

from app.mcp_tools.base import MCPTool
from app.mcp_tools.schemas import ToolCategory, ToolContract, ToolResult, ToolStatus


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
        StubTool("separate_lass", "Language-queried audio source separation using AudioSep or a compatible LASS model.", ToolCategory.AUDIO, uses_gpu=True, status=ToolStatus.EXPERIMENTAL),
    ]
