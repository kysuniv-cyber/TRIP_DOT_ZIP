import json
import re
from datetime import date
from typing import Any

from openai import OpenAI

from config import Settings
from llm.graph.contracts import StateKeys
from llm.graph.state import TravelAgentState


client = OpenAI(api_key=Settings.openai_api_key)
LLM_MODEL = "gpt-4.1-mini"
CURRENT_YEAR = date.today().year


STYLE_ALIASES = {
    "맛집": "맛집",
    "식당": "맛집",
    "먹거리": "맛집",
    "카페": "카페",
    "디저트": "카페",
    "전시": "전시",
    "미술관": "전시",
    "박물관": "전시",
    "쇼핑": "쇼핑",
    "풍경": "풍경",
    "뷰": "풍경",
    "산책": "산책",
    "공원": "산책",
    "데이트": "데이트",
    "관광": "관광",
    "명소": "관광",
    "액티비티": "액티비티",
    "체험": "액티비티",
}

CONSTRAINT_ALIASES = {
    "실내": "indoor",
    "실내위주": "indoor",
    "야외": "outdoor",
    "실외": "outdoor",
    "반려동물": "pet",
    "반려견": "pet",
    "조용한": "quiet",
    "한적한": "quiet",
    "가성비": "budget",
    "저렴한": "budget",
    "혼자": "solo",
    "혼행": "solo",
    "커플": "couple",
    "연인": "couple",
    "가족": "family",
    "부모님": "parents",
    "아이": "kids",
    "아기": "kids",
    "유아": "kids",
    "1박2일": "1박2일",
    "2박3일": "2박3일",
}


def _extract_destination(user_text: str) -> str | None:
    known_destinations = [
        "서울", "부산", "인천", "대구", "대전", "광주", "울산",
        "수원", "제주", "제주도", "경주", "전주", "여수", "강릉",
        "속초", "춘천", "포항", "창원", "성수", "동해", "남해",
    ]

    for place in known_destinations:
        if place in user_text:
            return place

    sub_locations = {
        "해운대": "부산",
        "광안리": "부산",
        "서면": "부산",
        "명동": "서울",
        "강남": "서울",
    }
    for sub, main in sub_locations.items():
        if sub in user_text:
            return main

    return None


def _extract_styles(user_text: str) -> list[str]:
    style_keywords = {
        "맛집": ["맛집", "먹거리", "식당", "밥집", "한식", "중식", "일식"],
        "카페": ["카페", "커피", "베이커리", "디저트"],
        "전시": ["전시", "미술관", "박물관", "갤러리"],
        "쇼핑": ["쇼핑", "편집샵", "백화점", "아울렛"],
        "풍경": ["풍경", "바다", "야경", "뷰"],
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
        "solo": ["혼자", "혼자 가기", "혼자여행", "혼행"],
        "couple": ["커플", "연인", "데이트"],
        "family": ["가족", "가족여행"],
        "parents": ["부모님", "부모님과", "모시고"],
        "kids": ["아이", "아이와", "아이 동반", "유아"],
        "1박2일": ["1박2일", "1박 2일"],
        "2박3일": ["2박3일", "2박 3일"],
    }

    found_constraints: list[str] = []
    for canonical, keywords in constraint_keywords.items():
        if any(keyword in user_text for keyword in keywords):
            found_constraints.append(canonical)
    return found_constraints


def _extract_date_fields(user_text: str) -> dict[str, Any]:
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

    for token in ["오늘", "내일", "모레", "글피", "이번주", "다음주"]:
        if token in user_text:
            result["raw_date_text"] = token
            return result

    match_relative = re.search(r"(\d+)\s*(일후|일 후|박)", user_text)
    if match_relative:
        result["relative_days"] = int(match_relative.group(1))
        return result

    return result


def _extract_start_time(user_text: str) -> str | None:
    text = user_text.strip()

    match_ampm = re.search(r"(오전|오후)\s*(\d{1,2})(?::(\d{2}))?\s*시?", text)
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


