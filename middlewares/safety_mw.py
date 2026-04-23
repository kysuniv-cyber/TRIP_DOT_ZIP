from openai import OpenAI
from middlewares.pipeline import LLMRequest, LLMResponse
import re

"""
사용자 입력을 LLM에 보내기 전에 검사하는 안전성 미들웨어

1. 욕설/유해 표현 검사
- 직접 정의한 욕설 리스트로 1차 감지
- OpenAI Moderation API로 2차 검사
- 점수가 임계값 이상이면 차단

2. 개인정보(PII) 탐지/마스킹
- 전화번호, 이메일, 카드번호, 주민번호, 여권번호, 계좌번호 패턴 탐지
- 고위험 정보는 차단
- 그 외는 마스킹해서 다음 단계로 넘김
"""

# =========================
# 1. Bad word 리스트
# =========================
BAD_WORDS = [
    "씨발", "시발", "ㅅㅂ",
    "병신", "븅신", "ㅄ",
    "개새끼", "ㅈ같", "좆", "fuck",
    "존나", "죽어", "죽일거야", "죽을래"
]

# =========================
# 1-1. Global moderation threshold
# =========================
GLOBAL_BLOCK_THRESHOLD = 0.6

print("### safety_mw loaded from:", __file__)
print("### GLOBAL_BLOCK_THRESHOLD:", GLOBAL_BLOCK_THRESHOLD)


def contains_bad_word(text: str) -> bool:
    """입력 텍스트에 욕설 포함 여부를 확인한다.

    BAD_WORDS 리스트를 기준으로 소문자 변환 후 포함 여부를 검사한다.
    단순 문자열 포함 검사이므로 맥락 분석은 하지 않는다.

    Args:
        text (str): 검사할 사용자 입력 문자열

    Returns:
        bool: 욕설이 포함되어 있으면 True, 아니면 False
    """
    normalized = re.sub(r"\s+", "", text.lower())
    return any(bad in normalized for bad in BAD_WORDS)

# =========================
# 2. Moderation API 호출
# =========================
def check_moderation(client: OpenAI, text: str) -> dict:
    """OpenAI Moderation API를 호출해 유해성 검사 결과를 반환한다.

    omni-moderation-latest 모델을 사용하여 입력 텍스트의
    정책 위반 가능성을 검사하고, flag 여부/카테고리/점수를 정리해 반환한다.

    Args:
        client (OpenAI): OpenAI API 클라이언트 객체
        text (str): 검사할 사용자 입력 문자열

    Returns:
        dict: moderation 결과 딕셔너리
            - flagged: 전체 차단 플래그
            - categories: 카테고리별 탐지 결과
            - scores: 카테고리별 점수
    """
    response = client.moderations.create(
        model="omni-moderation-latest",
        input=text
    )
    result = response.results[0]

    return {
        "flagged": result.flagged,
        "categories": dict(result.categories),
        "scores": dict(result.category_scores),
    }


def should_block_by_score(category_scores: dict) -> bool:
    """Moderation 점수를 기준으로 차단 여부를 판단한다.

    category_scores의 각 카테고리 점수를 순회하며
    GLOBAL_BLOCK_THRESHOLD 이상인 값이 하나라도 있으면 차단한다.

    Args:
        category_scores (dict): moderation 카테고리별 점수 딕셔너리

    Returns:
        bool: 차단이 필요하면 True, 아니면 False
    """
    for category, score in category_scores.items():
        if score >= GLOBAL_BLOCK_THRESHOLD:
            print(
                f"🚫 score 차단: {category}={score:.4f} "
                f"(threshold={GLOBAL_BLOCK_THRESHOLD})"
            )
            return True
    return False


# =========================
# 3. 차단 여부 판단
# =========================
def should_block(client: OpenAI, text: str) -> bool:
    """사용자 입력에 대해 최종 차단 여부를 판단한다.

    먼저 욕설 리스트로 1차 감지를 수행하고,
    이후 OpenAI Moderation API 결과 점수를 기준으로
    실제 차단 여부를 결정한다.

    Args:
        client (OpenAI): OpenAI API 클라이언트 객체
        text (str): 검사할 사용자 입력 문자열

    Returns:
        bool: 차단이 필요하면 True, 아니면 False
    """
    bad_word_hit = contains_bad_word(text)

    if contains_bad_word(text):
        print("⚠️ bad word 감지: soft 필터 적용 예정, moderation도 계속 실행")

    mod = check_moderation(client, text)

    print("🔍 moderation flagged:", mod["flagged"])
    print("🔍 moderation categories:", mod["categories"])
    print("🔍 moderation scores:", mod["scores"])


    return bad_word_hit or should_block_by_score(mod["scores"])


