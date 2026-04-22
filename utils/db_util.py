"""
    FileName: db_util.py
    Location: utils/db_util.py
    Role: DB 관련 객체인데.. 이걸 유틸로 해도 되나.
        PlaceReviewChunkInfo 모델 정의, 데이터 전처리, ChromaDB 연결 및 적재 로직.
"""
from dataclasses import dataclass, asdict

import streamlit as st
from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import List
from config import Settings

import os
import requests
import re
from utils.custom_exception import PlaceNotFoundError
from config import Settings
import json
from constants import PLACE_CATEGORY_MAP, INDOOR_TYPES

# 벡터 DB 적재 import
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import hashlib
import chromadb

# 전처리 완료된 청크를 저장 여부.
SAVE_FILE_TEST_MODE = True

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
    r"[~!@#$%^&*.]{2,}",      # 반복 특수문자 정리
    r"\s{2,}",                # 다중 공백 → 단일 공백
]

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
    review_name: str

    # 임베딩 대상 텍스트
    text_for_embedding: str # 전처리 완료 텍스트
    raw_text: str           # 원본 리뷰 텍스트

    # 메타데이터(필터링/검색용)
    place_name: str
    place_lat: float
    place_lng: float
    place_category: str
    place_rating: float
    place_type: str         # indoor/outdoor

    review_rating: int
    review_author: str
    review_published_at: str            # ISO 8601
    review_relative_time: str           # "2달 전" 등 원본 표현

    language_code: str

    # 분석용 파생 필드
    # 추가할지 고민 중.
    tags: str = ""  # 필터링용 태그 리스트 (ChromaDB 저장을 위해 콤마로 구분된 문자열로 관리)

    char_count: int = 0
    word_count: int = 0

    def to_chroma_doc(self) -> dict:
        """
            Chroma DB에 적재 가능한 형식으로 변환
            - Chroma DB 메타 데이터는 str/int/float/bool만 허용
            - list를 json 문자열로 변경(이건 지금 보류)
        """
        # dict 형태로 변환
        meta = asdict(self)

        text = meta.pop("text_for_embedding")   # 임베딩 대상 텍스트는 별도 분리
        cid = meta.pop("chunk_id")              # chunk_id는 Chroma의 id로 사용

        # raw_text는 용량초과 시 제외
        meta.pop("raw_text")

        return {"id": cid, "document": text, "metadata": meta}

class OpenAIEmbedder():
    """
        text_embedding-3-small 사용
    """
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = OpenAIEmbeddings(
            model=self.model,
            # batch_size를 생성자에서 지정할 수도 있습니다. (기본값 1024)
            chunk_size=1024
        )
    
    def embed_batch(self, texts: list[str], batch_size: int=100) -> List[List]:
        """ """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # self.client.embeddings.create 대신 self.client.embed_documents 사용
            response = self.client.embed_documents(batch) 
            all_embeddings.extend(response)
            print(f"  임베딩 완료: {min(i + batch_size, len(texts))}/{len(texts)}")
            
        return all_embeddings
    
class ChromaDBHandler():
    """
    """
    def __init__(self, collection_name: str = Settings.CHROMA_COLLECTION_NAME, persist_dir: str=Settings.CHROMA_PERSIST_DIR):
        """ Chroma DB 연결 및 컬렉션 초기화 """
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",     # 코사인 유사도 사용
                #sw:dim": 1536            # 차원 수는 임베딩 모델에 맞게 설정 임베딩 모델에 맞게 변경(chromadb는 첫 insert시 자동 감지)
            } # 
        )
    def upsert(self, chunks: List[PlaceReviewChunkInfo], embeddings: List[List[float]]):
        """ 청크 리스트를 받아 Chroma DB에 일괄 적재 """
        docs = [c.to_chroma_doc() for c in chunks]
        self.collection.upsert(
            ids        = [d["id"]       for d in docs],
            documents  = [d["document"] for d in docs],
            metadatas  = [d["metadata"] for d in docs],
            embeddings = embeddings,
        )

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

