import re

from llm.graph.contracts import StateKeys
from llm.graph.state import TravelAgentState


def _extract_destination(user_text: str) -> str | None:
    known_destinations = [
        "서울", "부산", "인천", "대구", "대전", "광주", "울산",
        "수원", "제주", "제주도", "경주", "전주", "여수", "강릉",
        "속초", "춘천", "포항", "창원", "성수", "남해", "울릉도",
    ]

    # 1. 시/도 단위 먼저 체크
    for place in known_destinations:
        if place in user_text:
            return place

    # 2. 해운대, 광안리 등 특정 지역 키워드가 들어왔을 때 상위 도시로 매핑하는 로직
    sub_locations = {
        "해운대": "부산",
        "광안리": "부산",
        "서면": "부산",
        "명동": "서울",
        "강남": "서울"
    }
    for sub, main in sub_locations.items():
        if sub in user_text:
            return main

    return None


def _extract_styles(user_text: str) -> list[str]:
    style_keywords = {
        "맛집": ["맛집", "먹거리", "식당", "밥집", "한식", "양식", "일식"],
        "카페": ["카페", "커피", "베이커리", "디저트"],
        "전시": ["전시", "미술관", "박물관", "갤러리"],
        "쇼핑": ["쇼핑", "편집샵", "백화점", "아울렛"],
        "풍경": ["풍경", "바닷가", "야경", "뷰"],
        "산책": ["산책", "걷기", "공원"],
        "데이트": ["데이트", "분위기 좋은"],
        "관광": ["관광", "명소", "핫플", "여행지"],
        "액티비티": ["액티비티", "체험", "놀거리"],
    }

    found_styles: list[str] = []
    for canonical, keywords in style_keywords.items():
        if any(keyword in user_text for keyword in keywords):
            found_styles.append(canonical)
    return found_styles


def _extract_constraints(user_text: str) -> list[str]:
    constraint_keywords = {
        "indoor": ["실내", "비오면 실내", "실내 위주"],
        "outdoor": ["야외", "실외", "야외 위주"],
        "pet": ["반려동물", "반려견 동반", "강아지"],
        "quiet": ["조용한", "한적한", "시끄럽지 않은"],
        "budget": ["가성비", "저렴한", "비싸지 않은"],
        "solo": ["혼자", "혼자 갈", "혼자갈", "혼행"],
        "couple": ["커플", "연인", "데이트"],
        "family": ["가족", "가족여행"],
        "parents": ["부모님", "부모님과", "모시고"],
        "kids": ["아이", "아이와", "아이 동반", "아기"],
        "1박2일": ["1박2일", "1박 2일"],
        "2박3일": ["2박3일", "2박 3일"],
    }

    found_constraints: list[str] = []
    for canonical, keywords in constraint_keywords.items():
        if any(keyword in user_text for keyword in keywords):
            found_constraints.append(canonical)
    return found_constraints


def _extract_date_fields(user_text: str) -> dict:
    result = {
        "travel_date": None,
        "relative_days": None,
        "raw_date_text": None,
    }

    match_date = re.search(r"(20\d{2}-\d{2}-\d{2})", user_text)
    if match_date:
        result["travel_date"] = match_date.group(1)
        return result

    match_month_day = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", user_text)
    if match_month_day:
        month = int(match_month_day.group(1))
        day = int(match_month_day.group(2))
        result["travel_date"] = f"2026-{month:02d}-{day:02d}"
        return result

    if "오늘" in user_text:
        result["raw_date_text"] = "오늘"
        return result
    if "내일" in user_text:
        result["raw_date_text"] = "내일"
        return result
    if "모레" in user_text:
        result["raw_date_text"] = "모레"
        return result
    if "다음 주 토요일" in user_text or "다음주 토요일" in user_text:
        result["raw_date_text"] = "다음주토요일"
        return result
    if "이번 주 토요일" in user_text or "이번주 토요일" in user_text:
        result["raw_date_text"] = "이번주토요일"
        return result

    match_relative = re.search(r"(\d+)\s*(일 뒤|일후|일 후)", user_text)
    if match_relative:
        result["relative_days"] = int(match_relative.group(1))
        return result

    return result


