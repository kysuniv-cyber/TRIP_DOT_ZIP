from typing import Annotated, Dict, List, Literal

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


IntentType = Literal[
    "general_chat",
    "travel_recommendation",
    "place_search",
    "schedule_generation",
    "weather_query",
    "modify_request",
]


class QualityCheck(TypedDict):
    is_passed: bool
    issues: List[str]
    target_node: str


# 장소 말하고, 이후 날짜 추가하는 등 다른 정보 modify할 때 사용
def keep_and_update(existing: str | None, new: str | None) -> str | None:
    """기존 상태를 유지하면서 새로운 입력이 있을 경우에만 값을 업데이트합니다.

        LangGraph의 State Reducer로 사용되며, 새로운 데이터(new)가 None이 아닌 경우에만
        기존 상태(existing)를 덮어씁니다. 이를 통해 특정 노드에서 데이터를 명시적으로
        업데이트하지 않을 때 기존 여행 정보(예: 목적지)가 유실되는 것을 방지합니다.

        Args:
            existing (str | None): 현재 State에 저장되어 있는 기존 값.
            new (str | None): 노드에서 반환된 새로운 값.

        Returns:
            str | None: 업데이트할 최종 값 (new가 있으면 new, 없으면 existing).
        """
    if new is not None:
        return new
    return existing

# 장소 자체를 바꿀 때 사용
def overwrite_list(existing: list, new: list) -> list:
    """기존 리스트를 무시하고 새로운 리스트로 완전히 대체합니다.

        LangGraph에서 기본적으로 리스트 타입에 적용되는 'append(추가)' 방식 대신,
        기존 장소 리스트나 일정 데이터를 초기화하거나 새로운 데이터로 교체할 때 사용합니다.
        특히 빈 리스트([])를 반환하여 상태를 초기화해야 하는 경우에 필수적입니다.

        Args:
            existing (list): 현재 State에 저장되어 있는 기존 리스트.
            new (list): 새로 교체할 리스트 (초기화 시 빈 리스트).

        Returns:
            list: 새롭게 전달받은 리스트(new).
        """
    return new


class TravelAgentState(TypedDict, total=False):
    # 기본 대화 / 라우팅
    messages: Annotated[list, add_messages]
    intent: IntentType
    confidence: float
    route: str

    # 여행 조건
    destination: Annotated[str | None, keep_and_update]
    styles: List[str]
    constraints: List[str]
    travel_date: str
    relative_days: int
    raw_date_text: str
    start_time: str

    # 장소 / 일정 / 날씨
    mapped_places: Annotated[List[Dict], overwrite_list]
    selected_places: Annotated[List[Dict], overwrite_list]
    itinerary: Annotated[List[Dict], overwrite_list]
    weather_data: Dict

    # 흐름 제어
    missing_slots: List[str]
    need_weather: bool
    state_type_cd: str
    quality_check: QualityCheck

    # 지도 / 응답
    map_metadata: Dict
    final_response: str

    # 안전 / 요약
    blocked: bool
    blocked_reason: str
    conversation_summary: str
    conversation_summarized: bool
