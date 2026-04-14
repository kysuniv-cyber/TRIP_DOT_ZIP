# 환경설정
# pip install googlemaps
import pandas as pd
import googlemaps
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.custom_exception import CommonCustomError, RouteNotFoundError
from config import Settings
load_dotenv()
api_key = os.getenv("PLACES_API_KEY")

# API 키
# 구글 맵 클라이언트 설정 (발급받은 API 키 입력)
places_api_key = Settings.places_api_key

# 2. STAY_TIME_CONFIG
# Google Places API Table A & B 기반 평균 체류 시간 설정 ★ Placesearch
STAY_TIME_CONFIG = {
    # --- 문화 및 역사 ---
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
    # --- 엔터테인먼트 및 여가 ---
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
    # --- 공원 및 자연 ---
    "park": 60,
    "city_park": 60,
    "national_park": 180,
    "hiking_area": 120,
    "garden": 60,
    "beach": 120,
    "marina": 45,
    "picnic_ground": 90,
    # --- 식음료 ---
    "restaurant": 90,
    "cafe": 60,
    "bar": 90,
    "bakery": 30,
    "coffee_shop": 45,
    "ice_cream_shop": 20,
    # --- 쇼핑 ---
    "shopping_mall": 150,
    "department_store": 120,
    "clothing_store": 60,
    "market": 90,
    "gift_shop": 30,
    "duty_free_store": 60,
    # --- 종교 및 기타 ---
    "church": 45,
    "hindu_temple": 45,
    "mosque": 45,
    "synagogue": 45,
    "shrine": 30,
    "library": 60,
    "university": 90,
    # --- 기본값 ---
    "default": 60
}

# 3. 이동시간 계산함수
def get_real_travel_time(origin: dict, destination: dict, departure_time: datetime, mode: str = 'transit'):
    """구글 Distance Matrix API를 사용하여 두 지점 간의 실제 이동 시간을 계산함.

    입력된 출발 시간(departure_time)의 교통 상황이나 대중교통 배차 간격을 반영하여
    최적의 소요 시간을 분(minute) 단위로 추출함.

    Args:
        origin (dict): 출발지 정보 (예: {'lat': 0.0, 'lng': 0.0})
        destination (dict): 목적지 정보 (예: {'lat': 0.0, 'lng': 0.0})
        departure_time (datetime): 해당 장소에서 출발할 예상 시각
        mode (str): 이동 수단 ('transit', 'walking', 'driving', 'bicycling'). 기본값 'transit'.

    Returns:
        int: 이동 소요 시간 (분 단위). 경로를 찾을 수 없는 경우 None 반환.
    """
    # mode: 'driving' (운전), 'walking' (도보), 'transit' (대중교통) -> 현재 transit으로 설정, 운전이나 도보로 설정하려면 [C] 수정 요망
    try:
        # [A] API 호출 자체 (서버 점검, 키 오류 등 발생 가능)
        result = gmaps.distance_matrix(
            origins=[(origin['lat'], origin['lng'])],
            destinations=[(destination['lat'], destination['lng'])],
            mode=mode,
            departure_time=departure_time
        )

        # [B] 결과 값 확인 (데이터상 경로가 있는지 확인)
        element = result['rows'][0]['elements'][0]

        # (오류1) 구글 API가 경로를 찾지 못한 경우 (ZERO_RESULTS 등) RouteNotFoundError (전용자식클래스) 사용
        if element['status'] != 'OK':
            raise RouteNotFoundError(
                origin=origin.get('name', '출발지'),
                destination=destination.get('name', '목적지')
            )

        # [C] 결과에서 시간(seconds) 추출 후 분(min) 단위로 변환
        seconds = element['duration']['value']
        return seconds // 60

        # (오류2) 예상치 못한 API 오류 시 CommonCustomError (부모클래스) 사용
    except Exception as e:
        if isinstance(e, RouteNotFoundError):
            raise e
        raise CommonCustomError(
            code="GOOGLE_API_ERROR",
            message=f"구글 API 호출 중 오류가 발생했습니다: {str(e)}",
            tool_name="get_real_travel_time"
        )