# =========================
# 4. 욕설 Middleware
# =========================
def profanity_middleware(openai_client: OpenAI):
    """욕설 및 유해 표현을 처리하는 미들웨어를 생성한다.

    사용자 메시지를 모아 욕설 및 moderation 검사를 수행한다.
    차단 대상이면 예외를 발생시키고,
    단순 욕설이 감지된 경우에는 메시지 앞에 경고 문구를 붙여
    다음 단계로 전달한다.

    Args:
        openai_client (OpenAI): OpenAI API 클라이언트 객체

    Returns:
        callable: LLMRequest를 받아 검사 후 next_로 전달하는 미들웨어 함수
    """
    def middleware(request: LLMRequest, next_) -> LLMResponse:
        if not hasattr(request, "metadata") or request.metadata is None:
            request.metadata = {}

        user_texts = [
            m.get("content", "")
            for m in request.messages
            if m.get("role") == "user" and isinstance(m.get("content"), str)
        ]
        full_text = " ".join(user_texts)

        print("🔥 profanity middleware 실행됨")
        print("입력:", full_text)

        if should_block(openai_client, full_text):
            print("🚫 차단됨")
            raise ValueError("땃쥐가 상처받아 뒤돌았습니다.")

        if contains_bad_word(full_text):
            print("🚫 욕설 차단됨")
            raise ValueError("땃쥐가 상처받아 뒤돌았습니다.")

        return next_(request)

    return middleware


# =========================
# 5. PII 패턴 정의
# =========================
PII_PATTERNS = {
    "PHONE": re.compile(r"01[0-9][-\s]?\d{3,4}[-\s]?\d{4}"),
    "EMAIL": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "CARD": re.compile(r"(?:\d{4}[- ]?){3}\d{4}"),
    "RRN": re.compile(r"\d{6}-?[1-4]\d{6}"),
    "PASSPORT": re.compile(r"[A-Z]{1,2}\d{7,8}"),
    "ACCOUNT": re.compile(r"\b(?!(010|011|016|017|018|019)-)\d{2,4}-\d{2,6}-\d{2,6}\b"),
}

HIGH_RISK_TYPES = {"RRN", "CARD", "ACCOUNT"}
MEDIUM_RISK_TYPES = {"PHONE", "EMAIL", "PASSPORT"}


# =========================
# 6. PII 탐지
# =========================
def detect_pii(text: str) -> list[dict]:
    """텍스트에서 개인정보 패턴을 탐지한다.

    전화번호, 이메일, 카드번호, 주민번호, 여권번호, 계좌번호를
    정규표현식으로 탐지하고, 중복/겹침 구간은 제외한 뒤
    타입, 값, 위치, 위험도를 포함한 리스트를 반환한다.

    Args:
        text (str): 검사할 사용자 입력 문자열

    Returns:
        list[dict]: 탐지된 개인정보 엔티티 목록
    """
    detected = []
    occupied_spans = []

    pattern_order = ["PHONE", "EMAIL", "CARD", "RRN", "PASSPORT", "ACCOUNT"]

    for pii_type in pattern_order:
        pattern = PII_PATTERNS[pii_type]

        for match in pattern.finditer(text):
            start, end = match.start(), match.end()

            overlapped = any(not (end <= s or start >= e) for s, e in occupied_spans)
            if overlapped:
                continue

            risk = "high" if pii_type in HIGH_RISK_TYPES else "medium"
            detected.append({
                "type": pii_type,
                "value": match.group(),
                "start": start,
                "end": end,
                "risk": risk,
            })
            occupied_spans.append((start, end))

    return detected


