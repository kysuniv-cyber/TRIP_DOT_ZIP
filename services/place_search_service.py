"""
    FileName: place_search_service.py
    Location: services/place_search_service.py
    Role: LLM에게 Destination 및 다른 제약조건이나 사용자의 선호도 조건을 받아서 
        Google Place API(NEW)를 호출해 장소 정보를 받아오는 역할
"""
from dataclasses import dataclass, asdict

import streamlit as st
from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import List
import os
import requests
from sympy import re
from utils.custom_exception import PlaceNotFoundError
from config import Settings
import json

# 벡터 DB 적재 import
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import hashlib

# API KEY
places_api_key = Settings.places_api_key
openai_api_key = Settings.openai_api_key

# Test를 위한 값. => True 시 파일로 다운로드 가능.
SAVE_FILE_TEST_MODE = True

# 카테고리 단순화를 위한 mapping값. => TODO: constants.py
PLACE_CATEGORY_MAP = {
    # --- 문화 및 역사 (STAY_TIME_CONFIG 기준) ---
    "art_gallery": ["art_gallery"],
    "art_museum": ["art_museum"],
    "museum": ["museum", "history_museum", "planetarium"],
    "castle": ["castle"],
    "cultural_landmark": ["cultural_landmark", "historical_landmark", "historical_place", "monument"],
    "historical_place": ["historical_place"],
    "history_museum": ["history_museum"],
    "monument": ["monument", "sculpture"],
    "sculpture": ["sculpture"],
    "cultural_center": ["cultural_center", "auditorium", "community_center", "convention_center", "art_studio"],

    # --- 엔터테인먼트 및 여가 ---
    "amusement_park": ["amusement_park", "amusement_center", "roller_coaster", "water_park"],
    "aquarium": ["aquarium"],
    "zoo": ["zoo", "wildlife_park", "wildlife_refuge"],
    "botanical_garden": ["botanical_garden"],
    "wildlife_park": ["wildlife_park"],
    "water_park": ["water_park"],
    "casino": ["casino"],
    "movie_theater": ["movie_theater", "movie_rental"],
    "performing_arts_theater": ["performing_arts_theater", "amphitheatre", "concert_hall", "philharmonic_hall"],
    "opera_house": ["opera_house"],

    # --- 공원 및 자연 ---
    "park": ["park", "city_park", "dog_park", "playground", "plaza"],
    "city_park": ["city_park"],
    "national_park": ["national_park", "state_park"],
    "hiking_area": ["hiking_area", "mountain_peak", "nature_preserve", "woods"],
    "garden": ["garden"],
    "beach": ["beach", "lake", "river", "island"],
    "marina": ["marina", "fishing_pier", "fishing_pond"],
    "picnic_ground": ["picnic_ground", "barbecue_area"],

    # --- 식음료 (모든 세부 음식점 포함) ---
    "restaurant": [
        "restaurant", "american_restaurant", "asian_restaurant", "chinese_restaurant", 
        "french_restaurant", "italian_restaurant", "japanese_restaurant", "korean_restaurant", 
        "mexican_restaurant", "thai_restaurant", "seafood_restaurant", "steak_house", 
        "sushi_restaurant", "vietnamese_restaurant", "fine_dining_restaurant", "food_court",
        "fast_food_restaurant", "pizza_restaurant", "hamburger_restaurant", "ramen_restaurant"
        # ... 기타 모든 *_restaurant 타입 포함
    ],
    "cafe": ["cafe", "cat_cafe", "dog_cafe", "internet_cafe"],
    "bar": ["bar", "pub", "wine_bar", "night_club", "cocktail_bar", "lounge_bar", "sports_bar"],
    "bakery": ["bakery", "cake_shop", "pastry_shop"],
    "coffee_shop": ["coffee_shop", "tea_house", "juice_shop", "coffee_roastery"],
    "ice_cream_shop": ["ice_cream_shop", "dessert_shop", "dessert_restaurant", "confectionery"],

    # --- 쇼핑 ---
    "shopping_mall": ["shopping_mall"],
    "department_store": ["department_store", "hypermarket", "warehouse_store"],
    "clothing_store": ["clothing_store", "shoe_store", "jewelry_store", "womens_clothing_store", "sportswear_store"],
    "market": ["market", "farmers_market", "flea_market", "grocery_store", "supermarket"],
    "gift_shop": ["gift_shop", "toy_store", "book_store"],
    "duty_free_store": ["duty_free_store"],

    # --- 종교 및 기타 ---
    "church": ["church", "mosque", "synagogue", "hindu_temple", "buddhist_temple", "shinto_shrine"],
    "hindu_temple": ["hindu_temple"],
    "mosque": ["mosque"],
    "synagogue": ["synagogue"],
    "shrine": ["shinto_shrine"],
    "library": ["library"],
    "university": ["university", "school", "secondary_school", "primary_school", "college"],
}

