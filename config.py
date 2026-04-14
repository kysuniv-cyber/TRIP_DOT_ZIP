from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")
    places_api_key: str = os.getenv("PLACES_API_KEY", "")
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    max_tool_rounds: int = int(os.getenv("MAX_TOOL_ROUNDS", "5"))

    def validate(self) -> None:
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        elif not self.weather_api_key:
            raise ValueError("WEATHER_API_KEY가 설정되지 않았습니다")
        elif not self.places_api_key:
            raise ValueError("PLACES_API_KEY가 설정되지 않았습니다")
        else:
            raise ValueError("메롱")