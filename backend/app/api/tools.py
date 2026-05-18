from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.mcp_tools.registry import registry
from app.mcp_tools.schemas import ToolContract, ToolResult

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolExecutionRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("", response_model=list[ToolContract])
def list_tools() -> list[ToolContract]:
    return registry.list_contracts()


@router.get("/names", response_model=list[str])
def list_tool_names() -> list[str]:
    return registry.names()


@router.post("/{tool_name}/execute", response_model=ToolResult)
async def execute_tool(tool_name: str, request: ToolExecutionRequest) -> ToolResult:
    try:
        tool = registry.get(tool_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return await tool.execute(request.payload)
