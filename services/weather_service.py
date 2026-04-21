# services/weather_service.py

import json
from datetime import date, datetime, timedelta

import openai
import requests

from config import Settings
from llm.prompts import SYSTEM_PROMPT


# -----------------------------
# 0. 설정
# -----------------------------
settings = Settings()
weather_api_key = settings.weather_api_key
openai_api_key = settings.openai_api_key
client = openai.OpenAI(api_key=openai_api_key)


# -----------------------------
# 도시명 변환용 맵
# 사용자에게는 한국어로 보여주고,
# API 호출할 때만 영어 표준명으로 변환
# -----------------------------
CITY_NAME_MAP = {
    "서울": "Seoul",
    "부산": "Busan",
    "전주": "Jeonju",
    "제주": "Jeju",
    "대구": "Daegu",
    "대전": "Daejeon",
    "광주": "Gwangju",
    "인천": "Incheon",
    "울산": "Ulsan",
    "수원": "Suwon",
    "경주": "Gyeongju",
    "여수": "Yeosu",
    "속초": "Sokcho",
    "강릉": "Gangneung",
    "춘천": "Chuncheon",
    "포항": "Pohang",
    "목포": "Mokpo",
    "도쿄": "Tokyo",
    "오사카": "Osaka",
    "후쿠오카": "Fukuoka",
    "교토": "Kyoto",
    "삿포로": "Sapporo",
}


def normalize_city_name_for_weather(city_name: str | None) -> str:
    """
    사용자 입력 도시명을 날씨 API 호출용 표준 도시명으로 변환한다.

    Args:
        city_name (str | None): 사용자 입력 도시명

    Returns:
        str: API 호출용 도시명
    """
    if not city_name:
        return "Seoul"
    return CITY_NAME_MAP.get(city_name, city_name)


# -----------------------------
# 1. 현재 날씨 조회
# -----------------------------
def get_current_weather(city_name: str = "Seoul", units: str = "metric") -> str:
    """
    OpenWeather API를 사용하여 지정 도시의 현재 날씨 정보를 조회한다.

    Args:
        city_name (str): 날씨 정보를 가져올 도시 이름
        units (str): 온도 단위
            - metric: 섭씨
            - imperial: 화씨
            - standard: 절대온도

    Returns:
        str: JSON 문자열 형태의 날씨 정보
    """
    if not weather_api_key:
        return json.dumps(
            {
                "status": "error",
                "message": "weather_api_key가 설정되지 않았습니다.",
            },
            ensure_ascii=False,
        )

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name,
        "appid": weather_api_key,
        "units": units,
        "lang": "kr",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if response.status_code == 200:
            weather_info = {
                "status": "success",
                "city": data.get("name", city_name),
                "country": data.get("sys", {}).get("country"),
                "description": data.get("weather", [{}])[0].get("description", "정보 없음"),
                "temperature": data.get("main", {}).get("temp"),
                "temperature_feels_like": data.get("main", {}).get("feels_like"),
                "temp_min": data.get("main", {}).get("temp_min"),
                "temp_max": data.get("main", {}).get("temp_max"),
                "humidity": data.get("main", {}).get("humidity"),
                "pressure": data.get("main", {}).get("pressure"),
                "wind_speed": data.get("wind", {}).get("speed"),
                "clouds": data.get("clouds", {}).get("all"),
            }
        else:
            weather_info = {
                "status": "error",
                "city": city_name,
                "message": data.get("message", "날씨 정보를 찾을 수 없습니다."),
                "description": "Not Found",
                "temperature": None,
                "temperature_feels_like": None,
                "humidity": None,
            }

        return json.dumps(weather_info, ensure_ascii=False)

    except requests.RequestException as e:
        return json.dumps(
            {
                "status": "error",
                "city": city_name,
                "message": f"요청 중 오류 발생: {str(e)}",
            },
            ensure_ascii=False,
        )


tools_to_execute = {
    "get_current_weather": get_current_weather
}


