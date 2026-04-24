# utils.py

import re
import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from test_backup.proto.constants import OPENAI_MODEL, TEMPERATURE, MAX_TOKENS, CSS_FILE_PATH

load_dotenv()

# app.py init
def init_app():
    """ app.py 최초 진입 시 css 파일 로드/ session 기본값 세팅 """
    load_css()
    init_session_state()

# 최초 진입 시 session state 기본값 세팅
def init_session_state():
    """최초 진입 시 세션 키 없으면 기본값 세팅"""
    defaults = {
        "messages":      [],
        "quick_buttons": [],
        "initialized":   False,
        "pending_input": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# session state reset 
def reset_session_state():
    """ 대화 초기화 버튼 눌렀을 때 session state 전체 리셋 """
    st.session_state.messages      = []
    st.session_state.quick_buttons = []
    st.session_state.initialized   = False
    st.session_state.pending_input = None

# CSS 로드 및 적용
def load_css():  
    """ css 파일 로드 """
    css_file = os.path.join(os.path.dirname(__file__), CSS_FILE_PATH)
    with open(css_file, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


# 버튼 파싱
def parse_buttons(text):
    """ 버튼 파싱 """
    btn_pattern = r'\[BUTTONS:(.*?)\]'
    matched = re.search(btn_pattern, text)

    if matched is None:
        return text, []

    clean_text = re.sub(btn_pattern, '', text).strip()
    raw_options = matched.group(1).split('|')
    # 자바 stream().filter().collect() 대신 list comprehension 쓰는 게 파이썬 방식이라고 함
    button_list = [opt.strip() for opt in raw_options if opt.strip()]

    return clean_text, button_list


# 채팅 말풍선 렌더링
def render_message(role, content):
    """ 채팅 말풍선 렌더링 """
    if role == "assistant":
        avatar_icon = "🤖"
        bubble_cls  = "bot"
        wrapper_cls = ""
    else:
        avatar_icon = "🧑"
        bubble_cls  = "user"
        wrapper_cls = "user"

    html_block = f"""
    <div class="bubble-wrapper {wrapper_cls}">
        <div class="avatar {bubble_cls}">{avatar_icon}</div>
        <div class="bubble {bubble_cls}">{content}</div>
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)

# OpenAI 캐싱처리
@st.cache_resource
def get_openai_client():
    """ OPEN AI 객체 단일 객체 사용. """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)

# OpenAI API 호출
def get_ai_response(message_list):
    """ OpenAI API 호출 """
    client = get_openai_client()

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=message_list,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content

