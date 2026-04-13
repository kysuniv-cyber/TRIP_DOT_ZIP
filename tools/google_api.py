from pydantic import BaseModel, Field
from langchain.tools import tool
import os
import requests
from dotenv import load_dotenv
from utils.custom_exception import PlaceNotFoundError

load_dotenv()

# TODO: 1. 필요한 부분 category(types 매핑)
# TODO: 2. API에서 가져온 정보가지고 LLM에 전달할 장소 추천 멘트 생성

# LLM에게 제공할 Schema
class PlaceSearchInfo(BaseModel):
    """
        PlaceSearchTool에서 LLM이 툴 호출 시 참고할 Input Schema
        BaseModel: 엄격한 타입 제한.
    """
    # LLM 확인을 위한 Field
    destination: str = Field(description="검색할 도시 또는 지역명(예: 부산, 서울, 타이페이)")
    styles: list[str] = Field(default=[], description="여행 스타일 목록(예: 카페, 명소, 관광지 등)")
    constraints: list[str] = Field(default=[], description="특별한 제약사항(예: 채식, 반려동물, 비, 우천)")
    limit: int = Field(default=10, description="추천받을 장소의 최대 개수")

# search_place tool
@tool("place_search", args_schema=PlaceSearchInfo)
def search_place_tool(destination: str, styles: list[str], constraints: list[str], limit: int = 5) -> dict[str, any]:
    """
        Google Places API (New)사용 특정 지역(destination)의 장소 데이터 검색

        destination (str):
        styles (list[str])
        constraints (list[str])
        limit (int)
    """
    api_key = os.getenv("GOOGLE_PLACE_API_KEY")
    print("api_key", api_key)

    url = "https://places.googleapis.com/v1/places:searchText"
    
    # 검색쿼리
    query = f"{destination} {' '.join(styles)} {' '.join(constraints)}"
    
    # API Headers (FieldMask 필수★ 까다로움 주의)
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.primaryType,places.primaryTypeDisplayName,places.types,places.priceLevel,places.priceRange,places.rating"
    }
    
    payload = {
        "textQuery": query,
        "maxResultCount": limit,
        "languageCode": "ko"
    }

    try:
        # TODO: API 호출 공통부로 구분 예정.
        response = requests.post(url, json=payload, headers=headers)
        print("response", response.text)
        response.raise_for_status()
        results = response.json().get("places", [])
        
        results = []    # placeNotFoundError 테스트

        mapped_places = []
        if len(results) > 0:
            for p in results:
                types = p.get("types", [])
                # TODO: 지금은 실내 여부 판별 로직을 간단하게 넣었는데, 이것도 따로 매핑하는 함수를 만들어야 함.
                is_indoor = any(t in ["shopping_mall", "museum", "cafe"] for t in types)

                temp_place_info = {
                    "place_id": p.get("id"),
                    "name": p.get("displayName", {}).get("text"),
                    # TODO: types의 종류가 많아서, 간단하게 변경할 함수 생성
                    "category": types[0] if types else "N/A",
                    "lat": p.get("location", {}).get("latitude"),
                    "lng": p.get("location", {}).get("longitude"),
                    "summary": p.get("editorialSummary", {}).get("text", "정보 없음"),
                    "rating": p.get("rating", {}),
                    "indoor_outdoor": "indoor" if is_indoor else "outdoor",
                }

                mapped_places.append({
                    **temp_place_info,
                    "recommended_reason": f"{destination}에서 평점 {temp_place_info.rating}의 {temp_place_info.category} 중 하나입니다."
                })

            return {
                "status": "success",
                "data": {"places": mapped_places},
                "error": None,
                "meta": {"tool_name": "place_search", "total_found": len(mapped_places)}
            }
        else: 
            raise PlaceNotFoundError(
                "place_search_tool"
            )
        
    except PlaceNotFoundError as e:
        # 정해진 error message 호출
        return e.error_response()

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": str(e),
            "meta": {"tool_name": "place_search"}
        }

    
# 호출 테스트
if __name__ == "__main__":

    # 함수호출에 필요한 값
    test_destination = "부산"
    test_styles = ["맛집", "카페"]
    test_constraints = ["실내", "주차 가능"]
    
    print(f"--- '{test_destination}' 검색 테스트 시작 ---")

    list = []

    # tool 호출
    result = search_place_tool.invoke({
        "destination": test_destination,
        "styles": test_styles,
        "constraints": test_constraints,
        "limit": 3
    })

    # 결과 확인
    import json
    print(json.dumps(result, indent=4, ensure_ascii=False))