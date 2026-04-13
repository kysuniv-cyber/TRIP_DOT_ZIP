from dataclasses import dataclass, field
from typing import Any


@dataclass
class TravelRequest:
    region: str
    date: str
    budget_krw: int
    start_time: str = "10:00"
    end_time: str = "20:00"
    theme: list[str] = field(default_factory=list)
    companion: str = "solo"
    weather_sensitive: bool = True


def normalize_user_input(raw: dict[str, Any]) -> TravelRequest:
    region = str(raw.get("region", "")).strip()
    date = str(raw.get("date", "")).strip()
    budget_krw = int(raw.get("budget_krw", 0))
    start_time = str(raw.get("start_time", "10:00")).strip()
    end_time = str(raw.get("end_time", "20:00")).strip()
    theme = raw.get("theme", [])
    companion = str(raw.get("companion", "solo")).strip()
    weather_sensitive = bool(raw.get("weather_sensitive", True))

    if not region:
        raise ValueError("region은 필수입니다.")
    if not date:
        raise ValueError("date는 필수입니다.")
    if budget_krw <= 0:
        raise ValueError("budget_krw는 1 이상이어야 합니다.")

    if isinstance(theme, str):
        theme = [theme]

    return TravelRequest(
        region=region,
        date=date,
        budget_krw=budget_krw,
        start_time=start_time,
        end_time=end_time,
        theme=theme,
        companion=companion,
        weather_sensitive=weather_sensitive,
    )