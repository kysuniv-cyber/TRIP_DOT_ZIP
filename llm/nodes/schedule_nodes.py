from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys
from services.scheduler_service import create_schedule


def scheduler_node(state: TravelAgentState) -> dict:
    """
    선택된 장소와 시작 시간을 바탕으로 실제 일정을 생성하는 노드
    """
    places = state.get(StateKeys.SELECTED_PLACES) or state.get(StateKeys.MAPPED_PLACES, [])
    start_time = state.get(StateKeys.START_TIME, "09:00")

    if not places:
        return {StateKeys.ITINERARY: []}

    # scheduler_service가 기대하는 형태로 보정
    normalized_places = []
    for p in places:
        metadata = p.get("metadata", {}) if isinstance(p, dict) else {}
        normalized_places.append({
            "name": p.get("name"),
            "lat": p.get("lat") or metadata.get("place_lat"),
            "lng": p.get("lng") or metadata.get("place_lng"),
            "types": [p.get("category", "default")] if p.get("category") else ["default"],
        })

    # start_time 형식 보정
    if isinstance(start_time, int):
        start_time = f"{start_time:02d}:00"
    elif not isinstance(start_time, str):
        start_time = "09:00"

    print("[DEBUG] scheduler_node start_time =", start_time)
    print("[DEBUG] scheduler_node places count =", len(places))

    itinerary_result = create_schedule(
        places=normalized_places,
        start_time_str=start_time,
    )

    # scheduler_service가 에러 dict를 줄 수도 있으면 여기서 분기 가능
    if isinstance(itinerary_result, dict) and itinerary_result.get("status") == "error":
        return {StateKeys.ITINERARY: []}

    return {StateKeys.ITINERARY: itinerary_result}
