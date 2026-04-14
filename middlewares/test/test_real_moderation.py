# test_real_moderation.py

from config import Settings
from llm.graph import build_trip_agent   # 네 프로젝트에 있으면
from middlewares.safety_mw import profanity_middleware
from middlewares.pipeline import LLMRequest, LLMResponse

# 가짜 next
def fake_next(request: LLMRequest) -> LLMResponse:
    return LLMResponse(
        content="통과",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        model="gpt-4o-mini",
        finish_reason="stop",
        metadata={"messages": request.messages, "meta": request.metadata},
    )

if __name__ == "__main__":
    settings = Settings()
    settings.validate()

    # 네 LLMClient 구조에 맞게 수정
    llm_client = build_trip_agent(settings)
    mw = profanity_middleware(llm_client)

    req = LLMRequest(
        messages=[{"role": "user", "content": "이런 엿같은 창자를 뽑아가지고 젓갈을 담가먹어야 하나흘 메롱"}],
        model="gpt-4o-mini",
        metadata={}
    )

    try:
        res = mw(req, fake_next)
        print(res.content)
        print(res.metadata)
    except Exception as e:
        print("차단:", e)