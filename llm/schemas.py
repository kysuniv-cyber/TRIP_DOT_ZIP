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