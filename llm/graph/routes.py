from llm.graph.contracts import StateKeys
from llm.graph.state import TravelAgentState


def _has_place_context(state: TravelAgentState) -> bool:
    selected_places = state.get(StateKeys.SELECTED_PLACES, [])
    mapped_places = state.get(StateKeys.MAPPED_PLACES, [])
    return bool(selected_places or mapped_places)


def should_continue(state: TravelAgentState):
    route = state.get(StateKeys.ROUTE, "chat")

    if route == "weather":
        return "weather_node"

    if route in ["place", "travel"]:
        return "place_node"

    if route == "schedule":
        if not _has_place_context(state):
            return "place_node"
        return "scheduler_node"

    if route == "modify":
        return "modify_node"

    return "response_node"


def route_after_missing_check(state: TravelAgentState):
    route = state.get(StateKeys.ROUTE, "chat")
    destination = state.get(StateKeys.DESTINATION)

    if route == "chat":
        return "response_node"

    print("[DEBUG] route_after_missing_check destination =", destination)

    if not destination:
        return "ask_user_node"

    return should_continue(state)


def route_after_safety_check(state: TravelAgentState):
    if state.get(StateKeys.BLOCKED, False):
        return "blocked_response_node"
    return "summary_node"
