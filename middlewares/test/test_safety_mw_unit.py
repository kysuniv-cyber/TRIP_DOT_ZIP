# test_safety_mw_unit.py

from dataclasses import dataclass
from middlewares.safety_mw import profanity_middleware
from middlewares.pipeline import LLMRequest, LLMResponse


# ---- 가짜 OpenAI client ----
class FakeModerationResult:
    def __init__(self, flagged, categories):
        self.flagged = flagged
        self.categories = categories


class FakeModerationResponse:
    def __init__(self, flagged, categories):
        self.results = [FakeModerationResult(flagged, categories)]


class FakeModerations:
    def create(self, model, input):
        # 테스트 규칙:
        # "죽여" 들어가면 violence=True
        # 그 외는 안전
        if "죽여" in input:
            return FakeModerationResponse(
                flagged=True,
                categories={"violence": True, "hate": False}
            )
        return FakeModerationResponse(
            flagged=False,
            categories={"violence": False, "hate": False}
        )


class FakeOpenAIClient:
    def __init__(self):
        self.moderations = FakeModerations()


class FakeLLMClient:
    def __init__(self):
        self.client = FakeOpenAIClient()


# ---- next 함수 ----
def fake_next(request: LLMRequest) -> LLMResponse:
    return LLMResponse(
        content="정상 통과",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        model="fake-model",
        finish_reason="stop",
        metadata={"echo_messages": request.messages, "echo_meta": request.metadata},
    )


if __name__ == "__main__":
    llm_client = FakeLLMClient()
    mw = profanity_middleware(llm_client)

    test_cases = [
        {
            "name": "정상 입력",
            "messages": [{"role": "user", "content": "부산 여행 추천해줘"}],
        },
        {
            "name": "욕설 포함 입력",
            "messages": [{"role": "user", "content": "씨발 부산 여행 추천해줘"}],
        },
        {
            "name": "차단 입력",
            "messages": [{"role": "user", "content": "너 죽여버릴거야"}],
        },
        {
            "name": "그 외 확인",
            "messages": [{"role": "user", "content": "이런 엿같은 창자를 뽑아가지고 젓갈을 담가먹어야 하나"}],
        }
    ]

    for case in test_cases:
        print(f"\n=== {case['name']} ===")
        req = LLMRequest(
            messages=case["messages"],
            model="gpt-4o-mini",
            metadata={}
        )

        try:
            res = mw(req, fake_next)
            print("content:", res.content)
            print("messages:", res.metadata["echo_messages"])
            print("metadata:", res.metadata["echo_meta"])
        except Exception as e:
            print("ERROR:", str(e))