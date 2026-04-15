from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from llm.prompts import SYSTEM_PROMPT
from llm.tools import TOOLS

from openai import OpenAI
from config import Settings


def build_trip_agent():
    llm = init_chat_model(
        model="gpt-4.1-mini",
        temperature=0
    )

    agent = create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent

def get_openai_clients(settings: Settings | None = None) -> OpenAI:
    s = settings or Settings()
    return OpenAI(api_key=s.openai_api_key)