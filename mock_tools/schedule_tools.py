from langchain.tools import tool
from llm.schemas import success_response


@tool
def build_schedule(
    start_time: str,
    end_time: str,
    places: list[dict],
) -> dict:
    """
    장소 리스트를 받아 간단한 일정표를 생성한다.
    지금은 mock 함수이며, 나중에 실제 최적화 로직으로 교체한다.
    """
    itinerary = []

    time_slots = ["10:00", "12:00", "14:00", "16:00", "18:00"]

    for idx, place in enumerate(places[:len(time_slots)]):
        itinerary.append(
            {
                "order": idx + 1,
                "place_id": place.get("place_id"),
                "place_name": place.get("name"),
                "category": place.get("category"),
                "time": time_slots[idx],
            }
        )

    return success_response(
        {
            "start_time": start_time,
            "end_time": end_time,
            "itinerary": itinerary,
        }
    )