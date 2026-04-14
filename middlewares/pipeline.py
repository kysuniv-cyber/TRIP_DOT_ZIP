from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class LLMRequest:
    # LLM에 전달할 요청 객체. 미들웨어들이 이 객체를 읽고/수정한다.
    messages: list[dict]
    model: str
    temperature: float = 0.7          # 0 = 결정론적, 1.0 = 창의적
    max_tokens: int = 2048
    tools: list[dict] | None = None   # Function Calling 도구 스키마. None이면 일반 대화.
    tool_choice: str | None = None
    metadata: dict = field(default_factory=dict)
    # ↑ metadata — 미들웨어끼리 정보를 주고받는 공유 공간
    #   예) logged_at, from_cache, token_guard_trimmed 등

@dataclass
class LLMResponse:
    content: str                      # 최종 텍스트 응답
    usage: dict                       # prompt_tokens, completion_tokens, total_tokens
    model: str = ""
    finish_reason: str = ""
    # finish_reason: 'stop'(정상) / 'length'(토큰 초과) / 'tool_calls'(도구 호출)
    metadata: dict = field(default_factory=dict)
    elapsed_ms: float = 0.0           # logging 미들웨어가 채워준다

# 미들웨어 타입 — (request, next함수) → response 형태의 callable
Middleware = Callable[[LLMRequest, Callable], LLMResponse]

class Pipeline:
    def __init__(self, base_handler):
        # base_handler — 실제 OpenAI API를 호출하는 함수. 가장 안쪽에 위치.
        self._base_handler = base_handler
        self._middlewares: list[Middleware] = []

    def use(self, mw: Middleware) -> "Pipeline":
        # 반환값이 Pipeline이라 .use().use() 체이닝이 가능하다.
        self._middlewares.append(mw)
        return self

    def execute(self, request: LLMRequest) -> LLMResponse:
        chain = self._base_handler
        for mw in reversed(self._middlewares):
            # reversed() — 마지막 .use()가 가장 안쪽 레이어.
            # 즉 첫 번째 .use()가 제일 먼저 실행된다.
            chain = (lambda req, mw=mw, nxt=chain: mw(req, nxt))
            # ↑ mw=mw, nxt=chain 기본 인수 바인딩 필수
            #   없으면 루프가 끝난 뒤의 변수를 참조하는 클로저 버그 발생
        return chain(request)