import logging
from openai import OpenAI
from middlewares.pipeline import LLMRequest, LLMResponse

"""
summary_mw.py

대화 길이가 길어질 때 이전 메시지를 요약하여
LLM 입력 토큰/문자 수를 줄이고, 핵심 맥락만 유지하기 위한
Conversation Summary Middleware 모듈이다.

주요 기능:
- 일정 길이 이상 대화가 누적되면 자동 요약 수행
- system 메시지는 유지하고, 과거 대화는 요약으로 압축
- 최근 N개의 메시지는 그대로 유지하여 문맥 손실 방지
- OpenAI LLM을 활용해 한국어 요약 생성

동작 방식:
1. 메시지 총 문자 수가 threshold를 초과하면 요약 트리거
2. 오래된 메시지를 분리하고 요약 생성
3. [이전 대화 요약] system 메시지로 삽입
4. 최근 메시지와 함께 LLM에 전달

이 모듈은 middlewares.pipeline의 LLMRequest / LLMResponse 구조에서
동작하도록 설계된 미들웨어이다.
"""

logger = logging.getLogger(__name__)


def collect_summary_target_messages(messages: list[dict]) -> list[dict]:
    """요약 대상 메시지를 필터링한다.

    system 메시지는 제외하고 user와 assistant 메시지만 추출한다.
    content가 list 타입(멀티모달)일 경우 text 파트만 추출하여 결합한다.

    Args:
        messages (list[dict]): 전체 대화 메시지 리스트

    Returns:
        list[dict]: 요약에 사용할 메시지 리스트
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
    """메시지 리스트를 요약용 문자열로 변환한다.

    각 메시지를 [role] content 형식으로 변환하여
    하나의 문자열로 결합한다.

    Args:
        messages (list[dict]): 요약 대상 메시지 리스트

    Returns:
        str: 요약 모델 입력용 문자열
    """
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
    """LLM을 사용하여 대화 요약을 생성한다.

    메시지를 문자열로 변환한 뒤,
    사용자 목표, 조건, 맥락을 포함한 요약을 생성한다.

    Args:
        client (OpenAI): OpenAI API 클라이언트
        messages (list[dict]): 요약 대상 메시지
        max_chars (int): 요약 최대 길이 제한

    Returns:
        str: 생성된 요약 텍스트
    """
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
    """메시지 내 전체 텍스트 길이를 계산한다.

    content가 문자열인 경우에만 길이를 합산한다.

    Args:
        messages (list[dict]): 전체 메시지 리스트

    Returns:
        int: 총 문자 수
    """
    total = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            total += len(content)
    return total


def conversation_summary_middleware(
    openai_client: OpenAI,
    trigger_char_count: int = 1000,
    keep_last_n: int = 4,
):
    """대화 요약을 수행하는 미들웨어를 생성한다.

    메시지 길이가 일정 기준을 초과하면 과거 메시지를 요약하고,
    최근 메시지와 함께 재구성하여 LLM에 전달한다.

    Args:
        openai_client (OpenAI): OpenAI API 클라이언트
        trigger_char_count (int): 요약 실행 기준 문자 수
        keep_last_n (int): 유지할 최근 메시지 개수

    Returns:
        callable: LLMRequest를 받아 요약 후 next_로 전달하는 미들웨어 함수
    """

    def middleware(request: LLMRequest, next_) -> LLMResponse:
        """요약 로직을 수행하고 다음 단계로 전달한다.

        메시지 길이를 확인하여 요약 여부를 판단하고,
        필요 시 과거 메시지를 요약하여 재구성한다.

        Args:
            request (LLMRequest): 현재 요청 객체 (messages 포함)
            next_ (callable): 다음 미들웨어 또는 LLM 호출 함수

        Returns:
            LLMResponse: 다음 단계 처리 결과
        """
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
