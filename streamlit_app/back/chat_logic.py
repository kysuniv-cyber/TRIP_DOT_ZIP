from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
ROOT_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")

from mock_tools.place_tools import search_places
from mock_tools.schedule_tools import build_schedule
from mock_tools.weather_tools import get_weather, get_weather_from_prompt
from services.intent_service import classify_intent_by_rule
from llm.prompts import SYSTEM_PROMPT
from proto.utils import parse_buttons
from agent_builder import agent

from streamlit_app.back.session_state import (
    now_label,
    update_trip_info,
    build_persona_context,
)


def extract_message_text(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")))
            else:
                text_parts.append(str(item))
        return " ".join(part for part in text_parts if part).strip()

    return str(content)


def invoke_tool(tool, payload: dict) -> dict:
    try:
        return tool.invoke(payload)
    except Exception as exc:
        return {
            "status": "error",
            "data": None,
            "error": {"message": str(exc)},
        }


def get_mock_preview() -> dict:
    info = st.session_state.trip_info
    destination = info["destination"] if info["destination"] != "미정" else "강릉"
    trip_date = info["date"] if info["date"] != "미정" else "2026-05-14"
    style = info["style"] if info["style"] != "미정" else "휴식형"

    weather = invoke_tool(get_weather, {"destination": destination, "date": trip_date})
    places = invoke_tool(search_places, {"region": destination, "theme": style})

    place_items = []
    if places.get("status") == "success":
        place_items = places.get("data", {}).get("places", [])

    schedule = invoke_tool(
        build_schedule,
        {
            "start_time": "10:00",
            "end_time": "18:00",
            "places": place_items,
        },
    )

    return {
        "weather": weather,
        "places": places,
        "schedule": schedule,
    }


def initialize_greeting() -> None:
    st.write("DEBUG: initialize_greeting 진입")

    if st.session_state.initialized:
        return

    try:
        with st.spinner("트립닷집이 준비 중이에요..."):
            print("DEBUG: executor.run 직전")
            response = agent.invoke(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "system", "content": build_persona_context()},
                        {"role": "user", "content": "안녕하세요! 여행 추천을 받고 싶어요."},
                    ]
                }
            )

        greeting_raw = extract_message_text(response["messages"][-1].content)

    except Exception as exc:
        print("DEBUG: initialize_greeting 예외 =", exc)
        st.write(f"DEBUG 예외: {exc}")
        greeting_raw = (
            "안녕하세요! 저는 여행 추천을 도와드릴 트립닷집이에요.\n"
            "어디로 여행을 가고 싶으신가요? [BUTTONS:국내 여행|해외 여행|아직 모르겠어요]"
        )

    greeting_text, greeting_buttons = parse_buttons(greeting_raw)
    st.session_state.messages.append(
        {"role": "assistant", "content": greeting_text, "time": now_label()}
    )
    st.session_state.quick_buttons = greeting_buttons
    st.session_state.initialized = True


def format_weather_first_reply(tool_result: dict, fallback_city: str) -> str:
    data = tool_result.get("data", {}) if isinstance(tool_result, dict) else {}
    result_data = data.get("result", {}) if isinstance(data, dict) else {}

    if (
        not isinstance(tool_result, dict)
        or tool_result.get("status") == "error"
        or result_data.get("status") == "error"
    ):
        return (
            "날씨 정보를 먼저 확인해보려 했는데 불러오지 못했어요.\n"
            f"- 오류: {tool_result.get('message') or result_data.get('message') or '알 수 없는 오류'}"
        )

    weather_info = result_data.get("weather", {})
    condition_info = result_data.get("condition", {})
    ddatchwi_info = result_data.get("ddatchwi", {})

    display_city = data.get("display_city_name", fallback_city)
    resolved_date = data.get("resolved_travel_date", "날짜 정보 없음")

    weather_text = weather_info.get("description", "정보 없음")
    temp = weather_info.get("temperature", "정보 없음")
    feels_like = weather_info.get("temperature_feels_like", "정보 없음")
    humidity = weather_info.get("humidity", "정보 없음")
    wind_speed = weather_info.get("wind_speed", "정보 없음")

    route_recommendation = condition_info.get("route_recommendation", "정보 없음")
    reason = condition_info.get("reason", "정보 없음")

    ddatchwi_character = ddatchwi_info.get("character", "땃쥐가 생각 중이에요…")
    ddatchwi_text = ddatchwi_info.get("message", "참고 정보가 없어요.")

    return (
        f"먼저 {display_city} 날씨부터 볼게요.\n"
        f"- 날짜: {resolved_date}\n"
        f"- 날씨: {weather_text}\n"
        f"- 기온: {temp}도\n"
        f"- 체감온도: {feels_like}도\n"
        f"- 습도: {humidity}%\n"
        f"- 바람: {wind_speed}m/s\n"
        f"- 추천 유형: {route_recommendation}\n"
        f"- 판단 이유: {reason}\n\n"
        f"{ddatchwi_character}\n"
        f"{ddatchwi_text}"
    )


