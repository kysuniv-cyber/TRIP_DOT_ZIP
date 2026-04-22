"""
    FileName: place_node.py
    Location: llm/nodes/place_node.py
    Role: Place Node
        사용자가 입력한 도착지 정보(State.destination)의 방문지 후보를 
        Google Place API를 통해 불러와 Vector DB에 저장
"""
from llm.graph.state import TravelAgentState
from typing import List
from config import Settings
import requests
from llm.graph.contracts import StateKeys
from utils.db_util import run_pipeline

# API KEY
PLACES_API_KEY = Settings.places_api_key
# Google API 호출 데이터 최댓값
API_LIMIT = 2 # 20

# API 호출 함수
def get_places_by_api(destination:str, search_task:List[dict]):
    """ destination과 search_task를 받아, google api 호출 """
    
    if destination and len(search_task) > 0 :
        url = "https://places.googleapis.com/v1/places:searchText"
        
        # API를 통해 호출할 column
        fields = [
            "places.id",                        # 장소 ID
            "places.displayName",               # 이름 {text, languageCode}
            "places.location",                  # 장소 {latitude, longitude}
            "places.primaryType",               # 대표 type
            "places.primaryTypeDisplayName",    # 대표 타입명
            "places.types",                     # 타입들
            "places.priceLevel",                # 가격대 -> 찍히는지 확인
            "places.priceRange",                # 가격대 {startPrice, endPrice}
            "places.rating",                    # 평점
            "places.reviews",                   # 리뷰정보
            "places.reviewSummary"              # 안됨.   
        ]

        # google place API 호출 header
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": PLACES_API_KEY,
            "X-Goog-FieldMask": ",".join(fields)
        }

        # API 결과값에서 결과 place 정보
        result_places = []
        
        for task in search_task:
            print(f"DEBUG: {task}")

            query = ' '.join([f"{destination} {s}" for s in task['styles']])

            payload = {
                "textQuery": query,
                "maxResultCount": API_LIMIT,
                "languageCode": "ko"
            }

            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json().get("places", []) 
                result_places.append(data)

                # print(f'DEBUG R: {len(result_places)}')
            else:
                print(f"API ERROR: {response.status_code} | {response.text}")
            

        return {
            "status_code": 200,
            "json_data": {"places": result_places[0]}
        }

        # print(result_list)
        # return {
        #     "status_code": response.status_code,
        #     "json_data": response.json() if response.status_code == 200 else None,
        #     "error_text": response.text if response.status_code != 200 else None
        # }
    else: 
        pass

def place_node(state: TravelAgentState):
    print(f'Debug: place_node {state}')

    # 만약 상태값 체크가 필요하면, 상태값 체크
    # 도착지
    destination = state.get(StateKeys.DESTINATION)

    # 제약조건 
    constraints = state.get(StateKeys.CONSTRAINTS)

    temp_places = []

    # 검색 전략 정의(관광지/식음료)
    search_tasks = [
        {"styles": ["관광명소", "가볼만한 곳", "추천여행지", "액티비티"]},  # 관광지
        {"styles": ["카페", "맛집", "식당"]}                            # 식음료
    ]

    # Google API 호출
    api_result = get_places_by_api(destination, search_tasks)
    # print(api_result)

    # api_result가 성공일 경우
    if api_result["status_code"] == 200:
    
        #print(f'DEBUG: type{api_result["json_data"]["places"][:1]}')
        result_chunk = run_pipeline(
            raw_data=api_result["json_data"]["places"], 
            chroma_dir=Settings.CHROMA_PERSIST_DIR, 
            collection_name=Settings.CHROMA_COLLECTION_NAME, 
            test_flag=False
        )

    # api_result가 실패
    else:
        pass

# 테스트 케이스 실행
if __name__ == "__main__":
    # 실제 사용자가 입력한 것 같은 State 객체 생성
    mock_state = TravelAgentState(
        destination="부산",
        styles=["액티비티", "바다"],
        constraints=["예산은 인당 5만원 이하", "도보 이동 위주"],
        # raw_places=[
        #     "1. 해운대 요트 투어 (인당 7만원)", 
        #     "2. 광안리 서핑 체험 (인당 6만원)"
        # ]
    )
    print("--- [테스트 시작: State 객체 전달] ---")
    place_node(mock_state)