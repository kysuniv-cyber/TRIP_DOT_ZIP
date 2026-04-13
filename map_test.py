# map.py
# 1차 맵 화면을 보여주는 임시 map 화면
# 차후 app.py 화면에 들어갈 예정.

import streamlit as st
from streamlit_folium import st_folium
from components.travel_map import TravelMap, PlaceInfo

st.title("AI 여행 코스 추천")

# 임시 테스트 데이터
places = [
    PlaceInfo(place_id="1", name="경복궁",     lat=37.5796, lng=126.9770, order=1),
    PlaceInfo(place_id="2", name="광장시장",   lat=37.5699, lng=126.9997, order=2),
    PlaceInfo(place_id="3", name="북촌한옥마을", lat=37.5826, lng=126.9853, order=3),
]

# TravelMap 생성 및 렌더링
travel_map = TravelMap(center_lat=37.5796, center_lng=126.9770)

travel_map \
    .add_markers(places) \
    .add_route() \
    .auto_fit()

st_folium(travel_map.render(), width="100%", height=500)

print(travel_map.get_place_count)
print(travel_map.get_places)