def format_schedule_reply(schedule_result: dict) -> str:
    if not isinstance(schedule_result, dict) or schedule_result.get("status") != "success":
        return "일정은 아직 만들지 못했어요."

    data = schedule_result.get("data", {}) or {}
    itinerary = data.get("itinerary", [])

    if not itinerary:
        return "일정 후보가 아직 없어요."

    lines = ["\n추천 일정은 이렇게 짜볼게요."]
    for idx, item in enumerate(itinerary[:5], start=1):
        time_text = item.get("time") or item.get("arrival") or ""
        place_name = item.get("place_name") or item.get("name") or f"{idx}번 장소"
        if time_text:
            lines.append(f"- {time_text} {place_name}")
        else:
            lines.append(f"- {place_name}")

    return "\n".join(lines)


def format_places_reply(places_result: dict) -> str:
    if not isinstance(places_result, dict) or places_result.get("status") != "success":
        return "추천 장소는 아직 찾지 못했어요."

    data = places_result.get("data", {}) or {}
    places = data.get("places", [])

    if not places:
        return "추천할 장소가 아직 없어요."

    lines = ["\n함께 볼 만한 장소도 골라봤어요."]
    for place in places[:5]:
        name = place.get("name", "이름 없는 장소")
        category = place.get("category", "장소")
        rating = place.get("rating", "정보 없음")
        lines.append(f"- {name} ({category}, 평점: {rating})")

    return "\n".join(lines)


def process_user_input(user_text: str) -> None:
    print("DEBUG: process_user_input 진입")
    print("DEBUG: user_text =", user_text)

    update_trip_info(user_text)
    st.session_state.messages.append(
        {"role": "user", "content": user_text, "time": now_label()}
    )
    st.session_state.quick_buttons = []

    print("DEBUG: executor.run 직전")
    print("DEBUG: current_messages =", st.session_state.messages)

    try:
        intent_result = classify_intent_by_rule(user_text)
        print("DEBUG: intent_result =", intent_result)

        info = st.session_state.trip_info
        destination = info.get("destination", "미정")
        style = info.get("style", "미정")

        if destination == "미정":
            destination = "서울"
        if style == "미정":
            style = "휴식형"

        is_travel_related = intent_result["intent"] in [
            "weather_query",
            "schedule_generation",
            "place_search",
            "travel_recommendation",
        ]

        if is_travel_related:
            print("🔥 WEATHER FIRST FLOW")
            print("DEBUG destination =", destination)
            print("DEBUG style =", style)

            weather_result = get_weather_from_prompt.invoke(
                {"user_prompt": user_text}
            )
            print("DEBUG weather_result =", weather_result)

            reply_parts = [format_weather_first_reply(weather_result, destination)]

            try:
                places_result = invoke_tool(
                    search_places,
                    {"region": destination, "theme": style},
                )
                print("DEBUG places_result =", places_result)
            except Exception as exc:
                print("DEBUG places_result 예외 =", exc)
                places_result = {
                    "status": "error",
                    "data": None,
                    "error": {"message": str(exc)},
                }

            place_items = []
            if places_result.get("status") == "success":
                place_items = places_result.get("data", {}).get("places", []) or []

            if intent_result["intent"] == "schedule_generation" and place_items:
                try:
                    schedule_result = invoke_tool(
                        build_schedule,
                        {
                            "start_time": "10:00",
                            "end_time": "18:00",
                            "places": place_items,
                        },
                    )
                    print("DEBUG schedule_result =", schedule_result)
                    reply_parts.append(format_schedule_reply(schedule_result))
                except Exception as exc:
                    print("DEBUG schedule_result 예외 =", exc)
                    reply_parts.append(f"\n일정 생성 중 오류가 있었어요.\n- 오류: {exc}")

            if intent_result["intent"] in [
                "place_search",
                "travel_recommendation",
                "schedule_generation",
            ]:
                reply_parts.append(format_places_reply(places_result))

            raw_reply = "\n".join(part for part in reply_parts if part).strip()

        else:
            response = agent.invoke(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "system", "content": build_persona_context()},
                        *[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                        ],
                    ]
                }
            )

            raw_reply = extract_message_text(response["messages"][-1].content)
            print("DEBUG: executor.run 직후", raw_reply)

    except Exception as exc:
        print("DEBUG: process_user_input 예외 =", exc)
        raw_reply = (
            "지금은 AI 응답을 불러오지 못했어요. 설정을 확인한 뒤 다시 시도해주세요.\n\n"
            f"오류: {exc}"
        )

    reply_text, reply_buttons = parse_buttons(raw_reply)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply_text, "time": now_label()}
    )
    st.session_state.quick_buttons = reply_buttons