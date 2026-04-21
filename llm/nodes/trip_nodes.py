import re
from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys


# -----------------------------
# 내부 헬퍼: 지역 후보 추출
# -----------------------------
def _extract_destination(user_text: str) -> str | None:
    """
    사용자 입력에서 여행 목적지(지역명)를 단순 규칙 기반으로 추출합니다.

    현재는 자주 등장하는 지역명을 우선 탐지하는 방식으로 구현하며,
    추후 NER 또는 LLM 기반 추출로 확장할 수 있습니다.
    """
    known_destinations = [
        "서울", "부산", "인천", "대구", "대전", "광주", "울산",
        "수원", "제주", "제주도", "경주", "전주", "여수", "강릉",
        "속초", "춘천", "포항", "창원", "성수", "홍대", "잠실",
    ]

    for place in known_destinations:
        if place in user_text:
            return place

    return None


# -----------------------------
# 내부 헬퍼: 스타일 후보 추출
# -----------------------------
def _extract_styles(user_text: str) -> list[str]:
    """
    사용자 입력에서 여행 스타일/카테고리 키워드를 추출합니다.

    예:
    - 맛집
    - 카페
    - 전시
    - 쇼핑
    - 야경
    """
    style_keywords = {
        "맛집": ["맛집", "먹거리", "식당", "밥집", "음식점"],
        "카페": ["카페", "디저트", "베이커리"],
        "전시": ["전시", "미술관", "박물관", "갤러리"],
        "쇼핑": ["쇼핑", "편집샵", "백화점", "쇼룸"],
        "야경": ["야경", "밤거리", "야간"],
        "산책": ["산책", "걷기", "공원"],
        "데이트": ["데이트", "분위기 좋은"],
        "관광": ["관광", "명소", "핫플"],
    }

    found_styles = []

    for canonical, keywords in style_keywords.items():
        if any(keyword in user_text for keyword in keywords):
            found_styles.append(canonical)

    return found_styles


# -----------------------------
# 내부 헬퍼: 제약사항 추출
# -----------------------------
def _extract_constraints(user_text: str) -> list[str]:
    """
    사용자 입력에서 제약사항을 추출합니다.

    예:
    - 실내 위주
    - 비 오면 실내
    - 반려동물 동반
    - 조용한 곳
    """
    constraint_keywords = {
        "indoor": ["실내", "비 오면 실내", "실내 위주"],
        "outdoor": ["야외", "실외", "실외 위주"],
        "pet": ["반려동물", "애견동반", "강아지"],
        "quiet": ["조용한", "한적한", "시끄럽지 않은"],
        "budget": ["가성비", "저렴한", "비싸지 않은"],
    }

    found_constraints = []

    for canonical, keywords in constraint_keywords.items():
        if any(keyword in user_text for keyword in keywords):
            found_constraints.append(canonical)

    return found_constraints


# -----------------------------
# 내부 헬퍼: 여행 날짜 추출
# -----------------------------
def _extract_travel_date(user_text: str) -> str | None:
    """
    사용자 입력에서 YYYY-MM-DD 형식 날짜를 단순 추출합니다.
    :param user_text:
    :return:
    """



