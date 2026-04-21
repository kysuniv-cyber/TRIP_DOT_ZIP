"""
agent_builder.py

LLM, tools, middleware를 결합하여
최종 agent를 생성하는 모듈이다.

주요 기능:
- ChatOpenAI 기반 LLM 초기화
- 여행 관련 tool 그룹 구성
- Intent Routing Middleware 설정
- LangChain agent 생성 및 반환

동작 방식:
1. 사용할 LLM 모델을 생성한다.
2. intent별 tool 그룹을 정의한다.
3. IntentRoutingMiddleware를 생성한다.
4. create_agent()를 통해 agent를 생성한다.

이 모듈은 프로젝트의 핵심 실행 진입점으로,
모든 기능을 하나의 agent로 통합하는 역할을 한다.
"""

from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from middlewares.intent_mw import IntentRoutingMiddleware
from test_backup.schemas.agent_state import TravelAgentState

from test_backup.tools import (
    get_weather_tool,
    search_place_tool,
    make_schedule_tool,
    modify_schedule_tool,
    recommend_travel_tool,
)


def build_agent() -> Any:
    """LLM, tool, middleware를 결합하여 agent를 생성한다.

    ChatOpenAI 모델을 초기화하고,
    tool 그룹과 IntentRoutingMiddleware를 연결하여
    최종 agent를 구성한다.

    Args:
        없음

    Returns:
        Any: 생성된 agent 객체
    """
    # 1. LLM 모델 초기화
    model = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0,
    )

    # 2. intent별 tool 그룹 정의
    weather_tools = [get_weather_tool]
    place_tools = [search_place_tool]
    schedule_tools = [make_schedule_tool]
    modify_tools = [modify_schedule_tool]
    travel_tools = [recommend_travel_tool]
    chat_tools = []

    # 3. agent에 전달할 전체 tool 리스트
    all_tools = (
        weather_tools
        + place_tools
        + schedule_tools
        + modify_tools
        + travel_tools
        + chat_tools
    )

    # 4. intent 기반 tool 선택을 위한 middleware
    intent_middleware = IntentRoutingMiddleware(
        weather_tools=weather_tools,
        place_tools=place_tools,
        schedule_tools=schedule_tools,
        modify_tools=modify_tools,
        travel_tools=travel_tools,
        chat_tools=chat_tools,
        enable_tool_filtering=True,
        debug=True,
    )

    # 5. 최종 agent 생성
    agent = create_agent(
        model=model,
        tools=all_tools,
        middleware=[intent_middleware],
        state_schema=TravelAgentState,
    )

    return agent


# test_app.py에서 바로 import 가능하도록 전역 agent도 함께 제공
agent = build_agent()