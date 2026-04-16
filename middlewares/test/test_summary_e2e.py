"""
실제 OpenAI API를 호출하는 E2E 테스트.
로컬에서만 실행하고 CI에서는 제외한다.

실행 방법:
    pytest tests/test_summary_e2e.py -m integration -v

CI에서 제외:
    pytest -m "not integration"
"""

import os
import pytest
from dataclasses import dataclass, field
from openai import OpenAI
from config import Settings

settings = Settings()
api_key = settings.openai_api_key


from middlewares.summary_mw import conversation_summary_middleware, generate_summary


@dataclass
class LLMRequest:
    messages: list[dict]
    model: str = "gpt-4o"
    metadata: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    usage: dict = field(default_factory=dict)


@pytest.fixture(scope="module")
def openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY 환경변수가 없어 E2E 테스트를 건너뜁니다.")
    return OpenAI(api_key=api_key)


@pytest.mark.integration
def test_generate_summary_returns_korean_text(openai_client):
    """실제 API 호출 시 한국어 요약이 반환되는지 확인한다."""
    messages = [
        {"role": "user", "content": "강아지 종류는 뭐가 있어?"},
        {"role": "assistant", "content": "강아지는 크기와 역할에 따라 다양하게 나뉩니다. 소형견은 말티즈, 포메라니안처럼 작고 실내 생활에 적합합니다. 중형견은 비글, 코기처럼 활동성이 적당합니다 "
                                          "대형견은 골든 리트리버, 허스키처럼 운동량이 많습니다. 또한 목양견, 사냥견, 경비견 등 역할에 따라서도 구분됩니다."},
        {"role": "user", "content": "그럼 말티즈의 특징은 뭐야?"},
        {"role": "assistant", "content": "말티즈는 작고 온순한 성격이 특징인 소형견입니다. 사람을 잘 따르고 애교가 많아 반려견으로 인기가 높습니다. "
                                          "털이 길고 하얀 것이 특징이며 털 빠짐은 적지만 대신 꾸준한 관리가 필요합니다. 활동량은 많지 않아 실내에서 키우기 적합한 편입니다."},
    ]

    summary = generate_summary(openai_client, messages, max_chars=300)

    assert isinstance(summary, str)
    assert len(summary) > 0
    # 핵심 키워드가 요약에 포함되는지 확인
    assert any(kw in summary for kw in ["강아지", "종류", "특징", "말티즈"])


@pytest.mark.integration
def test_middleware_end_to_end(openai_client):
    """미들웨어가 실제 API와 함께 정상 동작하는지 확인한다."""
    mw = conversation_summary_middleware(
        openai_client,
        trigger_char_count=200,
        keep_last_n=2,
    )

    system_msg = {"role": "system", "content": "너는 친절한 AI 어시스턴트야."}
    long_history = [
        {"role": "user", "content": "강아지 종류는 뭐가 있어? " + "내용 " * 30},
        {"role": "assistant",
         "content": "강아지는 크기와 역할에 따라 다양하게 나뉩니다. 소형견은 말티즈, 포메라니안처럼 작고 실내 생활에 적합합니다. 중형견은 비글, 코기처럼 활동성이 적당합니다. 대형견은 골든 리트리버, 허스키처럼 운동량이 많습니다. 또한 목양견, 사냥견, 경비견 등 역할에 따라서도 구분됩니다. " + "설명 " * 30},
        {"role": "user", "content": "그럼 말티즈 특징은 뭐야? " + "질문 " * 30},
        {"role": "assistant",
         "content": "말티즈는 작고 온순한 성격이 특징인 소형견입니다. 사람을 잘 따르고 애교가 많아 반려견으로 인기가 높습니다. 털이 길고 하얀 것이 특징이며 털 빠짐은 적지만 꾸준한 관리가 필요합니다. 활동량은 많지 않아 실내에서 키우기 적합한 편입니다. " + "답변 " * 30},
        {"role": "user", "content": "마지막 질문이에요"},
        {"role": "assistant", "content": "물론이죠!"},
    ]

    request = LLMRequest(messages=[system_msg] + long_history)

    def fake_next(req):
        return LLMResponse(content="최종 응답")

    response = mw(request, fake_next)

    assert response.content == "최종 응답"
    assert request.metadata["conversation_summarized"] is True
    assert len(request.metadata["conversation_summary"]) > 0

    # 원본 system 메시지 보존 확인
    assert request.messages[0]["role"] == "system"
    assert request.messages[0]["content"] == "너는 친절한 AI 어시스턴트야."
