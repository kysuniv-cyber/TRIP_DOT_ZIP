from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys       # 규약 임포트
from services.intent_service import classify_intent_by_rule
from services.place_search_service import search_place_tool
from services.scheduler_service import create_schedule

# 1. 의도 분석 노드
def route_intent_node(state: TravelAgentState):
    """
    state["messages"]에서 마지막 사용자 메시지를 읽어
    intent / route를 결정하는 mock 노드
    """
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        return {
            StateKeys.INTENT: "general_chat",
            StateKeys.ROUTE: "chat",
        }

    last_msg = messages[-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

    result = classify_intent_by_rule(user_text)

    # State의 약속된 키(intent, route 등)에 저장
    return {
        StateKeys.INTENT: result["intent"],
        StateKeys.ROUTE: result["route"],
        StateKeys.CONFIDENCE: result.get("confidence", 0.0),
    }


# 2. 장소 검색 노드 (place_search_service.py 참고)
def search_places_node(state: TravelAgentState):
    """
    State에 저장된 destination, styles, constraints를 꺼내서
    place_search_tool을 호출하는 mock 노드
    """
    destination = state.get(StateKeys.DESTINATION)
    styles = state.get(StateKeys.STYLES, [])
    constraints = state.get(StateKeys.CONSTRAINTS, [])

    # destination이 없으면 검색하지 않음
    if not destination:
        return {StateKeys.MAPPED_PLACES: []}

    # 내부 constraint 값을 API 검색용 키워드로 보정
    constraint_keyword_map = {
        "indoor": "실내",
        "outdoor": "실외",
        "pet": "애견동반",
        "quiet": "조용한",
        "budget": "가성비",
    }

    api_constraints = [
        constraint_keyword_map.get(c, c) for c in constraints
    ]

    # LangChain tool 객체 자체를 invoke하는 대신,
    # 현재 디버깅 단계에서는 원래 파이썬 함수(func)를 직접 호출
    response = search_place_tool.func(
        destination=destination,
        styles=styles,
        constraints=api_constraints,
        limit=5,
    )

    # mapped_places를 State에 저장 -> 알맹이(places)만 꺼내서 저장
    if isinstance(response, dict) and response.get("status") == "success":
        places = response.get("data", {}).get("places", [])
        return {StateKeys.MAPPED_PLACES: places}

    # 실패 시 빈 리스트 반환
    return {StateKeys.MAPPED_PLACES: []}


# 3. 날씨 노드
def weather_node(state: TravelAgentState):
    """
    날씨 서비스 연결 전까지 사용하는 placeholder 노드
    이후 services/weather_service.py와 연결하여 교체 예정
    """
    return {
        StateKeys.WEATHER_DATA: {
            "summary": "날씨 정보 placeholder",
            "condition": "unknown",
        }
    }


# 4. 일정 생성 노드 (scheduler_service.py 참고)
def scheduler_node(state: TravelAgentState):
    """
    검색된 후보지들을 꺼내서 스케줄러에 전달하는 mock 노드
    start_time이 state에 있으면 반영하고, 없으면 기본값 09:00 사용
    """
    # 사용자가 최종 선택한 장소가 있으면 그것을 우선 사용
    places = state.get(StateKeys.SELECTED_PLACES) or state.get(StateKeys.MAPPED_PLACES, [])
    start_time = state.get(StateKeys.START_TIME, "09:00")

    # 장소가 하나도 없으면 scheduler를 호출하지 않음
    if not places:
        return {
            StateKeys.ITINERARY: []
        }

    # 검색된 후보지들을 꺼내서 스케줄러에 전달
    itinerary_result = create_schedule(
        places=places,
        start_time_str=start_time,
    )

    return {StateKeys.ITINERARY: itinerary_result}


# 5. 최종 응답 생성 노드
def response_node(state: TravelAgentState):
    """
    현재 state에 쌓인 결과를 바탕으로 사용자에게 보여줄
    최종 텍스트 응답을 만드는 임시 노드
    """
    route = state.get(StateKeys.ROUTE, "chat")
    mapped_places = state.get(StateKeys.MAPPED_PLACES, [])
    itinerary = state.get(StateKeys.ITINERARY, [])
    weather_data = state.get(StateKeys.WEATHER_DATA, {})

    # 날씨 응답
    if route == "weather":
        final_response = f"날씨 조회 결과: {weather_data}"

    # 일정 생성 응답
    elif itinerary:
        final_response = f"총 {len(itinerary)}개의 일정이 생성되었습니다.\n{itinerary}"

    # 장소 검색 응답
    elif mapped_places:
        final_response = f"총 {len(mapped_places)}개의 장소 후보를 찾았습니다.\n{mapped_places}"

    # fallback
    else:
        final_response = "요청을 처리했지만 아직 표시할 결과가 충분하지 않습니다."

    return {StateKeys.FINAL_RESPONSE: final_response}