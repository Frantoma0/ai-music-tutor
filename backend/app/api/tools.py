from fastapi import APIRouter

from app.mcp_tools.registry import registry
from app.mcp_tools.schemas import ToolContract

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=list[ToolContract])
def list_tools() -> list[ToolContract]:
    return registry.list_contracts()


@router.get("/names", response_model=list[str])
def list_tool_names() -> list[str]:
    return registry.names()
