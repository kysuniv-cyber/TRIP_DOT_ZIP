"""
    FileName: validator.py
    Location: langgraph_jyhong/nodes/validator.py
    Role: 검증자 노드: 여행 계획에 대한 검증 제공
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from test_backup.langgraph_jyhong.state import TempTravelAgentState, QualityCheck # QualityCheck는 테스트용
from pydantic import BaseModel, Field
from typing import List


# 검증용 LLM 설정
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

# 검증 결과 구조체
# state.py 내용을 pydantic 모델로 변경하면서 그거 가지고 올 예정.
class QualityCheckResult(BaseModel):
    is_passed: bool = Field(default="False", description="통과 여부")
    issues: List[str] = Field(description="실패 사유 리스트")
    target_node: str = Field(description="분기처리를 위한 다음 노드")

# 검증 프롬프트(위치는 추후 llm/prompts.py로 이동 예정)
VALIDATION_PROMPT = """
    당신은 베테랑 여행 플래너이자 검증자입니다. 

    아래 사용자의 요구사항과 추천 장소 리스트를 비교하여 엄격하게 품질을 평가해줘.
    1. 사용자의 요구사항 '{styles}'과 추천 장소가 얼마나 일치하는지 평가
    2. 제약 조건: '{constraints}'이 일정에 잘 반영되었는지 평가
    3. 논리적 타당성: 추천장소 리스트의 장소들이'{raw_places}'가 실제로 여행 경로 상 실제로 방문이 가능한 곳인지.

    만약 하나라도 부적합하다면 is_passed = False로 하고, issues에는 구체적으로 어떤 점이 문제인지 작성해줘.
    target_node는 문제가 발견된 경우 돌아가야 할 노드 이름을 작성해줘. (예: "PlaceSearchNode", "MakeScheduleNode")
"""

# 생각해보니 validation은 사용자에게 보여주기 전에 존재해야하므로, schedule 부르기 전이겠는데?
# TODO: 검증이 필요한 시점과 검증 기준을 명확히 정의한 후, 프롬프트와 로직을 조정할 것.

def validate_travel_plan_node(state: TempTravelAgentState) -> dict:
    """ 여행 계획에 대한 검증을 수행하는 노드 함수. 
        Args: TempTravelAgentState 객체
        Returns: 검증 결과가 포함된 딕셔너리
    """
    # 검증 프롬프트 구성
    prompt = ChatPromptTemplate.from_messages([
        {"role": "system", "content": VALIDATION_PROMPT},
        {"role": "user", "content": f"사용자 요구사항: {state.styles}, 제약조건: {state.constraints}, 목적지: {state.destination}, 추천 장소 리스트: {state.raw_places}"}
    ])

    # 구조화된 출력 도구 생성
    structured_output = llm.with_structured_output(QualityCheckResult)

    try :   # 예외처리를 여기서? 또는 밖에서?
        # Chain 실행
        chain = prompt | structured_output
        result = chain.invoke(state.model_dump())

        return {"quality_check": result.model_dump(), "state_type_cd": "04"}
    except Exception as e:
        # 예외 처리: 검증 실패로 간주, 재호출 유도
        # TODO: 이것도 좀 더 고민거리.
        print(f"Error in Validator: {e}")
        return {
            "quality_check": {
                "is_passed": False, 
                "issues": ["시스템 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."],
                "target_node": "search_places"
            },
            "state_type_cd": "02" # 다시 검색 단계로 보내거나 에러 페이지로 유도
        }
    
# 테스트 케이스 실행
if __name__ == "__main__":
    # 실제 사용자가 입력한 것 같은 State 객체 생성
    mock_state = TempTravelAgentState(
        destination="부산",
        styles=["액티비티", "바다"],
        constraints=["예산은 인당 5만원 이하", "도보 이동 위주"],
        raw_places=[
            "1. 해운대 요트 투어 (인당 7만원)", 
            "2. 광안리 서핑 체험 (인당 6만원)"
        ]
    )

    print("--- [테스트 시작: State 객체 전달] ---")
    update_data = validate_travel_plan_node(mock_state)

    # 4. 결과 확인 (LangGraph가 업데이트를 수행하는 방식 시뮬레이션)
    print(f"\n[LLM 검증 결과]")
    print(f"통과 여부: {update_data['quality_check']['is_passed']}")
    print(f"발견된 문제: {update_data['quality_check']['issues']}")
    print(f"다음 상태 코드: {update_data['state_type_cd']}")

    # 실제 State 객체에 반영해보기
    mock_state.quality_check = QualityCheck(**update_data['quality_check'])
    mock_state.state_type_cd = update_data['state_type_cd']
    
    print(f"\n[최종 업데이트된 State 객체 상태]")
    print(mock_state)