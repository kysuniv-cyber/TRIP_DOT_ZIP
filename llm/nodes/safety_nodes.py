from openai import OpenAI

from config import Settings
from llm.graph.contracts import StateKeys
from llm.graph.state import TravelAgentState
from middlewares.safety_mw import contains_bad_word, sanitize_pii, should_block

client = OpenAI(api_key=Settings.openai_api_key)


def safe_input_node(state: TravelAgentState) -> dict:
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        return {}

    last_msg = messages[-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")

    if contains_bad_word(user_text):
        return {
            StateKeys.BLOCKED: True,
            StateKeys.BLOCK_REASON: "땃쥐가 상처받습니다. 부드럽게 말씀해 주시면 계속 도와드릴게요.",
        }

    if should_block(client, user_text):
        return {
            StateKeys.BLOCKED: True,
            StateKeys.BLOCK_REASON: "이번 요청은 안전 정책상 처리할 수 없습니다.",
        }

    pii_result = sanitize_pii(user_text)
    print("[DEBUG] pii_result =", pii_result)

    if pii_result["blocked"]:
        return {
            StateKeys.BLOCKED: True,
            StateKeys.BLOCK_REASON: "민감한 개인정보가 포함되어 있어 이번 요청은 처리할 수 없습니다.",
        }

    return {
        StateKeys.MESSAGES: messages,
        StateKeys.BLOCKED: False,
        "pii_detected": bool(pii_result["detected_entities"]),
        "pii_entities": pii_result["detected_entities"],
        "sanitized": pii_result["sanitized_text"] != pii_result["original_text"],
        "profanity_detected": False,
    }
