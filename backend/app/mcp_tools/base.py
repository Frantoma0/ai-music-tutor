from abc import ABC, abstractmethod
from typing import Any

from app.mcp_tools.schemas import ToolContract, ToolResult


class MCPTool(ABC):
    @property
    @abstractmethod
    def contract(self) -> ToolContract:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, payload: dict[str, Any]) -> ToolResult:
        raise NotImplementedError
