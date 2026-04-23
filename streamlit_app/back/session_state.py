"""
session_state.py
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
import re
from datetime import datetime
from pathlib import Path

import mysql.connector
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "tripdotzip")

CHAT_SLOT_IDS = ("chat_1", "chat_2")
CHAT_STATE_KEYS = (
    "messages",
    "quick_buttons",
    "initialized",
    "pending_input",
    "trip_info",
    "destination",
    "styles",
    "constraints",
    "travel_date",
    "start_time",
    "selected_places",
    "mapped_places",
    "itinerary",
)


def now_label() -> str:
    return datetime.now().strftime("%H:%M")


def default_trip_info() -> dict:
    return {
        "destination": "미정",
        "date": "미정",
        "people": "미정",
        "style": "미정",
    }


def ensure_profile_database() -> None:
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        auth_plugin="mysql_native_password",
        use_pure=True,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
        )
        conn.commit()
    finally:
        conn.close()


def get_profile_db_connection():
    ensure_profile_database()
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        auth_plugin="mysql_native_password",
        use_pure=True,
    )
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS persona_profiles (
            profile_id VARCHAR(255) PRIMARY KEY,
            nickname VARCHAR(255) NOT NULL,
            profile_json JSON NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def list_saved_profiles() -> list[dict]:
    conn = get_profile_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT profile_id, nickname, updated_at
            FROM persona_profiles
            ORDER BY updated_at DESC
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [
        {"profile_id": row[0], "nickname": row[1], "updated_at": str(row[2])}
        for row in rows
    ]


def load_profile_from_db(profile_id: str) -> dict | None:
    conn = get_profile_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT profile_json FROM persona_profiles WHERE profile_id = %s",
            (profile_id,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    payload = row[0]
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8")
    return json.loads(payload)


def save_profile_to_db(profile: dict) -> None:
    profile_id = profile["profile_id"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_profile_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO persona_profiles (profile_id, nickname, profile_json, updated_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                nickname = VALUES(nickname),
                profile_json = VALUES(profile_json),
                updated_at = VALUES(updated_at)
            """,
            (
                profile_id,
                profile.get("nickname", "사용자"),
                json.dumps(profile, ensure_ascii=False),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def build_empty_chat_slot(slot_id: str, title: str) -> dict:
    return {
        "slot_id": slot_id,
        "title": title,
        "messages": [],
        "quick_buttons": [],
        "initialized": False,
        "pending_input": None,
        "trip_info": default_trip_info(),
        "destination": None,
        "styles": [],
        "constraints": [],
        "travel_date": None,
        "start_time": None,
        "selected_places": [],
        "mapped_places": [],
        "itinerary": [],
    }


def _copy_slot_payload(slot: dict) -> dict:
    return {key: deepcopy(slot.get(key)) for key in CHAT_STATE_KEYS}


def _capture_current_chat_state() -> dict:
    return {key: deepcopy(st.session_state.get(key)) for key in CHAT_STATE_KEYS}


def _derive_chat_slot_title(slot: dict, fallback: str) -> str:
    for message in slot.get("messages", []):
        if message.get("role") == "user":
            text = str(message.get("content", "")).strip()
            if text:
                return text[:18] + ("..." if len(text) > 18 else "")
    return fallback


def sync_active_chat_slot() -> None:
    slot_id = st.session_state.get("active_chat_slot", CHAT_SLOT_IDS[0])
    slots = st.session_state.get("chat_slots", {})
    if slot_id not in slots:
        return

    slot = deepcopy(slots[slot_id])
    slot.update(_capture_current_chat_state())
    fallback = "현재 대화" if slot_id == CHAT_SLOT_IDS[0] else "보관 대화"
    slot["title"] = _derive_chat_slot_title(slot, fallback)
    slots[slot_id] = slot
    st.session_state.chat_slots = slots


def switch_chat_slot(slot_id: str) -> None:
    if slot_id not in CHAT_SLOT_IDS:
        return

    if "chat_slots" not in st.session_state:
        return

    sync_active_chat_slot()
    slot = deepcopy(st.session_state.chat_slots[slot_id])
    for key, value in _copy_slot_payload(slot).items():
        st.session_state[key] = value
    st.session_state.active_chat_slot = slot_id


def get_chat_slot_items() -> list[dict]:
    slots = st.session_state.get("chat_slots", {})
    items = []
    for slot_id in CHAT_SLOT_IDS:
        fallback = "현재 대화" if slot_id == CHAT_SLOT_IDS[0] else "보관 대화"
        slot = slots.get(slot_id, build_empty_chat_slot(slot_id, fallback))
        items.append(
            {
                "slot_id": slot_id,
                "title": slot.get("title") or fallback,
                "message_count": len(slot.get("messages", [])),
                "active": st.session_state.get("active_chat_slot") == slot_id,
            }
        )
    return items


def ensure_chat_slot_system() -> None:
    if "active_chat_slot" not in st.session_state:
        st.session_state.active_chat_slot = CHAT_SLOT_IDS[0]

    if "chat_slots" not in st.session_state:
        st.session_state.chat_slots = {
            CHAT_SLOT_IDS[0]: build_empty_chat_slot(CHAT_SLOT_IDS[0], "현재 대화"),
            CHAT_SLOT_IDS[1]: build_empty_chat_slot(CHAT_SLOT_IDS[1], "보관 대화"),
        }

    for key, default in {
        "destination": None,
        "styles": [],
        "constraints": [],
        "travel_date": None,
        "start_time": None,
        "selected_places": [],
        "mapped_places": [],
        "itinerary": [],
    }.items():
        if key not in st.session_state:
            st.session_state[key] = deepcopy(default)

    if "_chat_slots_ready" not in st.session_state:
        st.session_state._chat_slots_ready = True
        slot = deepcopy(st.session_state.chat_slots[st.session_state.active_chat_slot])
        for key, value in _copy_slot_payload(slot).items():
            st.session_state[key] = value
    else:
        sync_active_chat_slot()


def clear_active_chat_slot() -> None:
    slot_id = st.session_state.get("active_chat_slot", CHAT_SLOT_IDS[0])
    title = "현재 대화" if slot_id == CHAT_SLOT_IDS[0] else "보관 대화"
    empty_slot = build_empty_chat_slot(slot_id, title)
    st.session_state.chat_slots[slot_id] = empty_slot
    for key, value in _copy_slot_payload(empty_slot).items():
        st.session_state[key] = value


def init_state() -> None:
    defaults = {
        "messages": [],
        "quick_buttons": [],
        "initialized": False,
        "pending_input": None,
        "user_profile_completed": False,
        "user_profile": {},
        "trip_info": default_trip_info(),
        "history_items": [
            ("대만 타이페이 3박4일", "2025.12.20"),
            ("제주도 맛집 여행 2박3일", "2025.09.15"),
            ("부산 해운대 힐링", "2025.07.08"),
        ],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state() -> None:
    clear_active_chat_slot()


def reset_user_profile() -> None:
    st.session_state.user_profile = {}
    st.session_state.user_profile_completed = False
    clear_active_chat_slot()


def format_list_value(values: list[str] | None) -> str:
    if not values:
        return "선택 안함"
    return ", ".join(values)


def build_persona_context() -> str:
    profile = st.session_state.get("user_profile", {})
    if not profile:
        return ""

    travel_styles = format_list_value(profile.get("travel_styles", []))
    avoid_styles = format_list_value(profile.get("avoid_styles", []))

    return f"""
사용자 프로필
- 닉네임: {profile.get("nickname", "사용자")}
- 연령대: {profile.get("age_group", "선택 안함")}
- 성별: {profile.get("gender", "선택 안함")}
- 주요 동행: {profile.get("companion", "선택 안함")}
- 선호 여행 스타일: {travel_styles}
- 피하고 싶은 요소: {avoid_styles}
- 이동 강도: {profile.get("pace", "선택 안함")}
- 실내/실외 선호: {profile.get("indoor_outdoor", "선택 안함")}

이 프로필은 여행 추천 개인화에만 참고한다.
사용자의 현재 대화 요청과 충돌하면 현재 요청을 우선한다.
""".strip()


def update_trip_info(user_text: str) -> None:
    info = st.session_state.trip_info
    text = user_text.strip()

    destinations = [
        "강릉", "서울", "부산", "제주", "제주도", "속초", "여수", "경주", "전주",
        "대구", "인천", "대전", "광주", "성수", "남해", "대만", "타이페이", "일본", "오사카",
    ]
    for destination in destinations:
        if destination in text:
            info["destination"] = "제주도" if destination == "제주" else destination
            break

    date_patterns = [
        r"(\d{4})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})",
        r"(\d{1,2})\s*월\s*(\d{1,2})\s*일",
        r"(\d{1,2})[.\-/](\d{1,2})",
    ]
    for pattern in date_patterns:
        matched = re.search(pattern, text)
        if not matched:
            continue
        groups = matched.groups()
        if len(groups) == 3:
            if len(groups[0]) == 4:
                info["date"] = f"{groups[0]}.{int(groups[1]):02d}.{int(groups[2]):02d}"
            else:
                current_year = datetime.now().year
                info["date"] = f"{current_year}.{int(groups[0]):02d}.{int(groups[1]):02d}"
        elif len(groups) == 2:
            current_year = datetime.now().year
            info["date"] = f"{current_year}.{int(groups[0]):02d}.{int(groups[1]):02d}"
        break

    companions = {
        "혼자": "혼자",
        "친구": "친구",
        "연인": "연인",
        "가족": "가족",
        "부모님": "부모님",
        "아이": "아이 동반",
    }
    for keyword, label in companions.items():
        if keyword in text:
            info["people"] = label
            break

    styles = []
    for keyword in ["맛집", "카페", "쇼핑", "전시", "자연", "실내", "액티비티", "휴식"]:
        if keyword in text:
            styles.append(keyword)
    if styles:
        info["style"] = ", ".join(styles)
