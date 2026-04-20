from typing import Annotated, List, Dict, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

# 의도 타입 (intent_service.py 기준)
IntentType = Literal[
    "general_chat", "travel_recommendation", "place_search",
    "schedule_generation", "weather_query", "modify_request"
]


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

    # 3. 서비스 데이터 (각 함수 결과 저장용)
    # place_search_tool의 리턴값: mapped_places 데이터 저장
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