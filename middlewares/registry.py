"""
registry.py

프로젝트에서 사용하는 tool(함수)들을 이름으로 등록하고 조회하기 위한
Tool Registry 모듈이다.

주요 기능:
- tool 함수를 문자열 이름으로 등록
- 등록된 tool을 이름으로 조회
- 특정 tool의 등록 여부 확인

동작 방식:
1. register()로 tool 이름과 함수 객체를 등록한다.
2. get()으로 이름에 해당하는 함수를 조회한다.
3. has()로 특정 이름의 tool 등록 여부를 확인한다.

이 모듈은 tool 실행 관리, dispatcher, executor 등
상위 서비스에서 공통으로 사용할 수 있도록 설계되었다.
"""

from typing import Callable, Any


# 등록된 tool들을 중앙에서 관리하는 클래스
class ToolRegistry:
    """tool 함수를 이름으로 등록하고 조회하는 레지스트리 클래스.

    문자열 이름과 실제 함수 객체를 매핑하여,
    tool을 중앙에서 일관되게 관리할 수 있도록 한다.
    """

    def __init__(self) -> None:
        """ToolRegistry를 초기화한다.

        내부적으로 tool 이름과 함수 객체를 저장할
        빈 딕셔너리를 생성한다.

        Args:
            없음

        Returns:
            None: 초기화만 수행한다.
        """
        # 내부 tool 저장소 초기화
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        """tool 함수를 이름으로 등록한다.

        전달받은 이름을 key로, 함수 객체를 value로 하여
        내부 레지스트리에 저장한다.

        Args:
            name (str): 등록할 tool 이름
            fn (Callable[..., Any]): 등록할 함수 객체

        Returns:
            None: 등록만 수행한다.
        """
        # tool 이름과 함수 객체를 registry에 등록
        self._tools[name] = fn

    def get(self, name: str) -> Callable[..., Any]:
        """이름으로 등록된 tool 함수를 조회한다.

        지정한 이름의 tool이 레지스트리에 존재하면 해당 함수를 반환하고,
        없으면 KeyError를 발생시킨다.

        Args:
            name (str): 조회할 tool 이름

        Returns:
            Callable[..., Any]: 등록된 함수 객체
        """
        # 이름으로 등록된 tool 함수 조회
        if name not in self._tools:
            raise KeyError(f"등록되지 않은 tool: {name}")
        return self._tools[name]

    def has(self, name: str) -> bool:
        """특정 이름의 tool 등록 여부를 확인한다.

        Args:
            name (str): 확인할 tool 이름

        Returns:
            bool: 등록되어 있으면 True, 아니면 False
        """
        # 특정 tool이 등록되어 있는지 확인
        return name in self._tools