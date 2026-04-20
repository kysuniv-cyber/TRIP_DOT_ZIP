from langgraph.graph import StateGraph, END
from llm.graph.state import TravelAgentState
from llm.graph.routes import should_continue
from llm.nodes.nodes_mock import route_intent_node
from llm.graph.contracts import StateKeys # 규약 임포트

# 1. 그래프 초기화
workflow = StateGraph(TravelAgentState)

# 2. 노드 등록
workflow.add_node("intent_router", route_intent_node)
# 나머지 노드들은 담당자들이 완성하는 대로 추가 예정 -> 임의로 place_node 추가

# 3. 흐름 연결
workflow.set_entry_point("intent_router")

# 조건부 엣지 설정: 'intent_router'가 끝나면 'should_continue'의 판단에 따라 길을 가름
workflow.add_conditional_edges(
    "intent_router",
    should_continue,
    {
        "weather_node": "weather_node",
        "place_node": "place_node",             # 장소 검색이 필요하면 여기로
        "scheduler_node": "scheduler_node",     # 이미 장소가 충분하면 바로 여기로
        "final_answer_node": END                # 일단 끝내거나 답변 노드로 연결
    }
)

# 장소 검색 후 일정 생성으로 이어지는 흐름
workflow.add_edge("place_node", "scheduler_node")

# 4. 마무리
workflow.add_edge("weather_node", "response_node")
workflow.add_edge("scheduler_node", "response_node")
workflow.add_edge("response_node", END)

# 5. 컴파일
app = workflow.compile()