def build_embedding_text(place_name: str, place_category: str, review_text: str) -> str:
    """
    임베딩 텍스트 구성 전략: [장소 컨텍스트] + [리뷰 본문]
    → 검색 시 "동물원 청결 관련 리뷰 찾기" 같은 쿼리와 매칭 품질 향상

    TODO: 이부분은 품질테스트 필요.
    """
    return f"[{place_category}] {place_name} 리뷰: {review_text}"

def extract_tags(text: str) -> str:
    """
    KEYWORD_DICT를 순회하며 리뷰 텍스트에 포함된 키워드 그룹(태그)을 추출합니다.
    결과는 "아이,청결" 형태의 문자열로 반환합니다.
    """
    found_tags = []
    for tag_name, keywords in KEYWORD_DICT.items():
        if any(kw in text for kw in keywords):
            found_tags.append(tag_name)
    return ",".join(found_tags)

def parse_place_data(raw_data: dict) -> List[PlaceReviewChunkInfo]:
    """
        Google Place API 응답 JSON을 활용할 수 있는 리스트로 변환
        특히 한 장소에 여러 리뷰 -> 리뷰 별로 청크 1개 생성
    """

    chunks: List[PlaceReviewChunkInfo] = []

    for place in raw_data: 
        place_id   = place["id"]
        place_name = place["displayName"]["text"]
        place_category = next((k for k, cats in PLACE_CATEGORY_MAP.items() if place["primaryType"] in cats), "default")
        place_type = "indoor" if place["primaryType"] in INDOOR_TYPES else "outdoor"
        place_rating = float(place.get("rating", 0))
        lat = place["location"]["latitude"]
        lng = place["location"]["longitude"]

        for review in place.get("reviews", []):
            raw_text = review.get("text", {}).get("text", "").strip()
            if not raw_text:                    # 텍스트 없는 리뷰 스킵
                continue

            cleaned = clean_text(raw_text)
            tags = extract_tags(cleaned)
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
                text_for_embedding = build_embedding_text(place_name, place_category, cleaned),
                raw_text           = raw_text,
                place_name         = place_name,
                place_category     = place_category,
                place_type         = place_type,
                place_rating       = place_rating,
                place_lat          = lat,
                place_lng          = lng,
                review_rating      = r_rating,
                review_author      = author,
                review_published_at= pub_time,
                review_relative_time = rel_time,
                language_code      = lang,
                tags               = tags,
                char_count         = len(cleaned),
                word_count         = len(cleaned.split()),
            )
            chunks.append(chunk)
 
    return chunks

def run_pipeline(
        raw_data: List[dict], 
        chroma_dir: str=Settings.CHROMA_PERSIST_DIR, 
        collection_name: str=Settings.CHROMA_COLLECTION_NAME, 
        test_flag: bool=False
    ) -> List[PlaceReviewChunkInfo]:
    
    print(f'DEBUG: {raw_data}')
    # test_flag 적재 없이 전처리만 확인 가능한 파일 생성.

    # 1. 파싱 및 전처리
    chunks = parse_place_data(raw_data)

    # test_flag가 True인 경우, 전처리된 청크의 샘플을 출력하고 함수 종료
    if test_flag:
        print("\n[test_flag]] 전처리 결과 샘플:")
        for c in chunks[:10]:
            print(f"\n  chunk_id     : {c.chunk_id}")
            print(f"  place_name   : {c.place_name}")
            print(f"  embedding_text: {c.text_for_embedding[:80]}...")
        return chunks
    
    # 파일 저장모드. 전처리된 청크샘플 저장.
    if SAVE_FILE_TEST_MODE:
        with open("./data/preprocessed_chunks_sample.json", "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in chunks[:10]], f, ensure_ascii=False, indent=2)
        print("전처리된 청크 샘플을 ./data/preprocessed_chunks_sample.json에 저장했습니다.")

    # 2. 임베딩
    embedder = OpenAIEmbedder()
    texts = [c.text_for_embedding for c in chunks]
    embeddings = embedder.embed_batch(texts)
    print(f"임베딩된 {len(embeddings)}개 텍스트")

    # 3. Chroma DB 적재
    dbHandler = ChromaDBHandler(collection_name=collection_name, persist_dir=chroma_dir)
    dbHandler.upsert(chunks, embeddings)
    
    return chunks
