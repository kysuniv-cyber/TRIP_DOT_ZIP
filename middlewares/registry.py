from typing import Callable, Any


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> Callable[..., Any]:
        if name not in self._tools:
            raise KeyError(f"등록되지 않은 tool: {name}")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools