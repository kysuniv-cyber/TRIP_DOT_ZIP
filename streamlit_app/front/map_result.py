from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from llm.graph.contracts import StateKeys
from utils.map_util import generate_map_from_state


# 프로젝트 루트를 import 경로에 추가합니다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_itinerary_dataframe(itinerary: list[dict]) -> pd.DataFrame:
    """일정 리스트를 화면 표시용 표 형태로 변환합니다."""
    rows = []

    for item in itinerary:
        rows.append(
            {
                "순서": item.get("order", ""),
                "장소명": item.get("place_name", ""),
                "도착": item.get("arrival", ""),
                "출발": item.get("departure", ""),
                "체류시간": item.get("stay_time", ""),
            }
        )

    return pd.DataFrame(rows)


def render_itinerary_map(state: dict, key_suffix: str = "confirmed") -> None:
    """일정 상태를 기반으로 지도를 생성해 본문에 표시합니다."""
    travel_map_obj = generate_map_from_state(state)

    if not travel_map_obj:
        st.warning("지도에 표시할 위치 정보가 아직 없습니다.")
        return

    folium_map = travel_map_obj.render()
    st_folium(
        folium_map,
        width="100%",
        height=520,
        key=f"itinerary_map_{key_suffix}",
    )

    count = travel_map_obj.get_place_count
    st.caption(f"총 {count}개의 장소를 일정 동선으로 표시했습니다.")


def render_confirmed_plan() -> None:
    """확정된 일정표와 지도를 나란히 보여줍니다."""
    itinerary = st.session_state.get("confirmed_itinerary") or st.session_state.get("itinerary", [])

    if not itinerary:
        st.info("확정할 일정이 아직 없습니다. 먼저 대화를 통해 일정을 만들어주세요.")
        return

    st.markdown("## 확정 일정")
    st.caption("현재 대화에서 정리된 일정표와 이동 동선을 함께 확인할 수 있습니다.")

    left_col, right_col = st.columns([1.1, 1.3])

    with left_col:
        st.markdown("### 일정표")
        schedule_df = _build_itinerary_dataframe(itinerary)
        st.dataframe(schedule_df, use_container_width=True, hide_index=True)

    with right_col:
        st.markdown("### 일정 지도")
        render_itinerary_map({StateKeys.ITINERARY: itinerary})
