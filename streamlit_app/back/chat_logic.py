"""
chat_logic.py

Streamlit 기반 여행 추천 챗봇의 핵심 대화 처리 로직을 담당하는 모듈이다.

주요 역할:
- 사용자 입력 처리
- intent 기반 분기
- 날씨 → 장소 → 일정 순의 오케스트레이션 실행
- 일반 대화 fallback 처리
- UI에 표시할 응답 문자열 생성

이 모듈은 session_state, tool, agent를 연결하는
컨트롤 레이어 역할을 한다.
"""
from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st
from dotenv import load_dotenv

# =========================
# 환경 경로 설정
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# =========================
# 외부 기능 import
# =========================
from test_backup.mock_tools.place_tools import search_places
from test_backup.mock_tools.schedule_tools import build_schedule
from test_backup.mock_tools.weather_tools import get_weather, get_weather_from_prompt
from services.intent_service import classify_intent_by_rule
from llm.prompts import SYSTEM_PROMPT
from test_backup.proto.utils import parse_buttons
from test_backup.agent_builder import agent

from streamlit_app.back.session_state import (
    now_label,
    update_trip_info,
    build_persona_context,
)


def extract_message_text(content) -> str:
    """
    LLM 또는 tool 응답 content를 문자열로 안전하게 변환한다.

    Args:
        content: 문자열, 멀티모달 리스트, 기타 객체

    Returns:
        str: 사용자에게 출력 가능한 문자열
    """
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
    """
    tool.invoke 호출을 감싸고 예외를 안전하게 처리한다.

    Args:
        tool: LangChain tool 또는 invoke 가능한 객체
        payload (dict): tool 입력 데이터

    Returns:
        dict: tool 실행 결과 또는 에러 정보
    """
    try:
        return tool.invoke(payload)
    except Exception as exc:
        return {
            "status": "error",
            "data": None,
            "error": {"message": str(exc)},
        }


def get_mock_preview() -> dict:
    """
    사이드바 미리보기용 mock 결과를 생성한다.

    현재 session_state의 여행 조건을 바탕으로
    날씨 / 장소 / 일정 결과를 미리 계산한다.

    Returns:
        dict: weather, places, schedule 결과
    """
    info = st.session_state.trip_info
    destination = info["destination"] if info["destination"] != "미정" else "강릉"
    trip_date = info["date"] if info["date"] != "미정" else "2026-05-14"
    style = info["style"] if info["style"] != "미정" else "휴식형"

    # 1. 날씨 미리보기
    weather = invoke_tool(get_weather, {"destination": destination, "date": trip_date})

    # 2. 장소 미리보기
    places = invoke_tool(search_places, {"region": destination, "theme": style})

    place_items = []
    if places.get("status") == "success":
        place_items = places.get("data", {}).get("places", [])

    # 3. 일정 미리보기
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
    """
    앱 최초 진입 시 초기 인사를 생성한다.

    persona context와 system prompt를 함께 넣어
    첫 응답을 생성하고 session_state에 저장한다.

    Returns:
        None
    """
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
    """
    날씨 tool 결과를 사용자 친화적인 텍스트로 변환한다.

    Args:
        tool_result (dict): 날씨 tool 실행 결과
        fallback_city (str): 도시명 fallback 값

    Returns:
        str: 날씨 안내 문자열
    """
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
    """
    일정 생성 결과를 사용자용 문자열로 변환한다.

    Args:
        schedule_result (dict): 일정 생성 결과

    Returns:
        str: 일정 안내 문자열
    """
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
    """
    장소 검색 결과를 사용자용 문자열로 변환한다.

    Args:
        places_result (dict): 장소 검색 결과

    Returns:
        str: 장소 추천 문자열
    """
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
    """
    사용자 입력을 처리하고 최종 응답을 생성한다.

    흐름:
    1. 사용자 입력을 session_state에 저장
    2. intent를 분류
    3. 여행 관련 요청이면 날씨 → 장소 → 일정 흐름 실행
    4. 일반 대화면 agent로 fallback
    5. 최종 답변을 session_state에 저장

    Args:
        user_text (str): 사용자 입력 문장

    Returns:
        None
    """
    print("DEBUG: process_user_input 진입")
    print("DEBUG: user_text =", user_text)

    # 1. 여행 정보 업데이트
    update_trip_info(user_text)

    # 2. 사용자 메시지 저장
    st.session_state.messages.append(
        {"role": "user", "content": user_text, "time": now_label()}
    )
    st.session_state.quick_buttons = []

    print("DEBUG: executor.run 직전")
    print("DEBUG: current_messages =", st.session_state.messages)

    try:
        # 3. intent 분류
        intent_result = classify_intent_by_rule(user_text)
        print("DEBUG: intent_result =", intent_result)

        info = st.session_state.trip_info
        destination = info.get("destination", "미정")
        style = info.get("style", "미정")

        if destination == "미정":
            destination = "서울"
        if style == "미정":
            style = "휴식형"

        # 4. 여행 관련 요청인지 판별
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

            # 4-1. 자연어 기반 날씨 먼저 조회
            weather_result = get_weather_from_prompt.invoke(
                {"user_prompt": user_text}
            )
            print("DEBUG weather_result =", weather_result)

            reply_parts = [format_weather_first_reply(weather_result, destination)]

            # 4-2. 장소 검색
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

            # 4-3. 일정 생성 요청이면 일정까지 생성
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

            # 4-3. 일정 생성 요청이면 일정까지 생성
            if intent_result["intent"] in [
                "place_search",
                "travel_recommendation",
                "schedule_generation",
            ]:
                reply_parts.append(format_places_reply(places_result))

            raw_reply = "\n".join(part for part in reply_parts if part).strip()

        else:
            # 5. 일반 대화는 agent fallback
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

    # 6. 최종 응답 저장
    reply_text, reply_buttons = parse_buttons(raw_reply)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply_text, "time": now_label()}
    )
    st.session_state.quick_buttons = reply_buttons