# -----------------------------
# 2. LLM Function Calling
# -----------------------------
def run_conversation(user_prompt: str, model: str = "gpt-4.1-mini") -> str:
    """
    LLM function calling을 통해 날씨 조회 도구를 호출하고 응답을 생성한다.

    Args:
        user_prompt (str): 사용자 입력 문장
        model (str): 사용할 OpenAI 모델명

    Returns:
        str: 최종 응답 텍스트
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "특정 도시의 현재 날씨 정보를 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city_name": {
                            "type": "string",
                            "description": "도시 이름. 가능하면 영어로 작성. 예: Seoul, Busan, Tokyo",
                        },
                        "units": {
                            "type": "string",
                            "enum": ["metric", "imperial", "standard"],
                            "description": "온도 단위. metric=섭씨, imperial=화씨, standard=절대온도",
                        },
                    },
                    "required": ["city_name"],
                },
            },
        }
    ]

    response1 = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    response1_message = response1.choices[0].message
    tool_calls = response1_message.tool_calls

    if tool_calls:
        messages.append(response1_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"[tool] {function_name} 호출 중...")
            function_to_execute = tools_to_execute[function_name]
            function_response = function_to_execute(**function_args)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": function_response,
                }
            )

        response2 = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response2.choices[0].message.content

    return response1_message.content


# ---------------------
# 3. 날짜 판별
# ---------------------
def classify_trip_timing(travel_date: str | None = None) -> dict:
    """
    여행 날짜가 오늘 기준으로 얼마나 가까운지 판별한다.

    Args:
        travel_date (str | None): YYYY-MM-DD 형식 여행 날짜

    Returns:
        dict: 날짜 판별 결과
    """
    if not travel_date:
        return {
            "status": "unknown_date",
            "message": "여행 날짜 정보가 없습니다.",
        }

    try:
        target = datetime.strptime(travel_date, "%Y-%m-%d").date()
        today = date.today()
        diff_days = (target - today).days

        if diff_days < 0:
            return {
                "status": "past_date",
                "message": "이미 지난 날짜입니다.",
            }
        if diff_days <= 5:
            return {
                "status": "current_weather_available",
                "message": "가까운 날짜이므로 현재/단기 날씨 기준으로 추천할 수 있습니다.",
            }
        if diff_days <= 30:
            return {
                "status": "forecast_maybe",
                "message": "가까운 미래 여행입니다.",
            }
        return {
            "status": "too_far",
            "message": "정확한 날씨를 보기엔 너무 먼 날짜입니다.",
        }

    except ValueError:
        return {
            "status": "invalid_date",
            "message": "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식이어야 합니다.",
        }


# ----------------------
# 4. 야외 적합도 판별
# ----------------------
def classify_outdoor_condition(weather_data: dict) -> dict:
    """
    날씨 데이터를 바탕으로 야외 활동 적합도를 판별한다.

    Args:
        weather_data (dict): 날씨 정보 딕셔너리

    Returns:
        dict: 야외 활동 적합도 및 추천 경로
    """
    description = (weather_data.get("description") or "").lower()
    temperature = weather_data.get("temperature")
    humidity = weather_data.get("humidity")
    wind_speed = weather_data.get("wind_speed", 0)

    if temperature is None or humidity is None:
        return {
            "condition_level": "unknown",
            "route_recommendation": "mixed",
            "reason": "날씨 정보가 충분하지 않습니다.",
        }

    bad_keywords = ["비", "눈", "폭우", "천둥", "storm", "rain", "snow", "thunder"]
    if any(keyword in description for keyword in bad_keywords):
        return {
            "condition_level": "poor",
            "route_recommendation": "indoor",
            "reason": "강수 가능성이 있어 야외 활동이 어렵습니다.",
        }

    if temperature <= 5 or temperature >= 35:
        return {
            "condition_level": "poor",
            "route_recommendation": "indoor",
            "reason": "기온이 극단적이라 야외 활동이 어렵습니다.",
        }

    if humidity >= 85 and temperature >= 28:
        return {
            "condition_level": "poor",
            "route_recommendation": "indoor",
            "reason": "덥고 습해서 야외 활동이 불편합니다.",
        }

    if wind_speed >= 10:
        return {
            "condition_level": "poor",
            "route_recommendation": "indoor",
            "reason": "바람이 강해 야외 활동이 어렵습니다.",
        }

    if 18 <= temperature <= 26 and 30 <= humidity <= 70 and wind_speed < 7:
        return {
            "condition_level": "good",
            "route_recommendation": "outdoor",
            "reason": "기온과 습도가 비교적 쾌적해 야외 활동에 적합합니다.",
        }

    return {
        "condition_level": "normal",
        "route_recommendation": "mixed",
        "reason": "실내와 야외를 섞은 일정이 적절합니다.",
    }


# ----------------------
# 5. 땃쥐 멘트
# ----------------------
def get_ddatchwi_message(status: str) -> dict:
    """
    날씨 상태에 맞는 땃쥐 캐릭터 메시지를 반환한다.

    Args:
        status (str): 상태값

    Returns:
        dict: 캐릭터 메시지 정보
    """
    message_map = {
        "too_far": {
            "character": "땃쥐가 곤란해해요…",
            "message": "아직 그 날짜의 정확한 날씨는 알기 어려워요.",
            "options": ["1년 평균 날씨 보기", "여행 월 기준으로 추천받기", "정확한 날짜 다시 입력하기"],
        },
        "poor": {
            "character": "땃쥐가 우산을 챙겼어요!",
            "message": "오늘은 실내 위주 코스가 더 잘 어울려요.",
            "options": [],
        },
        "normal": {
            "character": "땃쥐가 지도를 펼쳤어요!",
            "message": "실내와 야외를 적절히 섞은 코스를 추천할게요.",
            "options": [],
        },
        "good": {
            "character": "땃쥐가 신났어요!",
            "message": "오늘은 야외 활동하기 좋은 날씨예요.",
            "options": [],
        },
        "unknown": {
            "character": "땃쥐가 생각 중이에요…",
            "message": "날짜를 알려주면 더 정확하게 추천할게요.",
            "options": [],
        },
    }
    return message_map.get(
        status,
        {
            "character": "땃쥐가 생각 중이에요…",
            "message": "조건을 다시 확인해볼게요.",
            "options": [],
        },
    )


# ----------------------
# 6. 최종 오케스트라
# ----------------------
def build_weather_based_route_decision(city_name: str, travel_date: str | None = None) -> dict:
    """
    도시명과 여행 날짜를 바탕으로 날씨 기반 여행 방향을 결정한다.

    Args:
        city_name (str): API 호출용 도시명
        travel_date (str | None): 여행 날짜

    Returns:
        dict: 날씨 기반 추천 결과
    """
    print("DEBUG build_weather_based_route_decision city_name =", city_name)
    print("DEBUG build_weather_based_route_decision travel_date =", travel_date)

    timing_result = classify_trip_timing(travel_date)

    if timing_result["status"] == "too_far":
        ddatchwi = get_ddatchwi_message("too_far")
        return {
            "status": "too_far",
            "weather_mode": "average_or_monthly_needed",
            "ddatchwi": ddatchwi,
            "message": timing_result["message"],
        }

    if timing_result["status"] == "unknown_date":
        ddatchwi = get_ddatchwi_message("unknown")
        return {
            "status": "need_date",
            "ddatchwi": ddatchwi,
            "message": "땃쥐가 달력을 찾고 있어요! 여행 날짜를 알려주시면 더 정확하게 추천할 수 있어요.",
        }

    if timing_result["status"] in ["invalid_date", "past_date"]:
        return {
            "status": timing_result["status"],
            "message": timing_result["message"],
        }

    weather_json = get_current_weather(city_name=city_name, units="metric")
    weather_data = json.loads(weather_json)

    if weather_data.get("status") != "success":
        return {
            "status": "error",
            "message": weather_data.get("message", "날씨 정보를 가져오지 못했습니다."),
        }

    condition_result = classify_outdoor_condition(weather_data)
    ddatchwi = get_ddatchwi_message(condition_result["condition_level"])

    return {
        "status": "success",
        "weather": weather_data,
        "condition": condition_result,
        "ddatchwi": ddatchwi,
    }


# -----------------------------
# 7. 날짜 계산 (상대 → 절대)
# -----------------------------
# from datetime import date, datetime, timedelta
#
#
# def resolve_travel_date(
#     travel_date: str | None,
#     relative_days: int | None,
#     raw_date_text: str | None = None,
# ) -> str | None:
#     """
#     절대 날짜 또는 상대 날짜 또는 자연어 날짜를 최종 여행 날짜로 변환한다.
#     """
#
#     today = date.today()
#
#     weekday_map = {
#         "월요일": 0,
#         "화요일": 1,
#         "수요일": 2,
#         "목요일": 3,
#         "금요일": 4,
#         "토요일": 5,
#         "일요일": 6,
#     }
#
#     def _resolve_korean_relative_weekday(today: date, text: str) -> str | None:
#         text = text.replace(" ", "")
#
#         for day_name, target_weekday in weekday_map.items():
#             if text == f"이번주{day_name}":
#                 days_until = (target_weekday - today.weekday()) % 7
#                 return (today + timedelta(days=days_until)).isoformat()
#
#             if text == f"다음주{day_name}":
#                 days_until = (target_weekday - today.weekday()) % 7
#                 return (today + timedelta(days=days_until + 7)).isoformat()
#
#             if text == f"다다음주{day_name}":
#                 days_until = (target_weekday - today.weekday()) % 7
#                 return (today + timedelta(days=days_until + 14)).isoformat()
#
#         return None
#
#     # 1. 이미 절대 날짜가 있는 경우
#     if travel_date:
#         try:
#             parsed = datetime.strptime(travel_date, "%Y-%m-%d").date()
#             return parsed.isoformat()
#         except ValueError:
#             pass
#
#     # 2. n일 뒤 형태
#     if relative_days is not None:
#         return (today + timedelta(days=relative_days)).isoformat()
#
#     # 3. 자연어 날짜 처리
#     if raw_date_text:
#         text = raw_date_text.strip().replace(" ", "")
#
#         if text == "오늘":
#             return today.isoformat()
#
#         if text == "내일":
#             return (today + timedelta(days=1)).isoformat()
#
#         if text == "모레":
#             return (today + timedelta(days=2)).isoformat()
#
#         resolved_weekday = _resolve_korean_relative_weekday(today, text)
#         if resolved_weekday:
#             return resolved_weekday
#
#     return None

