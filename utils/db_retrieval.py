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
    for doc in docs:
        search_results.append(
            {
                "name": doc.metadata.get("place_name"),
                "category": doc.metadata.get("place_category"),
                "text": doc.page_content,
                "metadata": doc.metadata,
            }
        )

    return search_results


if __name__ == "__main__":
    results = get_integrated_search_results(
        "해운대 근처에서 평점 4점 이상이고 아이와 가기 좋은 카페"
    )
    for item in results:
        print(f"[{item['name']}] {item['text'][:50]}...")
