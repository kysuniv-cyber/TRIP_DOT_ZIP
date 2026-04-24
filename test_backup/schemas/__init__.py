from typing import Any, Dict


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


__all__ = ["success_response", "error_response"]
