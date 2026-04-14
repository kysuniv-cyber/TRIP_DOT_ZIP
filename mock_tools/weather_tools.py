from langchain.tools import tool
from llm.schemas import success_response


@tool
def get_weather(destination: str, date: str) -> dict:
    """
    목적지와 날짜를 받아 날씨 정보를 반환한다.
    지금은 mock 함수이며, 나중에 실제 날씨 API로 교체한다.
    """
    return success_response(
        {
            "destination": destination,
            "date": date,
            "weather": "맑음",
            "temperature_c": 22,
            "precipitation_probability": 10,
            "advice": "야외 일정 진행에 무리가 없습니다."
        }
    )