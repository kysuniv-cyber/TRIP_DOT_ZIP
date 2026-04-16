from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import html
import base64
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]

from mock_tools.place_tools import search_places
from mock_tools.schedule_tools import build_schedule
from mock_tools.weather_tools import get_weather

from middlewares.executor import AgentExecutor
from middlewares.registry import ToolRegistry
from llm.prompts import SYSTEM_PROMPT
from proto.utils import parse_buttons
load_dotenv(ROOT_DIR / ".env")

GUIDE_MOUSE_IMAGE = ROOT_DIR / "assets" / "tripdotzip_guide_mouse.png"
MOUSE_ICON_IMAGE = ROOT_DIR / "assets" / "tripdotzip_mouse_icon.png"

tool_registry = ToolRegistry()
tool_registry.register("get_weather", get_weather)
tool_registry.register("search_places", search_places)
tool_registry.register("build_schedule", build_schedule)

executor = AgentExecutor(registry=tool_registry)


st.set_page_config(
    page_title="트립닷집",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css() -> None:
    css_path = Path(__file__).with_name("tripdotzip.css")
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def now_label() -> str:
    return datetime.now().strftime("%H:%M")


@st.cache_data
def image_data_uri(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def init_state() -> None:
    defaults = {
        "messages": [],
        "quick_buttons": [],
        "initialized": False,
        "pending_input": None,
        "trip_info": {
            "destination": "미정",
            "date": "미정",
            "people": "미정",
            "style": "미정",
        },
        "history_items": [
            ("대만 타이페이 3박 4일", "2025.12.20"),
            ("제주도 힐링 여행 2박 3일", "2025.09.15"),
            ("부산 해운대 당일치기", "2025.07.08"),
        ],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state() -> None:
    st.session_state.messages = []
    st.session_state.quick_buttons = []
    st.session_state.initialized = False
    st.session_state.pending_input = None
    st.session_state.trip_info = {
        "destination": "미정",
        "date": "미정",
        "people": "미정",
        "style": "미정",
    }


def update_trip_info(user_text: str) -> None:
    info = st.session_state.trip_info
    text = user_text.strip()

    destinations = [
        "강릉", "서울", "부산", "제주", "제주도", "속초", "여수", "경주", "전주",
        "대구", "인천", "대전", "광주", "성수", "홍대", "대만", "타이페이", "일본", "오사카",
    ]
    for destination in destinations:
        if destination in text:
            info["destination"] = "제주도" if destination == "제주" else destination
            break

    date_patterns = [
        r"(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})",
        r"(\d{1,2})\s*월\s*(\d{1,2})\s*일",
        r"(\d{1,2})[.\-/](\d{1,2})",
    ]
    for pattern in date_patterns:
        matched = re.search(pattern, text)
        if matched:
            groups = matched.groups()
            if len(groups) == 3:
                info["date"] = f"{groups[0]}.{int(groups[1]):02d}.{int(groups[2]):02d}"
            else:
                info["date"] = f"{int(groups[0])}월 {int(groups[1])}일"
            break

    people_match = re.search(r"(\d+)\s*(명|인|명이요|명이)", text)
    if people_match:
        info["people"] = f"{people_match.group(1)}명"

    style_keywords = {
        "휴식": "휴식형",
        "힐링": "휴식형",
        "카페": "카페 투어",
        "맛집": "먹방 여행",
        "먹방": "먹방 여행",
        "액티비티": "액티비티",
        "문화": "문화 탐방",
        "역사": "문화 탐방",
        "실내": "실내 위주",
        "바다": "바다 여행",
        "사진": "사진 명소",
    }
    for keyword, style in style_keywords.items():
        if keyword in text:
            info["style"] = style
            break


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


def render_message(message: dict) -> None:
    role = message["role"]
    wrapper_class = "user" if role == "user" else ""
    avatar_class = "user" if role == "user" else "bot"
    mouse_icon = image_data_uri(str(MOUSE_ICON_IMAGE))
    avatar = "나" if role == "user" else f'<img src="{mouse_icon}" alt="트립닷집">'
    content = html.escape(message["content"]).replace("\n", "<br>")
    timestamp = html.escape(message.get("time", ""))

    st.markdown(
        f"""
        <div class="bubble-wrapper {wrapper_class}">
            <div class="avatar {avatar_class}">{avatar}</div>
            <div class="message-group">
                <div class="bubble {avatar_class}">{content}</div>
                <div class="timestamp">{timestamp}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_loading_message() -> None:
    image_src = image_data_uri(str(GUIDE_MOUSE_IMAGE))
    st.markdown(
        f"""
        <div class="bubble-wrapper">
            <div class="avatar bot">AI</div>
            <div class="message-group">
                <div class="bubble bot loading-bubble">
                    <img class="loading-mouse" src="{image_src}" alt="트립닷집 안내 캐릭터">
                    <div class="loading-text">
                        <strong>트립닷집이 여행 코스를 찾고 있어요.</strong>
                        <span>날씨와 취향을 함께 살펴보는 중...</span>
                        <div class="loading-dots"><i></i><i></i><i></i></div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_card(icon: str, label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="info-card">
            <div class="info-icon">{html.escape(icon)}</div>
            <div>
                <div class="info-label">{html.escape(label)}</div>
                <div class="info-value">{html.escape(value)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_history_item(title: str, day: str) -> None:
    st.markdown(
        f"""
        <div class="history-card">
            <div class="history-title">{html.escape(title)}</div>
            <div class="history-date">{html.escape(day)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mock_preview() -> None:
    preview = get_mock_preview()
    weather_data = preview["weather"].get("data", {}) if preview["weather"].get("status") == "success" else {}
    schedule_data = preview["schedule"].get("data", {}) if preview["schedule"].get("status") == "success" else {}
    itinerary = schedule_data.get("itinerary", [])

    st.markdown('<div class="side-title">1차 추천 미리보기</div>', unsafe_allow_html=True)
    render_info_card("W", "날씨", str(weather_data.get("weather", "확인 예정")))

    if itinerary:
        first_item = itinerary[0]
        render_info_card(
            "T",
            "첫 일정",
            f"{first_item.get('time', '')} {first_item.get('place_name', '')}",
        )
    else:
        render_info_card("T", "첫 일정", "조건 입력 후 생성")


def render_left_panel() -> None:
    info = st.session_state.trip_info
    mouse_icon = image_data_uri(str(MOUSE_ICON_IMAGE))
    st.markdown(
        f"""
        <div class="brand">
            <div class="brand-icon"><img src="{mouse_icon}" alt="트립닷집"></div>
            <div>
                <div class="brand-name">트립닷집</div>
                <div class="brand-desc">AI 여행 추천 챗봇</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="side-title">나의 현재 여행 조건</div>', unsafe_allow_html=True)
    render_info_card("P", "목적지", info["destination"])
    render_info_card("D", "여행 날짜", info["date"])
    render_info_card("N", "인원", info["people"])
    render_info_card("S", "여행 스타일", info["style"])

    render_mock_preview()

    st.markdown('<div class="side-title">지난 여행 계획</div>', unsafe_allow_html=True)
    for title, day in st.session_state.history_items:
        render_history_item(title, day)

    if st.button("대화 초기화", use_container_width=True):
        reset_session_state()
        st.rerun()


def render_intro() -> None:
    if st.session_state.messages:
        return

    st.markdown(
        """
        <div class="chat-header">
            <h1>✈️ <span class="accent">AI 여행 추천</span> 챗봇</h1>
            <p>당신의 완벽한 여행지를 함께 찾아드려요 🌍</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def initialize_greeting() -> None:
    st.write("DEBUG: initialize_greeting 진입")
    print("DEBUG: initialize_greeting 진입")
    print("DEBUG: executor =", executor)

    if st.session_state.initialized:
        return

    try:
        with st.spinner("트립닷집이 준비 중이에요..."):
            init_payload = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "안녕하세요! 여행 추천을 받고 싶어요."},
            ]
            print("DEBUG: executor.run 직전")
            greeting_raw = executor.run(init_payload)
            print("DEBUG: executor.run 직후", greeting_raw)

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


def process_user_input(user_text: str) -> None:
    print("DEBUG: process_user_input 진입")
    print("DEBUG: user_text =", user_text)

    update_trip_info(user_text)
    st.session_state.messages.append(
        {"role": "user", "content": user_text, "time": now_label()}
    )
    st.session_state.quick_buttons = []

    api_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in st.session_state.messages:
        api_payload.append({"role": message["role"], "content": message["content"]})

    print("DEBUG: executor.run 직전")
    print("DEBUG: api_payload =", api_payload)

    loading_slot = st.empty()
    try:
        with loading_slot.container():
            render_loading_message()
        with st.spinner(""):
            raw_reply = executor.run(api_payload)
            print("DEBUG: executor.run 직후", raw_reply)
    except Exception as exc:
        print("DEBUG: process_user_input 예외 =", exc)
        raw_reply = f"지금은 AI 응답을 불러오지 못했어요. 설정을 확인한 뒤 다시 시도해주세요.\n\n오류: {exc}"
    finally:
        loading_slot.empty()

    reply_text, reply_buttons = parse_buttons(raw_reply)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply_text, "time": now_label()}
    )
    st.session_state.quick_buttons = reply_buttons

def render_chat_area() -> None:
    st.markdown('<div class="chat-stage">', unsafe_allow_html=True)
    render_intro()
    for message in st.session_state.messages:
        render_message(message)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.quick_buttons:
        st.markdown('<div class="quick-title">빠른 선택</div>', unsafe_allow_html=True)
        cols = st.columns(len(st.session_state.quick_buttons))
        for idx, label in enumerate(st.session_state.quick_buttons):
            with cols[idx]:
                if st.button(label, key=f"quick_{idx}", use_container_width=True):
                    st.session_state.pending_input = label
                    st.rerun()

    user_input = st.chat_input("여행에 대해 무엇이든 물어보세요...")
    if user_input and user_input.strip():
        process_user_input(user_input.strip())
        st.rerun()


load_css()
init_state()
initialize_greeting()

if st.session_state.pending_input is not None:
    pending = st.session_state.pending_input
    st.session_state.pending_input = None
    process_user_input(pending)
    st.rerun()

with st.sidebar:
    render_left_panel()

render_chat_area()
