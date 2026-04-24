from middlewares.safety_mw import profanity_middleware
from middlewares.pipeline import Pipeline, LLMRequest, LLMResponse


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


# ---- base_handler ----
def fake_base_handler(request: LLMRequest) -> LLMResponse:
    user_contents = [
        m["content"]
        for m in request.messages
        if m.get("role") == "user"
    ]
    return LLMResponse(
        content=f"최종 입력: {' | '.join(user_contents)}",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        model=request.model,
        finish_reason="stop",
        metadata={"request_metadata": request.metadata},
    )


if __name__ == "__main__":
    llm_client = FakeLLMClient()

    pipeline = Pipeline(fake_base_handler)
    pipeline.use(profanity_middleware(llm_client))

    tests = [
        "부산 여행 추천해줘",
        "이런 엿같은 창자를 뽑아가지고 젓갈을 담가먹어야 하나",
        "너 죽여버릴거야",
    ]

    for text in tests:
        print(f"\n입력: {text}")
        req = LLMRequest(
            messages=[{"role": "user", "content": text}],
            model="gpt-4o-mini",
            metadata={}
        )

        try:
            res = pipeline.execute(req)
            print("응답:", res.content)
            print("메타데이터:", res.metadata)
        except Exception as e:
            print("차단:", str(e))