"""
ui.py

Streamlit 기반 여행 추천 챗봇의 사용자 인터페이스(UI) 렌더링을 담당하는 모듈이다.

주요 역할:
- CSS 로드
- 프로필 입력 폼 렌더링
- 채팅 메시지 UI 렌더링
- 사이드바 정보/미리보기 렌더링
- 사용자 입력창(chat_input) 처리

이 모듈은 화면 표시 전용 레이어로,
실제 대화 처리 로직은 chat_logic.py,
상태 관리는 session_state.py에서 담당한다.
"""
from __future__ import annotations

import base64
import html
from pathlib import Path
import streamlit as st

from streamlit_app.back.session_state import (
    format_list_value,
    reset_session_state,
    reset_user_profile,
)
from streamlit_app.back.chat_logic import get_mock_preview, process_user_input

# =========================
# 경로 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = Path(__file__).resolve().parents[1]

GUIDE_MOUSE_IMAGE = ROOT_DIR / "assets" / "tripdotzip_guide_mouse.png"
MOUSE_ICON_IMAGE = ROOT_DIR / "assets" / "tripdotzip_mouse_icon.png"


def load_css() -> None:
    """
    Streamlit 앱에 CSS 스타일 파일을 로드한다.

    우선 front 폴더의 tripdotzip.css를 찾고,
    없으면 루트 경로의 css 파일을 fallback으로 사용한다.

    Returns:
        None
    """
    css_path = ROOT_DIR / "front" / "tripdotzip.css"
    if not css_path.exists():
        css_path = ROOT_DIR / "tripdotzip.css"

    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


