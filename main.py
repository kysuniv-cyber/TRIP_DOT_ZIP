import os
from dotenv import load_dotenv

from llm.graph import build_trip_agent

load_dotenv()


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

    agent = build_trip_agent()

    user_input = """
    성수에서 1일 데이트 코스 짜줘.
    오전 10시부터 오후 6시까지 놀 거고,
    감성 카페, 맛집, 산책 가능한 곳이 포함되면 좋겠어.
    """

    # 한번에 출력
    result = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": user_input}
            ]
        }
    )

    print("=== Agent Result ===")
    print(result['messages'][-1].content)

    # flush로 출력
    # stream = llm.stream(
    #     input={
    #         "messages": [('human', user_input)]
    #     },
    #     stream_mode='messages'
    # )
    #
    # for chunk, metadata in stream:
    #     print(chunk.content, end='', flush=True)


if __name__ == "__main__":
    main()



# --------------
import traceback

try:
    # 기존 실행 코드
    main()
except Exception as e:
    print("에러 타입:", type(e).__name__)
    print("에러 내용:", repr(e))
    traceback.print_exc()
    raise