# 4. 체류시간 계산 함수
def get_stay_duration(place_categories: list) -> int:
    """장소의 카테고리 목록을 기반으로 예상 체류 시간을 결정함.

    구글 Places API에서 제공하는 장소 유형(Table A & B) 리스트를 외부 설정 파일(STAY_TIME_CONFIG)과
    비교하여, 해당 장소에 가장 적합한(가장 긴) 평균 체류 시간을 선택함.

    Args:
        place_categories (list): 구글 API로부터 받은 장소 유형 리스트 (예: ['museum', 'art_gallery'])

    Returns:
        int: 해당 장소에서 머물 예상 시간 (분 단위). 매칭되는 항목이 없으면 기본값(60분) 반환.
    """
    # 장소에 카테고리 정보가 없으면 기본값 반환
    if not place_categories:
        return STAY_TIME_CONFIG["default"]

    # 해당 장소의 여러 카테고리 중 설정 파일에 있는 값들을 찾음
    durations = [STAY_TIME_CONFIG.get(cat, STAY_TIME_CONFIG["default"])
                 for cat in place_categories]

    # 여러 카테고리가 겹칠 경우(예: museum이면서 art_gallery), 가장 긴 시간을 선택
    return max(durations)

# 5. 스케쥴링 함수
def create_schedule(places: list, start_time_str: str = "09:00", mode: str = 'transit', optimize_route: bool = True):
    """사용자 요청에 따라 고정 순서 또는 최적 동선(Nearest Neighbor)으로 일정을 생성함.

    Args:
        places (list): 방문 후보 장소 객체들의 리스트.
        start_time_str (str): 여행 시작 시각 (HH:MM 형식). 기본값 "09:00".
        mode (str): 이동 수단 ('transit', 'walking', 'driving'). 기본값 'transit'.
        optimize_route (bool): True이면 최적 동선 계산, False이면 입력된 순서 그대로 생성.

    Returns:
        list or dict: 성공 시 일정 리스트, 실패 시 에러 응답 객체(dict) 반환.
    """
    # 1. 초기 시간 설정
    try:
        base_date = datetime.now().replace(
            hour=int(start_time_str[:2]),
            minute=int(start_time_str[3:]),
            second=0, microsecond=0
        )
    except (ValueError, IndexError):
        # 시작 시간 형식이 잘못된 경우 처리
        error = CommonCustomError(code="INVALID_TIME_FORMAT", message="시작 시간 형식이 올바르지 않습니다.", tool_name="create_schedule")
        return error.error_response()

    current_departure_time = base_date
    itinerary = []
    unvisited = places.copy()

    # 2. 첫 번째 장소 설정 (숙소 또는 시작점)
    current_place = unvisited.pop(0)
    order = 1

    while True:
        # [A] 현재 장소 일정 확정
        arrival_time = current_departure_time
        place_types = current_place.get('types', [])

        # 외부 STAY_TIME_CONFIG 참조하여 체류 시간 결정
        stay_min = get_stay_duration(place_types)
        actual_departure_time = arrival_time + timedelta(minutes=stay_min)

        itinerary.append({
            "order": order,
            "place_name": current_place['name'],
            "arrival": arrival_time.strftime("%H:%M"),
            "departure": actual_departure_time.strftime("%H:%M"),
            "stay_time": f"{stay_min}분",
            "lat": current_place['lat'],
            "lng": current_place['lng']
        })

        # 모든 장소를 방문했다면 루프 종료
        if not unvisited:
            break

        # [B] 다음 장소 결정 및 이동 시간 계산
        try:
            if optimize_route:
                # -------------------------------------------------------
                # 옵션 1: 최적 동선 모드 (가장 가까운 미방문지 선택)
                # -------------------------------------------------------
                travel_times = []
                for p in unvisited:
                    t = get_real_travel_time(current_place, p, actual_departure_time, mode=mode)
                    travel_times.append(t)

                min_travel_min = min(travel_times)
                next_idx = travel_times.index(min_travel_min)
                next_place = unvisited.pop(next_idx)
            else:
                # -------------------------------------------------------
                # 옵션 2: 고정 순서 모드 (리스트에 들어온 순서대로 방문)
                # -------------------------------------------------------
                next_place = unvisited.pop(0)
                min_travel_min = get_real_travel_time(current_place, next_place, actual_departure_time, mode=mode)

            # [C] 다음 목적지 도착 예정 시각 업데이트
            current_departure_time = actual_departure_time + timedelta(minutes=min_travel_min)
            current_place = next_place
            order += 1

        except (RouteNotFoundError, CommonCustomError) as e:
            # (오류1) 구글 API가 경로를 찾지 못한 경우 (ZERO_RESULTS 등) RouteNotFoundError (전용자식클래스) 사용
            return e.error_response()
        except Exception as e:
            # (오류3) 예상치 못한 시스템 오류 시 CommonCustomError (부모클래스) 사용
            system_error = CommonCustomError(code="INTERNAL_SERVER_ERROR", message=str(e), tool_name="create_schedule")
            return system_error.error_response()

    # 최종 일정 리스트 반환 (성공 응답은 호출부에서 status: success로 감싸서 처리 권장)
    return itinerary