@st.cache_data
def image_data_uri(path_text: str) -> str:
    """
    이미지 파일을 base64 data URI 문자열로 변환한다.

    Args:
        path_text (str): 이미지 파일 경로 문자열

    Returns:
        str: HTML img 태그에 사용할 data URI 문자열
    """
    path = Path(path_text)
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_profile_setup() -> None:
    """
    사용자 프로필 입력 폼을 렌더링한다.

    사용자가 여행 선호도, 동행자, 스타일 등을 입력하면
    session_state.user_profile에 저장하고 채팅 시작 상태로 전환한다.

    Returns:
        None
    """
    st.markdown(
        """
        <div class="chat-header">
            <h1>여행 추천을 시작하기 전에 알려주세요</h1>
            <p>입력한 정보는 현재 세션에서만 맞춤 추천에 사용됩니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("persona_profile_form"):
        nickname = st.text_input("닉네임 또는 이름", placeholder="예: 홍길동")
        col1, col2 = st.columns(2)

        with col1:
            age_group = st.selectbox(
                "나이대",
                ["선택 안 함", "10대", "20대", "30대", "40대", "50대", "60대 이상"],
            )
        with col2:
            gender = st.selectbox(
                "성별",
                ["선택 안 함", "남성", "여성", "기타"],
            )

        companion = st.selectbox(
            "주요 동행자",
            ["선택 안 함", "혼자", "친구", "연인", "가족", "부모님", "아이 동반"],
        )
        travel_styles = st.multiselect(
            "선호 여행 스타일",
            ["맛집", "카페", "자연", "실내", "액티비티", "휴식", "쇼핑", "문화/전시", "사진 명소"],
        )
        avoid_styles = st.multiselect(
            "피하고 싶은 요소",
            ["많이 걷기", "긴 이동", "야외 위주", "혼잡한 곳", "비싼 곳", "계단 많은 곳"],
        )

        col3, col4 = st.columns(2)
        with col3:
            pace = st.selectbox(
                "이동 강도",
                ["선택 안 함", "느긋하게", "보통", "빡빡해도 괜찮음"],
            )
        with col4:
            indoor_outdoor = st.selectbox(
                "실내/실외 선호",
                ["선택 안 함", "실내 위주", "실외 위주", "상관 없음"],
            )

        submitted = st.form_submit_button("채팅 시작하기", use_container_width=True)

    if submitted:
        st.session_state.user_profile = {
            "nickname": nickname.strip() or "사용자",
            "age_group": age_group,
            "gender": gender,
            "companion": companion,
            "travel_styles": travel_styles,
            "avoid_styles": avoid_styles,
            "pace": pace,
            "indoor_outdoor": indoor_outdoor,
        }
        st.session_state.user_profile_completed = True
        st.session_state.initialized = False
        st.rerun()


def render_message(message: dict) -> None:
    """
    채팅 메시지 한 개를 버블 형태로 렌더링한다.

    Args:
        message (dict): role, content, time 정보를 담은 메시지 딕셔너리

    Returns:
        None
    """
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
    """
    챗봇이 응답을 생성하는 동안 표시할 로딩 UI를 렌더링한다.

    Returns:
        None
    """

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
    """
    사이드바 정보 카드를 렌더링한다.

    Args:
        icon (str): 카드 아이콘
        label (str): 카드 제목
        value (str): 카드 값

    Returns:
        None
    """
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
    """
    지난 여행 기록 카드 한 개를 렌더링한다.

    Args:
        title (str): 여행 제목
        day (str): 여행 날짜

    Returns:
        None
    """
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
    """
    사이드바용 1차 추천 미리보기를 렌더링한다.

    Returns:
        None
    """
    preview = get_mock_preview()
    weather_data = (
        preview["weather"].get("data", {})
        if preview["weather"].get("status") == "success"
        else {}
    )
    schedule_data = (
        preview["schedule"].get("data", {})
        if preview["schedule"].get("status") == "success"
        else {}
    )
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
    """
    Streamlit 사이드바 전체를 렌더링한다.

    포함 내용:
    - 브랜드 영역
    - 현재 여행 조건
    - 사용자 프로필
    - 1차 추천 미리보기
    - 지난 여행 계획
    - 초기화 버튼

    Returns:
        None
    """
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

    # 현재 입력된 여행 조건
    st.markdown('<div class="side-title">나의 현재 여행 조건</div>', unsafe_allow_html=True)
    render_info_card("P", "목적지", info["destination"])
    render_info_card("D", "여행 날짜", info["date"])
    render_info_card("N", "인원", info["people"])
    render_info_card("S", "여행 스타일", info["style"])

    # 사용자 프로필 정보
    profile = st.session_state.get("user_profile", {})
    if profile:
        st.markdown('<div class="side-title">나의 프로필</div>', unsafe_allow_html=True)
        render_info_card("U", "닉네임", profile.get("nickname", "사용자"))
        render_info_card("A", "나이대", profile.get("age_group", "선택 안 함"))
        render_info_card("G", "성별", profile.get("gender", "선택 안 함"))
        render_info_card("T", "선호 스타일", format_list_value(profile.get("travel_styles", [])))
        render_info_card("C", "동행자", profile.get("companion", "선택 안 함"))

        if st.button("프로필 다시 설정", use_container_width=True):
            reset_user_profile()
            st.rerun()

    # 미리보기 영역
    render_mock_preview()

    # 지난 여행 기록
    st.markdown('<div class="side-title">지난 여행 계획</div>', unsafe_allow_html=True)
    for title, day in st.session_state.history_items:
        render_history_item(title, day)

    # 대화 초기화 버튼
    if st.button("대화 초기화", use_container_width=True):
        reset_session_state()
        st.rerun()


def render_intro() -> None:
    """
    채팅 시작 전 인트로 헤더를 렌더링한다.

    Returns:
        None
    """
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


def render_chat_area() -> None:
    """
    메인 채팅 영역을 렌더링한다.

    포함 내용:
    - 인트로 헤더
    - 채팅 메시지 목록
    - 빠른 선택 버튼
    - 사용자 입력창
    - 입력 후 process_user_input 실행

    Returns:
        None
    """
    st.markdown('<div class="chat-stage">', unsafe_allow_html=True)
    render_intro()

    # 채팅 메시지 출력
    for message in st.session_state.messages:
        render_message(message)

    st.markdown("</div>", unsafe_allow_html=True)

    # 빠른 선택 버튼 렌더링
    if st.session_state.quick_buttons:
        st.markdown('<div class="quick-title">빠른 선택</div>', unsafe_allow_html=True)
        cols = st.columns(len(st.session_state.quick_buttons))
        for idx, label in enumerate(st.session_state.quick_buttons):
            with cols[idx]:
                if st.button(label, key=f"quick_{idx}", use_container_width=True):
                    st.session_state.pending_input = label
                    st.rerun()

    # 채팅 입력창
    user_input = st.chat_input("여행에 대해 무엇이든 물어보세요...")
    if user_input and user_input.strip():
        loading_slot = st.empty()
        with loading_slot.container():
            render_loading_message()
        process_user_input(user_input.strip())
        loading_slot.empty()
        st.rerun()