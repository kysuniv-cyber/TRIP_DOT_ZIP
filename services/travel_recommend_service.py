# services/travel_recommend_service.py

from services.place_search_service import search_place_tool


def recommend_travel_places(query: str) -> dict:
    """
    사용자 여행 추천 요청을 받아
    적절한 장소 리스트를 반환한다.
    """

    try:
        # 1. 기본적으로 place search 사용
        result = search_place_tool.invoke({"query": query})

        # 2. 나중에 여기에 필터/랭킹 추가 가능
        # 예:
        # - 계절
        # - 인기순
        # - 실내/야외
        # - 여행 스타일

        return {
            "status": "success",
            "data": result,
            "meta": {
                "source": "travel_recommend_service"
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": str(e),
            "meta": {
                "source": "travel_recommend_service"
            }
        }