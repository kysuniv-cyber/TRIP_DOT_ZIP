"""
에이전트가 사용할 tool들을 정의하고 관리하는 모듈이다.

LLM이 외부 기능을 직접 호출할 수 있도록
각 기능을 tool 형태로 감싸서 제공한다.
"""

from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
from langchain.tools import tool

# service 레이어 연결
from services.place_search_service import get_places_from_api
from services.scheduler_service import create_schedule
from services.weather_service import (
    build_weather_based_route_decision,
    normalize_city_name_for_weather,
)
from services.travel_recommend_service import recommend_travel_places
from utils.custom_exception import PlaceNotFoundError


# =========================
# 날씨 조회 입력 스키마
# =========================
class WeatherInput(BaseModel):
    """
    날씨 조회 tool 입력 스키마.

    도시명과 여행 날짜를 입력받아 날씨 정보를 조회한다.

    Args:
        city_name (str): 날씨를 확인할 도시명
        travel_date (Optional[str]): 여행 날짜 (YYYY-MM-DD)

    Returns:
        None: 입력 스키마 객체 생성
    """

    city_name: str = Field(
        description="날씨를 확인할 도시명. 예: 부산, 서울, 도쿄"
    )
    travel_date: Optional[str] = Field(
        default=None,
        description="여행 날짜. YYYY-MM-DD 또는 상대 날짜 표현 가능"
    )
    user_query: Optional[str] = Field(
        default=None,
        description="원문 사용자 질문. 상대 날짜 해석이 필요할 때 사용"
    )

# =========================
# 날씨 조회 tool
# =========================
@tool("get_weather", args_schema=WeatherInput)
def get_weather_tool(
    city_name: str,
    travel_date: Optional[str] = None,
    user_query: Optional[str] = None,
) -> dict:
    """
    도시와 날짜를 기준으로 날씨 및 추천 정보를 반환한다.

    도시명을 정규화한 뒤 날씨 기반 추천 로직을 수행하고,
    사용자 입력 도시명과 정규화된 도시명을 함께 반환한다.

    Args:
        city_name (str): 사용자 입력 도시명
        travel_date (Optional[str]): 여행 날짜

    Returns:
        dict: 날씨 정보 및 추천 결과
    """
    try:
        print("✅ get_weather_tool CALLED")
        print("DEBUG get_weather_tool city_name =", city_name)
        print("DEBUG get_weather_tool travel_date =", travel_date)
        print("DEBUG get_weather_tool user_query =", user_query)

        normalized_city = normalize_city_name_for_weather(city_name)

        result = build_weather_based_route_decision(
            city_name=normalized_city,
            travel_date=travel_date,
            user_query=user_query,
        )

        result["display_city_name"] = city_name
        result["normalized_city_name"] = normalized_city
        return result

    except Exception as e:
        print("DEBUG get_weather_tool exception =", e)
        return {
            "status": "error",
            "message": str(e),
            "display_city_name": city_name,
            "normalized_city_name": None,
        }
# =========================
# 장소 검색 입력 스키마
# =========================
class PlaceSearchInput(BaseModel):
    """
    장소 검색 tool 입력 스키마.

    목적지, 여행 스타일, 제약사항을 바탕으로 장소를 검색한다.

    Args:
        destination (str): 검색할 도시 또는 지역명
        styles (List[str]): 여행 스타일 목록
        constraints (List[str]): 제약사항 목록
        limit (int): 추천 장소 최대 개수

    Returns:
        None
    """

    destination: str = Field(
        description="검색할 도시 또는 지역명(예: 부산, 서울, 타이페이)"
    )
    styles: List[str] = Field(
        default_factory=list,
        description="여행 스타일 목록(예: 카페, 맛집, 관광지, 명소)",
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="특별한 제약사항(예: 실내, 우천, 반려동물, 주차 가능)",
    )
    limit: int = Field(
        default=5,
        description="추천받을 장소의 최대 개수",
    )


