import folium
from pydantic import BaseModel
from streamlit_folium import st_folium
from dataclasses import dataclass
from constants import POPUP_TEMPLATE, TOOLTIP_TEMPLATE, MARKER_ICON_TEMPLATE
from folium import plugins

@dataclass
class PlaceInfo():
    # 장소 정보
    place_id: str                       # ID
    name: str                           # 장소명
    lat: float                          # 위도
    lng: float                          # 경도
    order: int = 0                      # 순서
    # 필요한 place 정보를 추가
    # 예를 들어, 별점이나 카테고리 등등
    # LLM에 보낼 schema와 구분되는 다른 값.
    category: str | None = "카테고리 정보가 없습니다."  # 카테고리
    # 이미지 컨트롤 icon이나 popup 제어 시 
    icon: str = 'default'               # icon -> 커스텀?

    # 동작 컨트롤
    is_confirmed: bool = False          # 확정되었는지 여부
    
class TravelMap:
    """ map 객체 """
    
    # init할 때 기본 값 넣기
    def __init__(self, center_lat: float, center_lng: float, zoom: int=13):
        self.zoom:int = zoom
        self._markers: list[PlaceInfo] = [] # 마커 리스트
        self._map:folium.Map = self._init_map(center_lat, center_lng)
    
    def _init_map(self, center_lat: float, center_lng: float) -> "TravelMap":
        """ 지도 초기화 """
        return folium.Map(
            location=[center_lat, center_lng],
            zoom_start=self.zoom
        )
    
    def add_marker(self, place: PlaceInfo) -> "TravelMap":
        """ 마커 추가 """
        # place의 validation 추가 예정.
        
        self._markers.append(place)
        
        folium.Marker(
            location=[place.lat, place.lng],
            tooltip=TOOLTIP_TEMPLATE.format(
                order=place.order,
                name=place.name,
            ),
            popup=folium.Popup(
                POPUP_TEMPLATE.format(
                    order=place.order,
                    name=place.name,
                ),
                max_width=200
            ),
            icon=folium.DivIcon(
                html=MARKER_ICON_TEMPLATE.format(order=place.order)
            )
        ).add_to(self._map)
        
        return self   # 체이닝용
    
    def add_markers(self, places: list[PlaceInfo]) -> "TravelMap":
        """마커 일괄 추가"""
        for place in places:
            self.add_marker(place)
        return self
    
    def add_route(self) -> "TravelMap":
        """ 내부 _markers 기반으로 동선 자동 그리기 """
        if len(self._markers) < 2:
            return self
        
        coords = [[m.lat, m.lng] for m in self._markers]
        folium.PolyLine(
            coords,
            color="#4A90E2",
            weight=2.5,
            opacity=0.7
        ).add_to(self._map)
        
        return self
    
    def clear(self) -> "TravelMap":
        """전체 초기화"""
        if self._map:
            # 기존 지도의 중심좌표
            center = self._map.location
            self._init_map(center[0], center[1])
            # 마커 리셋
            self._markers = []
        return self
    
    def auto_fit(self) -> "TravelMap":
        """모든 마커가 보이도록 줌 자동 조정"""
        if not self._markers:
            return self
        
        lats = [m.lat for m in self._markers]
        lngs = [m.lng for m in self._markers]
        self._map.fit_bounds([
            [min(lats), min(lngs)],
            [max(lats), max(lngs)]
        ])
        return self
    
    def render(self) -> "TravelMap":
        """(기존)Streamlit에 넘길 HTML 반환 -> (new)streamlit folium 사용으로 객체 자체를 반환"""
        return self._map
    
    # 상태 조회 일종의 getter
    @property
    def get_place_count(self) -> int:
        return len(self._markers)
    
    @property
    def get_places(self) -> list[PlaceInfo]:
        return self._markers.copy()   # 불변성 보장