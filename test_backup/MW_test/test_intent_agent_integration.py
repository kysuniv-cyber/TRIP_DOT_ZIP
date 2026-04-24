from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

from middlewares.intent_mw import IntentRoutingMiddleware
from test_backup.schemas.agent_state import TravelAgentState

from config import Settings

settings = Settings()
api_key = settings.openai_api_key



@tool
def get_weather(query: str) -> str:
    """날씨 조회 도구"""
    return f"날씨 조회됨: {query}"


@tool
def search_places(query: str) -> str:
    """장소 검색 도구"""
    return f"장소 검색됨: {query}"


def test_agent_with_intent_middleware():
    model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

    middleware = IntentRoutingMiddleware(
        weather_tools=[get_weather],
        place_tools=[search_places],
        debug=True,
    )

    agent = create_agent(
        model=model,
        tools=[get_weather, search_places],
        middleware=[middleware],
        state_schema=TravelAgentState,
    )

    result = agent.invoke({
        "messages": [("user", "부산 날씨 알려줘")]
    })

    assert result is not None