from datetime import date, timedelta

def fallback_resolve_date_with_rules(raw_text: str | None) -> str | None:
    if not raw_text:
        return None

    today = date.today()
    text = raw_text.replace(" ", "")

    weekday_map = {
        "월요일": 0,
        "화요일": 1,
        "수요일": 2,
        "목요일": 3,
        "금요일": 4,
        "토요일": 5,
        "일요일": 6,
    }

    for day_name, target_weekday in weekday_map.items():
        if text == f"이번주{day_name}":
            days = (target_weekday - today.weekday()) % 7
            return (today + timedelta(days=days)).isoformat()

        if text == f"다음주{day_name}":
            days = (target_weekday - today.weekday()) % 7
            return (today + timedelta(days=days + 7)).isoformat()

        if text == f"다다음주{day_name}":
            days = (target_weekday - today.weekday()) % 7
            return (today + timedelta(days=days + 14)).isoformat()

    return None


# -----------------------------
# 8. 날짜·도시 추출 (LLM)
# -----------------------------
def extract_trip_info_with_llm(user_prompt: str) -> dict:
    """
    사용자 자연어 입력에서 도시명과 날짜 정보를 구조화하여 추출한다.

    Args:
        user_prompt (str): 사용자 입력 문장

    Returns:
        dict: 추출 결과
    """

    extraction_system_prompt = """
    당신은 여행 정보 추출기입니다.
    오늘 날짜는 2026-04-20 입니다.
    오늘은 월요일입니다.

    사용자 문장에서 여행 도시와 날짜를 추출하세요.
    반드시 JSON만 출력하세요.

    규칙:
    1. city_name은 한국어 도시명으로 반환하세요.
    2. "다음주 목요일", "다다음주 토요일", "내일", "모레" 같은 상대 날짜는
       반드시 절대 날짜 YYYY-MM-DD로 계산해서 travel_date에 넣으세요.
    3. 기간 표현이면 시작일은 travel_date, 종료일은 end_date에 넣으세요.
    4. 계산이 불가능하면 travel_date는 null로 두고 raw_date_text에 원문을 넣으세요.

    출력 형식:
    {
      "city_name": "부산",
      "travel_date": "2026-04-30",
      "end_date": null,
      "raw_date_text": "다음주 목요일"
    }
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": extraction_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        print("DEBUG extract_trip_info_with_llm raw content =", content)

        if not content:
            return {
                "city_name": None,
                "travel_date": None,
                "end_date": None,
                "raw_date_text": user_prompt,
            }

        parsed = json.loads(content)

        if not isinstance(parsed, dict):
            return {
                "city_name": None,
                "travel_date": None,
                "end_date": None,
                "raw_date_text": user_prompt,
            }

        return parsed

    except Exception as e:
        print("DEBUG extract_trip_info_with_llm exception =", e)
        return {
            "city_name": None,
            "travel_date": None,
            "end_date": None,
            "raw_date_text": user_prompt,
        }
# -----------------------------
# 9. 자연어 입력 → 최종 결과
# -----------------------------
def build_weather_route_from_user_prompt(user_prompt: str) -> dict:
    extracted = extract_trip_info_with_llm(user_prompt)
    """
    사용자 자연어 입력을 받아 도시/날짜를 추출하고 최종 날씨 기반 추천 결과를 반환한다.

    Args:
        user_prompt (str): 사용자 자연어 문장

    Returns:
        dict: 추출 결과와 날씨 추천 결과
    """

    display_city_name = extracted.get("city_name") or "서울"
    api_city_name = normalize_city_name_for_weather(display_city_name)

    travel_date = extracted.get("travel_date")
    end_date = extracted.get("end_date")

    # fallback
    if not travel_date:
        travel_date = fallback_resolve_date_with_rules(
            extracted.get("raw_date_text")
        )

    result = build_weather_based_route_decision(api_city_name, travel_date)
    result["display_city_name"] = display_city_name

    return {
        "extracted": extracted,
        "display_city_name": display_city_name,
        "resolved_travel_date": travel_date,
        "result": result,
    }


# -----------------------------
# 10. 결과 포맷
# -----------------------------
def format_weather_recommendation(result: dict) -> str:
    """
    날씨 추천 결과를 사람이 읽기 쉬운 문자열로 변환한다.

    Args:
        result (dict): build_weather_based_route_decision() 결과

    Returns:
        str: 사용자 출력용 문자열
    """
    status = result.get("status")

    if status == "too_far":
        ddatchwi = result.get("ddatchwi", {})
        options = ddatchwi.get("options", [])
        option_text = "\n".join([f"- {opt}" for opt in options])

        return (
            f"{ddatchwi.get('character', '')}\n"
            f"{ddatchwi.get('message', result.get('message', ''))}\n\n"
            f"선택지:\n{option_text}"
        )

    if status == "need_date":
        ddatchwi = result.get("ddatchwi", {})
        return (
            f"{ddatchwi.get('character', '')}\n"
            f"{result.get('message', '날짜를 알려주세요.')}"
        )

    if status in ["invalid_date", "past_date", "error"]:
        return result.get("message", "오류가 발생했습니다.")

    if status == "success":
        weather = result.get("weather", {})
        condition = result.get("condition", {})
        ddatchwi = result.get("ddatchwi", {})
        display_city_name = result.get("display_city_name") or weather.get("city", "정보 없음")

        return (
            f"- 도시: {display_city_name}\n"
            f"- 설명: {weather.get('description', '정보 없음')}\n"
            f"- 온도: {weather.get('temperature', '정보 없음')}도\n"
            f"- 체감온도: {weather.get('temperature_feels_like', '정보 없음')}도\n"
            f"- 최저/최고: {weather.get('temp_min', '정보 없음')}도 / {weather.get('temp_max', '정보 없음')}도\n"
            f"- 습도: {weather.get('humidity', '정보 없음')}%\n"
            f"- 바람: {weather.get('wind_speed', '정보 없음')}m/s\n"
            f"- 추천 유형: {condition.get('route_recommendation', '정보 없음')}\n"
            f"- 판단 이유: {condition.get('reason', '정보 없음')}\n\n"
            f"{ddatchwi.get('character', '')}\n"
            f"{ddatchwi.get('message', '')}"
        )

    return "결과를 표시할 수 없습니다."


# ==============================
# 테스트
# ==============================
if __name__ == "__main__":
    print("\n=== 1. 먼 날짜 테스트 ===")
    result1 = build_weather_based_route_decision(
        city_name="Busan",
        travel_date="2027-05-20",
    )
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    print(format_weather_recommendation(result1))

    print("\n=== 2. 오늘 날짜 테스트 ===")
    result2 = build_weather_based_route_decision(
        city_name="Seoul",
        travel_date=str(date.today()),
    )
    print(json.dumps(result2, indent=2, ensure_ascii=False))
    print(format_weather_recommendation(result2))

    print("\n=== 3. 날짜 없음 테스트 ===")
    result3 = build_weather_based_route_decision(
        city_name="Seoul",
        travel_date=None,
    )
    print(json.dumps(result3, indent=2, ensure_ascii=False))
    print(format_weather_recommendation(result3))

    print("\n=== 4. 잘못된 날짜 테스트 ===")
    result4 = build_weather_based_route_decision(
        city_name="Seoul",
        travel_date="2026/05/20",
    )
    print(json.dumps(result4, indent=2, ensure_ascii=False))
    print(format_weather_recommendation(result4))

    print("\n=== 5. 자연어 입력 테스트 ===")
    final_result = build_weather_route_from_user_prompt("전주로 1주일 뒤 여행 가는데 날씨 어때?")
    print(json.dumps(final_result, indent=2, ensure_ascii=False))
    print("\n--- 최종 출력 ---")
    print(format_weather_recommendation(final_result["result"]))

    # print("\n=== 6. LLM Function Calling 테스트 ===")
    # print(run_conversation("서울 날씨 어때?"))