# =========================
# 장소 검색 tool
# =========================
@tool("place_search", args_schema=PlaceSearchInput)
def search_place_tool(
    destination: str,
    styles: List[str],
    constraints: List[str],
    limit: int = 5,
) -> dict:
    """
    목적지와 스타일, 제약사항을 기반으로 장소를 검색하여 반환한다.

    Google Places API 검색 결과를 일정 생성에 바로 활용할 수 있는 형태로
    가공하여 표준 응답 구조로 반환한다.

    Args:
        destination (str): 검색할 대상 지역명
        styles (List[str]): 검색 키워드에 포함할 스타일 리스트
        constraints (List[str]): 검색 키워드에 포함할 제약 조건 리스트
        limit (int): 검색 결과 최대 개수

    Returns:
        dict: 장소 검색 결과
    """
    try:
        response = get_places_from_api(destination, styles, constraints, limit)

        if response["status_code"] != 200:
            return {
                "status": "error",
                "data": None,
                "error": (
                    f"API 호출 실패 (Status: {response['status_code']}): "
                    f"{response['error_text']}"
                ),
                "meta": {"tool_name": "place_search"},
            }

        results = response["json_data"].get("places", [])
        mapped_places = []

        if len(results) == 0:
            raise PlaceNotFoundError("place_search_tool")

        for place in results:
            types = place.get("types", [])
            is_indoor = any(
                t in ["shopping_mall", "museum", "cafe"] for t in types
            )

            temp_place_info = {
                "place_id": place.get("id"),
                "name": place.get("displayName", {}).get("text"),
                "lat": place.get("location", {}).get("latitude"),
                "lng": place.get("location", {}).get("longitude"),
                "category": types[0] if types else "default",
                "types": types,
                "summary": place.get("editorialSummary", {}).get("text", "정보 없음"),
                "rating": place.get("rating", 0),
                "indoor_outdoor": "indoor" if is_indoor else "outdoor",
            }

            mapped_places.append(
                {
                    **temp_place_info,
                    "recommended_reason": (
                        f"{destination}에서 평점 {temp_place_info['rating']}의 "
                        f"{temp_place_info['category']} 중 하나입니다."
                    ),
                }
            )

        return {
            "status": "success",
            "data": {"places": mapped_places},
            "error": None,
            "meta": {
                "tool_name": "place_search",
                "total_found": len(mapped_places),
            },
        }

    except PlaceNotFoundError as e:
        return e.error_response()

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": str(e),
            "meta": {"tool_name": "place_search"},
        }


# =========================
# 일정 생성 입력 스키마
# =========================
class MakeScheduleInput(BaseModel):
    """
    일정 생성 tool 입력 스키마.

    장소 리스트와 시작 시간 등을 기반으로 일정을 생성한다.

    Args:
        places (List[Dict[str, Any]]): 방문할 장소 리스트
        start_time (str): 일정 시작 시간
        mode (str): 이동 수단
        optimize_route (bool): 동선 최적화 여부

    Returns:
        None
    """

    places: List[Dict[str, Any]] = Field(description="장소 리스트")
    start_time: str = Field(
        default="09:00",
        description="일정 시작 시각, HH:MM 형식",
    )
    mode: str = Field(
        default="transit",
        description="이동 수단: transit, walking, driving",
    )
    optimize_route: bool = Field(
        default=True,
        description="최적 동선 여부",
    )


