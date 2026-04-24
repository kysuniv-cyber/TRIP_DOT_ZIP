from langchain_openai import ChatOpenAI
from langchain_classic.retrievers import SelfQueryRetriever
from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_community.vectorstores import Chroma

from config import Settings
from utils.db_util import OpenAIEmbedder


def rerank_places(
    places: list[dict],
    user_query: str = "",
    destination: str = "",
    weather_data: dict | None = None,
    preferences: list[str] | None = None,
    constraints: list[str] | None = None,
) -> list[dict]:
    """
    벡터 유사도로 추출된 top-k 장소 후보를 규칙 기반으로 재정렬합니다.

    이 함수는 별도의 외부 reranker를 사용하지 않고,
    현재 가지고 있는 장소 metadata와 사용자 요청 정보를 기준으로 점수를 다시 계산합니다.

    반영 기준:
    - 기존 벡터 검색 순위
    - 목적지 적합성
    - 사용자 질의 키워드
    - 사용자 선호 조건
    - 제약 조건
    - 날씨에 따른 실내/실외 적합성
    - 장소 평점

    Args:
        places (list[dict]): 벡터 검색으로 가져온 장소 후보 리스트.
        user_query (str): 사용자 원본 질의.
        destination (str): 목적지. 예: "부산 해운대"
        weather_data (dict | None): 날씨 tool 결과.
        preferences (list[str] | None): 사용자 선호 조건.
        constraints (list[str] | None): 사용자 제약 조건.

    Returns:
        list[dict]: rerank_score 기준으로 재정렬된 장소 리스트.
    """
    weather_data = weather_data or {}
    preferences = preferences or []
    constraints = constraints or []
    destination_tokens = destination.split() if destination else []

    def safe_float(value, default=0.0) -> float:
        """None 또는 문자열 형태의 숫자를 안전하게 float으로 변환합니다."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def score_place(place: dict) -> float:
        """장소 하나에 대한 rerank 점수를 계산합니다."""
        score = 0.0

        name = place.get("name") or ""
        category = place.get("category") or ""
        text = place.get("text") or ""
        address = place.get("address") or ""
        rating = safe_float(place.get("rating"))

        metadata = place.get("metadata") or {}
        place_type = (
            metadata.get("place_type")
            or metadata.get("indoor_outdoor")
            or ""
        )
        tags = metadata.get("tags") or ""

        # 검색에 활용할 장소 정보를 하나의 문자열로 합칩니다.
        combined_text = f"{name} {category} {text} {address} {tags}".lower()

        # 1. 기존 벡터 검색 순위 반영
        # retrieval_score는 1 / rank 값입니다.
        # 즉, 벡터 검색에서 앞에 나온 후보일수록 높은 점수를 받습니다.
        retrieval_score = safe_float(place.get("retrieval_score"))
        score += retrieval_score * 40

        # 2. 목적지 적합성 반영
        # 예: destination이 "부산 해운대"면 "부산", "해운대" 중 하나라도 포함되는지 확인합니다.
        if destination_tokens:
            if any(token.lower() in combined_text for token in destination_tokens):
                score += 30

        # 3. 사용자 질의 키워드 반영
        # 너무 짧은 토큰까지 반영하지 않도록 2글자 이상만 사용합니다.
        for token in user_query.split():
            token = token.strip().lower()
            if len(token) >= 2 and token in combined_text:
                score += 2

        # 4. 사용자 선호 조건 반영
        for pref in preferences:
            pref = str(pref).strip().lower()
            if pref and pref in combined_text:
                score += 10

        # 5. 제약 조건 반영
        for constraint in constraints:
            constraint = str(constraint).strip().lower()
            if constraint and constraint in combined_text:
                score += 8

        # 6. 날씨 반영
        # 비가 오는 상황이면 실내 장소에 가산점, 실외 장소에 감점을 줍니다.
        weather_text = str(weather_data).lower()
        place_type = str(place_type).lower()

        if "비" in weather_text or "rain" in weather_text:
            if place_type in ["indoor", "실내"]:
                score += 20
            elif place_type in ["outdoor", "실외"]:
                score -= 10

        # 7. 평점 반영
        if rating >= 4.5:
            score += 12
        elif rating >= 4.3:
            score += 10
        elif rating >= 4.0:
            score += 5

        return score

    reranked_places = []

    for place in places:
        # 원본 dict를 직접 수정하지 않기 위해 copy해서 사용합니다.
        place_copy = place.copy()
        place_copy["rerank_score"] = score_place(place_copy)
        reranked_places.append(place_copy)

    # rerank_score가 높은 순서대로 정렬합니다.
    reranked_places.sort(
        key=lambda place: place.get("rerank_score", 0),
        reverse=True,
    )

    return reranked_places


def get_metadata_field_info() -> list[AttributeInfo]:
    """
    SelfQueryRetriever가 metadata filter를 만들 때 참고할 필드 정보를 정의합니다.

    예를 들어 사용자가 "평점 4점 이상인 카페"라고 입력하면,
    place_rating, place_category 같은 metadata를 활용할 수 있습니다.

    Returns:
        list[AttributeInfo]: 장소 검색에 사용할 metadata 필드 설명 리스트.
    """
    return [
        AttributeInfo(
            name="place_name",
            description="Official place name for a tourist spot, restaurant, cafe, or venue.",
            type="string",
        ),
        AttributeInfo(
            name="place_category",
            description=(
                "Primary place category such as cafe, restaurant, museum, park, "
                "shopping_mall, library, zoo, or aquarium."
            ),
            type="string",
        ),
        AttributeInfo(
            name="tags",
            description=(
                "Keywords extracted from reviews, for example child-friendly, clean, "
                "staff, mood, facilities, or price."
            ),
            type="string",
        ),
        AttributeInfo(
            name="place_type",
            description="Indoor or outdoor classification for the place.",
            type="string",
        ),
        AttributeInfo(
            name="place_address",
            description="Road-name or lot-number address of the place.",
            type="string",
        ),
        AttributeInfo(
            name="place_rating",
            description="Average place rating from 0.0 to 5.0.",
            type="float",
        ),
        AttributeInfo(
            name="review_rating",
            description="Individual review score from 1 to 5.",
            type="integer",
        ),
    ]


def get_integrated_search_results(
    user_query: str,
    k: int = 10,
    use_rerank: bool = True,
    destination: str = "",
    weather_data: dict | None = None,
    preferences: list[str] | None = None,
    constraints: list[str] | None = None,
) -> list[dict]:
    """
    SelfQueryRetriever로 장소 후보를 검색하고, 필요 시 rerank하여 반환합니다.

    전체 흐름:
    1. Chroma Vector DB 연결
    2. SelfQueryRetriever로 사용자 질의 기반 top-k 장소 검색
    3. 같은 장소가 여러 번 검색된 경우 중복 제거
    4. 검색 결과를 프로젝트에서 사용하기 쉬운 dict 형태로 변환
    5. use_rerank=True이면 rerank_places()로 재정렬
    6. 최종 장소 후보 리스트 반환

    Args:
        user_query (str): 사용자 질의.
        k (int): 검색할 후보 개수. 기본값은 10.
        use_rerank (bool): rerank 적용 여부.
        destination (str): 목적지. 예: "부산 해운대"
        weather_data (dict | None): 날씨 tool 결과.
        preferences (list[str] | None): 사용자 선호 조건.
        constraints (list[str] | None): 사용자 제약 조건.

    Returns:
        list[dict]: 장소 후보 리스트.
    """
    embedder = OpenAIEmbedder()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Chroma Vector DB 연결
    vectorstore = Chroma(
        persist_directory=Settings.CHROMA_PERSIST_DIR,
        embedding_function=embedder.embeddings,
        collection_name=Settings.CHROMA_COLLECTION_NAME,
    )

    # SelfQueryRetriever가 사용할 metadata 필드 정보
    metadata_field_info = get_metadata_field_info()

    retriever = SelfQueryRetriever.from_llm(
        llm=llm,
        vectorstore=vectorstore,
        document_contents="text_for_embedding",
        metadata_field_info=metadata_field_info,
        search_kwargs={"k": k},
    )

    # 사용자 질의 기반 검색 실행
    docs = retriever.invoke(user_query)

    search_results = []
    seen_place_ids = set()

    for rank, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}

        # place_id가 없을 경우 장소명 + 주소를 임시 고유값으로 사용합니다.
        place_id = (
            metadata.get("place_id")
            or f"{metadata.get('place_name')}|{metadata.get('place_address')}"
        )

        # 같은 장소의 여러 리뷰가 검색될 수 있으므로 장소 단위로 중복 제거합니다.
        if place_id in seen_place_ids:
            continue

        seen_place_ids.add(place_id)

        review_text = doc.page_content if hasattr(doc, "page_content") else ""

        search_results.append({
            "place_id": place_id,
            "name": metadata.get("place_name"),
            "category": metadata.get("place_category"),
            "text": review_text,
            "address": metadata.get("place_address"),
            "rating": metadata.get("place_rating"),

            # 실제 similarity score가 없으므로 검색 순위를 기반으로 대체 점수를 저장합니다.
            "retrieval_rank": rank,
            "retrieval_score": 1 / rank,

            # 원본 metadata는 추후 디버깅이나 응답 생성에 활용할 수 있도록 보존합니다.
            "metadata": metadata,
        })

    # top-k 후보를 최종 선택 전에 한 번 더 재정렬합니다.
    if use_rerank:
        search_results = rerank_places(
            places=search_results,
            user_query=user_query,
            destination=destination,
            weather_data=weather_data,
            preferences=preferences,
            constraints=constraints,
        )

    return search_results


if __name__ == "__main__":
    # 단독 실행 테스트용 코드
    results = get_integrated_search_results(
        user_query="해운대 근처에서 평점 4점 이상이고 아이와 가기 좋은 카페",
        k=10,
        use_rerank=True,
        destination="부산 해운대",
        preferences=["아이", "카페"],
        constraints=["평점 4점 이상"],
    )

    print(f"검색 결과 개수: {len(results)}")

    for idx, item in enumerate(results, start=1):
        print("=" * 60)
        print(f"{idx}. {item.get('name')}")
        print(f"카테고리: {item.get('category')}")
        print(f"주소: {item.get('address')}")
        print(f"평점: {item.get('rating')}")
        print(f"retrieval_rank: {item.get('retrieval_rank')}")
        print(f"rerank_score: {item.get('rerank_score')}")
        print(f"리뷰 일부: {(item.get('text') or '')[:80]}...")