from openai import OpenAI
from middlewares.pipeline import LLMRequest, LLMResponse
import re

# TODO: 1. 욕설 및 비방표현 필터링
# TODO: 2. 개인정보 마스킹 및 필터링

# =========================
# 1. Bad word 리스트
# =========================
BAD_WORDS = [
    "씨발", "시발", "ㅅㅂ",
    "병신", "븅신", "ㅄ",
    "개새끼", "ㅈ같", "좆", "fuck"
]

# =========================
# 1-1. Global moderation threshold
# =========================
GLOBAL_BLOCK_THRESHOLD = 0.6

print("### safety_mw loaded from:", __file__)
print("### GLOBAL_BLOCK_THRESHOLD:", GLOBAL_BLOCK_THRESHOLD)


def contains_bad_word(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in BAD_WORDS)


# =========================
# 2. Moderation API 호출
# =========================
def check_moderation(client: OpenAI, text: str) -> dict:
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
    if contains_bad_word(text):
        print("⚠️ bad word 감지: soft 필터 적용 예정, moderation도 계속 실행")

    mod = check_moderation(client, text)

    print("🔍 moderation flagged:", mod["flagged"])
    print("🔍 moderation categories:", mod["categories"])
    print("🔍 moderation scores:", mod["scores"])

    return should_block_by_score(mod["scores"])


# =========================
# 4. 욕설 Middleware
# =========================
def profanity_middleware(openai_client: OpenAI):
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
            print("⚠️ 욕설 감지됨")
            for msg in request.messages:
                if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                    msg["content"] = f"[주의: 과격한 표현 포함]\n{msg['content']}"
            request.metadata["profanity_detected"] = True
        else:
            request.metadata["profanity_detected"] = False

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
    return any(entity["type"] in HIGH_RISK_TYPES for entity in detected_entities)


# =========================
# 8. PII 마스킹
# =========================
def redact_pii(text: str, detected_entities: list[dict]) -> str:
    """detect_pii 결과를 바탕으로 정확한 위치만 마스킹한다."""
    redacted = text

    for entity in sorted(detected_entities, key=lambda x: x["start"], reverse=True):
        placeholder = f"[{entity['type']}]"
        redacted = redacted[:entity["start"]] + placeholder + redacted[entity["end"]:]

    return redacted


# =========================
# 9. Sanitizer
# =========================
def sanitize_pii(text: str) -> dict:
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
