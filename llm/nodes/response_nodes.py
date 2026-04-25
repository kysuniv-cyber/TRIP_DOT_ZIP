import json
import re
from typing import Any

from openai import OpenAI

from config import Settings
from llm.graph.contracts import StateKeys
from llm.graph.state import TravelAgentState


client = OpenAI(api_key=Settings.openai_api_key)
LLM_MODEL = "gpt-4.1-mini"


def _truncate_places(places: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # 응답 생성에 필요한 장소 정보만 남겨 프롬프트 길이를 줄입니다.
    simplified = []
    for place in places[:5]:
        simplified.append(
            {
                "name": place.get("name"),
                "category": place.get("category"),
                "rating": place.get("rating"),
                "address": place.get("address"),
            }
        )
    return simplified


def _truncate_itinerary(itinerary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # 일정도 핵심 필드만 남겨 LLM 입력 크기를 관리합니다.
    simplified = []
    for item in itinerary[:8]:
        simplified.append(
            {
                "place_name": item.get("place_name"),
                "arrival": item.get("arrival"),
                "departure": item.get("departure"),
                "stay_time": item.get("stay_time"),
            }
        )
    return simplified


def _build_display_date(state: TravelAgentState) -> str | None:
    # 상태에 저장된 날짜를 사용자에게 보여줄 문자열 형식으로 변환합니다.
    travel_date = state.get(StateKeys.TRAVEL_DATE)
    raw_date_text = state.get(StateKeys.RAW_DATE_TEXT)
    if travel_date:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(travel_date))
        if match:
            year, month, day = match.groups()
            return f"{int(year)}년 {int(month)}월 {int(day)}일"
        return str(travel_date)
    if raw_date_text:
        return str(raw_date_text)
    return None


def _normalize_response_date(final_response: str, state: TravelAgentState) -> str:
    # 모델이 날짜를 임의 형식으로 다시 쓰지 않도록 표시용 날짜로 맞춥니다.
    display_date = _build_display_date(state)
    if not display_date:
        return final_response

    raw_date_text = state.get(StateKeys.RAW_DATE_TEXT)
    if raw_date_text:
        month_day_match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", str(raw_date_text))
        if month_day_match:
            month = int(month_day_match.group(1))
            day = int(month_day_match.group(2))
            final_response = re.sub(
                rf"20\d{{2}}년\s*{month}월\s*{day}일",
                display_date,
                final_response,
            )
    return final_response


def _build_fallback_response(state: TravelAgentState) -> str:
    # LLM 응답 생성이 실패했을 때 상태값만으로 기본 답변을 만듭니다.
    itinerary = state.get(StateKeys.ITINERARY, [])
    destination = state.get(StateKeys.DESTINATION, "요청하신 지역")
    selected_places = state.get(StateKeys.SELECTED_PLACES, [])
    places = selected_places or state.get(StateKeys.MAPPED_PLACES, [])
    route = state.get(StateKeys.ROUTE)

    if route == "schedule" and itinerary:
        lines = [f"{destination} 추천 일정입니다."]
        for item in itinerary:
            lines.append(
                f"- {item.get('arrival', '시간 미정')} ~ {item.get('departure', '시간 미정')}: "
                f"{item.get('place_name', '장소명 미정')}"
            )
        return "\n".join(lines)

    if route in {"place", "travel", "modify"} and places:
        lines = [f"{destination} 추천 장소입니다."]
        for place in places[:3]:
            lines.append(f"- {place.get('name', '이름 없음')} ({place.get('category', '명소')})")
        if route == "travel":
            lines.append("원하시면 이 장소들 기준으로 일정도 이어서 만들어드릴게요.")
        return "\n".join(lines)

    if destination:
        return f"{destination}에서 조건에 맞는 장소를 아직 찾지 못했습니다. 조건을 조금 완화해서 다시 추천드릴까요?"

    return "죄송합니다. 요청하신 정보를 찾지 못했습니다. 다시 말씀해 주세요."


def build_response_node(state: TravelAgentState) -> dict:
    # 날씨 전용 응답은 직접 조립하고, 그 외에는 구조화된 상태를 LLM에 전달합니다.
    weather_data = state.get(StateKeys.WEATHER_DATA)
    itinerary = state.get(StateKeys.ITINERARY, [])
    destination = state.get(StateKeys.DESTINATION, "요청하신 지역")
    selected_places = state.get(StateKeys.SELECTED_PLACES, [])
    places = selected_places or state.get(StateKeys.MAPPED_PLACES, [])
    route = state.get(StateKeys.ROUTE, "chat")
    summary = state.get(StateKeys.CONVERSATION_SUMMARY, "")

    if route == "weather" and weather_data and isinstance(weather_data, dict):
        status = weather_data.get("status")
        if status == "success":
            weather = weather_data.get("weather", {})
            condition = weather_data.get("condition", {})
            ddatchwi = weather_data.get("ddatchwi", {})
            return {
                StateKeys.FINAL_RESPONSE: (
                    f"## **{destination} 날씨 정보**\n"
                    f"- 설명: {weather.get('description', '정보 없음')}\n"
                    f"- 온도: {weather.get('temperature', '정보 없음')}\n"
                    f"- 추천 유형: {condition.get('route_recommendation', '정보 없음')}\n"
                    f"- 이유: {condition.get('reason', '정보 없음')}\n\n"
                    f"{ddatchwi.get('character', '')}\n"
                    f"{ddatchwi.get('message', '')}"
                )
            }
        return {
            StateKeys.FINAL_RESPONSE: weather_data.get("message", "날씨 정보를 확인하지 못했습니다.")
        }

    payload = {
        "route": route,
        "destination": destination,
        "styles": state.get(StateKeys.STYLES, []),
        "constraints": state.get(StateKeys.CONSTRAINTS, []),
        "travel_date": state.get(StateKeys.TRAVEL_DATE),
        "raw_date_text": state.get(StateKeys.RAW_DATE_TEXT),
        "display_date": _build_display_date(state),
        "start_time": state.get(StateKeys.START_TIME),
        "selected_places": _truncate_places(places),
        "itinerary": _truncate_itinerary(itinerary),
        "conversation_summary": summary,
    }

    # 최종 답변은 상태에 있는 정보만 사용하도록 프롬프트를 제한합니다.
    system_prompt = """
You are a specialized Korean travel assistant for Korean travel planning.
Write a natural final response in Korean based only on structured state data.

[Response Rules]
- Format Persistence: If an itinerary exists in the state, ALWAYS present the schedule in the same list format used previously (e.g., "- 09:00 [Place Name]...").
- Minimal Modification: If the route is 'modify' or 'travel' with an existing itinerary:
  1. DO NOT discard the previous plan. 
  2. Replace only one relevant activity with the newly requested activity (e.g., replace 'walking' with 'surfing') while keeping the restaurant and other core slots.
  3. Start with a phrase like: "서핑을 추가해서 일정을 살짝 수정해봤어요!"
- Accuracy: Do not invent facts or years. Use date info (display_date, travel_date, or raw_date_text) verbatim. Do not convert to an absolute year unless provided.
- Route-Specific:
  - 'schedule' and an itinerary exists: Present the time-based table clearly.
  - 'travel': Recommend specific places and suggest the next step. Do not present it as a final/locked itinerary yet.
  - 'place' or 'modify': Explain the recommended places clearly.
- If data is incomplete: Ask exactly ONE short, relevant next-step question.

[Tone]
- Concise, helpful, and conversational (Polite Korean).
""".strip()

    try:
        # 구조화된 payload를 바탕으로 자연스러운 최종 답변을 생성합니다.
        response = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        final_response = (response.choices[0].message.content or "").strip()
        if final_response:
            final_response = _normalize_response_date(final_response, state)
            return {StateKeys.FINAL_RESPONSE: final_response}
    except Exception as exc:
        print(f"[DEBUG] build_response_node LLM fallback: {exc}")

    return {StateKeys.FINAL_RESPONSE: _build_fallback_response(state)}


def blocked_response_node(state: TravelAgentState) -> dict:
    reason = state.get(StateKeys.BLOCK_REASON, "이번 요청은 처리할 수 없습니다.")
    return {StateKeys.FINAL_RESPONSE: reason}
