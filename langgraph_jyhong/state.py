"""
    FileName: state.py
    Location: langgraph_jyhong/state.py
    Role: TempTravelAgentState
        여행 계획을 세우는 과정에서 필요한 정보를 담는 State 객체.
        단, 공유하기 전이므로 임시 상태.
""" 
from typing import Annotated, List, TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
import operator

class QualityCheck(TypedDict):  
    # TypedDict로 정의했으나 BaseModel로 변경예정.(26.04.20)
    """ 일정의 품질 검사 결과를 담는 구조체 """
    is_passed: bool     # 품질 검사 통과 여부
    issues: List[str]   # 발견된 문제(LLM에게 전달할 문제점, TODO: 리스트처리는 고민해볼 것.)
    target_node: str    # 돌아갈 노드(이건 flow상 단수처리) 이 분기처리는 어디서..?


class TempTravelAgentState(TypedDict):
    # TypedDict로 정의했으나 BaseModel로 변경예정(26.04.20)
    """ 여행 계획을 세우는 과정에서 필요한 정보를 담는 State 객체.
        단, 아직 temp로 테스트를 위해서 수립
        - 주요 구조
            1. 메시지 데이터
            2. place search tool에서 필요한 정보
            3. API에서 가지고 온 데이터
            4. 상태값
            5. 검증여부
        """
    # 사용자의 메시지 히스토리 
    messages: Annotated[List[str], operator.add]    # 내용 적재
    # middleware에서 넘어온 요약 데이터
    summary: str
    # TODO: 내용을 잘 몰라서 list로 일단 둠. 내용 확인 후 수정. => str로 확인.

    # PlaceSearchTool의 PlaceSearchInfo의 명을 가져옴.
    destination: str        # 목적지
    styles: List[str]       # 사용자가 선호하는 여행 스타일(예: 맛집, 카페, 명소 등)
    constraints: List[str]  # 제약사항 (날씨 등등) -> 날씨가 메인이었으나 제외 필요.

    # API에서 가지고 온 데이터구글 Place API에서 가져온 장소 정보
    raw_places: list       # 구글 API에서 가져온 가공 전 데이터
    weather_info: str      # 날씨 정보
    vector_db_path: str    # 벡터 DB 저장 경로
    final_answer: str      # 사용자에게 줄 최종 답변

    # 상태값
    state_type_cd: str = "01"   # 여행 계획의 단계코드
    # 01: 초기 | 02: 장소 검색 완료 | 03: 일정 생성 완료 | 04: 품질 검사 완료 | 05: 최종 답변 생성 완료
    # TODO: 단계코드 순서 다시 확인.
    
    # 검증여부
    quality_check: QualityCheck
