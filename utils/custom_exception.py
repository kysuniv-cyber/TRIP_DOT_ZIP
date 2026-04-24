# custom_exception.py
# LLM과 통신을 위해 메시지 양식이 통일되어서, 한번에 관리하기 위한 custom exception 파일

# 형식이 통일되어서 상속받을 부모 Error
class CommonCustomError(Exception):
    def __init__(self, code: str, message: str, tool_name: str=None):
        self.status = "error"
        self.code = code
        self.message = message
        self.tool_name = tool_name

    def error_response(self):
        """ LLM에 에러 메시지 통일 """
        return {
            "status": self.status,
            "data": None,
            "error": {
                "code": self.code,
                "message": self.message
            },
            "meta": {
                "tool_name": self.tool_name
            }
        }

# 장소 Not Found Error
# 이거 안 만들고 그냥 부모 exception에서 code랑 message랑 tool_name을 받으면 되는 거 아닌가?
class PlaceNotFoundError(CommonCustomError):
    def __init__(self, tool_name: str):
        super().__init__(
            code = "PLACE_NOT_FOUND",
            message = "해당 지역에서 추천 가능한 장소를 찾을 수 없습니다.",
            tool_name = tool_name
        )
        
# 경로 Not Found Error
class RouteNotFoundError(CommonCustomError):
    def __init__(self, origin: str, destination: str, tool_name: str = "create_schedule"):
        message = (
            f"'{origin}'에서 '{destination}'(으)로 이동할 수 있는 경로를 찾을 수 없습니다. "
            "현재 교통 상황이나 선택한 이동 수단으로는 접근이 불가능하니, "
            "해당 장소를 제외하거나 동선이 용이한 다른 장소를 새롭게 추천해 주세요."
        )
        super().__init__(
            code="ROUTE_NOT_FOUND",
            message=message,
            tool_name=tool_name
        )

class MapRenderError(CommonCustomError):
    def __init__(self, message: str, tool_name: str = "map_tool"):
        super().__init__(
            code = "MAP_RENDER_ERROR",
            message = message,
            tool_name = tool_name
        )