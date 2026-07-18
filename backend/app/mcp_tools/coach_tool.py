"""Practice Coach exposed through the internal tool registry."""

from __future__ import annotations

from typing import Any

from app.agent.practice_coach import run_practice_coach
from app.mcp_tools.base import MCPTool
from app.mcp_tools.schemas import ToolCategory, ToolContract, ToolResult, ToolStatus


class PracticeCoachTool(MCPTool):
    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="practice_coach",
            version="0.1.0",
            description=(
                "Builds a personalized practice plan from recorded practice "
                "sessions: loop sections, tempos, hand focus and coaching tips. "
                "Deterministic core; local LLM may only rewrite tip texts."
            ),
            category=ToolCategory.LESSON,
            status=ToolStatus.READY,
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "language": {"type": "string", "enum": ["en", "bg"]},
                },
                "required": ["job_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "plan": {"type": "object"},
                },
            },
            deterministic=False,
            uses_gpu=False,
        )

    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        job_id = str(payload.get("job_id") or "").strip()

        if not job_id:
            return ToolResult(
                tool_name="practice_coach",
                status="error",
                error="job_id is required",
            )

        language = payload.get("language") if payload.get("language") in ("en", "bg") else "en"

        result = await run_practice_coach(job_id=job_id, language=language)

        return ToolResult(
            tool_name="practice_coach",
            status="success",
            data=result,
        )
