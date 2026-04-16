import logging
from openai import OpenAI
from middlewares.pipeline import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


def collect_summary_target_messages(messages: list[dict]) -> list[dict]:
    """
    요약 대상 메시지에서 system은 제외하고,
    text content만 남긴다. list 타입 content는 텍스트 파트만 추출한다.
    """
    filtered = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role not in ("user", "assistant"):
            continue

        # str 타입: 그대로 사용
        if isinstance(content, str):
            filtered.append({"role": role, "content": content})

        # list 타입 (멀티모달): text 파트만 추출
        elif isinstance(content, list):
            text_parts = [
                part["text"]
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            if text_parts:
                filtered.append({"role": role, "content": " ".join(text_parts)})

    return filtered


def format_messages_for_summary(messages: list[dict]) -> str:
    lines = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        lines.append(f"[{role}] {content}")

    return "\n".join(lines)


def generate_summary(
    client: OpenAI,
    messages: list[dict],
    max_chars: int = 700,
) -> str:
    summary_input = format_messages_for_summary(messages)

    if not summary_input.strip():
        return ""

    prompt = f"""
다음 대화 내역을 한국어로 요약해 주세요.

반드시 포함할 것:
- 사용자의 핵심 목표
- 중요 조건 / 제약사항
- 이미 논의된 내용
- 이후 응답에 필요한 맥락

너무 길지 않게 실용적으로 정리하세요.
가능하면 {max_chars}자 이내로 작성하세요.

대화:
{summary_input}
""".strip()

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "너는 대화 기록을 압축 요약하는 시스템이다.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()


def count_text_chars(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            total += len(content)
    return total


def conversation_summary_middleware(
    openai_client: OpenAI,
    trigger_char_count: int = 300,
    keep_last_n: int = 4,
):
    def middleware(request: LLMRequest, next_) -> LLMResponse:
        logger.debug("conversation summary middleware 실행됨")
        logger.debug("현재 message 수: %d", len(request.messages))

        text_chars = count_text_chars(request.messages)
        logger.debug("현재 누적 문자 수: %d", text_chars)

        # 조건 미달 시 요약 스킵 (둘 다 충족해야 요약 실행)
        if text_chars < trigger_char_count or len(request.messages) <= keep_last_n:
            request.metadata["conversation_summarized"] = False
            request.metadata["conversation_summary"] = ""
            return next_(request)

        # 원본 system 메시지 보존 (페르소나, 지시사항 등)
        original_system_messages = [
            msg for msg in request.messages if msg.get("role") == "system"
        ]

        old_messages = request.messages[:-keep_last_n]
        recent_messages = request.messages[-keep_last_n:]

        summary_target = collect_summary_target_messages(old_messages)

        try:
            summary = generate_summary(openai_client, summary_target)

            print("===== 요약 결과 =====")
            print(summary)

        except Exception as e:
            # 요약은 부가 기능이므로 실패해도 원본 메시지로 계속 진행
            logger.warning("대화 요약 실패, 원본 메시지로 진행합니다: %s", e)
            request.metadata["conversation_summarized"] = False
            request.metadata["conversation_summary"] = ""
            return next_(request)

        logger.debug("요약 결과: %s", summary)

        if summary:
            summary_message = {
                "role": "system",
                "content": f"[이전 대화 요약]\n{summary}",
            }

            # 원본 system → 요약 system → 최근 메시지 순서로 재구성
            request.messages = original_system_messages + [summary_message] + recent_messages

            print("===== 최종 messages =====")
            for m in request.messages:
                print(m)

            request.metadata["conversation_summarized"] = True
            request.metadata["conversation_summary"] = summary
        else:
            request.metadata["conversation_summarized"] = False
            request.metadata["conversation_summary"] = ""

        return next_(request)

    return middleware
