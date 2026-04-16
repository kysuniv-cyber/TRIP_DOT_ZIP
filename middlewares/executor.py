from __future__ import annotations

import json
from typing import Any
from openai import OpenAI

from config import Settings
from llm.tool_specs import TOOLS
from middlewares.pipeline import LLMRequest, LLMResponse, Pipeline
from middlewares.registry import ToolRegistry
from middlewares.summary_mw import conversation_summary_middleware


class ToolExecutionError(Exception):
    pass


class AgentExecutor:
    def __init__(self, registry: ToolRegistry, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.registry = registry

        # middleware 파이프라인 구성
        self.pipeline = Pipeline(self._base_handler)
        self.pipeline.use(
            conversation_summary_middleware(
                openai_client=self.client,
                trigger_char_count=2000,   # 테스트 시 300~500으로 낮춰도 됨
                keep_last_n=4,
            )
        )

    def run(self, messages: list[dict]) -> str:

        request = LLMRequest(
            messages=messages,
            model=self.settings.openai_model,
            temperature=0.7,
            max_tokens=2048,
            tools=TOOLS,
            tool_choice=None,
            metadata={},
        )

        response = self.pipeline.execute(request)
        return response.content

    def _base_handler(self, request: LLMRequest) -> LLMResponse:
        response = self.client.responses.create(
            model=request.model,
            input=request.messages,
            tools=request.tools,
        )

        rounds = 0

        while rounds < self.settings.max_tool_rounds:
            rounds += 1

            function_calls = [
                item for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                usage = {}
                if getattr(response, "usage", None):
                    usage = {
                        "input_tokens": getattr(response.usage, "input_tokens", 0),
                        "output_tokens": getattr(response.usage, "output_tokens", 0),
                        "total_tokens": getattr(response.usage, "total_tokens", 0),
                    }

                return LLMResponse(
                    content=response.output_text,
                    usage=usage,
                    model=request.model,
                    finish_reason="stop",
                    metadata=request.metadata,
                )

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
                model=request.model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=request.tools,
            )

        raise ToolExecutionError("최대 tool 호출 라운드를 초과했습니다.")