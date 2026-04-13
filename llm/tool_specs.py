TOOLS = [
    {
        "type": "function",
        "name": "get_weather_forecast",
        "description": "특정 지역과 날짜의 날씨 예보를 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "예: 서울, 부산, 제주"},
                "date": {"type": "string", "description": "YYYY-MM-DD 형식"}
            },
            "required": ["region", "date"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "search_places",
        "description": "지역, 테마, 예산, 날씨 조건에 맞는 장소 목록을 검색한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "theme": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "예: cafe, museum, indoor, photo, local_food"
                },
                "budget_krw": {"type": "integer"},
                "weather_condition": {"type": "string"},
                "count": {"type": "integer", "default": 10}
            },
            "required": ["region", "theme", "budget_krw", "weather_condition"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "build_day_schedule",
        "description": "장소 목록과 조건을 바탕으로 하루 여행 일정을 생성한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "region": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "budget_krw": {"type": "integer"},
                "places": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "weather_summary": {"type": "string"}
            },
            "required": [
                "date", "region", "start_time", "end_time",
                "budget_krw", "places", "weather_summary"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
]