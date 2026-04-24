from middlewares.intent_mw import IntentRoutingMiddleware


class DummyMessage:
    def __init__(self, content):
        self.content = content


def test_before_agent_sets_weather_intent():
    middleware = IntentRoutingMiddleware(debug=False)

    state = {
        "messages": [DummyMessage("부산 이번 주말 날씨 어때?")]
    }

    result = middleware.before_agent(state, runtime=None)

    assert result is not None
    assert result["intent"] == "weather_query"
    assert result["route"] == "weather"
    assert result["confidence"] > 0


def test_before_agent_sets_schedule_intent():
    middleware = IntentRoutingMiddleware(debug=False)

    state = {
        "messages": [DummyMessage("제주도 2박 3일 일정 짜줘")]
    }

    result = middleware.before_agent(state, runtime=None)

    assert result is not None
    assert result["intent"] == "schedule_generation"
    assert result["route"] == "schedule"


def test_before_agent_sets_modify_intent():
    middleware = IntentRoutingMiddleware(debug=False)

    state = {
        "messages": [DummyMessage("그 일정 말고 다시 짜줘")]
    }

    result = middleware.before_agent(state, runtime=None)

    assert result is not None
    assert result["intent"] == "modify_request"
    assert result["route"] == "modify"