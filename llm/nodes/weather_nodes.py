from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys
from services.weather_service import normalize_city_name_for_weather, build_weather_based_route_decision

def weather_node(state: TravelAgentState):
    """
    state의 destination을 바탕으로 실제 weather_service를 호출하는 노드
    """
    destination = state.get(StateKeys.DESTINATION)

    if not destination:
        return {
            StateKeys.WEATHER_DATA: {
                "status": "need_city",
                "message": "도시 정보가 없어 날씨를 조회할 수 없습니다."
            }
        }

    api_city_name = normalize_city_name_for_weather(destination)

    result = build_weather_based_route_decision(
        city_name=api_city_name,
        travel_date=None,
    )

    return {StateKeys.WEATHER_DATA: result}