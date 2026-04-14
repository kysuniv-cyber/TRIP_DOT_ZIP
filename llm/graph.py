from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from llm.prompts import SYSTEM_PROMPT
from mock_tools.weather_tools import get_weather
from mock_tools.place_tools import search_places
from mock_tools.schedule_tools import build_schedule


def build_trip_agent():
    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0
    )

    tools = [
        get_weather,
        search_places,
        build_schedule,
    ]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent