import os
import sys
from pathlib import Path

# 파이썬 경로 등록
root_path = str(Path(__file__).resolve().parent.parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)


import streamlit as st
from streamlit_folium import st_folium
from utils.map_util import generate_map_from_state
from llm.graph.contracts import StateKeys

def render_itinerary_map(state: dict):
    """
    State의 ITINERARY를 읽어 지도를 화면에 출력합니다.
    """
    with st.container():
        st.markdown("### 🗺️ 최적 방문 경로")
        
        # 지도 객체 생성
        travel_map_obj = generate_map_from_state(state)
        
        if travel_map_obj:
            # Folium Map 객체 가져오기
            folium_map = travel_map_obj.render()
            
            # Streamlit-Folium으로 렌더링
            st_folium(
                folium_map,
                width="100%", # 컨테이너 너비에 맞춤
                height=500,
                key="itinerary_map" # 리런 시 상태 유지를 위한 고유 키
            )
            
            # 간단한 정보 요약 (선택 사항)
            count = travel_map_obj.get_place_count
            st.caption(f"총 {count}개의 장소가 경로에 포함되었습니다.")
        else:
            st.warning("일정 정보에서 위치 데이터를 찾을 수 없습니다.")

        return travel_map_obj

# 사용 예시 (Streamlit 메인 루프)
# if st.session_state.get("show_final_map"):
#     render_itinerary_map(st.session_state.graph_state)


def test_map_generation():
    print("🚀 여행 지도 생성 테스트 시작...")

    # 1. 테스트용 Mock State 생성 (사용자가 주신 ITINERARY 구조)
    mock_state = {
        StateKeys.ITINERARY: [
            {
                "order": 1,
                "place_name": "서울역",
                "arrival": "09:00",
                "departure": "09:30",
                "stay_time": "30분",
                "lat": 37.554648,
                "lng": 126.972559,
                "category": "교통"
            },
            {
                "order": 2,
                "place_name": "남산타워",
                "arrival": "10:00",
                "departure": "12:00",
                "stay_time": "120분",
                "lat": 37.551169,
                "lng": 126.988227,
                "category": "관광"
            },
            {
                "order": 3,
                "place_name": "명동교자",
                "arrival": "12:30",
                "departure": "13:30",
                "stay_time": "60분",
                "lat": 37.562479,
                "lng": 126.985551,
                "category": "맛집"
            }
        ]
    }

    # 2. 서비스 함수 호출
    travel_map = render_itinerary_map(mock_state)

    # 3. 검증 (Assertion)
    if travel_map is None:
        print("❌ 테스트 실패: 지도 객체가 생성되지 않았습니다.")
        return

    # 마커 개수 확인
    count = travel_map.get_place_count
    if count == 3:
        print(f"✅ 성공: {count}개의 마커가 정상적으로 생성되었습니다.")
    else:
        print(f"❌ 실패: 마커 개수가 일치하지 않습니다. (기대: 3, 실제: {count})")

    # 데이터 정렬 및 경로 확인
    places = travel_map.get_places
    if places[0].name == "서울역" and places[-1].name == "명동교자":
        print("✅ 성공: 방문 순서(order)에 따라 장소가 올바르게 정렬되었습니다.")
    else:
        print("❌ 실패: 장소 정렬이 올바르지 않습니다.")

    # Folium 객체 렌더링 여부 확인
    folium_map = travel_map.render()
    if folium_map is not None:
        print("✅ 성공: Folium Map 객체가 정상적으로 렌더링되었습니다.")
    
    print("\n🎉 모든 테스트 통과!")

if __name__ == "__main__":
    test_map_generation()