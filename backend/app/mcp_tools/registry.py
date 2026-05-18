from app.mcp_tools.base import MCPTool
from app.mcp_tools.schemas import ToolContract
from app.mcp_tools.tools import build_default_tools


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        name = tool.contract.name
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> MCPTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def list_contracts(self) -> list[ToolContract]:
        return [tool.contract for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def count(self) -> int:
        return len(self._tools)


registry = ToolRegistry()

for default_tool in build_default_tools():
    registry.register(default_tool)
