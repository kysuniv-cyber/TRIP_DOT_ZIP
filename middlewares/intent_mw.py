"""
intent_mw.py

사용자 입력을 분석하여 intent(의도)를 분류하고,
해당 intent에 맞는 tool을 선택하도록 라우팅하는
Intent Routing Middleware 모듈이다.

주요 기능:
- 사용자 입력에서 intent를 추출한다.
- intent에 따라 route를 결정한다.
- route에 맞는 tool만 선택하여 모델에 전달한다.
- agent 실행 전에 state에 intent 정보를 반영한다.

동작 방식:
1. 사용자 메시지에서 텍스트를 추출한다.
2. classify_intent_by_rule()로 intent를 분류한다.
3. 분류 결과를 route 정보와 함께 state에 저장한다.
4. before_model()에서 route에 맞는 tool만 선택한다.

이 모듈은 LangChain의 AgentMiddleware를 기반으로 동작하며,
TravelAgentState를 상태 스키마로 사용한다.
"""

from __future__ import annotations

from typing import Any
from langchain.agents.middleware import AgentMiddleware

from test_backup.schemas.agent_state import TravelAgentState
from services.intent_service import classify_intent_by_rule


class IntentRoutingMiddleware(AgentMiddleware[TravelAgentState]):
    """사용자 의도를 분석하여 적절한 tool을 선택하는 미들웨어 클래스.

    LangChain AgentMiddleware를 상속받아,
    agent 실행 전에는 intent를 분석하고,
    model 호출 전에는 route에 맞는 tool만 선택하도록 동작한다.
    """

    state_schema = TravelAgentState

    def __init__(
        self,
        weather_tools: list | None = None,
        place_tools: list | None = None,
        schedule_tools: list | None = None,
        modify_tools: list | None = None,
        travel_tools: list | None = None,
        chat_tools: list | None = None,
        enable_tool_filtering: bool = True,
        debug: bool = True,
    ) -> None:
        """Intent Routing Middleware를 초기화한다.

        각 intent별로 사용할 tool 그룹을 받아 저장하고,
        tool filtering 활성화 여부와 debug 출력 여부를 설정한다.

        Args:
            weather_tools (list | None): 날씨 관련 tool 리스트
            place_tools (list | None): 장소 검색 관련 tool 리스트
            schedule_tools (list | None): 일정 생성 관련 tool 리스트
            modify_tools (list | None): 일정 수정 관련 tool 리스트
            travel_tools (list | None): 여행 추천 관련 tool 리스트
            chat_tools (list | None): 일반 대화용 tool 리스트
            enable_tool_filtering (bool): route에 따라 tool 필터링을 적용할지 여부
            debug (bool): 디버그 로그 출력 여부

        Returns:
            None: 초기화만 수행한다.
        """
        self.weather_tools = weather_tools or []
        self.place_tools = place_tools or []
        self.schedule_tools = schedule_tools or []
        self.modify_tools = modify_tools or []
        self.travel_tools = travel_tools or []
        self.chat_tools = chat_tools or []
        self.enable_tool_filtering = enable_tool_filtering
        self.debug = debug

    def _extract_user_text(self, state: TravelAgentState) -> str:
        """state에서 마지막 사용자 메시지의 텍스트를 추출한다.

        마지막 메시지의 content가 문자열이면 그대로 반환하고,
        list 형태의 멀티모달 메시지인 경우 text 타입 파트만 추출하여 결합한다.

        Args:
            state (TravelAgentState): 현재 agent 상태 객체

        Returns:
            str: intent 분류에 사용할 사용자 입력 텍스트
        """
        messages = state.get("messages", [])
        if not messages:
            return ""

        last_message = messages[-1]

        if hasattr(last_message, "content"):
            content = last_message.content

            if isinstance(content, str):
                return content.strip()

            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                return " ".join(text_parts).strip()

        return str(last_message).strip()

    def before_agent(
        self,
        state: TravelAgentState,
        runtime,
    ) -> dict[str, Any] | None:
        """agent 실행 전에 사용자 intent를 분석하여 state에 반영한다.

        마지막 사용자 메시지를 추출한 뒤 classify_intent_by_rule()로
        intent를 분류하고, confidence, route, reason 정보를 반환한다.

        Args:
            state (TravelAgentState): 현재 agent 상태 객체
            runtime: agent 실행 환경 정보

        Returns:
            dict[str, Any] | None: state에 반영할 intent 관련 정보
        """
        if self.debug:
            print("🔥🔥 middleware 들어옴 🔥🔥")

        user_text = self._extract_user_text(state)
        result = classify_intent_by_rule(user_text)

        if self.debug:
            print("[IntentRoutingMiddleware] user_text =", user_text)
            print("[IntentRoutingMiddleware] result =", result)

        return {
            "intent": result["intent"],
            "confidence": result["confidence"],
            "route": result["route"],
            "intent_reason": result["reason"],
        }

    def before_model(
        self,
        state: TravelAgentState,
        runtime,
    ) -> dict[str, Any] | None:
        """모델 호출 전에 route에 맞는 tool만 선택한다.

        state에 저장된 route 값을 기준으로 tool 그룹을 선택하고,
        enable_tool_filtering이 False이면 아무 변경 없이 None을 반환한다.

        Args:
            state (TravelAgentState): 현재 agent 상태 객체
            runtime: agent 실행 환경 정보

        Returns:
            dict[str, Any] | None: 선택된 tools 정보를 담은 딕셔너리
        """
        if not self.enable_tool_filtering:
            return None

        route = state.get("route", "chat")

        route_to_tools = {
            "weather": self.weather_tools,
            "place": self.place_tools,
            "schedule": self.schedule_tools,
            "modify": self.modify_tools,
            "travel": self.travel_tools,
            "chat": self.chat_tools,
        }

        selected_tools = route_to_tools.get(route, self.chat_tools)

        if self.debug:
            tool_names = [getattr(tool, "name", str(tool)) for tool in selected_tools]
            print("[IntentRoutingMiddleware] route =", route)
            print("[IntentRoutingMiddleware] selected_tools =", tool_names)

        return {"tools": selected_tools}