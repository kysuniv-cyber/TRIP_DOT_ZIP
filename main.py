"""
애플리케이션 실행의 진입점이 되는 파일.

사용자 입력을 받아 agent graph를 실행하고,
LLM이 생성한 최종 응답을 반환하는 역할을 한다.
전체 실행 흐름을 시작하고 필요한 구성 요소를 연결한다.
"""

import os
import traceback
from dotenv import load_dotenv

from agent_builder import build_agent

load_dotenv()

# 실행 모드 선택
# "invoke" : 최종 답변만 한 번에 출력
# "debug"  : 중간 tool trace까지 전부 출력
# "stream" : 스트리밍 형태로 flush 출력
RUN_MODE = "debug"         # <- 여기 있는 RUN_MODE를 바꾸면 출력 형식이 바뀜.


def run_invoke(agent, user_input: str):
    result = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": user_input}
            ]
        }
    )

    print("=== Agent Result ===")
    print(result.get("final_response", "final_response 없음"))


def run_debug(agent, user_input: str):
    result = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": user_input}
            ]
        }
    )

    print("=== Final Answer ===")
    print(result.get("final_response", "final_response 없음"))

    print("\n=== Full State ===")
    for k, v in result.items():
        print(f"{k}: {v}")


def run_stream(agent, user_input: str):
    stream = agent.stream(
        {
            "messages": [
                {"role": "user", "content": user_input}
            ]
        },
        stream_mode="messages",
    )

    print("=== Streaming Result ===")

    for chunk, metadata in stream:
        if metadata.get("langgraph_node") != "model":
            continue

        # text block 기반 출력
        if hasattr(chunk, "content_blocks"):
            for block in chunk.content_blocks:
                if block.get("type") == "text":
                    print(block.get("text", ""), end="", flush=True)

        # fallback
        elif hasattr(chunk, "content") and isinstance(chunk.content, str):
            print(chunk.content, end="", flush=True)

    print()


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

    agent = build_agent()

    user_input = """
    내일 부산에서 1일 여행 일정 짜줘.
    카페랑 맛집이 포함되면 좋고,
    오전 10시부터 시작하는 시간대별 일정으로 만들어줘.
    비 오면 실내 위주면 좋겠어.
    """

    if RUN_MODE == "invoke":
        run_invoke(agent, user_input)
    elif RUN_MODE == "debug":
        run_debug(agent, user_input)
    elif RUN_MODE == "stream":
        run_stream(agent, user_input)
    else:
        raise ValueError(f"지원하지 않는 RUN_MODE입니다: {RUN_MODE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("에러 타입:", type(e).__name__)
        print("에러 내용:", repr(e))
        traceback.print_exc()
        raise