# 실내/실외를 위한 카테고리값.
INDOOR_TYPES = {
    # 문화 및 예술
    "art_gallery", "art_museum", "museum", "history_museum", "planetarium",
    "cultural_center", "auditorium", "community_center", "convention_center", "art_studio",
    "library", "library",

    # 엔터테인먼트 (실내형)
    "casino", "movie_theater", "movie_rental", "performing_arts_theater", 
    "concert_hall", "philharmonic_hall", "opera_house", "amusement_center",
    "aquarium", # 아쿠아리움은 대부분 실내이므로 추가

    # 식음료 (전체)
    "restaurant", "american_restaurant", "asian_restaurant", "chinese_restaurant", 
    "french_restaurant", "italian_restaurant", "japanese_restaurant", "korean_restaurant", 
    "mexican_restaurant", "thai_restaurant", "seafood_restaurant", "steak_house", 
    "sushi_restaurant", "vietnamese_restaurant", "fine_dining_restaurant", "food_court",
    "fast_food_restaurant", "pizza_restaurant", "hamburger_restaurant", "ramen_restaurant",
    "cafe", "cat_cafe", "dog_cafe", "internet_cafe",
    "bar", "pub", "wine_bar", "night_club", "cocktail_bar", "lounge_bar", "sports_bar",
    "bakery", "cake_shop", "pastry_shop",
    "coffee_shop", "tea_house", "juice_shop", "coffee_roastery",
    "ice_cream_shop", "dessert_shop", "dessert_restaurant", "confectionery",

    # 쇼핑 (전체)
    "shopping_mall", "department_store", "hypermarket", "warehouse_store",
    "clothing_store", "shoe_store", "jewelry_store", "womens_clothing_store", "sportswear_store",
    "grocery_store", "supermarket", "gift_shop", "toy_store", "book_store", "duty_free_store",

    # 종교 및 교육
    "church", "mosque", "synagogue", "hindu_temple", "buddhist_temple", "shinto_shrine",
    "university", "school", "secondary_school", "primary_school", "college",
}

KEYWORD_DICT = {
    "청결": ["깔끔", "청결", "위생", "냄새", "깨끗"],
    "직원": ["직원", "친절", "설명", "서비스"],
    "아이": ["아이", "아기", "어린이", "키즈", "아들", "딸"],
    "동물": ["동물", "카피바라", "토끼", "강아지"],
    "시설": ["시설", "넓", "공간", "층", "주차"],
    "가격": ["가격", "비용", "무료", "유료", "입장"],
    "재방문": ["재방문", "또 올", "다음에도", "추천"],
}
 
NOISE_PATTERNS = [
    r"https?://\S+",          # URL 제거
    r"[ㅋㅎㅠㅜ]{2,}",         # 반복 자모 축약 (ㅋㅋ → 공백)
    r"[~!@#$%^&*]{2,}",       # 반복 특수문자 정리
    r"\s{2,}",                # 다중 공백 → 단일 공백
]

# LLM에게 제공할 Schema
class PlaceSearchInfo(BaseModel):
    """
        PlaceSearchTool에서 LLM이 툴 호출 시 참고할 Input Schema
        BaseModel: 엄격한 타입 제한.
    """
    # LLM 확인을 위한 Field
    destination: str = Field(..., description="검색할 도시 또는 지역명(예: 부산, 서울, 타이페이)")
    styles: List[str] = Field(default=[], description="여행 스타일 목록(예: 카페, 명소, 관광지 등)")
    constraints: List[str] = Field(default=[], description="특별한 제약사항(예: 채식, 반려동물, 비, 우천)")
    limit: int = Field(default=10, description="추천받을 장소의 최대 개수")

