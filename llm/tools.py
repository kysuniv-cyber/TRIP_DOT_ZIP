from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import tool

from mock_tools.weather_tools import get_weather
from services.place_search_tool import search_place_tool
from services.scheduler_service import create_schedule


class MakeScheduleInput(BaseModel):
    places: List[Dict[str, Any]] = Field(description="장소 리스트")
    start_time: str = Field(default="09:00", description="일정 시작 시각, HH:MM 형식")
    mode: str = Field(default="transit", description="이동 수단: transit, walking, driving")
    optimize_route: bool = Field(default=True, description="최적 동선 여부")


@tool("make_schedule", args_schema=MakeScheduleInput)
def make_schedule_tool(
    places: List[Dict[str, Any]],
    start_time: str = "09:00",
    mode: str = "transit",
    optimize_route: bool = True,
) -> dict:
    """장소 리스트를 기반으로 시간대별 일정을 생성한다."""
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


TOOLS = [
    get_weather,
    search_place_tool,
    make_schedule_tool,
]