import pandas as pd
import googlemaps
from datetime import datetime, timedelta
from dotenv import load_dotenv

from config import Settings
from utils.custom_exception import CommonCustomError, RouteNotFoundError


load_dotenv()

setting = Settings()
places_api_key = setting.places_api_key

try:
    gmaps = googlemaps.Client(key=places_api_key)
except Exception as e:
    print(f"googlemaps client init failed: {e}")


STAY_TIME_CONFIG = {
    "art_gallery": 120,
    "art_museum": 150,
    "museum": 150,
    "castle": 120,
    "cultural_landmark": 90,
    "historical_place": 90,
    "history_museum": 150,
    "monument": 30,
    "sculpture": 20,
    "cultural_center": 90,
    "amusement_park": 240,
    "aquarium": 120,
    "zoo": 180,
    "botanical_garden": 120,
    "wildlife_park": 180,
    "water_park": 240,
    "casino": 120,
    "movie_theater": 150,
    "performing_arts_theater": 150,
    "opera_house": 180,
    "park": 60,
    "city_park": 60,
    "national_park": 180,
    "hiking_area": 120,
    "garden": 60,
    "beach": 120,
    "marina": 45,
    "picnic_ground": 90,
    "restaurant": 90,
    "cafe": 60,
    "bar": 90,
    "bakery": 30,
    "coffee_shop": 45,
    "ice_cream_shop": 20,
    "shopping_mall": 150,
    "department_store": 120,
    "clothing_store": 60,
    "market": 90,
    "gift_shop": 30,
    "duty_free_store": 60,
    "church": 45,
    "hindu_temple": 45,
    "mosque": 45,
    "synagogue": 45,
    "shrine": 30,
    "library": 60,
    "university": 90,
    "default": 60,
}


def get_real_travel_time(origin: dict, destination: dict, departure_time: datetime, mode: str = "transit"):
    """Google Distance Matrix를 사용해 실제 이동 시간을 분 단위로 계산합니다."""
    try:
        result = gmaps.distance_matrix(
            origins=[(origin["lat"], origin["lng"])],
            destinations=[(destination["lat"], destination["lng"])],
            mode=mode,
            departure_time=departure_time,
        )

        element = result["rows"][0]["elements"][0]
        if element["status"] != "OK":
            raise RouteNotFoundError(
                origin=origin.get("name", "출발지"),
                destination=destination.get("name", "목적지"),
            )

        return element["duration"]["value"] // 60
    except Exception as e:
        if isinstance(e, RouteNotFoundError):
            raise e
        raise CommonCustomError(
            code="GOOGLE_API_ERROR",
            message=f"Google API 호출 중 오류가 발생했습니다: {str(e)}",
            tool_name="get_real_travel_time",
        )


def get_stay_duration(place_categories: list) -> int:
    """장소 카테고리에 따라 기본 체류 시간을 계산합니다."""
    if not place_categories:
        return STAY_TIME_CONFIG["default"]

    durations = [STAY_TIME_CONFIG.get(category, STAY_TIME_CONFIG["default"]) for category in place_categories]
    return max(durations)


def _get_day_count(trip_length: str | None) -> int:
    """여행 길이 문자열을 일정 일수로 변환합니다."""
    if trip_length == "2박3일":
        return 3
    if trip_length == "1박2일":
        return 2
    return 1


def _split_places_by_day(places: list, trip_length: str | None) -> list[list]:
    """선택된 장소를 여행 일수에 맞춰 일차별로 고르게 분배합니다."""
    day_count = _get_day_count(trip_length)
    return [places[index::day_count] for index in range(day_count)]


def create_schedule(
    places: list,
    start_time_str: str = "09:00",
    mode: str = "transit",
    optimize_route: bool = True,
    trip_length: str | None = None,
):
    """선택된 장소를 기준으로 여행 일수에 맞는 일정표를 생성합니다."""
    print("[DEBUG] create_schedule start_time_str =", start_time_str)

    try:
        base_date = datetime.now().replace(
            hour=int(start_time_str[:2]),
            minute=int(start_time_str[3:]),
            second=0,
            microsecond=0,
        )
    except (ValueError, IndexError):
        error = CommonCustomError(
            code="INVALID_TIME_FORMAT",
            message="시작 시간 형식이 올바르지 않습니다.",
            tool_name="create_schedule",
        )
        return error.error_response()

    itinerary = []
    place_chunks = _split_places_by_day(places, trip_length)

    for day_index, chunk in enumerate(place_chunks, start=1):
        if not chunk:
            continue

        current_departure_time = base_date
        unvisited = chunk.copy()
        current_place = unvisited.pop(0)
        order = 1

        while True:
            arrival_time = current_departure_time
            place_types = current_place.get("types", [])
            stay_min = get_stay_duration(place_types)
            actual_departure_time = arrival_time + timedelta(minutes=stay_min)

            itinerary.append(
                {
                    "day": day_index,
                    "order": order,
                    "place_name": current_place["name"],
                    "arrival": arrival_time.strftime("%H:%M"),
                    "departure": actual_departure_time.strftime("%H:%M"),
                    "stay_time": f"{stay_min}분",
                    "lat": current_place["lat"],
                    "lng": current_place["lng"],
                }
            )

            if not unvisited:
                break

            try:
                if optimize_route:
                    travel_times = []
                    for place in unvisited:
                        travel_times.append(
                            get_real_travel_time(current_place, place, actual_departure_time, mode=mode)
                        )

                    min_travel_min = min(travel_times)
                    next_idx = travel_times.index(min_travel_min)
                    next_place = unvisited.pop(next_idx)
                else:
                    next_place = unvisited.pop(0)
                    min_travel_min = get_real_travel_time(
                        current_place,
                        next_place,
                        actual_departure_time,
                        mode=mode,
                    )

                current_departure_time = actual_departure_time + timedelta(minutes=min_travel_min)
                current_place = next_place
                order += 1

            except (RouteNotFoundError, CommonCustomError) as e:
                return e.error_response()
            except Exception as e:
                system_error = CommonCustomError(
                    code="INTERNAL_SERVER_ERROR",
                    message=str(e),
                    tool_name="create_schedule",
                )
                return system_error.error_response()

    return itinerary


def print_final_itinerary(itinerary):
    """생성된 일정표를 콘솔에서 보기 쉬운 형태로 출력합니다."""
    if isinstance(itinerary, dict) and itinerary.get("status") == "error":
        print(f"일정 생성 실패: {itinerary.get('message')}")
        return

    print("\n" + "=" * 50)
    print("Trip.Zip 추천 일정")
    print("=" * 50)

    df = pd.DataFrame(itinerary)
    columns = ["order", "arrival", "departure", "place_name", "stay_time"]
    if "day" in df.columns:
        columns = ["day", *columns]
    display_df = df[columns]
    print(display_df.to_string(index=False))
    print("-" * 50)

    for spot in itinerary:
        day_prefix = f"[Day {spot['day']}] " if "day" in spot else ""
        print(f"{day_prefix}[{spot['arrival']}] {spot['place_name']} 방문 ({spot['stay_time']} 체류)")

    print("=" * 50)
    print("즐거운 여행 되세요!")
