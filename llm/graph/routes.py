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
        return "response_node"

    # 기본값
    return "response_node"


def route_after_missing_check(state: TravelAgentState):
    """
    missing_slots 존재 여부에 따라 다음 노드를 결정합니다.

    - missing_slots가 있으면 사용자에게 질문
    - 없으면 원래 route 기준으로 다음 단계 진행
    """
    missing_slots = state.get(StateKeys.MISSING_SLOTS, [])
    if missing_slots:
        return "ask_user_node"

    return should_continue(state)