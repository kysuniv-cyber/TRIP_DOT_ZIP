class StateKeys:
    """
    State에서 공통으로 사용하는 키 상수 모음.
    노드 간 데이터 전달 시 문자열 하드코딩 대신 이 값을 사용한다.
    """

    # 기본 대화/라우팅
    MESSAGES = "messages"
    INTENT = "intent"
    CONFIDENCE = "confidence"
    ROUTE = "route"
    FINAL_RESPONSE = "final_response"

    # 장소 검색
    DESTINATION = "destination"
    STYLES = "styles"
    CONSTRAINTS = "constraints"
    MAPPED_PLACES = "mapped_places"
    SELECTED_PLACES = "selected_places"

    # 일정/날씨
    ITINERARY = "itinerary"
    WEATHER_DATA = "weather_data"

    # 여행 날짜
    TRAVEL_DATE = "travel_date"
    RELATIVE_DAYS = "relative_days"
    RAW_DATE_TEXT = "raw_date_text"

    # 흐름 제어
    NEED_WEATHER = "need_weather"
    START_TIME = "start_time"
    MISSING_SLOTS = "missing_slots"
    STATE_TYPE_CD = "state_type_cd"

    # 안전 차단
    BLOCKED = "blocked"
    BLOCK_REASON = "blocked_reason"

    # 대화 요약
    CONVERSATION_SUMMARY = "conversation_summary"
    CONVERSATION_SUMMARIZED = "conversation_summarized"
