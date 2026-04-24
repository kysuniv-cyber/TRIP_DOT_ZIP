from middlewares.intent_mw import IntentRoutingMiddleware


class DummyTool:
    def __init__(self, name):
        self.name = name


def test_before_model_selects_weather_tools():
    weather_tool = DummyTool("get_weather")
    place_tool = DummyTool("search_places")

    middleware = IntentRoutingMiddleware(
        weather_tools=[weather_tool],
        place_tools=[place_tool],
        debug=False,
    )

    state = {
        "route": "weather"
    }

    result = middleware.before_model(state, runtime=None)

    assert result is not None
    assert "tools" in result
    assert len(result["tools"]) == 1
    assert result["tools"][0].name == "get_weather"


def test_before_model_selects_place_tools():
    weather_tool = DummyTool("get_weather")
    place_tool = DummyTool("search_places")

    middleware = IntentRoutingMiddleware(
        weather_tools=[weather_tool],
        place_tools=[place_tool],
        debug=False,
    )

    state = {
        "route": "place"
    }

    result = middleware.before_model(state, runtime=None)

    assert result is not None
    assert len(result["tools"]) == 1
    assert result["tools"][0].name == "search_places"