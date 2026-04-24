import logging
from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys  # 규약 임포트
from services.intent_service import classify_intent_by_rule

logger = logging.getLogger(__name__)


def route_intent_node(state: TravelAgentState) -> dict:
    """
    사용자의 입력으로부터 의도를 분류하고
    State의 route를 결정하는 첫 번째 노드
    """
    # 1. 메시지 추출 및 안전한 텍스트 획득
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        logger.warning("messages가 비어 있어 기본값으로 general_chat/chat 반환")
        return {
            StateKeys.INTENT: "general_chat",
            StateKeys.CONFIDENCE: 0.0,
            StateKeys.ROUTE: "chat",
        }

    last_msg = messages[-1]

    # 메시지 객체일 경우 .content, 딕셔너리일 경우 get("content") 사용
    user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

    # 2. 의도 분석 실행
    intent_result = classify_intent_by_rule(user_text)

    # 3. 규약된 키값으로 결과 반환
    return {
        StateKeys.INTENT: intent_result["intent"],
        StateKeys.CONFIDENCE: intent_result.get("confidence", 0.0),
        StateKeys.ROUTE: intent_result["route"],
    }

#====================[내용 추가]================================

# 1. 사용자 정의 타입 반영
IntentType = Literal[
    "general_chat",
    "travel_recommendation",
    "place_search",
    "schedule_generation",
    "weather_query",
    "modify_request",
]

class IntentResult(TypedDict):
    intent: IntentType
    confidence: float
    route: str
    reason: str

# 2. LLM 구조화 출력용 Pydantic 모델
class IntentAnalysis(BaseModel):
    intent: IntentType = Field(description="사용자의 의도 분류")
    confidence: float = Field(description="분류 확신도 (0.0~1.0)")
    reason: str = Field(description="분류 근거")

class intent_node():

    def __init__(self, llm: ChatOpenAI):
        # 2. 프롬프트 설계: 시스템 메시지에 역할을 부여하고 대화 기록(MessagesPlaceholder)을 넣습니다.
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
                당신은 여행 에이전트의 의도 분류기입니다. 
                사용자의 입력과 이전 대화 맥락을 분석하여 의도를 정확히 분류하세요.
                [분류 가이드]
                1. '응', '그래', '좋아', '그렇게 해' 등의 긍정 답변:
                - 이전 시스템 메시지가 정보 수정이나 제안에 대한 확인이었다면 -> 'modify_request'
                - 새로운 여행지 추천에 대한 수락이었다면 -> 'travel_recommendation'
                2. '아니', '그거 말고', '딴거':
                - 기존 계획을 바꾸려는 의도이므로 -> 'modify_request'
                3. 특정 지역이나 '맛집', '명소' 언급:
                - 단순 정보 검색이면 -> 'place_search'
                - 전체적인 여행지 추천을 원하면 -> 'travel_recommendation'
                4. 날짜, 기간, '일정 짜줘' 언급 -> 'schedule_generation'
                5. 날씨 관련 언급 -> 'weather_query'"""),
                MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # 3. 구조화된 출력을 사용하는 체인 생성
        self.chain = self.prompt | llm.with_structured_output(IntentAnalysis)

    def __call__(self, state: TravelAgentState) -> dict:
        print(f'[DEBUG] intent_node __call__: {state}')
        
        # 1. 메시지 추출 및 안전한 텍스트 획득
        messages = state.get(StateKeys.MESSAGES, [])
        if not messages:
            logger.warning("messages가 비어 있어 기본값으로 general_chat/chat 반환")
            return {
                StateKeys.INTENT: "general_chat",
                StateKeys.CONFIDENCE: 0.0,
                StateKeys.ROUTE: "chat",
            }

        last_msg = messages[-1]

        # 메시지 객체일 경우 .content, 딕셔너리일 경우 get("content") 사용
        user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

        # 2. 의도 분석 실행
        # 
        # intent_result = classify_intent_by_rule(user_text)

        # if intent_result == "general_chat":
        intent_result = classify_intent_by_rule(user_text)
        if intent_result.get("confidence", 0.0) >= 0.9:
            return {
                StateKeys.INTENT: intent_result["intent"],
                StateKeys.CONFIDENCE: intent_result.get("confidence", 0.0),
                StateKeys.ROUTE: intent_result["route"],
            }

        logger.info("[LLM Path] Invoking OpenAI for intent analysis...")
        print("[DEBUG] Invoking OpenAI for intent analysis...")
        llm_result = self.chain.invoke({
            "history": messages[:-1],
            "input": user_text
        })

        # Route 매핑 테이블
        route_map = {
            "modify_request": "modify",
            "weather_query": "weather",
            "schedule_generation": "schedule",
            "place_search": "place",
            "travel_recommendation": "travel",
            "general_chat": "chat"
        }

        return {
            StateKeys.INTENT: llm_result.intent,
            StateKeys.CONFIDENCE: llm_result.confidence,
            StateKeys.ROUTE: route_map.get(llm_result.intent, "chat"),
        }

        # 3. 규약된 키값으로 결과 반환
        # return {
        #     StateKeys.INTENT: intent_result["intent"],
        #     StateKeys.CONFIDENCE: intent_result.get("confidence", 0.0),
        #     StateKeys.ROUTE: intent_result["route"],
        # }       
