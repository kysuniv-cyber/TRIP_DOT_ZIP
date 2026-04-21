from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from streamlit_app.back.session_state import init_state
from streamlit_app.back.chat_logic import initialize_greeting
from streamlit_app.front.ui import (
    load_css,
    render_profile_setup,
    render_left_panel,
    render_chat_area,
)



st.set_page_config(
    page_title="트립닷집",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
init_state()

if not st.session_state.get("user_profile_completed"):
    render_profile_setup()
    st.stop()

initialize_greeting()

if st.session_state.pending_input is not None:
    pending = st.session_state.pending_input
    st.session_state.pending_input = None
    from streamlit_app.back.chat_logic import process_user_input
    process_user_input(pending)
    st.rerun()

with st.sidebar:
    render_left_panel()

render_chat_area()