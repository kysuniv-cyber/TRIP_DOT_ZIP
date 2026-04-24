from dataclasses import dataclass, field
from typing import Any

"""
normalizer.py

사용자 여행 요청 입력을 표준 형식으로 정리하고 검증하는 모듈이다.

주요 기능:
- 여행 요청 데이터를 TravelRequest 데이터 클래스로 구조화
- raw dict 입력값을 문자열/정수/리스트 등 적절한 타입으로 변환
- 필수값 누락 및 잘못된 예산 입력을 검증
- 기본값이 없는 항목은 기본 설정값으로 보정

동작 방식:
1. 사용자 입력(raw dict)에서 필요한 값을 추출한다.
2. 각 필드를 적절한 타입으로 변환한다.
3. region, date, budget_krw 등 필수값을 검증한다.
4. 최종적으로 TravelRequest 객체를 생성하여 반환한다.

이 모듈은 여행 추천, 일정 생성, 날씨 기반 판단 등
후속 서비스에서 공통 입력 형식으로 사용할 수 있도록 설계되었다.
"""

from dataclasses import dataclass, field
from typing import Any


# 정규화된 여행 요청 스키마
@dataclass
class TravelRequest:
    """정규화된 여행 요청 데이터를 저장하는 데이터 클래스.

    사용자 입력에서 필요한 여행 정보를 구조화하여
    이후 서비스나 tool에서 일관된 형식으로 사용할 수 있도록 한다.

    Args:
        region (str): 여행 지역명
        date (str): 여행 날짜
        budget_krw (int): 여행 예산(원)
        start_time (str): 일정 시작 시간
        end_time (str): 일정 종료 시간
        theme (list[str]): 여행 테마 목록
        companion (str): 동행 유형
        weather_sensitive (bool): 날씨 민감 여부

    Returns:
        None: 데이터 클래스 인스턴스를 생성한다.
    """

    region: str
    date: str
    budget_krw: int
    start_time: str = "10:00"
    end_time: str = "20:00"
    theme: list[str] = field(default_factory=list)
    companion: str = "solo"
    weather_sensitive: bool = True


# raw 사용자 입력을 안전하게 정리하고 검증하여
# TravelRequest 객체로 변환하는 함수
def normalize_user_input(raw: dict[str, Any]) -> TravelRequest:
    """사용자 입력 딕셔너리를 TravelRequest 객체로 정규화한다.

    raw 입력값에서 여행 관련 필드를 추출하고,
    문자열 정리, 타입 변환, 기본값 보정, 필수값 검증을 수행한 뒤
    최종적으로 TravelRequest 객체를 반환한다.

    Args:
        raw (dict[str, Any]): 사용자 원본 입력 데이터

    Returns:
        TravelRequest: 정규화 및 검증이 완료된 여행 요청 객체
    """
    # 1. raw 입력값 추출 및 기본값 설정
    region = str(raw.get("region", "")).strip()
    date = str(raw.get("date", "")).strip()
    budget_krw = int(raw.get("budget_krw", 0))
    start_time = str(raw.get("start_time", "10:00")).strip()
    end_time = str(raw.get("end_time", "20:00")).strip()
    theme = raw.get("theme", [])
    companion = str(raw.get("companion", "solo")).strip()
    weather_sensitive = bool(raw.get("weather_sensitive", True))

    # 2. 필수값 검증
    if not region:
        raise ValueError("region은 필수입니다.")
    if not date:
        raise ValueError("date는 필수입니다.")
    if budget_krw <= 0:
        raise ValueError("budget_krw는 1 이상이어야 합니다.")

    # 3. theme가 문자열 하나로 들어온 경우 리스트로 변환
    if isinstance(theme, str):
        theme = [theme]

    # 4. 최종 TravelRequest 객체 생성
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