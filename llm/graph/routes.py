from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys

def should_continue(state: TravelAgentState):
    """
    State의 route 값에 따라 다음 노드를 결정하는 Router 함수
    """
    route = state.get(StateKeys.ROUTE, "chat")

    # 1. 날씨 확인이 필요한 경우
    if route == "weather":
        return "weather_node"

    # 2. 장소 검색이 필요한 경우 (travel_recommendation 포함)
    elif route in ["place", "travel"]:
        return "place_node"

    # 3. 일정 생성이 필요한 경우
    elif route == "schedule":
        # 만약 장소 검색 결과(mapped_places)가 이미 있다면 바로 일정 생성으로 가고,
        # 없다면 장소 검색을 먼저 거치도록 설계할 수 있습니다.
        if not state.get(StateKeys.MAPPED_PLACES):
            return "place_node"
        return "scheduler_node"

    # 4. 수정 요청이나 일반 대화
    elif route in ["modify", "chat"]:
        return "final_answer_node"

    # 기본값
    return "final_answer_node"