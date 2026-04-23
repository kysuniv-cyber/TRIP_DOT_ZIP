"""
app.py

Streamlit 기반 여행 추천 챗봇의 실행 진입점(entry point)이다.

주요 역할:
- Streamlit 페이지 설정
- CSS 및 전역 상태 초기화
- 사용자 프로필 입력 여부에 따른 화면 분기
- 초기 인사 생성
- 사이드바 및 채팅 UI 렌더링
- 빠른 선택 버튼 입력 처리

구조 흐름:
1. 초기 설정 (CSS, session_state)
2. 프로필 입력 여부 확인 → 입력 안 했으면 프로필 화면
3. 초기 인사 실행
4. pending_input 처리 (빠른 버튼 클릭)
5. 사이드바 렌더링
6. 채팅 영역 렌더링
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# =========================
# 경로 설정
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# =========================
# 내부 모듈 import
# =========================
from streamlit_app.back.session_state import ensure_chat_slot_system, init_state
from streamlit_app.back.chat_logic import initialize_greeting
from streamlit_app.front.ui import (
    load_css,
    render_profile_setup,
    render_left_panel,
    render_chat_area,
)

# =========================
# Streamlit 페이지 설정
# =========================
st.set_page_config(
    page_title="트립닷집",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# 초기 설정
# =========================
load_css()
init_state()
ensure_chat_slot_system()

# =========================
# 1. 사용자 프로필 입력 단계
# =========================
if not st.session_state.get("user_profile_completed"):
    render_profile_setup()  # 프로필 입력 UI
    st.stop()               # 이후 로직 실행 중단

# =========================
# 2. 초기 인사 실행
# =========================
initialize_greeting()

# =========================
# 3. 빠른 버튼 입력 처리
# =========================
if st.session_state.pending_input is not None:
    pending = st.session_state.pending_input
    st.session_state.pending_input = None
    # lazy import (순환참조 방지)
    from streamlit_app.back.chat_logic import process_user_input

    process_user_input(pending)
    st.rerun()

# =========================
# 4. 사이드바 렌더링
# =========================
with st.sidebar:
    render_left_panel()

# =========================
# 5. 채팅 UI 렌더링
# =========================
render_chat_area()
