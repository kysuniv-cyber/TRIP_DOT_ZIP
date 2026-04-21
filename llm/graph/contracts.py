

class StateKeys:
    """
    State에서 공통으로 사용하는 Key들을 정의합니다.
    모든 노드는 이 상수를 참조하여 데이터를 읽고 써야 합니다.
    """
    # 기본 대화 / 라우팅 관련
    MESSAGES = "messages"
    INTENT = "intent"
    CONFIDENCE = "confidence"
    ROUTE = "route"
    FINAL_RESPONSE = "final_response"

    # 장소 검색 영역
    DESTINATION = "destination"
    STYLES = "styles"
    CONSTRAINTS = "constraints"
    MAPPED_PLACES = "mapped_places"
    SELECTED_PLACES = "selected_places"     # 사용자가 최종 선택한 장소 목록

    # 일정/날씨 영역
    ITINERARY = "itinerary"
    WEATHER_DATA = "weather_data"
    TRAVEL_DATES = "travel_dates"

    # 대화형 흐름 확장용
    NEED_WEATHER = "need_weather"           # 날씨 조회 필요 여부
    START_TIME = "start_time"               # 일정 시작 시간
    MISSING_SLOTS = "missing_slots"         # 아직 비어 있는 필수 정보 목록