def _extract_start_time(user_text: str) -> str | None:
    text = user_text.strip()

    match_ampm = re.search(r"(오전|오후)\s*(\d{1,2})(?::(\d{2}))?\s*시", text)
    if match_ampm:
        ampm = match_ampm.group(1)
        hour = int(match_ampm.group(2))
        minute = int(match_ampm.group(3)) if match_ampm.group(3) else 0

        if ampm == "오후" and hour < 12:
            hour += 12
        elif ampm == "오전" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    match_hm = re.search(r"(\d{1,2}):(\d{2})", text)
    if match_hm:
        hour = int(match_hm.group(1))
        minute = int(match_hm.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"

    match_hour = re.search(r"(\d{1,2})\s*시", text)
    if match_hour:
        hour = int(match_hour.group(1))
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"

    return None


def extract_trip_requirements_node(state: TravelAgentState) -> dict:
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        return {}

    last_msg = messages[-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

    destination = _extract_destination(user_text)
    styles = _extract_styles(user_text)
    constraints = _extract_constraints(user_text)
    date_info = _extract_date_fields(user_text)
    start_time = _extract_start_time(user_text)

    updates = {}

    if destination:
        updates[StateKeys.DESTINATION] = destination
    if styles:
        updates[StateKeys.STYLES] = styles
    if constraints:
        updates[StateKeys.CONSTRAINTS] = constraints
    if date_info.get("travel_date"):
        updates[StateKeys.TRAVEL_DATE] = date_info.get("travel_date")
    if date_info.get("relative_days") is not None:
        updates[StateKeys.RELATIVE_DAYS] = date_info.get("relative_days")
    if date_info.get("raw_date_text"):
        updates[StateKeys.RAW_DATE_TEXT] = date_info.get("raw_date_text")
    if start_time:
        updates[StateKeys.START_TIME] = start_time

    print("[DEBUG] destination =", destination)
    print("[DEBUG] styles =", styles)
    print("[DEBUG] constraints =", constraints)
    print("[DEBUG] start_time =", start_time)
    print("[DEBUG] updates =", updates)

    return updates


def check_missing_info_node(state: TravelAgentState) -> dict:
    missing_slots = []

    destination = state.get(StateKeys.DESTINATION)
    if not destination:
        missing_slots.append(StateKeys.DESTINATION)

    print("[DEBUG] check_missing_info_node missing_slots =", missing_slots)

    return {StateKeys.MISSING_SLOTS: missing_slots}


def ask_user_for_missing_info_node(state: TravelAgentState) -> dict:
    destination = state.get(StateKeys.DESTINATION)

    if not destination:
        return {StateKeys.FINAL_RESPONSE: "어느 지역으로 여행 일정을 짜드릴까요?"}

    return {}


def modify_trip_requirements_node(state: TravelAgentState) -> dict:
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        return {}

    last_msg = messages[-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

    updates = {}
    current_styles = list(state.get(StateKeys.STYLES, []))

    parse_text = user_text
    if "말고" in user_text:
        parse_text = user_text.split("말고", 1)[1].strip()

    if "카페 말고" in user_text and "맛집" in user_text:
        updates[StateKeys.STYLES] = ["맛집"]
    elif "맛집 말고" in user_text and "카페" in user_text:
        updates[StateKeys.STYLES] = ["카페"]
    else:
        extracted_styles = _extract_styles(parse_text)
        if extracted_styles:
            updates[StateKeys.STYLES] = extracted_styles
        else:
            updates[StateKeys.STYLES] = current_styles

    date_info = _extract_date_fields(parse_text)

    if date_info.get("travel_date"):
        updates[StateKeys.TRAVEL_DATE] = date_info.get("travel_date")
        updates[StateKeys.RAW_DATE_TEXT] = None
        updates[StateKeys.RELATIVE_DAYS] = None
    elif date_info.get("relative_days") is not None:
        updates[StateKeys.RELATIVE_DAYS] = date_info.get("relative_days")
        updates[StateKeys.TRAVEL_DATE] = None
        updates[StateKeys.RAW_DATE_TEXT] = None
    elif date_info.get("raw_date_text"):
        updates[StateKeys.RAW_DATE_TEXT] = date_info.get("raw_date_text")
        updates[StateKeys.TRAVEL_DATE] = None
        updates[StateKeys.RELATIVE_DAYS] = None

    updates[StateKeys.MAPPED_PLACES] = []
    updates[StateKeys.SELECTED_PLACES] = []
    updates[StateKeys.ITINERARY] = []

    print("[DEBUG] modify updates =", updates)

    return updates


def select_places_node(state: TravelAgentState) -> dict:
    existing_selected = state.get(StateKeys.SELECTED_PLACES, [])
    if existing_selected:
        return {StateKeys.SELECTED_PLACES: existing_selected}

    mapped_places = state.get(StateKeys.MAPPED_PLACES, [])
    if not mapped_places:
        return {StateKeys.SELECTED_PLACES: []}

    selected_places = mapped_places[:3]
    print("[DEBUG] selected_places =", selected_places)
    return {StateKeys.SELECTED_PLACES: selected_places}
