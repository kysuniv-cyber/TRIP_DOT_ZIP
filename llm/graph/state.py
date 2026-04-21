from typing import Annotated, List, Dict, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

# 의도 타입 (intent_service.py 기준)
IntentType = Literal[
    "general_chat", "travel_recommendation", "place_search",
    "schedule_generation", "weather_query", "modify_request"
]

# validate_node의 결과값을 담는 객체
class QualityCheck(TypedDict):  
    # TypedDict로 정의했으나 BaseModel로 변경예정.(26.04.20)
    """ 일정의 품질 검사 결과를 담는 구조체 """
    is_passed: bool     # 품질 검사 통과 여부
    issues: List[str]   # 발견된 문제(LLM에게 전달할 문제점, TODO: 리스트처리는 고민해볼 것.)
    target_node: str    # 돌아갈 노드(이건 flow상 단수처리) 이 분기처리는 어디서..?

class TravelAgentState(TypedDict, total=False):     # 처음부터 모든 값이 채워져 있을 필요 없으므로, total=False를 줬음.
    # 1. 기본 대화 및 의도
    messages: Annotated[list, add_messages]
    intent: IntentType
    confidence: float
    route: str              # 'weather', 'schedule' 등 실제 분기 경로

    # 2. 핵심 검색 파라미터 (place_search_tool.py의 PlaceSearchInfo 참고)
    destination: str        # 검색할 도시 또는 지역명
    styles: List[str]       # 여행 스타일 (맛집, 카페 등)
    constraints: List[str]  # 제약사항 (반려동물, 실내 등)

    # 여행 날짜
    travel_dates: str

    # 3. 서비스 데이터 (각 함수 결과 저장용)
    # LLM이 벡터DB에서 호출한 장소 후보지 목록
    mapped_places: List[Dict]

    # 사용자가 최종 선택한 장소 목록
    selected_places: List[Dict]

    # scheduler_service의 리턴값: itinerary 데이터 저장
    # (order, arrival, departure, place_name, stay_time 포함)
    itinerary: List[Dict]

    # weather_service의 리턴값 저장
    weather_data: Dict

    # 4. 대화형 흐름 제어
    missing_slot: List[str]     # 아직 입력되지 않은 필수 정보
    need_weather: bool          # 날씨 조회 필요 여부

    # 4. 지도 및 응답 제어
    # map_tool.py에서 사용하는 마커 및 센터 정보
    map_metadata: Dict

    final_response: str         # 사용자에게 보여줄 최종 텍스트 응답

    # 5. 상태값
    state_type_cd: str = "01"   # 여행 계획의 단계코드
    # 01: 초기 | 02: 장소 검색 완료 | 03: 일정 생성 완료 | 04: 품질 검사 완료 | 05: 최종 답변 생성 완료
    # TODO: 단계코드 순서 다시 확인.
    
    # 6. 검증여부
    quality_check: QualityCheck