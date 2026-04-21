from langgraph.graph import StateGraph, END
from llm.graph.state import TravelAgentState
from llm.graph.routes import should_continue, route_after_missing_check
from llm.nodes.intent_nodes import route_intent_node
from llm.nodes.trip_nodes import extract_trip_requirements_node, check_missing_info_node, ask_user_for_missing_info_node, select_places_node
from llm.nodes.weather_nodes import weather_node
from llm.nodes.response_nodes import build_response_node
from llm.nodes.nodes_mock import search_places_node, scheduler_node       # mock node 등록해서 돌아가는지 확인
from llm.graph.contracts import StateKeys # 규약 임포트

# 1. 그래프 초기화
workflow = StateGraph(TravelAgentState)

# 2. 노드 등록
workflow.add_node("intent_router", route_intent_node)
workflow.add_node("extract_trip_requirements_node", extract_trip_requirements_node)
workflow.add_node("check_missing_info_node", check_missing_info_node)
workflow.add_node("ask_user_node", ask_user_for_missing_info_node)
workflow.add_node("response_node", build_response_node) # 최종 답변 노드
# 나머지 노드들은 담당자들이 완성하는 대로 추가 예정 -> 임의로 place_node 추가

# 일단 확인용 mock node 추가
workflow.add_node("place_node", search_places_node)
workflow.add_node("select_places_node", select_places_node)     # 장소 선택 노드
workflow.add_node("scheduler_node", scheduler_node)
workflow.add_node("weather_node", weather_node)

# 3. 흐름 연결
workflow.set_entry_point("intent_router")

# 먼저 intent 분류 후 여행 조건 추출
workflow.add_edge("intent_router", "extract_trip_requirements_node")

# 추출 후 부족 정보 확인
workflow.add_edge("extract_trip_requirements_node", "check_missing_info_node")

# 조건부 엣지 설정: 'check_missing_info_node'가 끝나면 route에 따라 분기
# 부족 정보가 있으면 질문, 없으면 기존 라우팅 수행
workflow.add_conditional_edges(
    "check_missing_info_node",
    route_after_missing_check,
    {
        "ask_user_node": "ask_user_node",       # 사용자에게 정보를 더 받아야 하면 여기로
        "weather_node": "weather_node",         # 날씨 정보가 필요하면 여기로
        "place_node": "place_node",             # 장소 검색이 필요하면 여기로
        "scheduler_node": "scheduler_node",     # 이미 장소가 충분하면 바로 여기로
        "response_node": "response_node"        # 일반 대화는 바로 답변으로!
    }
)

# 장소 검색 -> 장소 선택 -> 일정 생성
workflow.add_edge("place_node", "select_places_node")
workflow.add_edge("select_places_node", "scheduler_node")

# ask_user는 질문을 만든 뒤 종료
workflow.add_edge("ask_user_node", END)

# 4. 마무리
workflow.add_edge("weather_node", "response_node")
workflow.add_edge("scheduler_node", "response_node")
workflow.add_edge("response_node", END)

# 5. 컴파일
app = workflow.compile()