def _extract_date_fields_current_year(user_text: str) -> dict[str, Any]:
    result = {
        "travel_date": None,
        "relative_days": None,
        "raw_date_text": None,
    }

    match_date = re.search(r"(20\d{2}-\d{2}-\d{2})", user_text)
    if match_date:
        result["travel_date"] = match_date.group(1)
        return result

    match_year_month_day = re.search(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", user_text)
    if match_year_month_day:
        year = int(match_year_month_day.group(1))
        month = int(match_year_month_day.group(2))
        day = int(match_year_month_day.group(3))
        result["travel_date"] = f"{year:04d}-{month:02d}-{day:02d}"
        result["raw_date_text"] = match_year_month_day.group(0)
        return result

    match_month_day = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", user_text)
    if match_month_day:
        month = int(match_month_day.group(1))
        day = int(match_month_day.group(2))
        result["travel_date"] = f"{CURRENT_YEAR:04d}-{month:02d}-{day:02d}"
        result["raw_date_text"] = match_month_day.group(0)
        return result

    for token in ["오늘", "내일", "모레", "글피", "이번주", "다음주"]:
        if token in user_text:
            result["raw_date_text"] = token
            return result

    match_relative = re.search(r"(\d+)\s*(일후|일 뒤|박)", user_text)
    if match_relative:
        result["relative_days"] = int(match_relative.group(1))
        return result

    return result


def _normalize_messages(messages: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages:
        if hasattr(message, "content"):
            role = getattr(message, "type", None) or getattr(message, "role", None) or "user"
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"
            normalized.append({"role": role, "content": str(message.content)})
        elif isinstance(message, dict):
            normalized.append(
                {"role": message.get("role", "user"), "content": str(message.get("content", ""))}
            )
    return normalized


def _safe_json_loads(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _normalize_style_values(values: list[Any]) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        if not value:
            continue
        canonical = STYLE_ALIASES.get(str(value).strip(), str(value).strip())
        if canonical not in normalized:
            normalized.append(canonical)
    return normalized


def _normalize_constraint_values(values: list[Any]) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        if not value:
            continue
        raw = str(value).strip()
        canonical = CONSTRAINT_ALIASES.get(raw, raw)
        if canonical not in normalized:
            normalized.append(canonical)
    return normalized


def _call_trip_extractor_llm(
    messages: list[Any],
    current_state: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    normalized_messages = _normalize_messages(messages)[-8:]
    system_prompt = f"""
You extract structured travel planning data from a Korean conversation.

Mode: {mode}

Return JSON only with this shape:
{{
  "destination": string or null,
  "styles": string[],
  "constraints": string[],
  "travel_date": string or null,
  "relative_days": integer or null,
  "raw_date_text": string or null,
  "start_time": string or null,
  "replace_styles": boolean,
  "reset_place_context": boolean,
  "route": string or null
}}

Rules:
- Keep values null if the user did not specify them.
- Put experiential preferences in "styles" and operating conditions in "constraints".
- styles examples: 맛집, 카페, 전시, 쇼핑, 풍경, 산책, 데이트, 관광, 액티비티
- constraints examples: indoor, outdoor, quiet, budget, solo, couple, family, parents, kids, pet, 1박2일, 2박3일
- "조용한", "실내", "부모님 모시고" belong to constraints, not styles.
- Use "replace_styles": true when the user explicitly excludes or swaps styles, like "카페 말고 맛집".
- Use "reset_place_context": true only when the destination clearly changed.
- Use "route": "travel" only when destination changed and old place/schedule context should be rebuilt.
- Do not invent a destination.
""".strip()

    user_payload = {
        "current_state": current_state,
        "messages": normalized_messages,
    }

    response = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )
    content = response.choices[0].message.content or "{}"
    return _safe_json_loads(content)


def _fallback_extract_updates(state: TravelAgentState, user_text: str) -> dict[str, Any]:
    current_destination = state.get(StateKeys.DESTINATION)
    current_styles = state.get(StateKeys.STYLES, [])
    current_constraints = state.get(StateKeys.CONSTRAINTS, [])

    destination = _extract_destination(user_text)
    styles = _extract_styles(user_text)
    constraints = _extract_constraints(user_text)
    date_info = _extract_date_fields_current_year(user_text)
    start_time = _extract_start_time(user_text)

    updates: dict[str, Any] = {}

    if destination:
        updates[StateKeys.DESTINATION] = destination
    elif current_destination:
        updates[StateKeys.DESTINATION] = current_destination

    if styles:
        updates[StateKeys.STYLES] = list(dict.fromkeys(current_styles + styles))
    elif current_styles:
        updates[StateKeys.STYLES] = current_styles

    if constraints:
        updates[StateKeys.CONSTRAINTS] = list(dict.fromkeys(current_constraints + constraints))
    elif current_constraints:
        updates[StateKeys.CONSTRAINTS] = current_constraints

    if date_info.get("travel_date"):
        updates[StateKeys.TRAVEL_DATE] = date_info["travel_date"]
    if date_info.get("relative_days") is not None:
        updates[StateKeys.RELATIVE_DAYS] = date_info["relative_days"]
    if date_info.get("raw_date_text"):
        updates[StateKeys.RAW_DATE_TEXT] = date_info["raw_date_text"]
    if start_time:
        updates[StateKeys.START_TIME] = start_time

    return updates


def _build_extract_updates(state: TravelAgentState, llm_result: dict[str, Any]) -> dict[str, Any]:
    current_destination = state.get(StateKeys.DESTINATION)
    current_styles = state.get(StateKeys.STYLES, [])
    current_constraints = state.get(StateKeys.CONSTRAINTS, [])

    updates: dict[str, Any] = {}

    destination = llm_result.get("destination")
    styles = _normalize_style_values(llm_result.get("styles") or [])
    constraints = _normalize_constraint_values(llm_result.get("constraints") or [])

    if destination:
        updates[StateKeys.DESTINATION] = destination
    elif current_destination:
        updates[StateKeys.DESTINATION] = current_destination

    if styles:
        updates[StateKeys.STYLES] = list(dict.fromkeys(current_styles + styles))
    elif current_styles:
        updates[StateKeys.STYLES] = current_styles

    if constraints:
        updates[StateKeys.CONSTRAINTS] = list(dict.fromkeys(current_constraints + constraints))
    elif current_constraints:
        updates[StateKeys.CONSTRAINTS] = current_constraints

    if llm_result.get("travel_date"):
        updates[StateKeys.TRAVEL_DATE] = llm_result["travel_date"]
        updates[StateKeys.RAW_DATE_TEXT] = None
        updates[StateKeys.RELATIVE_DAYS] = None
    elif llm_result.get("relative_days") is not None:
        updates[StateKeys.RELATIVE_DAYS] = llm_result["relative_days"]
        updates[StateKeys.TRAVEL_DATE] = None
        updates[StateKeys.RAW_DATE_TEXT] = None
    elif llm_result.get("raw_date_text"):
        updates[StateKeys.RAW_DATE_TEXT] = llm_result["raw_date_text"]
        updates[StateKeys.TRAVEL_DATE] = None
        updates[StateKeys.RELATIVE_DAYS] = None

    if llm_result.get("start_time"):
        updates[StateKeys.START_TIME] = llm_result["start_time"]

    return updates


def extract_trip_requirements_node(state: TravelAgentState) -> dict:
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        return {}

    last_msg = messages[-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

    current_state = {
        "destination": state.get(StateKeys.DESTINATION),
        "styles": state.get(StateKeys.STYLES, []),
        "constraints": state.get(StateKeys.CONSTRAINTS, []),
        "travel_date": state.get(StateKeys.TRAVEL_DATE),
        "relative_days": state.get(StateKeys.RELATIVE_DAYS),
        "raw_date_text": state.get(StateKeys.RAW_DATE_TEXT),
        "start_time": state.get(StateKeys.START_TIME),
    }

    try:
        llm_result = _call_trip_extractor_llm(messages, current_state, mode="extract")
        updates = _build_extract_updates(state, llm_result)
    except Exception as exc:
        print(f"[DEBUG] extract_trip_requirements_node LLM fallback: {exc}")
        updates = _fallback_extract_updates(state, user_text)

    print(f"[DEBUG] Existing State: dest={state.get(StateKeys.DESTINATION)}, styles={state.get(StateKeys.STYLES, [])}")
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

    current_state = {
        "destination": state.get(StateKeys.DESTINATION),
        "styles": state.get(StateKeys.STYLES, []),
        "constraints": state.get(StateKeys.CONSTRAINTS, []),
        "travel_date": state.get(StateKeys.TRAVEL_DATE),
        "relative_days": state.get(StateKeys.RELATIVE_DAYS),
        "raw_date_text": state.get(StateKeys.RAW_DATE_TEXT),
        "start_time": state.get(StateKeys.START_TIME),
    }

    try:
        llm_result = _call_trip_extractor_llm(messages, current_state, mode="modify")
    except Exception as exc:
        print(f"[DEBUG] modify_trip_requirements_node LLM fallback: {exc}")
        llm_result = {}

    updates: dict[str, Any] = {}
    current_dest = state.get(StateKeys.DESTINATION)

    new_destination = llm_result.get("destination") or _extract_destination(user_text)
    if new_destination is not None and new_destination != current_dest:
        updates[StateKeys.DESTINATION] = new_destination
        updates[StateKeys.MAPPED_PLACES] = []
        updates[StateKeys.SELECTED_PLACES] = []
        updates[StateKeys.ITINERARY] = []
        updates[StateKeys.ROUTE] = llm_result.get("route") or "travel"
        print(f"[DEBUG] Destination CHANGED to {new_destination}. Resetting ALL data.")

    styles = _normalize_style_values(llm_result.get("styles") or [])
    if styles:
        if llm_result.get("replace_styles"):
            updates[StateKeys.STYLES] = styles
        else:
            current_styles = state.get(StateKeys.STYLES, [])
            updates[StateKeys.STYLES] = list(dict.fromkeys(current_styles + styles))

    constraints = _normalize_constraint_values(llm_result.get("constraints") or [])
    if constraints:
        current_constraints = state.get(StateKeys.CONSTRAINTS, [])
        updates[StateKeys.CONSTRAINTS] = list(dict.fromkeys(current_constraints + constraints))

    if llm_result.get("travel_date"):
        updates[StateKeys.TRAVEL_DATE] = llm_result["travel_date"]
        updates[StateKeys.RAW_DATE_TEXT] = None
        updates[StateKeys.RELATIVE_DAYS] = None
    elif llm_result.get("relative_days") is not None:
        updates[StateKeys.RELATIVE_DAYS] = llm_result["relative_days"]
        updates[StateKeys.TRAVEL_DATE] = None
        updates[StateKeys.RAW_DATE_TEXT] = None
    elif llm_result.get("raw_date_text"):
        updates[StateKeys.RAW_DATE_TEXT] = llm_result["raw_date_text"]
        updates[StateKeys.TRAVEL_DATE] = None
        updates[StateKeys.RELATIVE_DAYS] = None
    else:
        fallback_date = _extract_date_fields_current_year(user_text)
        if fallback_date.get("travel_date"):
            updates[StateKeys.TRAVEL_DATE] = fallback_date["travel_date"]
            updates[StateKeys.RAW_DATE_TEXT] = None
            updates[StateKeys.RELATIVE_DAYS] = None
        elif fallback_date.get("relative_days") is not None:
            updates[StateKeys.RELATIVE_DAYS] = fallback_date["relative_days"]
            updates[StateKeys.TRAVEL_DATE] = None
            updates[StateKeys.RAW_DATE_TEXT] = None
        elif fallback_date.get("raw_date_text"):
            updates[StateKeys.RAW_DATE_TEXT] = fallback_date["raw_date_text"]
            updates[StateKeys.TRAVEL_DATE] = None
            updates[StateKeys.RELATIVE_DAYS] = None

    if llm_result.get("start_time"):
        updates[StateKeys.START_TIME] = llm_result["start_time"]
    else:
        fallback_start_time = _extract_start_time(user_text)
        if fallback_start_time:
            updates[StateKeys.START_TIME] = fallback_start_time

    print("[DEBUG] Final modify updates =", updates)
    return updates


def select_places_node(state: TravelAgentState) -> dict:
    current_dest = state.get(StateKeys.DESTINATION)
    mapped_places = state.get(StateKeys.MAPPED_PLACES, [])
    existing_selected = state.get(StateKeys.SELECTED_PLACES, [])
    existing_itinerary = state.get(StateKeys.ITINERARY, [])

    def is_valid_selected_places() -> bool:
        if not existing_selected or not current_dest:
            return False

        for place in existing_selected:
            text = place.get("text", "")
            name = place.get("name", "")
            if current_dest not in text and current_dest not in name:
                return False
        return True

    if existing_selected and existing_itinerary:
        if is_valid_selected_places():
            print("[DEBUG] Existing selection valid for current destination. Keeping them.")
            return {}
        print("[DEBUG] Destination changed. Resetting selected_places and itinerary.")
        return {
            StateKeys.SELECTED_PLACES: [],
            StateKeys.ITINERARY: [],
        }

    if mapped_places and current_dest:
        valid_mapped = [
            place for place in mapped_places
            if current_dest in place.get("text", "") or current_dest in place.get("name", "")
        ]

        if not valid_mapped:
            print("[DEBUG] No valid mapped places for current destination.")
            return {
                StateKeys.SELECTED_PLACES: [],
                StateKeys.ITINERARY: [],
            }
    else:
        valid_mapped = mapped_places

    selected = valid_mapped[:3]

    print(f"[DEBUG] New places selected for {current_dest}. Resetting itinerary for scheduler.")
    return {
        StateKeys.SELECTED_PLACES: selected,
        StateKeys.ITINERARY: [],
    }
