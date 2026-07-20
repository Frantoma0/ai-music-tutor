from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolStatus(StrEnum):
    READY = "ready"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"


class ToolCategory(StrEnum):
    INGESTION = "ingestion"
    AUDIO = "audio"
    TRANSCRIPTION = "transcription"
    MUSIC_THEORY = "music_theory"
    CORRECTION = "correction"
    LESSON = "lesson"
    SYSTEM = "system"


class ToolContract(BaseModel):
    name: str = Field(..., min_length=1)
    version: str = "0.1.0"
    description: str
    category: ToolCategory
    status: ToolStatus = ToolStatus.READY
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    deterministic: bool = False
    uses_gpu: bool = False


class ToolResult(BaseModel):
    tool_name: str
    status: Literal["success", "error", "skipped"]
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
