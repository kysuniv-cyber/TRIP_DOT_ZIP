from langchain.tools import tool
from llm.schemas import success_response


@tool
def search_places(region: str, theme: str) -> dict:
    """
    지역과 테마를 받아 후보 장소 리스트를 반환한다.
    지금은 mock 함수이며, 나중에 장소 검색 API/DB로 교체한다.
    """
    mock_places = [
        {
            "place_id": 1,
            "name": f"{region} 감성 카페",
            "category": "cafe",
            "address": f"{region} 어딘가 1",
            "rating": 4.7,
        },
        {
            "place_id": 2,
            "name": f"{region} 유명 맛집",
            "category": "restaurant",
            "address": f"{region} 어딘가 2",
            "rating": 4.6,
        },
        {
            "place_id": 3,
            "name": f"{region} 산책 명소",
            "category": "attraction",
            "address": f"{region} 어딘가 3",
            "rating": 4.8,
        },
    ]

    return success_response(
        {
            "region": region,
            "theme": theme,
            "places": mock_places,
        }
    )