from services.intent_service import classify_intent_by_rule


def test_weather_intent():
    result = classify_intent_by_rule("부산 이번 주말 날씨 어때?")
    assert result["intent"] == "weather_query"
    assert result["route"] == "weather"


def test_schedule_intent():
    result = classify_intent_by_rule("제주도 2박 3일 일정 짜줘")
    assert result["intent"] == "schedule_generation"
    assert result["route"] == "schedule"


def test_modify_intent():
    result = classify_intent_by_rule("그 일정 말고 당일치기로 바꿔줘")
    assert result["intent"] == "modify_request"
    assert result["route"] == "modify"


def test_place_search_intent():
    result = classify_intent_by_rule("강릉 카페 추천해줘")
    assert result["intent"] == "place_search"
    assert result["route"] == "place"


def test_travel_recommendation_intent():
    result = classify_intent_by_rule("국내 여행 추천해줘")
    assert result["intent"] == "travel_recommendation"
    assert result["route"] == "travel"


def test_general_chat_intent():
    result = classify_intent_by_rule("안녕")
    assert result["intent"] == "general_chat"
    assert result["route"] == "chat"