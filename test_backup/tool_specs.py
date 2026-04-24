TOOLS = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "특정 지역과 날짜의 날씨 예보를 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "예: 서울, 부산, 제주"
                },
                "date": {
                    "type": "string",
                    "description": "YYYY-MM-DD 형식"
                }
            },
            "required": ["destination", "date"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "search_places",
        "description": "지역과 테마를 기준으로 장소를 검색한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "검색할 지역명"
                },
                "theme": {
                    "type": "string",
                    "description": "장소 테마"
                },
                "count": {
                    "type": "integer",
                    "description": "반환할 장소 수"
                }
            },
            "required": ["region", "theme", "count"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "build_schedule",
        "description": "추천된 장소들을 바탕으로 하루 일정을 생성한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "string",
                    "description": "일정 시작 시각 (HH:MM 형식)"
                },
                "end_time": {
                    "type": "string",
                    "description": "일정 종료 시각 (HH:MM 형식)"
                },
                "places": {
                    "type": "array",
                    "description": "방문할 장소 리스트",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "장소 이름"
                            },
                            "lat": {
                                "type": "number",
                                "description": "위도"
                            },
                            "lng": {
                                "type": "number",
                                "description": "경도"
                            }
                        },
                        "required": ["name", "lat", "lng"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["start_time", "end_time", "places"],
            "additionalProperties": False
        },
        "strict": True
    }
]