# common.py
# 공통.. 이라고 할 게 뭐가 있으려나.
import re
import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from constants import CSS_FILE_PATH

# app.py init
def init_app():
    """ app.py 최초 진입 시 css 파일 로드/ session 기본값 세팅 """
    load_css()
    init_session_state()

# 최초 진입 시 session state 기본값 세팅
def init_session_state():
    """ 최초 진입 시 세션 키 없으면 기본값 세팅 """
    defaults = {
        "map_obj": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# session state reset 
def reset_session_state():
    """ 대화 초기화 버튼 눌렀을 때 session state 전체 리셋 """
    st.session_state.map_obj        = None

# CSS 로드 및 적용
def load_css():  
    """ css 파일 로드 """
    css_file = os.path.join(os.path.dirname(__file__), CSS_FILE_PATH)
    with open(css_file, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)