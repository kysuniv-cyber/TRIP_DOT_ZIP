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
           
                [핵심 규칙: 대화 맥락 활용]
                - 사용자의 입력이 '응', '그래', '좋아', '알려줘'와 같은 단답형 긍정인 경우, 반드시 직전 시스템(AI) 메시지의 질문 내용을 확인하십시오.
                - AI가 "XX 정보가 필요하신가요?"라고 물었고 사용자가 "응"이라고 했다면, 사용자의 의도는 "XX 정보를 제공해달라"는 것입니다.
                - 사용자가 "XX도 하고 싶어", "XX 추가해줘", "XX 대신 OO"라고 말하는 경우:
                  - 이는 기존 일정을 유지하면서 특정 장소를 변경/추가하려는 의도입니다.
                  - 반드시 'modify_request'로 분류하고 route를 'travel'로 설정하십시오.
                - 'general_chat'은 인사나 감사 인사처럼 여행 계획과 무관한 경우에만 사용하십시오.
                - Scope: You are only authorized to plan activities for a single day.
                - Prohibited Topics: Never mention, recommend, or ask about:
                  1. Accommodations (Hotels, Airbnb, etc.)
                  2. Long-term stay duration (e.g., "How many days are you staying?")
                  3. Long-distance transportation (Flights, Intercity trains, etc.)
                - If a user asks about prohibited topics, politely state: "저는 당일치기 일정 전문이라 숙소나 교통 정보는 잘 몰라요! 대신 해운대에서의 멋진 하루를 계획해 드릴게요."

            
                [의도 분류 가이드]
                1. travel_recommendation (추천 및 정보 제공):
                   - 새로운 여행지, 맛집, 명소 추천을 원할 때
                   - AI의 정보 제공 제안(예: "서핑 강습 정보 드릴까요?")에 "응"이라고 답했을 때
                   - 특정 스타일(서핑, 카페 등)을 언급하며 추천을 요청할 때
                
                2. schedule_generation (일정 생성):
                   - "일정 짜줘", "표로 만들어줘", "스케줄 생성해" 등 시간 순서대로의 계획을 원할 때
                   - 기존에 뽑힌 장소들을 가지고 "이걸로 일정 확정해줘"라고 할 때
            
                3. modify_request (수정 요청):
                   - "아니", "그거 말고 다른거", "XX는 빼줘" 등 기존 계획의 변경을 원할 때
                   - "장소 하나만 바꿔줘" 등 부분적인 수정을 요청할 때
            
                4. weather_query (날씨):
                   - "내일 날씨 어때?", "비 와?" 등 기상 정보 언급 시
            
                5. general_chat (일반 대화):
                   - "고마워", "안녕", "너는 누구니?" 등 여행 계획과 직접 상관없는 대화
            
                [출력 규칙]
                - 반드시 지정된 의도 키워드 중 하나만 출력하십시오.
                - 사용자가 "응"이라고 했을 때, AI의 직전 질문이 '정보 제공'에 관한 것이었다면 route를 반드시 'travel'로 유도해야 합니다."""),
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
