"""
LLM 동작 검증을 위한 Weather mock tool.

실제 외부 API나 서비스가 연결되기 전에도
에이전트의 실행 흐름과 응답 형식을 확인할 수 있도록
가상의 결과를 반환하는 tool이다..
"""

from langchain.tools import tool
from test_backup.schemas import success_response

from services.weather_service import (
    build_weather_based_route_decision,
    build_weather_route_from_user_prompt,
    normalize_city_name_for_weather,
)


@tool
def get_weather(destination: str, date: str) -> dict:
    """
    목적지와 날짜를 받아 실제 날씨 정보를 조회하고
    여행 추천 결과를 반환한다.

    Args:
        destination: 한국어 또는 영어 도시명
        date: YYYY-MM-DD 형식 날짜

    Returns:
        success_response 형태의 dict
    """
    api_city_name = normalize_city_name_for_weather(destination)
    result = build_weather_based_route_decision(api_city_name, date)

    # 사용자 화면용 도시명도 같이 넣어주기
    result["display_city_name"] = destination

    return success_response(result)


@tool
def get_weather_from_prompt(user_prompt: str) -> dict:
    """
    사용자 자연어 입력 전체를 받아
    도시/날짜 추출부터 날씨 추천까지 수행한다.
    """
    result = build_weather_route_from_user_prompt(user_prompt)
    return success_response(result)