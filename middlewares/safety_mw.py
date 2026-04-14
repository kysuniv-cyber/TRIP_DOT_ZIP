import re
from openai import OpenAI
from middlewares.pipeline import LLMRequest, LLMResponse

# =========================
# 1. Bad word 리스트
# =========================
BAD_WORDS = [
    "씨발", "시발", "ㅅㅂ",
    "병신", "븅신","ㅄ",
    "개새끼", "ㅈ같", "좆", "fuck"
]


def contains_bad_word(text: str) -> bool:
    """텍스트에 욕설이 포함되어 있는지 확인한다.

    Args:
        text (str): 검사할 입력 문자열

    Returns:
        bool: 욕설이 포함되어 있으면 True, 아니면 False
    """
    lowered = text.lower()
    return any(word in lowered for word in BAD_WORDS)


# =========================
# 2. Moderation API 호출
# =========================
def check_moderation(client: OpenAI, text: str) -> dict:
    """OpenAI Moderation API를 호출하여 유해성 여부를 판단한다.

    Args:
        client (OpenAI): OpenAI 클라이언트 인스턴스
        text (str): 검사할 입력 문자열

    Returns:
        dict: moderation 결과
            {
                "flagged": bool,          # 전체 위험 여부
                "categories": dict        # 카테고리별 판단 결과
            }
    """
    response = client.moderations.create(
        model="omni-moderation-latest",
        input=text
    )
    result = response.results[0]

    return {
        "flagged": result.flagged,
        "categories": dict(result.categories),
    }


# =========================
# 3. 차단 여부 판단
# =========================
def should_block(client: OpenAI, text: str) -> bool:
    """텍스트를 차단해야 하는지 여부를 판단한다.

    욕설만 포함된 경우는 soft 필터로 처리하고,
    violence / hate 등 강한 유해성만 차단한다.

    Args:
        client (OpenAI): OpenAI 클라이언트
        text (str): 검사할 입력 문자열

    Returns:
        bool: 차단해야 하면 True, 아니면 False
    """
    # 욕설만 있는 경우 → moderation API 호출 생략
    if contains_bad_word(text):
        return False

    # moderation 검사
    mod = check_moderation(client, text)
    categories = mod["categories"]

    # 강한 유해성만 차단
    if categories.get("violence"):
        return True
    if categories.get("hate"):
        return True

    return False


# =========================
# 4. Middleware 팩토리
# =========================
def profanity_middleware(llm_client):
    """욕설 및 유해 입력을 필터링하는 미들웨어를 생성한다.

    LangChain이 아닌 커스텀 Pipeline 구조에 맞는 middleware를 반환한다.

    Args:
        llm_client: OpenAI client를 포함하는 객체
            (llm_client.client 형태로 접근 가능해야 함)

    Returns:
        Callable: (request, next) 형태의 middleware 함수
    """
    openai_client = llm_client.client

    def middleware(request: LLMRequest, next_) -> LLMResponse:
        """Pipeline에서 실행되는 실제 미들웨어 로직.

        Args:
            request (LLMRequest): LLM 요청 객체
            next_ (Callable): 다음 middleware 또는 base_handler

        Returns:
            LLMResponse: 다음 단계에서 반환된 응답
        """
        # user 메시지만 검사
        user_texts = [
            m.get("content", "")
            for m in request.messages
            if m.get("role") == "user" and isinstance(m.get("content"), str)
        ]
        full_text = " ".join(user_texts)

        # Hard 차단
        if should_block(openai_client, full_text):
            raise ValueError("부적절한 요청입니다.")

        # Soft 필터 (욕설 → 경고)
        if contains_bad_word(full_text):
            for msg in request.messages:
                if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                    msg["content"] = f"[주의: 과격한 표현 포함]\n{msg['content']}"
            request.metadata["profanity_detected"] = True

        return next_(request)

    return middleware