# =========================
# 7. PII 차단 여부 판단
# =========================
def should_block_pii(detected_entities: list[dict]) -> bool:
    """탐지된 개인정보 목록을 기준으로 차단 여부를 판단한다.

    주민번호, 카드번호, 계좌번호처럼 고위험 정보가 하나라도 포함되면
    요청을 차단 대상으로 본다.

    Args:
        detected_entities (list[dict]): 탐지된 개인정보 엔티티 목록

    Returns:
        bool: 차단이 필요하면 True, 아니면 False
    """
    return any(entity["type"] in HIGH_RISK_TYPES for entity in detected_entities)


# =========================
# 8. PII 마스킹
# =========================
def redact_pii(text: str, detected_entities: list[dict]) -> str:
    """탐지된 개인정보를 placeholder로 마스킹한다.

    detect_pii 결과에 포함된 시작/끝 위치를 기준으로
    원문 문자열의 해당 구간만 [TYPE] 형식으로 대체한다.
    뒤쪽 인덱스부터 처리하여 위치 어긋남을 방지한다.

    Args:
        text (str): 원본 사용자 입력 문자열
        detected_entities (list[dict]): 탐지된 개인정보 엔티티 목록

    Returns:
        str: 개인정보가 마스킹된 문자열
    """
    redacted = text

    for entity in sorted(detected_entities, key=lambda x: x["start"], reverse=True):
        placeholder = f"[{entity['type']}]"
        redacted = redacted[:entity["start"]] + placeholder + redacted[entity["end"]:]

    return redacted


# =========================
# 9. Sanitizer
# =========================
def sanitize_pii(text: str) -> dict:
    """텍스트의 개인정보를 탐지하고 마스킹 결과를 반환한다.

    detect_pii, should_block_pii, redact_pii를 순서대로 수행하여
    원본 텍스트, 마스킹 텍스트, 탐지 엔티티, 차단 여부를 묶어 반환한다.

    Args:
        text (str): 검사할 사용자 입력 문자열

    Returns:
        dict: 개인정보 처리 결과 딕셔너리
            - original_text: 원본 입력
            - sanitized_text: 마스킹된 입력
            - detected_entities: 탐지 엔티티 목록
            - blocked: 차단 여부
    """
    detected = detect_pii(text)
    blocked = should_block_pii(detected)
    sanitized_text = redact_pii(text, detected)

    return {
        "original_text": text,
        "sanitized_text": sanitized_text,
        "detected_entities": detected,
        "blocked": blocked,
    }


# =========================
# 10. PII Middleware
# =========================
def pii_middleware():
    """개인정보 탐지 및 마스킹을 수행하는 미들웨어를 생성한다.

    사용자 메시지마다 개인정보를 탐지하고,
    발견된 경우 마스킹된 텍스트로 교체한다.
    고위험 개인정보가 포함되면 예외를 발생시켜 요청을 차단한다.
    또한 탐지 결과와 마스킹 여부를 request.metadata에 기록한다.

    Args:
        없음

    Returns:
        callable: LLMRequest를 받아 개인정보 검사 후 next_로 전달하는 미들웨어 함수
    """
    def middleware(request: LLMRequest, next_) -> LLMResponse:
        if not hasattr(request, "metadata") or request.metadata is None:
            request.metadata = {}

        has_pii = False
        all_detected = []
        sanitized_user_texts = []

        for msg in request.messages:
            if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                result = sanitize_pii(msg["content"])

                print("입력:", msg["content"])
                print("탐지:", result["detected_entities"])
                print("마스킹 결과:", result["sanitized_text"])
                print("차단 여부:", result["blocked"])

                if result["detected_entities"]:
                    has_pii = True
                    all_detected.extend(result["detected_entities"])

                # 항상 먼저 마스킹 반영
                msg["content"] = result["sanitized_text"]
                sanitized_user_texts.append(result["sanitized_text"])

                # high risk면 차단
                if result["blocked"]:
                    request.metadata["pii_detected"] = has_pii
                    request.metadata["pii_entities"] = all_detected
                    request.metadata["sanitized"] = has_pii
                    request.metadata["sanitized_user_input"] = " ".join(sanitized_user_texts)
                    raise ValueError("민감한 개인정보가 포함되어 있어 요청이 차단되었습니다.")

        request.metadata["pii_detected"] = has_pii
        request.metadata["pii_entities"] = all_detected if has_pii else []
        request.metadata["sanitized"] = has_pii
        request.metadata["sanitized_user_input"] = " ".join(sanitized_user_texts)

        return next_(request)

    return middleware
