# app.py
import streamlit as st

from llm.graph import get_openai_clients

from config import Settings
from middlewares.safety_mw import profanity_middleware, pii_middleware
from middlewares.pipeline import LLMRequest, LLMResponse, Pipeline
from test_backup.proto.constants import SYSTEM_PROMPT
from test_backup.proto.utils import (
    init_app,
    reset_session_state,
    parse_buttons,
    render_message,
    get_ai_response,
)
from middlewares.safety_mw import sanitize_pii
from services.weather_case import (
    build_weather_route_from_user_prompt,
    format_weather_recommendation,
)

# 페이지 기본 설정
st.set_page_config(
    page_title="✈️ AI 여행 추천 챗봇",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# css 적용 / 세션스테이트 초기화
init_app()

# =========================
# Safety middleware 초기화
# =========================
settings = Settings()
settings.validate()

openai_client = get_openai_clients(settings)


def fake_next(request: LLMRequest) -> LLMResponse:
    """미들웨어 체인의 base_handler. 처리된 메시지를 그대로 반환한다."""
    return LLMResponse(
        content=request.messages[-1]["content"],
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        model="gpt-4o-mini",
        finish_reason="stop",
        metadata={"meta": request.metadata},
    )


# Pipeline에 미들웨어 등록
# 실행 순서: profanity → pii → fake_next
safety_pipeline = (
    Pipeline(fake_next)
    .use(profanity_middleware(openai_client))
    .use(pii_middleware())
)


def run_safety_check(user_text: str) -> tuple[bool, str]:
    """사용자 입력에 대해 safety pipeline을 실행한다.

    Args:
        user_text (str): 사용자가 입력한 원본 텍스트

    Returns:
        tuple[bool, str]:
            (통과 여부, 처리된 텍스트 또는 차단 메시지)
    """
    req = LLMRequest(
        messages=[{"role": "user", "content": user_text}],
        model="gpt-4o-mini",
        metadata={},
    )

    try:
        res = safety_pipeline.execute(req)
        return True, res.content
    except Exception as e:
        return False, str(e)


# 사이드바
with st.sidebar:
    st.markdown("---")
    st.markdown("**모델 정보**")
    st.caption("gpt-4o-mini 사용 중")
    st.markdown("---")

    if st.button("🔄 대화 초기화", use_container_width=True):
        reset_session_state()
        st.rerun()


# 헤더
st.markdown("""
<div class="chat-header">
    <h1>✈️ <span class="header-accent">AI 여행 추천</span> 챗봇</h1>
    <p>당신의 완벽한 여행지를 함께 찾아드려요 🌍</p>
</div>
""", unsafe_allow_html=True)


# 최초 인사 메시지 생성
if not st.session_state.initialized:
    with st.spinner("트립닷집이 준비 중이에요..."):
        init_payload = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": "안녕하세요! 여행 추천을 받고 싶어요."}
        ]
        greeting_raw = get_ai_response(init_payload)

    greeting_text, greeting_buttons = parse_buttons(greeting_raw)
    st.session_state.quick_buttons = greeting_buttons
    st.session_state.initialized   = True
    st.rerun()


# 대화 히스토리 렌더링
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    render_message(msg["role"], msg["content"])
st.markdown('</div>', unsafe_allow_html=True)


# 빠른 선택 버튼
def handle_button_click(label):
    st.session_state.pending_input = label
    st.session_state.quick_buttons = []

if st.session_state.quick_buttons:
    st.markdown('<div class="quick-reply-label">빠른 선택</div>', unsafe_allow_html=True)
    btn_count = len(st.session_state.quick_buttons)
    cols      = st.columns(btn_count)

    for idx, btn_label in enumerate(st.session_state.quick_buttons):
        with cols[idx]:
            if st.button(btn_label, key="qbtn_" + str(idx)):
                handle_button_click(btn_label)
                st.rerun()

def is_weather_query(text: str) -> bool:
    keywords = [
        "날씨", "기온", "온도", "비", "눈", "우산",
        "여행 가는데", "여행가는데", "여행 예정",
        "실내", "야외"
    ]
    return any(k in text for k in keywords)


# =========================
# 유저 입력 처리
# =========================
def process_user_input(user_text: str) -> None:
    """사용자 입력을 처리한다.

    순서:
    1. safety pipeline 검사 (profanity → pii)
    2. 차단되면 안내 메시지 출력
    3. 통과되면 GPT 응답 생성
    """
    is_safe, checked_text = run_safety_check(user_text)

    # Hard 차단
    if not is_safe:
        masked_input = sanitize_pii(user_text)["sanitized_text"]

        st.session_state.messages.append({
            "role": "user",
            "content": masked_input
        })

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"⚠️ 입력이 차단되었습니다: {checked_text}"
        })

        st.session_state.quick_buttons = []
        return

    # soft 필터 반영된 텍스트 사용
    safe_user_text = checked_text

    st.session_state.messages.append({"role": "user", "content": safe_user_text})
    st.session_state.quick_buttons = []

    # =========================
    # 날씨 정보
    # =========================

    if is_weather_query(safe_user_text):
        with st.spinner("날씨를 확인하고 있어요 🌤️"):
            weather_result = build_weather_route_from_user_prompt(safe_user_text)
            reply_text = format_weather_recommendation(weather_result["result"])

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply_text
        })
        return
    # =========================

    # 시스템 프롬프트 + 전체 대화 히스토리 전달
    api_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in st.session_state.messages:
        api_payload.append({"role": m["role"], "content": m["content"]})

    with st.spinner("트립닷집이 생각 중이에요 ✈️"):
        raw_reply = get_ai_response(api_payload)

    reply_text, reply_buttons = parse_buttons(raw_reply)
    st.session_state.messages.append({"role": "assistant", "content": reply_text})
    st.session_state.quick_buttons = reply_buttons


if st.session_state.pending_input is not None:
    process_user_input(st.session_state.pending_input)
    st.session_state.pending_input = None
    st.rerun()




# 텍스트 입력창 + 전송 버튼
st.markdown("---")
col_input, col_send = st.columns([5, 1])

with col_input:
    user_input = st.text_input(
        label="",
        placeholder="여행에 대해 무엇이든 물어보세요...",
        label_visibility="collapsed",
        key="user_text_input",
    )

with col_send:
    is_send_clicked = st.button("전송 ➤", use_container_width=True)

if is_send_clicked and user_input.strip():
    process_user_input(user_input.strip())
    st.rerun()

def check_moderation(client, text: str) -> dict:
    print("=== moderation 호출됨 ===")
    print("client type:", type(client))
    print("input:", text)

    response = client.moderations.create(
        model="omni-moderation-latest",
        input=text
    )
    result = response.results[0]

    print("flagged:", result.flagged)
    print("scores:", dict(result.category_scores))

    return {
        "flagged": result.flagged,
        "categories": dict(result.categories),
        "scores": dict(result.category_scores),
    }

def is_weather_query(text: str) -> bool:
    keywords = [
        "날씨", "기온", "온도", "비", "눈", "우산",
        "여행 가는데", "여행가는데", "여행 예정",
        "실내", "야외"
    ]
    return any(k in text for k in keywords)