# LLM에게 제공할 Schema 부분이 빠짐. => LLM에게 직접 전달하지 않으니.
@dataclass 
class PlaceReviewChunkInfo:
    """
        장소에 대한 리뷰 정보를 담는 데이터 클래스
        벡터 DB에 적재할 최소 단위 청크
        하나의 리뷰 = 하나의 청크 + 장소 메타데이터
    """
    # 식별자
    chunk_id: str
    place_id: str

    # 임베딩 대상 텍스트
    text_for_embedding: str # 전처리 완료 텍스트
    raw_text: str           # 원본 리뷰 텍스트

    # 메타데이터(필터링/검색용)
    place_name: str
    place_lat: float
    place_lng: float
    place_category: str
    place_rating: float
    place_type: str     # indoor/outdoor

    review_rating: int
    review_author: str
    review_published_at: str            # ISO 8601
    review_relative_time: str           # "2달 전" 등 원본 표현

    language_code: str

    # 분석용 파생 필드
    # 사용할지 고민 중.

    def to_chroma_doc(self) -> dict:
        """
            Chroma DB에 적재 가능한 형식으로 변환
            - Chroma DB 메타 데이터는 str/int/float/bool만 허용
            - list를 json 문자열로 변경(이건 지금 보류)
        """
        # dict 형태로 변환
        meta = asdict(self)

        text = meta.pop("text_for_embedding")  # 임베딩 대상 텍스트는 별도 분리
        cid = meta.pop("chunk_id")              # chunk_id는 Chroma의 id로 사용

        # raw_text는 용량초과 시 제외
        meta.pop("raw_text")

        return {id: cid, "document": text, "metadata": meta}


@st.cache_data(ttl=3600)
def get_places_from_api(destination: str, styles: List[str], constraints: List[str], limit: int) -> dict[str, any]:
    """ Google Places API(New)를 사용하여 특정 지역의 장소 데이터를 검색하고 추천 정보를 생성함.

        사용자의 목적지, 여행 스타일, 제약 사항을 기반으로 텍스트 쿼리를 생성하여 장소를 검색하며,
        결과 데이터에는 장소 정보, 평점, 실내외 여부 및 LLM용 추천 사유가 포함됨.

        Args:
            destination (str): 검색할 도시 또는 지역명 (예: '부산', '서울')
            styles (List[str]): 선호하는 여행 스타일 목록 (예: ['맛집', '카페'])
            constraints (List[str]): 특별한 제약 사항 또는 환경 (예: ['실내', '주차 가능'])
            limit (int): 검색할 최대 장소 개수 (기본값: 5)

        Returns:
            dict: 검색 성공 시 장소 목록(data)과 메타 정보를 반환하고, 실패 시 에러 정보를 반환함.
    """
    url = "https://places.googleapis.com/v1/places:searchText"
    query = f"{destination} {' '.join(styles)} {' '.join(constraints)}"
    
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

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": places_api_key,
        "X-Goog-FieldMask": ",".join(fields)

    }
    
    payload = {
        "textQuery": query,
        "maxResultCount": limit,
        "languageCode": "ko"
    }

    response = requests.post(url, json=payload, headers=headers)
    
    return {
        "status_code": response.status_code,
        "json_data": response.json() if response.status_code == 200 else None,
        "error_text": response.text if response.status_code != 200 else None
    }

