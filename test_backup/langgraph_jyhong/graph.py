"""
    FileName: graph.py
    Location: langgraph_jyhong/graph.py
    Role: graph
"""
from langgraph.graph import StateGraph
from test_backup.langgraph_jyhong.state import TempTravelAgentState
from nodes import validate_travel_plan_node

# 품질검사 확인 후 return 노드 반환
def route_validation_result(state: TempTravelAgentState) -> str:
    valid_nodes = ["node1", "node2", "node3", "node4"]   # 노드명 검증용
    target = "node4" if state.quality_check.is_passed else state.quality_check.target_node
    
    # 검증된 노드 리스트에 있으면 해당 노드로, 없으면 'error_handler'로
    return target if target in valid_nodes else "error_handler"

# 2. 그래프 정의
workflow = StateGraph(TempTravelAgentState)

# 노드 등록
# workflow.add_node("노드이름", 호출할_함수)
# workflow.add_node("search_places", search_node)
workflow.add_node("validator", validate_travel_plan_node)


# 에지 연결
# workflow.set_entry_point("search_places")
# workflow.add_edge("search_places", "validator")

# 조건부 에지 추가
workflow.add_conditional_edges(
    "validator",              
    route_validation_result,   # 어떤 기준으로 판단하는가?
)

app = workflow.compile()

# 가이드를 위해 값을 이렇게 넣었는데.. 차후 수정 필요.