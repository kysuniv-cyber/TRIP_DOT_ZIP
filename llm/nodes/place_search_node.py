from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys
from utils.db_retrieval import get_integrated_search_results


def place_search_node(state: TravelAgentState) -> dict:
    """
    State에 저장된 목적지(destination), 스타일(styles), 제약사항(constraints)을 조합하여
    ChromaDB에서 적합한 장소를 검색합니다.
    """
    # 1. 검색 쿼리 조합 (분석된 정보들 활용)
    destination = state.get(StateKeys.DESTINATION, "")
    styles = ", ".join(state.get(StateKeys.STYLES, []))

    # 예: "부산 맛집, 카페 실내 위주"
    constraints = ", ".join(state.get(StateKeys.CONSTRAINTS, []))

    location_constraint = ""
    for c in constraints:
        if any(loc in c for loc in ["해운대", "광안리", "서면", "남포동", "기장"]):
            location_constraint = c
            break

    # 2. 검색 쿼리 재조합: destination보다 상세 위치(constraints)를 우선순위에 둠
    if location_constraint:
        search_query = f"{destination} {location_constraint} {styles} {constraints}".strip()
    else:
        search_query = f"{destination} {styles} {constraints}".strip()

    print(f"[DEBUG] place_search_node optimized query: {search_query}")

    # 2. Self-Querying 검색 실행
    # k값은 select_places_node가 선택할 수 있도록 여유 있게(10개 정도) 가져옵니다.
    raw_results = get_integrated_search_results(search_query, k=10)

    # 3. 결과 저장 (mapped_places에 리스트 형태로 저장)
    return {StateKeys.MAPPED_PLACES: raw_results}