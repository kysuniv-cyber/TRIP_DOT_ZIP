from langchain_openai import ChatOpenAI
from langchain_classic.retrievers import SelfQueryRetriever
from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_community.vectorstores import Chroma
from utils.db_util import OpenAIEmbedder
from config import Settings

def get_integrated_search_results(user_query: str, k: int = 5):
    """
    SelfQueryRetriever를 활용하여
    메타데이터 필터링 + 벡터 유사도 검색을 동시에 수행합니다.
    """
    # 1. 임베딩 및 LLM 초기화
    embedder = OpenAIEmbedder()
    # 쿼리 분석용 LLM은 정확도가 중요하므로 gpt-4o-mini 등을 추천합니다.
    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)

    # 2. 벡터스토어 연결 (Chroma)
    vectorstore = Chroma(
        persist_directory=Settings.CHROMA_PERSIST_DIR,
        embedding_function=embedder.embeddings,
        collection_name=Settings.CHROMA_COLLECTION_NAME
    )

    # 3. AttributeInfo 설정 (설명서)
    metadata_field_info = [
        AttributeInfo(
            name="place_name",
            description="관광지, 음식점, 카페 등 장소의 공식 명칭",
            type="string",
        ),
        AttributeInfo(
            name="place_category",
            description="장소의 주요 분류. 사용 가능한 값: cafe, restaurant, museum, park, shopping_mall, library, zoo, aquarium 등",
            type="string",
        ),
        AttributeInfo(
            name="tags",
            description="리뷰 분석을 통해 추출된 특징 키워드. '아이', '청결', '직원', '동물', '시설', '가격', '재방문' 등의 단어가 포함될 수 있으며, 사용자가 특정 분위기나 타겟을 언급할 때 이 필드를 사용하세요.",
            type="string",
        ),
        AttributeInfo(
            name="place_type",
            description="장소의 활동 환경 구분. 'indoor'(실내) 또는 'outdoor'(실외) 값만 가집니다.",
            type="string",
        ),
        AttributeInfo(
            name="place_address",
            description="장소의 도로명 주소 또는 지번 주소. 지역 기반 검색 시 참고하세요.",
            type="string",
        ),
        AttributeInfo(
            name="place_rating",
            description="장소의 평균 평점 (0.0에서 5.0 사이의 실수). '좋은', '인기 있는', '높은 점수' 등의 요청 시 이 필드로 필터링하세요.",
            type="float",
        ),
        AttributeInfo(
            name="review_rating",
            description="사용자가 작성한 개별 리뷰의 별점 (1에서 5 사이의 정수). 특정 만족도 이상의 리뷰만 볼 때 사용합니다.",
            type="integer",
        ),
    ]
    document_content_description = "여행 장소에 대한 사용자 리뷰 데이터"

    # 4. SelfQueryRetriever 생성
    # 이 리트리버는 내부적으로 [질문 -> 필터 생성 -> 유사도 검색]을 수행합니다.
    retriever = SelfQueryRetriever.from_llm(
        llm=llm,
        vectorstore=vectorstore,
        document_contents="text_for_embedding", # db_util에서 정의한 임베딩용 텍스트 필드
        metadata_field_info=metadata_field_info,
        search_kwargs={"k": k} # 유사도 검색 결과 개수
    )

    # 5. 검색 실행 (유사도 검색 결과 반환)
    # LLM이 필터를 적용한 뒤, 그 안에서 벡터 유사도가 높은 순으로 가져옵니다.
    docs = retriever.invoke(user_query)

    # 6. 결과 가공
    search_results = []
    for doc in docs:
        search_results.append({
            "name": doc.metadata.get("place_name"),
            "category": doc.metadata.get("place_category"),
            "text": doc.page_content,
            "metadata": doc.metadata
        })

    return search_results

# 실행 테스트
if __name__ == "__main__":
    # 질문에 '별점 4점 이상' 같은 조건이 있으면 LLM이 필터로 변환하고,
    # '아이와 가기 좋은'의 의미는 유사도 검색으로 찾습니다.
    res = get_integrated_search_results("해운대 근처 별점 4점 이상인 아이와 가기 좋은 카페")
    for r in res:
        print(f"[{r['name']}] {r['text'][:50]}...")