# -----------------------------
# 내부 헬퍼: 일정 시작 시간 추출
# -----------------------------
def _extract_start_time(user_text: str) -> str | None:
    """
    사용자 입력에서 일정 시작 시간을 추출합니다.

    지원 예시:
    - 오전 10시
    - 오후 2시
    - 10시부터
    - 10:30부터
    - 오전 10시부터 시작
    """
    text = user_text.strip()

    # 1) 오전/오후 + 시(:분) 패턴
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

    # 2) 24시간 형식 10:30
    match_hm = re.search(r"(\d{1,2}):(\d{2})", text)
    if match_hm:
        hour = int(match_hm.group(1))
        minute = int(match_hm.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"

    # 3) 단순 '10시'
    match_hour = re.search(r"(\d{1,2})\s*시", text)
    if match_hour:
        hour = int(match_hour.group(1))
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"

    return None


# -----------------------------
# 메인 노드 1: 여행 조건 추출
# -----------------------------
def extract_trip_requirements_node(state: TravelAgentState) -> dict:
    """
    사용자 입력에서 여행 조건을 추출하여 State에 반영하는 노드입니다.

    현재 추출 대상:
    - destination
    - styles
    - constraints
    - start_time (선택값)

    주의:
    - start_time은 필수가 아니므로, 없으면 반환하지 않습니다.
    - scheduler 쪽 기본값(09:00)을 그대로 활용합니다.
    """
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        return {}

    last_msg = messages[-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

    destination = _extract_destination(user_text)
    styles = _extract_styles(user_text)
    constraints = _extract_constraints(user_text)
    start_time = _extract_start_time(user_text)

    updates = {}

    # 추출된 값만 state에 반영
    if destination:
        updates[StateKeys.DESTINATION] = destination

    if styles:
        updates[StateKeys.STYLES] = styles

    if constraints:
        updates[StateKeys.CONSTRAINTS] = constraints

    # start_time은 선택값
    if start_time:
        updates[StateKeys.START_TIME] = start_time

    print("[DEBUG] destination =", destination)
    print("[DEBUG] styles =", styles)
    print("[DEBUG] constraints =", constraints)
    print("[DEBUG] start_time =", start_time)
    print("[DEBUG] updates =", updates)

    return updates


# -----------------------------
# 메인 노드 2: 부족한 정보 확인
# -----------------------------
def check_missing_info_node(state: TravelAgentState) -> dict:
    """
    일정 생성/장소 검색에 필요한 정보 중 비어 있는 값을 확인합니다.

    현재 1차 버전에서는 destination만 필수로 간주합니다.
    이유:
    - destination이 없으면 place search가 어렵습니다.
    - start_time은 없어도 scheduler 기본값(09:00) 사용 가능
    - styles / constraints는 없어도 기본 추천 가능
    """
    missing_slots = []

    destination = state.get(StateKeys.DESTINATION)
    if not destination:
        missing_slots.append(StateKeys.DESTINATION)

    print("[DEBUG] check_missing_info_node missing_slots =", missing_slots)

    return {StateKeys.MISSING_SLOTS: missing_slots}


# -----------------------------
# 메인 노드 3: 부족 정보 질문 생성
# -----------------------------
def ask_user_for_missing_info_node(state: TravelAgentState) -> dict:
    """
    부족한 정보가 있을 때 사용자에게 다시 질문할 문장을 생성합니다.

    현재 1차 버전에서는 destination만 필수로 간주합니다.
    """
    destination = state.get(StateKeys.DESTINATION)

    if not destination:
        return {StateKeys.FINAL_RESPONSE: "어느 지역으로 여행 일정을 짜드릴까요?"}

    return {}


# -----------------------------
# 메인 노드 4: 사용자가 선택한 장소 저장
# -----------------------------
def select_places_node(state: TravelAgentState) -> dict:
    """
    장소 후보(mapped_places) 중 실제 일정 생성에 사용할 selected_places를 결정하는 노드입니다.

    현재 1차 버전:
    - 사용자가 이미 selected_places를 골라둔 경우: 그 값을 그대로 사용
    - 아직 고르지 않은 경우: mapped_places 상위 3개를 임시 선택

    추후 확장:
    - 사용자 응답에서 place_id / 장소명 기반 선택 반영
    - 카테고리 다양성 고려
    - 필수 카테고리(카페/맛집 등) 균형 선택
    """
    # 이미 사용자 선택 결과가 있으면 그대로 사용
    existing_selected = state.get(StateKeys.SELECTED_PLACES, [])
    if existing_selected:
        return {StateKeys.SELECTED_PLACES: existing_selected}

    mapped_places = state.get(StateKeys.MAPPED_PLACES, [])
    if not mapped_places:
        return {StateKeys.SELECTED_PLACES: []}

    # 1차 버전: 상위 3개만 임시 선택
    selected_places = mapped_places[:3]

    print("[DEBUG] selected_places =", selected_places)

    return {StateKeys.SELECTED_PLACES: selected_places}