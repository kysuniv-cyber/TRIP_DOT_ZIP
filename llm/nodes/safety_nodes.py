from openai import OpenAI

from config import Settings
from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys
from middlewares.safety_mw import (
    contains_bad_word,
    should_block,
    sanitize_pii,
)

client = OpenAI(api_key=Settings.openai_api_key)


def safe_input_node(state: TravelAgentState) -> dict:
    """
    마지막 사용자 메시지만 검사한다.
    - 고위험 입력이면 이번 턴만 차단
    - PII는 마스킹
    - 대화 자체는 계속 가능
    """
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        return {}

    last_msg = messages[-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

    # 1. 고위험 입력 차단 -> 이번 턴만 응답하고 종료
    if should_block(client, user_text):
        return {
            StateKeys.BLOCKED: True,
            StateKeys.BLOCK_REASON: "입력에 민감하거나 부적절한 내용이 포함되어 있어 이번 요청은 처리할 수 없습니다.",
        }

    # 2. PII 마스킹
    pii_result = sanitize_pii(user_text)
    print("[DEBUG] pii_result =", pii_result)

    if pii_result["blocked"]:
        return {
            StateKeys.BLOCKED: True,
            StateKeys.BLOCK_REASON: "민감한 개인정보가 포함되어 있어 이번 요청은 처리할 수 없습니다.",
        }

    # 3. soft flag
    profanity_detected = contains_bad_word(user_text)

    return {
        StateKeys.MESSAGES: messages,
        StateKeys.BLOCKED: False,
        "pii_detected": bool(pii_result["detected_entities"]),
        "pii_entities": pii_result["detected_entities"],
        "sanitized": pii_result["sanitized_text"] != pii_result["original_text"],
        "profanity_detected": profanity_detected,
    }