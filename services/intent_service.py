import re
from typing import TypedDict, Literal

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


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def classify_intent_by_rule(user_text: str) -> IntentResult:
    text = user_text.strip().lower()

    if not text:
        return {
            "intent": "general_chat",
            "confidence": 0.0,
            "route": "chat",
            "reason": "빈 입력",
        }

    weather_keywords = [
        "날씨", "비", "기온", "온도", "맑", "흐림", "눈", "우산", "더워", "추워",
        "weather", "temperature", "rain"
    ]

    schedule_keywords = [
        "일정", "코스", "플랜", "루트", "짜줘", "계획", "여행 일정",
        "당일치기", "1박", "2박", "3박", "4박", "5박"
    ]

    place_keywords = [
        "장소", "명소", "관광지", "맛집", "카페", "어디 가", "어디갈", "볼거리",
        "놀거리", "가볼만", "추천 장소", "핫플"
    ]

    modify_keywords = [
        "수정", "변경", "다시", "바꿔", "말고", "재추천", "다른 걸로",
        "그거 말고", "일정 바꿔", "고쳐줘"
    ]

    travel_keywords = [
        "여행", "여행 추천", "여행지 추천", "국내 여행", "해외 여행",
        "여행 갈만한 곳", "놀러 갈 곳", "추천해줘", "여행 어디",
        "가려고", "가려", "갈거", "가고싶", "가고 싶", "놀러"
    ]

    duration_keywords = [
        "부터", "까지",
        "월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일",
        "이번주", "다음주", "다다음주",
        "오늘", "내일", "모레"
    ]

    city_keywords = [
        "서울", "부산", "전주", "제주", "강릉", "속초", "경주", "여수",
        "대구", "대전", "광주", "인천", "울산", "수원", "춘천", "포항", "목포"
    ]

    greeting_patterns = [
        r"^안녕+$",
        r"^하이+$",
        r"^ㅎㅇ+$",
        r"^반가워+$",
        r"^고마워+$",
        r"^thanks+$",
        r"^hello+$",
    ]

    # 1. 수정 요청 우선
    if _contains_any(text, modify_keywords):
        return {
            "intent": "modify_request",
            "confidence": 0.94,
            "route": "modify",
            "reason": "수정/변경 요청 키워드 감지",
        }

    # 2. 기간 + 여행/도시 → 일정 생성
    if ("부터" in text and "까지" in text) and (
        _contains_any(text, travel_keywords) or _contains_any(text, city_keywords)
    ):
        return {
            "intent": "schedule_generation",
            "confidence": 0.95,
            "route": "schedule",
            "reason": "기간이 포함된 여행 요청 감지",
        }

    # 3. 여행/도시 + 요일/주차 표현 → 일정 생성
    if (
        (_contains_any(text, travel_keywords) or _contains_any(text, city_keywords))
        and _contains_any(text, duration_keywords)
    ):
        return {
            "intent": "schedule_generation",
            "confidence": 0.93,
            "route": "schedule",
            "reason": "여행지 + 날짜/요일 표현 감지",
        }

    # 4. 날씨
    if _contains_any(text, weather_keywords):
        return {
            "intent": "weather_query",
            "confidence": 0.95,
            "route": "weather",
            "reason": "날씨 관련 키워드 감지",
        }

    # 5. 일정 명시 키워드
    if _contains_any(text, schedule_keywords):
        return {
            "intent": "schedule_generation",
            "confidence": 0.93,
            "route": "schedule",
            "reason": "일정 생성 관련 키워드 감지",
        }

    # 6. 장소 검색
    if _contains_any(text, place_keywords):
        return {
            "intent": "place_search",
            "confidence": 0.90,
            "route": "place",
            "reason": "장소 검색 관련 키워드 감지",
        }

    # 7. 일반 여행 추천
    if _contains_any(text, travel_keywords):
        return {
            "intent": "travel_recommendation",
            "confidence": 0.89,
            "route": "travel",
            "reason": "여행 추천 관련 키워드 감지",
        }

    for pattern in greeting_patterns:
        if re.fullmatch(pattern, text):
            return {
                "intent": "general_chat",
                "confidence": 0.98,
                "route": "chat",
                "reason": "인사/일반 대화 패턴 감지",
            }

    return {
        "intent": "general_chat",
        "confidence": 0.65,
        "route": "chat",
        "reason": "명확한 여행 의도가 없어 일반 대화로 분류",
    }