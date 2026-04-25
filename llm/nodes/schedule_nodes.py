from llm.graph.contracts import StateKeys
from llm.graph.state import TravelAgentState
from services.scheduler_service import create_schedule


def scheduler_node(state: TravelAgentState) -> dict:
    selected_places = state.get(StateKeys.SELECTED_PLACES, [])
    start_time = state.get(StateKeys.START_TIME, "09:00")
    trip_length = state.get(StateKeys.TRIP_LENGTH, "당일치기")

    if not selected_places:
        print("[DEBUG] scheduler_node skipped: no validated selected_places")
        return {StateKeys.ITINERARY: []}

    normalized_places = []
    for place in selected_places:
        metadata = place.get("metadata", {}) if isinstance(place, dict) else {}
        normalized_places.append(
            {
                "name": place.get("name"),
                "lat": place.get("lat") or metadata.get("place_lat"),
                "lng": place.get("lng") or metadata.get("place_lng"),
                "types": [place.get("category", "default")] if place.get("category") else ["default"],
            }
        )

    if isinstance(start_time, int):
        start_time = f"{start_time:02d}:00"
    elif not isinstance(start_time, str):
        start_time = "09:00"

    print("[DEBUG] scheduler_node start_time =", start_time)
    print("[DEBUG] scheduler_node places count =", len(selected_places))

    itinerary_result = create_schedule(
        places=normalized_places,
        start_time_str=start_time,
        trip_length=trip_length,
    )

    if isinstance(itinerary_result, dict) and itinerary_result.get("status") == "error":
        return {StateKeys.ITINERARY: []}

    return {StateKeys.ITINERARY: itinerary_result}