# search_place tool
@tool("place_search", args_schema=PlaceSearchInfo)
def search_place_tool(destination: str, styles: List[str], constraints: List[str], limit: int = 5) -> dict[str, any]:
    """ Google Places API:searchText 엔드포인트를 호출하여 원본 장소 데이터를 가져옴.

        Streamlit의 cache_data를 사용하여 동일한 쿼리에 대해 1시간 동안 API 호출 결과를 캐싱함.

        Args:
            destination (str): 검색할 대상 지역명
            styles (List[str]): 검색 키워드에 포함할 스타일 리스트
            constraints (List[str]): 검색 키워드에 포함할 제약 조건 리스트
            limit (int): API로부터 응답받을 결과의 최대 개수

        Returns:
            dict: API 응답 상태 코드(status_code), 성공 시 JSON 데이터(json_data), 
                실패 시 에러 메시지(error_text)를 포함한 딕셔너리.
    """
    try:
        # print(f"DEBUG: [PLACE TOOL 호출]: {destination}, {styles}, {constraints}, {limit}")
        # TODO: API 호출 공통부로 구분 예정.
        # 특히 만약에 오류가 발생하거나, 정보가 부족한 경우 LLM이 지속적으로 호출해야할 수 있기 때문에 session 관리를 하는 util 함수 필요.
        response = get_places_from_api(destination, styles, constraints, limit)
        
        if response["status_code"] != 200:
            return {
                "status": "error",
                "data": None,
                "error": f"API 호출 실패 (Status: {response['status_code']}): {response['error_text']}",
                "meta": {"tool_name": "place_search"}
            }
    
        results = response["json_data"].get("places", [])

        # print(f"DEBUG: {results=}")

        # 테스트를 위한 코드 삽입(DELETE_CODE)
        if SAVE_FILE_TEST_MODE:
            print(f'{SAVE_FILE_TEST_MODE = }') 
            print(json.dumps(results, indent=4, ensure_ascii=False))
            # 저장할 파일명 설정
            file_path = "travel_itinerary.json"
            # 데이터를 보기 위한 파일 다운로드 
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
        
        # results = []    # placeNotFoundError 테스트(DELETE_CODE)

        mapped_places = []
        # 결과값이 있을 때
        if len(results) > 0:
            for p in results:
                # 장소 타입(원래는 types를 썼으나, primary_type으로 변환)
                primary_type = p.get("primaryType", "")

                temp_place_info = {
                    "place_id": p.get("id"),
                    "name": p.get("displayName", {}).get("text"),
                    "lat": p.get("location", {}).get("latitude"),
                    "lng": p.get("location", {}).get("longitude"),
                    "category": next((k for k, cats in PLACE_CATEGORY_MAP.items() if primary_type in cats), "default"),
                    "summary": p.get("reviewSummary", {}).get("text", "정보 없음"),
                    "rating": p.get("rating", 0),
                    "indoor_outdoor": "indoor" if primary_type in INDOOR_TYPES else "outdoor",
                }

                mapped_places.append({
                    **temp_place_info,
                    "recommended_reason": f"{destination}에서 평점 {temp_place_info['rating']}의 {temp_place_info['category']} 중 하나입니다."
                })

            return {
                "status": "success",
                "data": {"places": mapped_places},
                "error": None,
                "meta": {"tool_name": "place_search", "total_found": len(mapped_places)}
            }
        # 결과값이 없는 경우 Exception으로 공통된 return 메시지
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
    
def preprocess_place_data(raw_data: dict) -> List[dict]:
    """ Google Places API로부터 받은 원본 장소 데이터를 LLM이 활용하기 쉬운 형태로 가공함.

        원본 데이터에서 장소 ID, 이름, 위치, 카테고리, 평점, 리뷰 요약 등을 추출하여 
        카테고리를 사전에 정의된 단순화된 카테고리로 매핑함.

        Args:
            raw_data (dict): Google Places API로부터 받은 원본 장소 데이터

        Returns:
            List[dict]: 가공된 장소 정보 리스트. 각 장소는 ID, 이름, 위도/경도, 단순화된 카테고리, 평점, 실내외 여부 등을 포함함.
    """
    mapped_places = []
    for p in raw_data.get("places", []):
        primary_type = p.get("primaryType", "")
        mapped_places.append({
            "place_id": p.get("id"),
            "name": p.get("displayName", {}).get("text"),
            "lat": p.get("location", {}).get("latitude"),
            "lng": p.get("location", {}).get("longitude"),
            "category": next((k for k, cats in PLACE_CATEGORY_MAP.items() if primary_type in cats), "default"),
            "summary": p.get("reviewSummary", {}).get("text", "정보 없음"),
            "rating": p.get("rating", 0),
            "indoor_outdoor": "indoor" if primary_type in INDOOR_TYPES else "outdoor",
        })
    return mapped_places

def make_chunk_id(place_id: str, review_name: str) -> str:
    """ 장소 ID에 hash 함수를 적용하여 고유한 청크 ID를 생성함. 
        Args:
            place_id (str): Google Places API에서 제공하는 장소 ID
        Returns:
            str: 고유한 청크 ID
    """
    raw_id = f"{place_id}:{review_name}"
    return hashlib.sha256(raw_id.encode()).hexdigest()[:32]


def clean_text(text: str) -> str:
    """ 리뷰 텍스트를 전처리하여 임베딩에 적합한 형태로 변환함.

        HTML 태그 제거, 특수문자 제거, 불필요한 공백 제거 등을 수행함.

        Args:
            text (str): 원본 리뷰 텍스트
        Returns:
            str: 전처리된 리뷰 텍스트
    """
    text = text.strip()
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text)
    # 줄바꿈 → 공백 (임베딩 모델은 단일 시퀀스 선호)
    text = text.replace("\n", " ").strip()
    return text

def build_embedding_text(place_name: str, place_type: str, review_text: str) -> str:
    """
    임베딩 텍스트 구성 전략: [장소 컨텍스트] + [리뷰 본문]
    → 검색 시 "동물원 청결 관련 리뷰 찾기" 같은 쿼리와 매칭 품질 향상

    TODO: 이부분은 품질테스트 필요.
    """
    return f"[{place_type}] {place_name} 리뷰: {review_text}"

