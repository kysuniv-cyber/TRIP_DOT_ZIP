"""
Validation node for itinerary quality checks.

This file is currently not on the active Streamlit execution path.
The implementation is kept for future use and still needs a broader redesign.
"""

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from llm.graph.state import TravelAgentState
from test_backup.langgraph_jyhong.state import TempTravelAgentState, QualityCheck


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

Validation rules:
- If the problem is mostly schedule quality, return target_node = "scheduler_node".
- If the problem is mostly place quality or place selection, return target_node = "place_node".

If any requirement is not satisfied, set is_passed to false and describe the issues clearly.
"""


def validate_travel_plan_node(state: TempTravelAgentState) -> dict:
    """Legacy validation entry that accepts TempTravelAgentState."""
    prompt = ChatPromptTemplate.from_messages(
        [
            {"role": "system", "content": VALIDATION_PROMPT},
            {
                "role": "user",
                "content": (
                    f"styles: {state.styles}, constraints: {state.constraints}, "
                    f"destination: {state.destination}, raw_places: {state.raw_places}"
                ),
            },
        ]
    )

    structured_output = llm.with_structured_output(QualityCheckResult)

    try:
        chain = prompt | structured_output
        result = chain.invoke(state.model_dump())
        return {"quality_check": result.model_dump(), "state_type_cd": "04"}
    except Exception as exc:
        print(f"Error in Validator: {exc}")
        return {
            "quality_check": {
                "is_passed": False,
                "issues": ["Validation failed because an internal error occurred."],
                "target_node": "search_places",
            },
            "state_type_cd": "02",
        }


def validate_travel_plan_node(state: dict) -> dict:
    """Current validation entry used by the graph builder."""
    try:
        itinerary = state.get("itinerary", [])
        styles = state.get("styles", [])
        constraints = state.get("constraints", [])

        prompt = ChatPromptTemplate.from_template(VALIDATION_PROMPT)
        structured_output = llm.with_structured_output(QualityCheckResult)
        chain = prompt | structured_output

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
    """Route to the next node based on validation output."""
    quality_check = state.get("quality_check")

    if quality_check and not quality_check.get("is_passed", True):
        target = quality_check.get("target_node")
        return target if target in ["place_node", "scheduler_node"] else "place_node"

    return "response_node"


if __name__ == "__main__":
    mock_state = TempTravelAgentState(
        destination="부산",
        styles=["액티비티", "바다"],
        constraints=["예산은 인당 5만원 이하", "도보 이동 위주"],
        raw_places=[
            "1. 해운대 요트 투어 (인당 7만원)",
            "2. 광안리 서핑 체험 (인당 6만원)",
        ],
    )

    print("--- Validation node smoke test ---")
    update_data = validate_travel_plan_node(mock_state)

    print(f"\n[Validation result]")
    print(f"passed: {update_data['quality_check']['is_passed']}")
    print(f"issues: {update_data['quality_check']['issues']}")
    print(f"state code: {update_data['state_type_cd']}")

    mock_state.quality_check = QualityCheck(**update_data["quality_check"])
    mock_state.state_type_cd = update_data["state_type_cd"]

    print(f"\n[Updated state]")
    print(mock_state)
