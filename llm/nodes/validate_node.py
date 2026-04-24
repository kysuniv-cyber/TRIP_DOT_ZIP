"""
Validation node for itinerary quality checks.

This file is currently not on the active Streamlit execution path.
The implementation is kept for future use and still needs a broader redesign.
"""

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from llm.graph.contracts import StateKeys
from llm.graph.state import TravelAgentState

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)


class QualityCheckResult(BaseModel):
    is_passed: bool = Field(default=False, description="Whether validation passed.")
    issues: List[str] = Field(description="Validation issues.")
    target_node: str = Field(description="Next node to revisit when validation fails.")


VALIDATION_PROMPT = """
You are a travel itinerary validator.

Review the generated plan against the user's preferences and constraints.

Check the following:
1. Whether the selected places match the requested styles: {styles}
2. Whether the plan reflects the constraints: {constraints}
3. Whether the itinerary is realistic and internally consistent
4. Whether time allocation and movement between places look reasonable

Consider a place a match if its category or activities broadly align with the requested styles (e.g., 'Surfing' matches 'Activity' and 'Ocean').

Validation rules:
- If the problem is mostly schedule quality, return target_node = "scheduler_node".
- If the problem is mostly place quality or place selection, return target_node = "place_node".

If any requirement is not satisfied, set is_passed to false and describe the issues clearly.
"""


def validate_travel_plan_node(state: dict) -> dict:
    """
    생성된 여행 일정을 사용자의 취향 및 제약 조건과 비교하여 품질 검수를 수행합니다.

    LLM을 사용하여 일정의 현실성, 스타일 일치 여부, 동선의 효율성 등을 종합적으로 평가합니다.
    검수 결과(is_passed)가 False일 경우, 원인에 따라 '장소 선택(place_node)' 또는
    '일정 생성(scheduler_node)' 단계로 되돌아가도록 타겟 노드를 지정합니다.

    Args:
        state (dict): 그래프의 현재 상태 데이터.
            - itinerary: 생성된 여행 일정 리스트
            - styles: 사용자가 선호하는 여행 스타일
            - constraints: 여행 시 고려해야 할 제약 사항

    Returns:
        dict: 품질 검수 결과를 담은 딕셔너리.
            - quality_check: {
                "is_passed": 검수 통과 여부 (bool),
                "issues": 발견된 문제점 리스트 (List[str]),
                "target_node": 재작업이 필요한 노드명 (str)
              }
    """
    try:
        # 상태에서 필요한 데이터 추출
        itinerary = state.get(StateKeys.ITINERARY, [])  # 가능하면 Enum/Constant 사용 권장
        styles = state.get(StateKeys.STYLES, [])
        constraints = state.get(StateKeys.CONSTRAINTS, [])

        # 프롬프트 및 LLM 설정
        prompt = ChatPromptTemplate.from_template(VALIDATION_PROMPT)
        structured_output = llm.with_structured_output(QualityCheckResult)
        chain = prompt | structured_output

        # 검수 수행
        result = chain.invoke(
            {
                "itinerary": itinerary,
                "styles": styles,
                "constraints": constraints,
            }
        )

        return {"quality_check": result.model_dump()}

    except Exception as exc:
        print(f"Error in Validator: {exc}")
        return {
            "quality_check": {
                "is_passed": False,
                "issues": ["Validation failed because an internal error occurred."],
                "target_node": "place_node",
            }
        }


def route_after_validation(state: TravelAgentState):
    """
    품질 검수 결과에 따라 다음으로 이동할 노드를 결정하는 라우팅 함수입니다.

    'quality_check' 결과가 통과(is_passed=True)인 경우 사용자에게 최종 응답을 전달하는
    'response_node'로 이동합니다. 만약 검수에 실패했다면, LLM이 제안한 'target_node'로
    되돌아가 일정을 재조정합니다. 이때, 유효하지 않은 노드로의 이동을 방지하기 위한
    방어 로직이 포함되어 있습니다.

    Args:
        state (TravelAgentState): 그래프의 현재 상태 객체.
            - quality_check: validate_travel_plan_node에서 생성된 검수 결과 정보

    Returns:
        str: 다음으로 실행할 노드의 이름.
            - 'response_node': 검수 통과 시
            - 'place_node' 또는 'scheduler_node': 검수 실패 시 재작업 노드
    """
    quality_check = state.get("quality_check")

    # 1. 검수 결과가 없거나 통과한 경우 -> 최종 응답 단계로 이동
    if quality_check and not quality_check.get("is_passed", True):
        # 2. 검수 실패 시 되돌아갈 노드 확인
        target = quality_check.get("target_node")

        # 3. 허용된 노드('place_node', 'scheduler_node')인지 검증 후 리턴
        # 만약 정의되지 않은 노드라면 기본값인 'place_node'로 이동
        return target if target in ["place_node", "scheduler_node"] else "place_node"

    return "response_node"


if __name__ == "__main__":
    # 1. 테스트용 가상 데이터 설정
    mock_state = {
        "destination": "부산",
        "styles": ["액티비티", "바다"],
        "constraints": ["예산은 인당 5만원 이하", "도보 이동 위주"],
        "itinerary": [
            {
                "place_name": "해운대 해수욕장 산책",
                "stay_time": "60분",
                "memo": "무료 (도보 이동 가능, 바다 스타일 부합)"
            },
            {
                "place_name": "해운대 전통시장 맛집 탐방",
                "stay_time": "90분",
                "memo": "인당 1.5만원 (도보 5분 거리)"
            }
        ]
    }

    print("--- Validation node smoke test ---")

    # 2. 노드 실행
    update_data = validate_travel_plan_node(mock_state)

    # 3. 결과 출력
    quality_check = update_data.get("quality_check", {})

    print(f"\n[Validation result]")
    print(f"✅ Passed: {quality_check.get('is_passed')}")
    print(f"📌 Issues: {quality_check.get('issues')}")
    print(f"🎯 Target Node: {quality_check.get('target_node')}")

    # 4. 상태 업데이트 시뮬레이션
    mock_state["quality_check"] = quality_check

    print(f"\n[Updated state summary]")
    print(f"Next step should be: {mock_state['quality_check'].get('target_node')}")
