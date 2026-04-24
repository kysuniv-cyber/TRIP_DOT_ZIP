"""
ui.py
"""
from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

from streamlit_app.back.chat_logic import process_user_input
from streamlit_app.front.map_result import render_confirmed_plan
from streamlit_app.back.session_state import (
    clear_active_chat_slot,
    format_list_value,
    get_chat_slot_items,
    reset_user_profile,
    switch_chat_slot,
)
from streamlit_app.back.database import (
    load_profile_from_db,
    list_saved_profiles,
    save_profile_to_db,
)

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]

GUIDE_MOUSE_IMAGE = PROJECT_ROOT / "assets" / "tripdotzip_guide_mouse.png"
MOUSE_ICON_IMAGE = PROJECT_ROOT / "assets" / "tripdotzip_mouse_icon.png"


def load_css() -> None:
    css_path = BASE_DIR / "front" / "tripdotzip.css"
    if not css_path.exists():
        css_path = PROJECT_ROOT / "tripdotzip.css"

    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


@st.cache_data
def image_data_uri(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_profile_setup() -> None:
    st.markdown(
        """
        <div class="chat-header">
            <h1>여행 추천을 시작하기 전에 알려주세요</h1>
            <p>입력한 정보는 현재 세션의 추천 품질을 높이는 데만 사용됩니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info("프로필은 MySQL에 저장되며, 이후 다시 불러올 수 있습니다.")

    saved_profiles = list_saved_profiles()
    if saved_profiles:
        profile_options = {
            f"{row['nickname']} ({row['profile_id']}) - {row['updated_at']}": row["profile_id"]
            for row in saved_profiles
        }
        selected_profile = st.selectbox(
            "저장된 프로필 불러오기",
            ["새 프로필 만들기", *profile_options.keys()],
        )
        if selected_profile != "새 프로필 만들기" and st.button("선택한 프로필로 시작", use_container_width=True):
            loaded_profile = load_profile_from_db(profile_options[selected_profile])
            if loaded_profile:
                st.session_state.user_profile = loaded_profile
                st.session_state.user_profile_completed = True
                st.session_state.initialized = False
                st.rerun()

    with st.form("persona_profile_form"):
        nickname = st.text_input("닉네임 또는 이름", placeholder="예: 민지")
        col1, col2 = st.columns(2)
        with col1:
            age_group = st.selectbox("연령대", ["선택 안함", "10대", "20대", "30대", "40대", "50대", "60대 이상"])
        with col2:
            gender = st.selectbox("성별", ["선택 안함", "여성", "남성", "기타"])

        companion = st.selectbox(
            "주요 동행",
            ["선택 안함", "혼자", "친구", "연인", "가족", "부모님", "아이 동반"],
        )
        travel_styles = st.multiselect(
            "선호 여행 스타일",
            ["맛집", "카페", "자연", "실내", "액티비티", "휴식", "쇼핑", "문화/전시", "사진 명소"],
        )
        avoid_styles = st.multiselect(
            "피하고 싶은 요소",
            ["많이 걷기", "긴 이동", "야외 위주", "웨이팅 긴 곳", "비싼 곳", "계단 많은 곳"],
        )

        col3, col4 = st.columns(2)
        with col3:
            pace = st.selectbox("이동 강도", ["선택 안함", "여유롭게", "보통", "빽빽해도 괜찮음"])
        with col4:
            indoor_outdoor = st.selectbox("실내/실외 선호", ["선택 안함", "실내 위주", "실외 위주", "상관 없음"])

        submitted = st.form_submit_button("채팅 시작하기", use_container_width=True)

    if submitted:
        resolved_profile_id = nickname.strip() or "default_user"
        st.session_state.user_profile = {
            "profile_id": resolved_profile_id,
            "nickname": nickname.strip() or "사용자",
            "age_group": age_group,
            "gender": gender,
            "companion": companion,
            "travel_styles": travel_styles,
            "avoid_styles": avoid_styles,
            "pace": pace,
            "indoor_outdoor": indoor_outdoor,
        }
        save_profile_to_db(st.session_state.user_profile)
        st.session_state.user_profile_completed = True
        st.session_state.initialized = False
        st.rerun()


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
                        <strong>트립닷집이 여행 코스를 찾고 있어요</strong>
                        <span>날씨와 취향을 함께 보고 있는 중...</span>
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
                <div class="info-value">{html.escape(str(value))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    profile = st.session_state.get("user_profile", {})
    if profile:
        st.markdown('<div class="side-title">나의 프로필</div>', unsafe_allow_html=True)
        render_info_card("U", "닉네임", profile.get("nickname", "사용자"))
        render_info_card("A", "연령대", profile.get("age_group", "선택 안함"))
        render_info_card("G", "성별", profile.get("gender", "선택 안함"))
        render_info_card("T", "선호 스타일", format_list_value(profile.get("travel_styles", [])))
        render_info_card("C", "동행", profile.get("companion", "선택 안함"))

        if st.button("프로필 다시 설정", use_container_width=True):
            reset_user_profile()
            st.rerun()

    st.markdown('<div class="side-title">채팅 전환</div>', unsafe_allow_html=True)
    for item in get_chat_slot_items():
        count_text = f"메시지 {item['message_count']}개"
        active_prefix = "● " if item["active"] else ""
        label = f"{active_prefix}{item['title']} | {count_text}"
        if st.button(label, key=f"chat_slot_{item['slot_id']}", use_container_width=True):
            switch_chat_slot(item["slot_id"])
            st.rerun()

    if st.button("현재 채팅 비우기", use_container_width=True):
        clear_active_chat_slot()
        st.rerun()

    st.markdown('<div class="side-title">일정 확정</div>', unsafe_allow_html=True)
    has_itinerary = bool(st.session_state.get("itinerary"))

    if st.button("일정 확정", use_container_width=True, disabled=not has_itinerary):
        # 현재 생성된 일정을 확정 화면에서 그대로 보여주기 위해 별도 상태에 저장합니다.
        st.session_state.confirmed_itinerary = list(st.session_state.get("itinerary", []))
        st.session_state.show_confirmed_plan = True
        st.rerun()

    if not has_itinerary:
        st.caption("일정이 생성되면 확정 버튼을 누를 수 있습니다.")


def render_intro() -> None:
    if st.session_state.messages:
        return

    st.markdown(
        """
        <div class="chat-header">
            <h1>딱맞는 <span class="accent">AI 여행 추천</span> 챗봇</h1>
            <p>당신의 일정과 취향에 맞는 여행지를 함께 찾아드릴게요</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    if st.session_state.get("show_confirmed_plan"):
        # 확정된 일정은 채팅 아래에서 표와 지도를 함께 보여줍니다.
        render_confirmed_plan()

    user_input = st.chat_input("여행에 대해 무엇이든 물어보세요...")
    if user_input and user_input.strip():
        loading_slot = st.empty()
        with loading_slot.container():
            render_loading_message()
        process_user_input(user_input.strip())
        loading_slot.empty()
        st.rerun()
