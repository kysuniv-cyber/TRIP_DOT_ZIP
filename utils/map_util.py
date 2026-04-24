from typing import List, Optional
from uis.travel_map import TravelMap, PlaceInfo
from llm.graph.contracts import StateKeys

def generate_map_from_state(state: dict) -> Optional[TravelMap]:
    """
    LangGraph의 State 내 ITINERARY 데이터를 기반으로 TravelMap 객체를 생성합니다.
    """
    itinerary = state.get(StateKeys.ITINERARY, [])
    
    if not itinerary:
        # 일정이 아직 생성되지 않았다면 표시할 내용이 없음
        return None

    place_infos = []
    
    # 전달해주신 ITINERARY 내부 구조에 맞춰 데이터 추출
    for item in itinerary:
        # item 예시: {"order": 1, "place_name": "...", "lat": 37.x, "lng": 127.x, ...}
        lat = item.get("lat")
        lng = item.get("lng")
        
        # 위경도 정보가 유효한 경우에만 마커 추가
        if lat is not None and lng is not None:
            place_infos.append(PlaceInfo(
                place_id=f"p_{item.get('order')}", # 고유 ID 생성
                name=item.get("place_name", "이름 없음"),
                lat=float(lat),
                lng=float(lng),
                order=item.get("order", 0),
                category=item.get("category", "default"), # 카테고리가 없다면 기본값
                is_confirmed=True
            ))

    if not place_infos:
        return None

    # 방문 순서(order)에 따라 리스트 정렬 (PolyLine 동선을 위해 필수)
    place_infos.sort(key=lambda x: x.order)

    # 지도의 중심은 첫 번째 방문지로 설정
    center_lat = place_infos[0].lat
    center_lng = place_infos[0].lng
    
    # TravelMap 객체 생성 및 체이닝
    travel_map = (
        TravelMap(center_lat=center_lat, center_lng=center_lng)
        .add_markers(place_infos)  # 모든 마커 찍기
        .add_route()               # 순서대로 파란 선 연결
        .auto_fit()                 # 모든 마커가 보이게 줌 조정
    )
    
    return travel_map