# =========================
# 일정 생성 tool
# =========================
@tool("make_schedule", args_schema=MakeScheduleInput)
def make_schedule_tool(
    places: List[Dict[str, Any]],
    start_time: str = "09:00",
    mode: str = "transit",
    optimize_route: bool = True,
) -> dict:
    """
    장소 리스트를 기반으로 시간대별 일정을 생성한다.

    내부적으로 scheduler_service의 create_schedule을 호출하여
    일정 데이터를 생성하고 표준 형태로 반환한다.

    Args:
        places (List[Dict[str, Any]]): 장소 리스트
        start_time (str): 시작 시간
        mode (str): 이동 수단
        optimize_route (bool): 동선 최적화 여부

    Returns:
        dict: 생성된 일정 결과
    """
    try:
        result = create_schedule(
            places=places,
            start_time_str=start_time,
            mode=mode,
            optimize_route=optimize_route,
        )

        if isinstance(result, dict) and result.get("status") == "error":
            return result

        return {
            "status": "success",
            "data": {
                "start_time": start_time,
                "mode": mode,
                "optimize_route": optimize_route,
                "itinerary": result,
            },
            "error": None,
            "meta": {"tool_name": "make_schedule"},
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": str(e),
            "meta": {"tool_name": "make_schedule"},
        }


# =========================
# 일정 수정 입력 스키마
# =========================
class ModifyScheduleInput(BaseModel):
    """
    일정 수정 tool 입력 스키마.

    기존 장소 리스트와 설정값을 바탕으로 일정을 다시 생성한다.

    Args:
        places (List[Dict[str, Any]]): 수정할 장소 리스트
        start_time (str): 일정 시작 시간
        mode (str): 이동 수단
        optimize_route (bool): 동선 최적화 여부

    Returns:
        None
    """

    places: List[Dict[str, Any]] = Field(description="수정할 장소 리스트")
    start_time: str = Field(
        default="09:00",
        description="일정 시작 시각, HH:MM 형식",
    )
    mode: str = Field(
        default="transit",
        description="이동 수단: transit, walking, driving",
    )
    optimize_route: bool = Field(
        default=True,
        description="최적 동선 여부",
    )


# =========================
# 일정 수정 tool
# =========================
@tool("modify_schedule", args_schema=ModifyScheduleInput)
def modify_schedule_tool(
    places: List[Dict[str, Any]],
    start_time: str = "09:00",
    mode: str = "transit",
    optimize_route: bool = True,
) -> dict:
    """
    기존 일정을 수정하거나 재생성한다.

    현재는 make_schedule과 동일한 로직을 사용하여
    새로운 일정을 생성한다.

    Args:
        places (List[Dict[str, Any]]): 수정할 장소 리스트
        start_time (str): 시작 시간
        mode (str): 이동 수단
        optimize_route (bool): 동선 최적화 여부

    Returns:
        dict: 수정된 일정 결과
    """
    try:
        result = create_schedule(
            places=places,
            start_time_str=start_time,
            mode=mode,
            optimize_route=optimize_route,
        )

        if isinstance(result, dict) and result.get("status") == "error":
            return result

        return {
            "status": "success",
            "data": {
                "start_time": start_time,
                "mode": mode,
                "optimize_route": optimize_route,
                "itinerary": result,
            },
            "error": None,
            "meta": {"tool_name": "modify_schedule"},
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": str(e),
            "meta": {"tool_name": "modify_schedule"},
        }


# =========================
# 여행 추천 입력 스키마
# =========================
class RecommendTravelInput(BaseModel):
    """
    여행 추천 tool 입력 스키마.

    사용자 자연어 요청을 받아 여행지를 추천한다.

    Args:
        query (str): 여행 추천 요청 문장

    Returns:
        None
    """

    query: str = Field(
        description="여행 추천 요청 문장. 예: 국내 여행 추천해줘"
    )


# =========================
# 여행 추천 tool
# =========================
@tool("recommend_travel", args_schema=RecommendTravelInput)
def recommend_travel_tool(query: str) -> dict:
    """
    사용자 요청 기반 여행 추천 결과를 반환한다.

    Args:
        query (str): 사용자 요청 문장

    Returns:
        dict: 추천 여행 결과
    """
    try:
        return recommend_travel_places(query)
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": str(e),
            "meta": {"tool_name": "recommend_travel"},
        }


# =========================
# 전체 tool 리스트
# =========================
TOOLS = [
    get_weather_tool,
    search_place_tool,
    make_schedule_tool,
    modify_schedule_tool,
    recommend_travel_tool,
]