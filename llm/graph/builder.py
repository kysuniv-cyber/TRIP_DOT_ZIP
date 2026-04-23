from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, END

from llm.graph.state import TravelAgentState
from llm.graph.routes import route_after_missing_check, route_after_safety_check
from llm.nodes.intent_nodes import route_intent_node
from llm.nodes.trip_nodes import (
    extract_trip_requirements_node,
    check_missing_info_node,
    ask_user_for_missing_info_node,
    select_places_node,
    modify_trip_requirements_node,
)
from llm.nodes.weather_nodes import weather_node
from llm.nodes.response_nodes import build_response_node, blocked_response_node
from llm.nodes.place_node import place_node
from llm.nodes.place_search_node import place_search_node
from llm.nodes.schedule_nodes import scheduler_node
from llm.nodes.validate_node import validate_travel_plan_node
from llm.nodes.safety_nodes import safe_input_node
from llm.nodes.summary_nodes import summary_node
from llm.nodes.intent_nodes import route_intent_node, intent_node

# Initialize graph
workflow = StateGraph(TravelAgentState)

# 공용 LLM 하나만 생성
shared_llm = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)

# 노드 등록 시 인스턴스화해서 전달
intent_node_instance = intent_node(shared_llm)

# Register nodes
workflow.add_node("intent_router", route_intent_node)
workflow.add_node("extract_trip_requirements_node", extract_trip_requirements_node)
workflow.add_node("check_missing_info_node", check_missing_info_node)
workflow.add_node("ask_user_node", ask_user_for_missing_info_node)
workflow.add_node("response_node", build_response_node)
workflow.add_node("place_node", place_node)
workflow.add_node("place_search_node", place_search_node)
workflow.add_node("weather_node", weather_node)
workflow.add_node("select_places_node", select_places_node)
workflow.add_node("scheduler_node", scheduler_node)
workflow.add_node("modify_node", modify_trip_requirements_node)
workflow.add_node("validate_node", validate_travel_plan_node)
workflow.add_node("safe_input_node", safe_input_node)
workflow.add_node("blocked_response_node", blocked_response_node)
workflow.add_node("summary_node", summary_node)

# Graph entry
workflow.set_entry_point("safe_input_node")

# Safety and summary middleware path
workflow.add_conditional_edges(
    "safe_input_node",
    route_after_safety_check,
    {
        "blocked_response_node": "blocked_response_node",
        "summary_node": "summary_node",
    },
)
workflow.add_edge("blocked_response_node", END)
workflow.add_edge("summary_node", "intent_router")

# Extract user travel requirements
workflow.add_edge("intent_router", "extract_trip_requirements_node")
workflow.add_edge("extract_trip_requirements_node", "check_missing_info_node")

# Route after checking whether required fields are missing
workflow.add_conditional_edges(
    "check_missing_info_node",
    route_after_missing_check,
    {
        "ask_user_node": "ask_user_node",
        "weather_node": "weather_node",
        "place_node": "place_node",
        "scheduler_node": "scheduler_node",
        "modify_node": "modify_node",
        "response_node": "response_node",
    },
)

workflow.add_edge("modify_node", "place_node")

# Place search -> place selection -> schedule generation
workflow.add_edge("place_node", "place_search_node")
workflow.add_edge("place_search_node", "select_places_node")
workflow.add_edge("select_places_node", "scheduler_node")

# Validation is intentionally bypassed for now because the current
# prompt/branching logic is unstable in the Streamlit execution path.

# Asking for missing info ends the current turn.
workflow.add_edge("ask_user_node", END)

# Final response edges
workflow.add_edge("weather_node", "response_node")
workflow.add_edge("scheduler_node", "response_node")
workflow.add_edge("response_node", END)

app = workflow.compile()
