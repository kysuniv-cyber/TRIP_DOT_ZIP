"""
agent_builder.py

새 LangGraph 기반 app을 반환하는 모듈이다.
기존 create_agent() 방식 대신, llm.graph.builder에서 컴파일된 graph app을 사용한다.
"""

from typing import Any
from llm.graph.builder import app


def build_agent() -> Any:
    """
    컴파일된 LangGraph app을 반환한다.
    """
    return app


# test_app.py 등에서 바로 import 가능하도록 전역 agent 제공
agent = build_agent()