from langgraph.graph import StateGraph, END
from llm.graph.state import TravelAgentState
from llm.graph.routes import should_continue, route_after_missing_check, route_after_safety_check
from llm.nodes.intent_nodes import route_intent_node
from llm.nodes.trip_nodes import extract_trip_requirements_node, check_missing_info_node, ask_user_for_missing_info_node, select_places_node, modify_trip_requirements_node
from llm.nodes.weather_nodes import weather_node
from llm.nodes.response_nodes import build_response_node, blocked_response_node
from llm.nodes.place_node import place_node
from llm.nodes.place_search_node import place_search_node
from llm.nodes.schedule_nodes import scheduler_node
from llm.nodes.validate_node import validate_travel_plan_node, route_after_validation

# middleware node
from llm.nodes.safety_nodes import safe_input_node
from llm.nodes.summary_nodes import summary_node

from llm.graph.contracts import StateKeys # 규약 임포트


# 1. 그래프 초기화
workflow = StateGraph(TravelAgentState)

# 2. 노드 등록
workflow.add_node("intent_router", route_intent_node)
workflow.add_node("extract_trip_requirements_node", extract_trip_requirements_node)
workflow.add_node("check_missing_info_node", check_missing_info_node)
workflow.add_node("ask_user_node", ask_user_for_missing_info_node)
workflow.add_node("response_node", build_response_node)         # 최종 답변 노드
workflow.add_node("place_node", place_node)                     # DB에 장소 적재 노드
workflow.add_node("place_search_node", place_search_node)       # DB에서 장소 선택 노드
workflow.add_node("weather_node", weather_node)
workflow.add_node("select_places_node", select_places_node)     # 선택한 장소 저장 노드
workflow.add_node("scheduler_node", scheduler_node)
workflow.add_node("modify_node", modify_trip_requirements_node)
workflow.add_node("validate_node", validate_travel_plan_node)

# middleware node
workflow.add_node("safe_input_node", safe_input_node)
workflow.add_node("blocked_response_node", blocked_response_node)
workflow.add_node("summary_node", summary_node)


# 3. 흐름 연결
workflow.set_entry_point("safe_input_node")
workflow.add_edge("safe_input_node", "summary_node")    # 경로가 아래 조건부 엣지에 중복으로 걸려 있는데 삭제해도 되지 않을까요?
workflow.add_edge("summary_node", "intent_router")      # 상동

workflow.add_conditional_edges(
    "safe_input_node",
    route_after_safety_check,
    {
        "blocked_response_node": "blocked_response_node",
        "intent_router": "summary_node",
    }
)

workflow.add_edge("blocked_response_node", END)

workflow.add_edge("summary_node", "intent_router")

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
        "modify_node": "modify_node",           # 수정할 내용이 있다면 여기로
        "response_node": "response_node"        # 일반 대화는 바로 답변으로!
    }
)

workflow.add_edge("modify_node", "place_node")

# 장소 검색 -> 장소 선택 -> 일정 생성
workflow.add_edge("place_node", "place_search_node")
workflow.add_edge("place_search_node", "select_places_node")
workflow.add_edge("select_places_node", "scheduler_node")

# 검증 흐름
# validate_node는 현재 prompt/분기 로직이 불안정해서
# Streamlit 경로에서는 임시로 우회한다.

# ask_user는 질문을 만든 뒤 종료
workflow.add_edge("ask_user_node", END)

# 4. 마무리
workflow.add_edge("weather_node", "response_node")
workflow.add_edge("scheduler_node", "response_node")
workflow.add_edge("response_node", END)

# 5. 컴파일
app = workflow.compile()
