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
from llm.graph.builder import app as graph_app
from test_backup.proto.utils import parse_buttons
from streamlit_app.back.session_state import (
    now_label,
    build_persona_context,
)

from streamlit_app.back.session_state import (
    now_label,
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


def should_reuse_itinerary(user_text: str) -> bool:
    # 일정 관련 요청이면 기존 itinerary를 다음 턴에서도 재사용합니다.
    schedule_keywords = [
        "일정", "코스", "플랜", "루트", "짜줘", "계획",
        "동선", "스케줄", "순서", "중심으로", "기준으로",
    ]
    text = user_text.strip().lower()
    return any(keyword in text for keyword in schedule_keywords)


def get_mock_preview() -> dict:
    """
    UI 하위 호환용 프리뷰 응답 형식을 반환한다.

    최신 Streamlit UI는 사이드바 프리뷰 섹션에서 이 함수를 import한다.
    현재 실제 노드 기반 프리뷰 집계는 아직 구현되지 않았으므로,
    렌더링이 깨지지 않도록 빈 성공 응답 형태만 반환한다.

    Returns:
        dict: weather, places, schedule 키를 가진 기본 프리뷰 구조
    """
    return {
        "weather": {"status": "success", "data": {}},
        "places": {"status": "success", "data": {"places": []}},
        "schedule": {"status": "success", "data": {"itinerary": []}},
    }


# def get_mock_preview() -> dict:
#     """
#     사이드바 미리보기용 mock 결과를 생성한다.
#
#     현재 session_state의 여행 조건을 바탕으로
#     날씨 / 장소 / 일정 결과를 미리 계산한다.
#
#     Returns:
#         dict: weather, places, schedule 결과
#     """
#     info = st.session_state.trip_info
#     destination = info["destination"] if info["destination"] != "미정" else "강릉"
#     trip_date = info["date"] if info["date"] != "미정" else "2026-05-14"
#     style = info["style"] if info["style"] != "미정" else "휴식형"
#
#     # 1. 날씨 미리보기
#     weather = invoke_tool(get_weather, {"destination": destination, "date": trip_date})
#
#     # 2. 장소 미리보기
#     places = invoke_tool(search_places, {"region": destination, "theme": style})
#
#     place_items = []
#     if places.get("status") == "success":
#         place_items = places.get("data", {}).get("places", [])
#
#     # 3. 일정 미리보기
#     schedule = invoke_tool(
#         build_schedule,
#         {
#             "start_time": "10:00",
#             "end_time": "18:00",
#             "places": place_items,
#         },
#     )
#
#     return {
#         "weather": weather,
#         "places": places,
#         "schedule": schedule,
#     }


def initialize_greeting() -> None:
    """
    앱 최초 진입 시 초기 인사를 생성한다.

    persona context와 system prompt를 함께 넣어
    첫 응답을 생성하고 session_state에 저장한다.

    Returns:
        None
    """
    print("DEBUG: initialize_greeting 진입")

    if st.session_state.initialized:
        return

    # 버튼 마크업이 포함된 초기 인사 문구를 만들어 첫 메시지로 저장합니다.
    # greeting_raw = (
    #     "안녕하세요! 저는 여행 추천을 도와드릴 트립닷집이에요.\n"
    #     # "어디로 여행을 가고 싶으신가요? [BUTTONS:국내 여행|해외 여행|아직 모르겠어요]"
    # )

    # greeting_text, greeting_buttons = parse_buttons(greeting_raw)
    greeting_text = "안녕하세요! 저는 여행 추천을 도와드릴 트립땃쥐예요.\n" \
    "여행을 가실 장소와 여행을 가실 날짜를 알려주세요!"
    st.session_state.messages.append(
        {"role": "assistant", "content": greeting_text, "time": now_label()}
    )
    # st.session_state.quick_buttons = greeting_buttons
    st.session_state.initialized = True

# def format_weather_from_state(state: dict) -> str:
#     weather_data = state.get("weather_data", {}) or {}
#
#     if not weather_data:
#         return "날씨 정보를 불러오지 못했어요."
#
#     display_city = weather_data.get("display_city_name", "여행지")
#     resolved_date = weather_data.get("resolved_travel_date", "날짜 정보 없음")
#
#     weather_info = weather_data.get("weather", {})
#     condition_info = weather_data.get("condition", {})
#     ddatchwi_info = weather_data.get("ddatchwi", {})
#
#     weather_text = weather_info.get("description", "정보 없음")
#     temp = weather_info.get("temperature", "정보 없음")
#     feels_like = weather_info.get("temperature_feels_like", "정보 없음")
#     humidity = weather_info.get("humidity", "정보 없음")
#     wind_speed = weather_info.get("wind_speed", "정보 없음")
#
#     route_recommendation = condition_info.get("route_recommendation", "정보 없음")
#     reason = condition_info.get("reason", "정보 없음")
#
#     ddatchwi_character = ddatchwi_info.get("character", "땃쥐가 생각 중이에요…")
#     ddatchwi_text = ddatchwi_info.get("message", "참고 정보가 없어요.")
#
#     return (
#         f"먼저 {display_city} 날씨부터 볼게요.\n"
#         f"- 날짜: {resolved_date}\n"
#         f"- 날씨: {weather_text}\n"
#         f"- 기온: {temp}도\n"
#         f"- 체감온도: {feels_like}도\n"
#         f"- 습도: {humidity}%\n"
#         f"- 바람: {wind_speed}m/s\n"
#         f"- 추천 유형: {route_recommendation}\n"
#         f"- 판단 이유: {reason}\n\n"
#         f"{ddatchwi_character}\n"
#         f"{ddatchwi_text}"
#     )

# def format_schedule_from_state(state: dict) -> str:
#     """
#     LangGraph state의 itinerary를 사용자용 문자열로 변환한다.
#
#     Args:
#         state (dict): LangGraph 상태값
#
#     Returns:
#         str: 일정 안내 문자열
#     """
#     itinerary = state.get("itinerary", []) or []
#
#     if not itinerary:
#         return "일정은 아직 만들지 못했어요."
#
#     lines = ["\n추천 일정은 이렇게 짜볼게요."]
#     for idx, item in enumerate(itinerary[:5], start=1):
#         time_text = item.get("time") or item.get("arrival") or ""
#         place_name = item.get("place_name") or item.get("name") or f"{idx}번 장소"
#
#         if time_text:
#             lines.append(f"- {time_text} {place_name}")
#         else:
#             lines.append(f"- {place_name}")
#
#     return "\n".join(lines)

# def format_places_from_state(state: dict) -> str:
#     """
#     LangGraph state의 장소 목록을 사용자용 문자열로 변환한다.
#
#     Args:
#         state (dict): LangGraph 상태값
#
#     Returns:
#         str: 장소 추천 문자열
#     """
#     places = state.get("selected_places") or state.get("mapped_places") or []
#
#     if not places:
#         return "추천할 장소가 아직 없어요."
#
#     lines = ["\n함께 볼 만한 장소도 골라봤어요."]
#     for place in places[:5]:
#         name = place.get("name", "이름 없는 장소")
#         category = place.get("category", "장소")
#         rating = place.get("rating", "정보 없음")
#         lines.append(f"- {name} ({category}, 평점: {rating})")
#
#     return "\n".join(lines)


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

    # 1. 사용자 메시지 저장
    st.session_state.messages.append(
        {"role": "user", "content": user_text, "time": now_label()}
    )
    st.session_state.quick_buttons = []

    try:
        # 3. LangGraph 입력 state 구성

        # --- 목적지 변경 감지 및 초기화 로직 ---
        current_dest = st.session_state.get("destination")
        current_selected = st.session_state.get("selected_places", [])
        current_mapped = st.session_state.get("mapped_places", [])

        # 목적지 정합성 체크 (장소 이름이나 텍스트에 도시명이 있는지 확인)
        is_mismatch = False
        if current_dest:
            # 선택된 장소가 있다면 체크
            if current_selected and current_dest not in current_selected[0].get('name', ''):
                is_mismatch = True
            # 검색된 리스트가 있다면 체크 (이게 핵심!)
            elif current_mapped and current_dest not in current_mapped[0].get('text', ''):
                is_mismatch = True

        if is_mismatch:
            print(f"DEBUG: Destination mismatch ({current_dest}). Clearing old data.")
            current_selected = []
            current_mapped = []
            st.session_state["itinerary"] = []  # 일정도 비워줌

        # 메시지뿐만 아니라 세션에 저장된 기존 상태값들을 함께 전달합니다.
        # 일정은 후속 대화에서도 유지하고, 목적지가 바뀌는 경우에만 위 초기화 로직으로 비운다.
        current_itinerary = st.session_state.get("itinerary", [])

        # UI 세션 상태와 대화 이력을 함께 묶어 그래프 입력으로 전달합니다.
        graph_input = {
            "messages": [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            "destination": current_dest,
            "styles": st.session_state.get("styles", []),
            "constraints": st.session_state.get("constraints", []),
            "travel_date": st.session_state.get("travel_date"),
            "trip_length": st.session_state.get("trip_length"),
            "start_time": st.session_state.get("start_time"),
            "selected_places": current_selected, # 정제된 리스트 전달
            "itinerary": current_itinerary,
            "mapped_places": current_mapped,
        }

        print("DEBUG: graph_app.invoke 직전")
        print("DEBUG: graph_input =", graph_input)

        # 4. LangGraph 실행
        result = graph_app.invoke(graph_input)

        # 4-1. 그래프 실행 결과로 업데이트된 상태를 Streamlit 세션에 저장
        # 필드가 존재하는지 확인하고, None이 아니면 덮어씁니다.
        state_fields = [
            "destination", "styles", "constraints", "travel_date", "trip_length",
            "start_time", "selected_places", "mapped_places", "itinerary"
        ]

        # 현재 그래프 결과에서 목적지가 바뀌었는지 확인
        graph_dest = result.get("destination")
        session_dest = st.session_state.get("destination")

        for field in state_fields:
            if field in result:
                # 그래프가 명시적으로 반환한 값으로 업데이트
                st.session_state[field] = result[field]
            elif graph_dest and graph_dest != session_dest:
                # 목적지가 바뀌었는데 그래프 결과에 해당 필드가 없다면,
                # 이전 도시 데이터가 섞이지 않도록 초기화
                if field in ["selected_places", "mapped_places", "itinerary", "styles", "constraints"]:
                    st.session_state[field] = []
                else:
                    st.session_state[field] = None

        print(
            f"DEBUG: Session Updated - dest={st.session_state.get('destination')}, places_cnt={len(st.session_state.get('selected_places', []))}")

        print("DEBUG: graph result =", result)
        print("DEBUG: final_response =", result.get("final_response"))
        print("DEBUG: route =", result.get("route"))
        print("DEBUG: weather_data =", result.get("weather_data"))

        # 5. 최종 응답 추출
        raw_reply = result.get("final_response", "응답을 만들지 못했어요.")

    except Exception as exc:
        print("DEBUG: process_user_input 예외 =", exc)
        raw_reply = (
            "지금은 AI 응답을 불러오지 못했어요. 설정을 확인한 뒤 다시 시도해주세요.\n\n"
            f"오류: {exc}"
        )

    # 6. 최종 응답 저장
    # 버튼 마크업을 분리해 메시지 본문과 빠른 선택 버튼으로 저장합니다.
    reply_text, reply_buttons = parse_buttons(raw_reply)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply_text, "time": now_label()}
    )
    st.session_state.quick_buttons = reply_buttons
