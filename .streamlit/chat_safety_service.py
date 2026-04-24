from openai import OpenAI
from middlewares.safety_mw import sanitize_pii, contains_bad_word, should_block


client = OpenAI()


def check_user_input_for_streamlit(user_text: str) -> dict:
    """
    Streamlit 앱에서 바로 사용할 수 있는 안전 처리 함수

    return 예시:
    {
        "blocked": False,
        "display_text": "...",
        "llm_text": "...",
        "warning": None,
        "pii_detected": True,
        "profanity_detected": False,
        "detected_entities": [...]
    }
    """
    pii_result = sanitize_pii(user_text)
    sanitized_text = pii_result["sanitized_text"]

    # high-risk 개인정보 차단
    if pii_result["blocked"]:
        return {
            "blocked": True,
            "display_text": sanitized_text,
            "llm_text": None,
            "warning": "민감한 개인정보가 포함되어 있어 요청이 차단되었습니다.",
            "pii_detected": bool(pii_result["detected_entities"]),
            "profanity_detected": False,
            "detected_entities": pii_result["detected_entities"],
        }

    # 욕설 soft filter 여부
    profanity_detected = contains_bad_word(sanitized_text)

    # moderation 차단 여부
    try:
        harmful = should_block(client, sanitized_text)
    except Exception as exc:
        return {
            "blocked": True,
            "display_text": sanitized_text,
            "llm_text": None,
            "warning": f"안전성 검사를 수행하지 못했습니다: {exc}",
            "pii_detected": bool(pii_result["detected_entities"]),
            "profanity_detected": profanity_detected,
            "detected_entities": pii_result["detected_entities"],
        }

    if harmful:
        return {
            "blocked": True,
            "display_text": sanitized_text,
            "llm_text": None,
            "warning": "안전하지 않은 표현이 포함되어 있어 요청이 차단되었습니다.",
            "pii_detected": bool(pii_result["detected_entities"]),
            "profanity_detected": profanity_detected,
            "detected_entities": pii_result["detected_entities"],
        }

    llm_text = sanitized_text
    if profanity_detected:
        llm_text = f"[주의: 과격한 표현 포함]\n{sanitized_text}"

    return {
        "blocked": False,
        "display_text": sanitized_text,   # 화면에 보여줄 텍스트
        "llm_text": llm_text,             # 모델에 보낼 텍스트
        "warning": None,
        "pii_detected": bool(pii_result["detected_entities"]),
        "profanity_detected": profanity_detected,
        "detected_entities": pii_result["detected_entities"],
    }