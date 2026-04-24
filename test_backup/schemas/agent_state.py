"""
agent_state.py

LangChain agent 실행 중 사용되는 상태(state) 구조를 정의하는 모듈이다.

사용자 입력 분석 결과(intent, route 등)를 저장하고,
middleware와 agent 간 데이터 전달을 담당한다.

주요 기능:
- intent(사용자 의도) 저장
- confidence(분류 신뢰도) 저장
- route(tool 분기 정보) 저장
- intent_reason(판단 근거) 저장

동작 방식:
1. middleware에서 intent 분석 수행
2. 분석 결과를 state에 저장
3. 이후 model/tool 실행 시 state를 참고

이 모듈은 LangChain의 AgentState를 확장하여
여행 agent에 필요한 상태 정보를 정의한다.
"""

from typing import Literal
from typing_extensions import NotRequired
from langchain.agents.middleware import AgentState


IntentType = Literal[
    "general_chat",
    "travel_recommendation",
    "place_search",
    "schedule_generation",
    "weather_query",
    "modify_request",
]

RouteType = Literal[
    "weather",
    "place",
    "schedule",
    "modify",
    "travel",
    "chat",
]


class TravelAgentState(AgentState):
    """여행 agent에서 사용하는 상태(state) 구조.

    intent 분석 결과와 routing 정보를 저장하여
    middleware와 agent 간 데이터 전달에 사용된다.

    Args:
        intent (IntentType): 사용자 의도
        confidence (float): intent 분류 신뢰도
        route (RouteType): tool 선택을 위한 라우팅 정보
        intent_reason (str): intent 판단 근거

    Returns:
        None: 상태 객체 정의
    """

    intent: NotRequired[IntentType]
    confidence: NotRequired[float]
    route: NotRequired[RouteType]
    intent_reason: NotRequired[str]