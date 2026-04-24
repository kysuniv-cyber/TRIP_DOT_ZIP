"""
LLM과 tool 사이에서 사용하는 표준 입출력 형식을 정의하는 파일.

데이터 구조를 일관되게 유지할 수 있도록 도와주는 helper 역할을 하며,
입력값과 출력값이 정해진 형식에 맞게 전달되도록 지원한다.
팀원 간 인터페이스를 통일하기 위한 기준으로 사용한다.
"""

from typing import Any, Dict, Optional

# 표준 입출력 형식을 맞추기 위한 helper 역할.
def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "success",
        "data": data,
        "error": None,
    }


def error_response(message: str, code: str = "TOOL_ERROR") -> Dict[str, Any]:
    return {
        "status": "error",
        "data": None,
        "error": {
            "code": code,
            "message": message,
        },
    }