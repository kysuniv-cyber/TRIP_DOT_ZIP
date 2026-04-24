"""
    Filename: database.py
    Path: streamlit_app/back/database.py
    Role: SQL DB(MySQL DB)와 연결 및 SQL 로직
"""
from config import Settings
import json
from datetime import datetime
import mysql.connector
from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys


MYSQL_HOST = Settings.MYSQL_HOST
MYSQL_USER = Settings.MYSQL_USER
MYSQL_PASSWORD = Settings.MYSQL_PASSWORD
MYSQL_DATABASE = Settings.MYSQL_DATABASE


def get_db_connection():
    return mysql.connector.connect(
        host=Settings.MYSQL_HOST,
        user=Settings.MYSQL_USER,
        password=Settings.MYSQL_PASSWORD,
        database=Settings.MYSQL_DATABASE,
        auth_plugin="mysql_native_password"
    )

def ensure_profile_database() -> None:
    conn = get_db_connection()

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

    # profile table 생성
    ensure_profile_database()

    # 연결
    conn = get_db_connection()
    
    cursor = conn.cursor()

    # 1. persona_profiles
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

     # 2. trip_masters
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trip_masters (
            trip_id INT AUTO_INCREMENT PRIMARY KEY,
            profile_id VARCHAR(255),
            destination VARCHAR(100) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES persona_profiles(profile_id) ON DELETE CASCADE
        )
    """)

    # 3. trip_details
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trip_details (
            detail_id INT AUTO_INCREMENT PRIMARY KEY,
            trip_id INT,
            place_name VARCHAR(255) NOT NULL,
            place_category VARCHAR(50),
            visit_order INT,
            FOREIGN KEY (trip_id) REFERENCES trip_masters(trip_id) ON DELETE CASCADE
        )
    """)
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

def save_trip_log_to_db(profile:dict, final_state: dict) -> None:
    profile_id = profile["profile_id"]
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_profile_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO persona_profiles (profile_id, nickname, age_group, gender, companion, travel_styles, pace)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                nickname=VALUES(nickname), age_group=VALUES(age_group), 
                gender=VALUES(gender), companion=VALUES(companion), 
                travel_styles=VALUES(travel_styles), pace=VALUES(pace)
            """,
            (
                profile_id,
                profile.get("nickname", "사용자"),
                json.dumps(profile, ensure_ascii=False),
                now,
            ),
        )

        cursor.execute(
            """
            INSERT INTO persona_profiles (profile_id, nickname, age_group, gender, companion, travel_styles, pace)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                nickname=VALUES(nickname), age_group=VALUES(age_group), 
                gender=VALUES(gender), companion=VALUES(companion), 
                travel_styles=VALUES(travel_styles), pace=VALUES(pace)
            """,
            (
                profile_id,
                profile.get("nickname", "사용자"),
                json.dumps(profile, ensure_ascii=False),
                now,
            ),
        )

        master_sql = "INSERT INTO trip_masters (profile_id, destination) VALUES (%s, %s)"
        cursor.execute(master_sql, (profile_id, final_state.get(StateKeys.DESTINATION, "미정")))
        trip_id = cursor.lastrowid # 생성된 trip_id 획득

        # 3. 상세 방문지 저장 (리스트 형태의 방문지를 개별 로우로 삽입)
        # final_state['selected_places']가 ['장소A', '장소B', '장소C'] 형태라고 가정
        detail_sql = "INSERT INTO trip_details (trip_id, place_name, visit_order) VALUES (%s, %s, %s)"
        
        selected_places = final_state.get(StateKeys.ITINERARY, [])
        for i, place in enumerate(selected_places, start=1):
            cursor.execute(detail_sql, (trip_id, place, i))

        conn.commit()
    
    finally:
        conn.close()
