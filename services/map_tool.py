"""
    FileName: map_tool.py
    Location: services/map_tool.py
    Role: LLM에게 위치 좌표 정보를 받아서 map을 그리는 역할.
"""

import streamlit as st
from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import List, Optional

from ui.travel_map import TravelMap, PlaceInfo   # 기존 TravelMap 재사용
from utils.custom_exception import MapRenderError


# ---------------------------------------------------------------------------
# 1. LLM에게 노출할 Input Schema
# ---------------------------------------------------------------------------
class MarkerInfo(BaseModel):
    """ MarkerInfo
        place Tool의 PlaceInfo랑은 다른 개념. Marker를 찍고 popup에 표출할 값을 정리하는 개념
    """
    # 아 이게 LLM에게서 받아와야 할 정보구마.ㄴ 
    place_id: str       = Field(description="Google Place ID")
    name:     str       = Field(description="장소명")
    lat:      float     = Field(description="위도")
    lng:      float     = Field(description="경도")
    order:    int       = Field(description="방문 순서 (1부터 시작)")
    # popup에 표출할 정보.
    category: Optional[str] = Field(default=None, description="장소 카테고리 (예: cafe, museum)")
    

class MapToolInput(BaseModel):
    """
    MapTool에서 LLM이 툴 호출 시 참고할 Input Schema.

    places: ScheduleTool이 확정한 장소 리스트 (order 포함 필수)
    center_lat / center_lng: 지도 초기 중심 좌표.
                             전달하지 않으면 places의 위경도 평균으로 자동 계산.
    zoom: 초기 줌 레벨 (기본 13)
    """
    places:     List[MarkerInfo] = Field(description="방문 확정 장소 목록 (order 포함)")
    center_lat: Optional[float] = Field(default=None, description="지도 중심 위도 (생략 시 자동)")
    center_lng: Optional[float] = Field(default=None, description="지도 중심 경도 (생략 시 자동)")
    zoom:       int             = Field(default=13,   description="초기 줌 레벨")


# ---------------------------------------------------------------------------
# 2. 내부 헬퍼
# ---------------------------------------------------------------------------

def _calc_center(places: List[PlaceInfo]) -> tuple[float, float]:
    """장소 목록의 위경도 평균으로 지도 중심 계산"""
    lat = sum(p.lat for p in places) / len(places)
    lng = sum(p.lng for p in places) / len(places)
    return lat, lng


def _build_place_infos(places: List[MarkerInfo]) -> list[PlaceInfo]:
    """MarkerInfo(Pydantic) → PlaceInfo(dataclass) 변환"""
    # order 기준 정렬 보장
    sorted_places = sorted(places, key=lambda p: p.order)
    return [
        PlaceInfo(
            place_id=p.place_id,
            name=p.name,
            lat=p.lat,
            lng=p.lng,
            order=p.order,
            category=p.category or "default",
            is_confirmed=True,
        )
        for p in sorted_places
    ]


# ---------------------------------------------------------------------------
# 3. MapTool
# ---------------------------------------------------------------------------

@tool("map_render", args_schema=MapToolInput)
def map_tool(
    places:     List[MarkerInfo],
    center_lat: Optional[float] = None,
    center_lng: Optional[float] = None,
    zoom:       int = 13,
) -> dict:
    """
    확정된 여행 장소 목록을 받아 Folium 지도를 생성하고
    Streamlit session_state["travel_map"]에 저장한다.

    - 마커: 방문 순서(order)가 번호로 표시된 커스텀 DivIcon
    - 동선: 순서대로 파란 PolyLine 연결
    - 줌:   모든 마커가 보이도록 자동 조정 (auto_fit)

    LLM에게는 folium 객체 대신 성공 여부 + 메타 정보만 반환한다.
    실제 렌더링은 Streamlit 레이어에서 session_state를 읽어 수행한다.
    """
    try:
        if not places:
            raise MapRenderError("map_render", reason="장소 목록이 비어 있습니다.")

        # 중심 좌표 결정
        c_lat, c_lng = (
            (center_lat, center_lng)
            if center_lat is not None and center_lng is not None
            else _calc_center(places)
        )

        # MarkerInfo → PlaceInfo 변환
        place_infos = _build_place_infos(places)

        # TravelMap 체이닝
        travel_map = (
            TravelMap(center_lat=c_lat, center_lng=c_lng, zoom=zoom)
            .add_markers(place_infos)   # 마커 일괄 추가
            .add_route()                # PolyLine 동선
            .auto_fit()                 # 전체 마커 보이도록 줌 조정
        )

        # ── Streamlit session_state에 저장 ──────────────────────────────────
        # folium.Map 객체는 JSON 직렬화가 불가하므로 LLM에 직접 반환하지 않는다.
        # Streamlit 레이어에서 st.session_state["travel_map"]을 읽어 st_folium()으로 렌더링.
        st.session_state["travel_map"] = travel_map.render()
        st.session_state["travel_map_ready"] = True

        # LLM에게 반환할 메타 정보
        return {
            "status": "success",
            "data": {
                "center": {"lat": c_lat, "lng": c_lng},
                "zoom":   zoom,
                "markers": [
                    {"order": p.order, "name": p.name, "lat": p.lat, "lng": p.lng}
                    for p in place_infos
                ],
                "route_drawn": len(place_infos) >= 2,
            },
            "error": None,
            "meta": {
                "tool_name":    "map_render",
                "total_places": len(place_infos),
            },
        }

    except MapRenderError as e:
        return e.error_response()

    except Exception as e:
        st.session_state["travel_map_ready"] = False
        return {
            "status": "error",
            "data":   None,
            "error":  str(e),
            "meta":   {"tool_name": "map_render"},
        }