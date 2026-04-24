from test_backup.tools import (
    TOOLS,
    get_weather_tool,
    make_schedule_tool,
    modify_schedule_tool,
    recommend_travel_tool,
)

def test_tools_import():
    assert TOOLS is not None
    assert get_weather_tool is not None
    assert make_schedule_tool is not None
    assert modify_schedule_tool is not None
    assert recommend_travel_tool is not None