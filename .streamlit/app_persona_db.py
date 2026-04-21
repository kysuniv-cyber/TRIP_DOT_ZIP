from __future__ import annotations

import sys
import html
import base64
import re
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

ROOT_DIR = Path(__file__).resolve().parents[1]

from test_backup.mock_tools.place_tools import search_places
from test_backup.mock_tools.schedule_tools import build_schedule
from test_backup.mock_tools import get_weather
from test_backup.mock_tools import get_weather_from_prompt

from llm.prompts import SYSTEM_PROMPT
from test_backup.proto import parse_buttons
from agent_builder import agent

load_dotenv(ROOT_DIR / ".env")

GUIDE_MOUSE_IMAGE = ROOT_DIR / "assets" / "tripdotzip_guide_mouse.png"
MOUSE_ICON_IMAGE = ROOT_DIR / "assets" / "tripdotzip_mouse_icon.png"
PROFILE_DB_PATH = ROOT_DIR / "data" / "persona_profiles.sqlite3"


st.set_page_config(
    page_title="트립닷집",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css() -> None:
    css_path = Path(__file__).with_name("tripdotzip.css")
    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


def now_label() -> str:
    return datetime.now().strftime("%H:%M")


@st.cache_data
def image_data_uri(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def extract_message_text(content) -> str:
    """LangChain message content를 안전하게 문자열로 변환한다."""
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


def init_state() -> None:
    defaults = {
        "messages": [],
        "quick_buttons": [],
        "initialized": False,
        "pending_input": None,
        # Persona gate state. This DB version also persists profiles to local SQLite.
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
    # Reset both persona and chat state so the next run starts from the profile form.
    st.session_state.user_profile = {}
    st.session_state.user_profile_completed = False
    reset_session_state()


def format_list_value(values: list[str] | None) -> str:
    # Sidebar/profile prompt helper for optional multiselect values.
    if not values:
        return "선택 안 함"
    return ", ".join(values)


def build_persona_context() -> str:
    # Convert the profile form values into a system message for the agent.
    # The profile is guidance only; the user's current request must still win.
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


def get_profile_db_connection() -> sqlite3.Connection:
    # Local SQLite storage for profiles that should survive Streamlit restarts.
    PROFILE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(PROFILE_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS persona_profiles (
            profile_id TEXT PRIMARY KEY,
            nickname TEXT NOT NULL,
            profile_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def list_saved_profiles() -> list[dict]:
    # Return lightweight profile rows for the "load saved persona" selector.
    with get_profile_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT profile_id, nickname, updated_at
            FROM persona_profiles
            ORDER BY updated_at DESC
            """
        ).fetchall()

    return [
        {"profile_id": row[0], "nickname": row[1], "updated_at": row[2]}
        for row in rows
    ]


def load_profile_from_db(profile_id: str) -> dict | None:
    # Load the full profile payload by id.
    with get_profile_db_connection() as conn:
        row = conn.execute(
            "SELECT profile_json FROM persona_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()

    if not row:
        return None
    return json.loads(row[0])


def save_profile_to_db(profile: dict) -> None:
    # Upsert persona profile for later reuse. No chat messages are stored here.
    profile_id = profile["profile_id"]
    now = datetime.now().isoformat(timespec="seconds")

    with get_profile_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO persona_profiles (profile_id, nickname, profile_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET
                nickname = excluded.nickname,
                profile_json = excluded.profile_json,
                updated_at = excluded.updated_at
            """,
            (
                profile_id,
                profile.get("nickname", "사용자"),
                json.dumps(profile, ensure_ascii=False),
                now,
            ),
        )


def render_profile_setup() -> None:
    # First screen for this copied app: collect lightweight persona data before chat starts.
    st.markdown(
        """
        <div class="chat-header">
            <h1>여행 추천을 시작하기 전에 알려주세요</h1>
            <p>입력한 정보는 현재 세션에서만 맞춤 추천에 사용됩니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(f"DB 저장 버전입니다. 프로필은 로컬 SQLite 파일에 저장됩니다: {PROFILE_DB_PATH}")

    # Saved profile loader for the DB-backed persona app.
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
        if selected_profile != "새 프로필 만들기" and st.button("선택한 프로필로 시작하기"):
            loaded_profile = load_profile_from_db(profile_options[selected_profile])
            if loaded_profile:
                st.session_state.user_profile = loaded_profile
                st.session_state.user_profile_completed = True
                st.session_state.initialized = False
                st.rerun()

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
        # Save to both current session and local SQLite for later reuse.
        # Use nickname as the local profile key so users do not need a separate id field.
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
        # Show the active persona in the existing sidebar so users can verify the context.
        st.markdown('<div class="side-title">나의 프로필</div>', unsafe_allow_html=True)
        render_info_card("U", "닉네임", profile.get("nickname", "사용자"))
        render_info_card("A", "나이대", profile.get("age_group", "선택 안 함"))
        render_info_card("G", "성별", profile.get("gender", "선택 안 함"))
        render_info_card("T", "선호 스타일", format_list_value(profile.get("travel_styles", [])))
        render_info_card("C", "동행자", profile.get("companion", "선택 안 함"))

        if st.button("프로필 다시 설정", use_container_width=True):
            # Return to the profile form and clear chat state tied to the old persona.
            reset_user_profile()
            st.rerun()

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

    if st.session_state.initialized:
        return

    try:
        with st.spinner("트립닷집이 준비 중이에요..."):
            print("DEBUG: executor.run 직전")
            response = agent.invoke(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        # Persona context is passed as a second system message for personalization.
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

    loading_slot = st.empty()
    try:
        with loading_slot.container():
            render_loading_message()

        with st.spinner(""):
            # =========================
            # 1. 날씨 질문이면 tool 직접 호출
            # =========================
            if "날씨" in user_text:


                city_name = st.session_state.trip_info["destination"]
                if city_name == "미정":
                    city_name = "서울"

                # 아주 단순한 상대 날짜 추출
                travel_date = None
                if "다음주 토요일" in user_text or "다음 주 토요일" in user_text:
                    travel_date = "다음주 토요일"
                elif "내일" in user_text:
                    travel_date = "내일"
                elif "모레" in user_text:
                    travel_date = "모레"

                print("🔥 FORCE TOOL CALL")
                print("DEBUG direct weather city_name =", city_name)
                print("DEBUG direct weather travel_date =", travel_date)

                tool_result = get_weather_from_prompt.invoke(
                    {"user_prompt": user_text}
                )

                print("DEBUG tool_result =", tool_result)

                # tool 결과를 사용자용 문장으로 변환
                if tool_result.get("status") == "error":
                    raw_reply = (
                        f"날씨 정보를 불러오지 못했어요.\n"
                        f"오류: {tool_result.get('message', '알 수 없는 오류')}"
                    )
                else:
                    data = tool_result.get("data", {})
                    result_data = data.get("result", {})

                    weather_info = result_data.get("weather", {})
                    ddatchwi_info = result_data.get("ddatchwi", {})

                    weather_text = weather_info.get("description", "정보 없음")
                    ddatchwi_character = ddatchwi_info.get("character", "")
                    ddatchwi_text = ddatchwi_info.get("message", "참고 정보가 없어요.")
                    display_city = data.get("display_city_name", city_name)
                    resolved_date = data.get("resolved_travel_date", travel_date)

                    raw_reply = (
                        f"{display_city} 날씨 조회 결과예요.\n"
                        f"- 날짜: {resolved_date}\n"
                        f"- 날씨: {weather_text}\n\n"
                        f"{ddatchwi_character}\n"
                        f"{ddatchwi_text}"
                    )
            # =========================
            # 2. 그 외 질문은 기존 agent 사용
            # =========================
            else:
                response = agent.invoke(
                    {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            # Keep persona context in every agent call because session history is rebuilt each turn.
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

# Block chat rendering until the user completes the persona form.
if not st.session_state.get("user_profile_completed"):
    render_profile_setup()
    st.stop()

initialize_greeting()

if st.session_state.pending_input is not None:
    pending = st.session_state.pending_input
    st.session_state.pending_input = None
    process_user_input(pending)
    st.rerun()

with st.sidebar:
    render_left_panel()

render_chat_area()
