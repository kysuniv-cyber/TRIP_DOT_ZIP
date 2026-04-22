# nodes/response_nodes.py
from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys


def build_response_node(state: TravelAgentState) -> dict:
    """
    모든 분석 결과를 종합하여 사용자에게 줄 최종 답변을 생성합니다.
    """
    # 1. 데이터 가져오기
    weather_data = state.get(StateKeys.WEATHER_DATA)
    itinerary = state.get(StateKeys.ITINERARY, [])
    destination = state.get(StateKeys.DESTINATION, "요청하신 지역")
    selected_places = state.get(StateKeys.SELECTED_PLACES, [])
    places = selected_places or state.get(StateKeys.MAPPED_PLACES, [])      # 장소를 보여줄 때 선택된 장소를 우선 순위에 놓고 보여주도록 함.
    route = state.get(StateKeys.ROUTE)

    # 2. 답변 시나리오 구성
    response_text = ""

    # (A) weather route는 우선 처리 후 바로 종료. 아래로 내려가지 못 하게.
    if route == "weather" and weather_data and isinstance(weather_data, dict):
        status = weather_data.get("status")

        if status == "success":
            weather = weather_data.get("weather", {})
            condition = weather_data.get("condition", {})
            ddatchwi = weather_data.get("ddatchwi", {})

            response_text = (
                f"☀️ **{destination} 날씨 정보**\n"
                f"- 설명: {weather.get('description', '정보 없음')}\n"
                f"- 온도: {weather.get('temperature', '정보 없음')}도\n"
                f"- 추천 유형: {condition.get('route_recommendation', '정보 없음')}\n"
                f"- 이유: {condition.get('reason', '정보 없음')}\n\n"
                f"{ddatchwi.get('character', '')}\n"
                f"{ddatchwi.get('message', '')}"
            )
            return {StateKeys.FINAL_RESPONSE: response_text}

        response_text = weather_data.get("message", "날씨 정보를 확인하지 못했습니다.")
        return {StateKeys.FINAL_RESPONSE: response_text}

    # (B) 일정 정보가 있을 때 (최우선순위)
    if itinerary:
        response_text += f"📅 **{destination} 추천 일정**을 짜봤어요!\n"
        for item in itinerary:
            # scheduler_service의 데이터 구조에 맞춰 출력
            arrival = item.get("arrival", "시간 미정")
            departure = item.get("departure", "시간 미정")
            place_name = item.get("place_name", "장소명 미정")
            response_text += f"- {arrival} ~ {departure}: {place_name}\n"
        response_text += "\n이 일정대로 이동하시면 효율적이에요! 마음에 드시나요?"

    # (C) 장소 추천만 있을 때
    elif places:
        response_text += f"📍 **{destination} 추천 장소**들이에요:\n"
        for p in places[:3]:  # 상위 3개만 노출
            place_name = p.get("name", "이름 없음")
            category = p.get("category", "명소")
            response_text += f"- {place_name} ({category})\n"
        response_text += "\n이 장소들을 중심으로 일정을 짜드릴까요?"

    # (D) 목적지는 있는데 장소 검색 결과가 비었을 때
    elif destination:
        response_text = f"{destination}에서 조건에 맞는 장소를 아직 찾지 못했어요. 조건을 조금 완화해서 다시 추천해드릴까요?"

    # (E) 일반 대화 혹은 데이터 부족 시
    else:
        response_text = "죄송해요, 요청하신 정보를 찾지 못했습니다. 다시 말씀해 주시겠어요?"

    # 3. 결과 반환 (final_response 업데이트)
    return {StateKeys.FINAL_RESPONSE: response_text}