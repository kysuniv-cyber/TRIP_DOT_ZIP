import tiktoken
from openai import OpenAI

from config import Settings
from llm.graph.state import TravelAgentState
from llm.graph.contracts import StateKeys

client = OpenAI(api_key=Settings.openai_api_key)


def _normalize_messages(messages):
    normalized = []
    for msg in messages:
        if hasattr(msg, "content"):
            role = getattr(msg, "type", None) or getattr(msg, "role", None) or "user"
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"
            normalized.append({"role": role, "content": content})
        elif isinstance(msg, dict):
            normalized.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    return normalized


def _count_message_tokens(messages, model_name: str = "gpt-4o-mini") -> int:
    """
    messages 전체의 대략적인 토큰 수를 계산한다.
    """
    normalized = _normalize_messages(messages)

    try:
        enc = tiktoken.encoding_for_model(model_name)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")

    total_tokens = 0
    for msg in normalized:
        role = msg.get("role", "")
        content = msg.get("content", "")

        # role/content에 대한 토큰 수 + 메시지 오버헤드 약간
        total_tokens += len(enc.encode(role))
        total_tokens += len(enc.encode(content))
        total_tokens += 4

    return total_tokens


def _generate_summary(messages, max_chars: int = 700) -> str:
    lines = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role in ("user", "assistant"):
            lines.append(f"[{role}] {content}")

    summary_input = "\n".join(lines).strip()
    if not summary_input:
        return ""

    prompt = f"""
다음 대화 내역을 한국어로 요약해 주세요.

반드시 포함할 것:
- 사용자의 핵심 목표
- 중요 조건 / 제약사항
- 이미 논의된 내용
- 이후 응답에 필요한 맥락

가능하면 {max_chars}자 이내로 작성하세요.

대화:
{summary_input}
""".strip()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "너는 대화 기록을 압축 요약하는 시스템이다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


def summary_node(state: TravelAgentState) -> dict:
    messages = state.get(StateKeys.MESSAGES, [])
    if not messages:
        return {
            StateKeys.CONVERSATION_SUMMARIZED: False,
            StateKeys.CONVERSATION_SUMMARY: "",
        }

    trigger_token_count = 1000
    keep_last_n = 3

    token_count = _count_message_tokens(messages, model_name="gpt-4o-mini")

    print("[DEBUG] token_count =", token_count)
    print("[DEBUG] len(messages) =", len(messages))
    print("[DEBUG] trigger_token_count =", trigger_token_count)
    print("[DEBUG] keep_last_n =", keep_last_n)

    if token_count < trigger_token_count or len(messages) <= keep_last_n:
        return {
            StateKeys.CONVERSATION_SUMMARIZED: False,
            StateKeys.CONVERSATION_SUMMARY: state.get(StateKeys.CONVERSATION_SUMMARY, ""),
        }

    normalized = _normalize_messages(messages)
    old_messages = normalized[:-keep_last_n]
    recent_messages = normalized[-keep_last_n:]

    try:
        summary = _generate_summary(old_messages)
    except Exception:
        return {
            StateKeys.CONVERSATION_SUMMARIZED: False,
            StateKeys.CONVERSATION_SUMMARY: state.get(StateKeys.CONVERSATION_SUMMARY, ""),
        }

    if not summary:
        return {
            StateKeys.CONVERSATION_SUMMARIZED: False,
            StateKeys.CONVERSATION_SUMMARY: state.get(StateKeys.CONVERSATION_SUMMARY, ""),
        }

    summarized_messages = (
        [{"role": "system", "content": f"[이전 대화 요약]\n{summary}"}]
        + recent_messages
    )

    return {
        StateKeys.MESSAGES: summarized_messages,
        StateKeys.CONVERSATION_SUMMARIZED: True,
        StateKeys.CONVERSATION_SUMMARY: summary,
    }