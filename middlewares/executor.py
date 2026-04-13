import json
from typing import Any
from openai import OpenAI

from config import Settings
from llm.tool_specs import TOOLS
from middlewares.registry import ToolRegistry


class ToolExecutionError(Exception):
    pass


class AgentExecutor:
    def __init__(self, registry: ToolRegistry, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.registry = registry

    def run(self, user_prompt: str) -> str:
        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=user_prompt,
            tools=TOOLS,
        )

        rounds = 0

        while rounds < self.settings.max_tool_rounds:
            rounds += 1

            function_calls = [
                item for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                return response.output_text

            tool_outputs: list[dict[str, Any]] = []

            for call in function_calls:
                tool_name = call.name
                arguments = json.loads(call.arguments)

                try:
                    tool_fn = self.registry.get(tool_name)
                    result = tool_fn(**arguments)
                except Exception as e:
                    result = {
                        "error": True,
                        "tool_name": tool_name,
                        "message": str(e),
                    }

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                })

            response = self.client.responses.create(
                model=self.settings.openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOLS,
            )

        raise ToolExecutionError("최대 tool 호출 라운드를 초과했습니다.")