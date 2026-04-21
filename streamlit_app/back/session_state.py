"""
session_state.py

Streamlit 앱에서 사용하는 전역 상태(session_state)를 관리하는 모듈이다.

주요 역할:
- 채팅 메시지 및 UI 상태 초기화
- 사용자 프로필 관리
- 여행 정보(destination, date 등) 추출 및 저장
- LLM 프롬프트에 사용할 사용자 persona 컨텍스트 생성

이 파일은 Streamlit의 st.session_state를 기반으로
앱 전반에서 공유되는 데이터를 일관되게 관리한다.
"""
from __future__ import annotations

import re
from datetime import datetime
import streamlit as st


def now_label() -> str:
    """
    현재 시간을 HH:MM 형식으로 반환한다.

    Returns:
        str: 현재 시각 (예: "14:23")
    """
    return datetime.now().strftime("%H:%M")


def init_state() -> None:
    """
    Streamlit session_state를 초기화한다.

    필요한 기본 상태값들을 정의하고,
    아직 존재하지 않는 key에 대해서만 값을 세팅한다.

    주요 상태:
        - messages: 채팅 메시지 목록
        - quick_buttons: 빠른 선택 버튼
        - trip_info: 여행 정보
        - user_profile: 사용자 프로필

    Returns:
        None
    """
    defaults = {
        "messages": [],
        "quick_buttons": [],
        "initialized": False,
        "pending_input": None,
        "user_profile_completed": False,
        "user_profile": {},
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
    """
    채팅 및 여행 정보를 초기 상태로 리셋한다.

    Returns:
        None
    """
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


def reset_user_profile() -> None:
    """
    사용자 프로필을 초기화하고 전체 세션도 리셋한다.

    Returns:
        None
    """
    st.session_state.user_profile = {}
    st.session_state.user_profile_completed = False
    reset_session_state()


def format_list_value(values: list[str] | None) -> str:
    """
    리스트 형태 값을 문자열로 변환한다.

    Args:
        values (list[str] | None): 문자열 리스트

    Returns:
        str: "A, B, C" 형식 문자열 또는 "선택 안 함"
    """
    if not values:
        return "선택 안 함"
    return ", ".join(values)


def build_persona_context() -> str:
    """
    사용자 프로필 정보를 기반으로 LLM 프롬프트용 컨텍스트를 생성한다.

    Returns:
        str: 사용자 프로필 요약 텍스트
    """
    profile = st.session_state.get("user_profile", {})
    if not profile:
        return ""

    travel_styles = format_list_value(profile.get("travel_styles", []))
    avoid_styles = format_list_value(profile.get("avoid_styles", []))

    return f"""
사용자 프로필:
- 닉네임: {profile.get("nickname", "사용자")}
- 나이대: {profile.get("age_group", "선택 안 함")}
- 성별: {profile.get("gender", "선택 안 함")}
- 주요 동행자: {profile.get("companion", "선택 안 함")}
- 선호 여행 스타일: {travel_styles}
- 피하고 싶은 요소: {avoid_styles}
- 이동 강도: {profile.get("pace", "선택 안 함")}
- 실내/실외 선호: {profile.get("indoor_outdoor", "선택 안 함")}

위 프로필은 여행 추천 개인화에만 참고한다.
사용자의 현재 대화 요청과 충돌하면 현재 요청을 우선한다.
민감한 개인정보를 답변에 불필요하게 반복하지 않는다.
""".strip()


def update_trip_info(user_text: str) -> None:
    """
    사용자 입력에서 여행 정보를 추출하여 session_state에 업데이트한다.

    Args:
        user_text (str): 사용자 입력 문장

    Returns:
        None
    """
    info = st.session_state.trip_info
    text = user_text.strip()

    # =========================
    # 1. 목적지 추출
    # =========================
    destinations = [
        "강릉", "서울", "부산", "제주", "제주도", "속초", "여수", "경주", "전주",
        "대구", "인천", "대전", "광주", "성수", "홍대", "대만", "타이페이", "일본", "오사카",
    ]
    for destination in destinations:
        if destination in text:
            info["destination"] = "제주도" if destination == "제주" else destination
            break

    # =========================
    # 2. 날짜 추출
    # =========================
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

    # =========================
    # 3. 인원 추출
    # =========================
    people_match = re.search(r"(\d+)\s*(명|인|명이요|명이)", text)
    if people_match:
        info["people"] = f"{people_match.group(1)}명"

    # =========================
    # 4. 여행 스타일 추출
    # =========================
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