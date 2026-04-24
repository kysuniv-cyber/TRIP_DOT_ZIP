from langchain_openai import ChatOpenAI
from langchain_classic.retrievers import SelfQueryRetriever
from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_community.vectorstores import Chroma

from config import Settings
from utils.db_util import OpenAIEmbedder


def get_integrated_search_results(user_query: str, k: int = 5):
    """
    Run metadata-aware retrieval with SelfQueryRetriever and return
    vector-search results in a UI-friendly format.
    """
    embedder = OpenAIEmbedder()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    vectorstore = Chroma(
        persist_directory=Settings.CHROMA_PERSIST_DIR,
        embedding_function=embedder.embeddings,
        collection_name=Settings.CHROMA_COLLECTION_NAME,
    )

    metadata_field_info = [
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

    retriever = SelfQueryRetriever.from_llm(
        llm=llm,
        vectorstore=vectorstore,
        document_contents="text_for_embedding",
        metadata_field_info=metadata_field_info,
        search_kwargs={"k": k},
    )

    docs = retriever.invoke(user_query)

    search_results = []
    seen_place_ids = set()  # 중복 체크용 셋

    for doc in docs:

        # 장소 중복 체크용
        place_id = doc.metadata.get("place_id")
        if place_id in seen_place_ids:
            continue
        seen_place_ids.add(place_id)

        # 리뷰 중복 체크용
        # page_content가 없거나 비어있을 경우를 대비해 기본값 "" 설정
        review_text = doc.page_content if hasattr(doc, 'page_content') else ""

        search_results.append({
            "name": doc.metadata.get("place_name"),         # 'place_name'을 'name'으로 매핑
            "category": doc.metadata.get("place_category"), # 'place_category'를 'category'로 매핑
            "text": review_text,                            # 안전하게 가공된 리뷰 본문
            "address": doc.metadata.get("place_address"),   # 주소 (필요시 사용)
            "rating": doc.metadata.get("place_rating"),     # 별점 (필요시 사용)
            "metadata": doc.metadata                        # 전체 메타데이터 백업
        })

    return search_results


if __name__ == "__main__":
    results = get_integrated_search_results(
        "해운대 근처에서 평점 4점 이상이고 아이와 가기 좋은 카페"
    )
    for item in results:
        print(f"[{item['name']}] {item['text'][:50]}...")
