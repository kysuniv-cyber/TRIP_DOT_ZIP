from unittest.mock import patch
from services.travel_recommend_service import recommend_travel_places


@patch("services.travel_recommend_service.search_place_tool")
def test_recommend_travel_places_success(mock_search_place_tool):
    mock_search_place_tool.invoke.return_value = {
        "status": "success",
        "data": [{"name": "해운대"}]
    }

    result = recommend_travel_places("부산 여행 추천")

    assert result["status"] == "success"
    assert "data" in result
    mock_search_place_tool.invoke.assert_called_once_with({"query": "부산 여행 추천"})


@patch("services.travel_recommend_service.search_place_tool")
def test_recommend_travel_places_error(mock_search_place_tool):
    mock_search_place_tool.invoke.side_effect = Exception("검색 실패")

    result = recommend_travel_places("부산 여행 추천")

    assert result["status"] == "error"
    assert result["data"] is None
    assert "error" in result