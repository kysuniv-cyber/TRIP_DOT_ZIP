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

    system_prompt = """
You are a Korean travel planning assistant.
Write a natural final response in Korean based only on structured state data.

Rules:
- Do not invent missing facts.
- Never infer or invent a year that is not explicitly present in state data.
- If display_date exists, use that exact date wording.
- If travel_date is null, use raw_date_text or display_date verbatim. Do not convert it into an absolute year.
- If route is schedule and itinerary exists, explain the schedule clearly.
- If route is travel, recommend places and next steps. Do not present the answer as a finalized full itinerary.
- If route is place or modify and places exist, explain the place recommendations clearly.
- If data is incomplete, ask one short next-step question.
- Keep the tone concise, helpful, and conversational.
""".strip()

    try:
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