def parse_place_data(raw_data: dict) -> List[PlaceReviewChunkInfo]:
    """
        Google Place API 응답 JSON을 활용할 수 있는 리스트로 변환
        특히 한 장소에 여러 리뷰 -> 리뷰 별로 청크 1개 생성
    """

    chunks: List[PlaceReviewChunkInfo] = []

    for place in raw_data: 
        place_id   = place["id"]
        place_name = place["displayName"]["text"]
        place_type = next((k for k, cats in PLACE_CATEGORY_MAP.items() if place["primary_type"] in cats), "default"),
        place_rating = float(place.get("rating", 0))
        lat = place["location"]["latitude"]
        lng = place["location"]["longitude"]

        for review in place.get("reviews", []):
            raw_text = review.get("text", {}).get("text", "").strip()
            if not raw_text:                    # 텍스트 없는 리뷰 스킵
                continue
            
            cleaned = clean_text(raw_text)
            r_rating = int(review.get("rating", 3))
            author   = review.get("authorAttribution", {}).get("displayName", "익명")
            pub_time = review.get("publishTime", "")
            rel_time = review.get("relativePublishTimeDescription", "")
            lang     = review.get("text", {}).get("languageCode", "ko")
            r_name   = review.get("name", "")
            
            chunk = PlaceReviewChunkInfo(
                chunk_id           = make_chunk_id(place_id, r_name),
                place_id           = place_id,
                review_name        = r_name,
                text_for_embedding = build_embedding_text(place_name, place_type, cleaned),
                raw_text           = raw_text,
                place_name         = place_name,
                place_type         = place_type,
                place_rating       = place_rating,
                place_lat          = lat,
                place_lng          = lng,
                review_rating      = r_rating,
                review_author      = author,
                review_published_at= pub_time,
                review_relative_time = rel_time,
                language_code      = lang,
                char_count         = len(cleaned),
                word_count         = len(cleaned.split()),
            )
            chunks.append(chunk)
 
    return chunks


def test_db_storage():
    # 테스트용 가짜 데이터 (Mock Data)
    # 실제 place_search_tool이 반환하는 형식과 동일하게 구성
    mock_places = [
        {
            "place_id": "test_001",
            "name": "해운대 블루라인파크",
            "category": "park",
            "indoor_outdoor": "outdoor",
            "summary": "해안 열차를 탈 수 있는 산책로",
            "rating": 4.5,
            "lat": 35.16, "lng": 129.16,
            "recommended_reason": "부산에서 가장 유명한 산책 코스입니다."
        }
    ]

    # 3. 데이터 전처리 (Document 객체화)
    docs = []
    for p in mock_places:
        # content와 metadata 분리
        content = f"{p['name']} {p['category']} {p['summary']} {p['recommended_reason']}"
        metadata = {"place_id": p['place_id'], "name": p['name']}
        docs.append(Document(page_content=content, metadata=metadata))

    # 4. 벡터 DB 생성 및 저장
    persist_dir = "./db/chroma_db"
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, model="text-embedding-3-small")
    
    print("--- DB 생성 및 저장 중... ---")
    vector_db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name="test_collection"
    )
    print(f"성공: '{persist_dir}' 폴더에 데이터가 저장되었습니다.")

    # 잘 저장됐는지 즉시 검색 테스트
    print("\n--- 검색 테스트 진행 중... ---")
    query = "바닷가 열차 타는 곳 어디야?"
    results = vector_db.similarity_search(query, k=1)
    
    if len(results) > 0:
        print(f"검색 성공! 찾은 장소: {results[0].metadata['name']}")
    else:
        print("검색 결과가 없습니다.")

    
# 호출 테스트
if __name__ == "__main__":

    # # 1. 벡터 적재 테스트
    # test_db_storage()
    
    # 함수호출에 필요한 값
    test_destination = "부산"
    test_styles = ["맛집", "동물원"]
    test_constraints = ["실내", "주차 가능"]
    
    print(f"--- '{test_destination}' 검색 테스트 시작 ---")

    list = []
    # print(f"DEBUG: {places_api_key}")

    # # tool 호출
    result = search_place_tool.invoke({
        "destination": test_destination,
        "styles": test_styles,
        "constraints": test_constraints,
        "limit": 3
    })

    # 결과 확인
    print(json.dumps(result, indent=4, ensure_ascii=False))
  