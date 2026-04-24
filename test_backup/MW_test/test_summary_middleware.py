import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field

from middlewares.summary_mw import conversation_summary_middleware


# ── 테스트용 LLMRequest / LLMResponse (pipeline.py 의존성 없이 독립 실행 가능) ──

@dataclass
class LLMRequest:
    messages: list[dict]
    model: str = "gpt-4o"
    metadata: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    usage: dict = field(default_factory=dict)


def make_request(messages: list[dict]) -> LLMRequest:
    return LLMRequest(messages=messages)


def dummy_next(response_text: str = "응답"):
    """next_ 함수를 흉내내는 더미 핸들러."""
    def _next(request: LLMRequest) -> LLMResponse:
        return LLMResponse(content=response_text)
    return _next


def make_long_messages(n: int = 10, chars_per_msg: int = 300) -> list[dict]:
    """트리거 조건을 넘기는 긴 메시지 목록 생성."""
    messages = [{"role": "system", "content": "You are helpful."}]
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": "가" * chars_per_msg})
    return messages


# ── 트리거 조건 테스트 ──────────────────────────────────────────────────────────

class TestTriggerCondition:

    def test_skips_when_chars_below_threshold(self):
        """문자 수가 임계값 미만이면 요약을 건너뛴다 (메시지 수는 충분해도)."""
        client = MagicMock()
        # trigger_char_count를 아주 높게 설정 → 글자 수 조건 미달
        mw = conversation_summary_middleware(client, trigger_char_count=99999, keep_last_n=2)

        messages = [
            {"role": "user", "content": "짧은 메시지"},
            {"role": "assistant", "content": "네"},
        ] * 10  # 메시지 수는 keep_last_n 초과, 글자 수만 미달

        request = make_request(messages)
        mw(request, dummy_next())

        client.chat.completions.create.assert_not_called()
        assert request.metadata["conversation_summarized"] is False

    def test_skips_when_message_count_below_keep_last_n(self):
        """메시지 수가 keep_last_n 이하이면 요약을 건너뛴다."""
        client = MagicMock()
        mw = conversation_summary_middleware(client, trigger_char_count=10, keep_last_n=4)

        messages = [{"role": "user", "content": "가" * 100}] * 3  # keep_last_n=4 미만

        request = make_request(messages)
        mw(request, dummy_next())

        client.chat.completions.create.assert_not_called()
        assert request.metadata["conversation_summarized"] is False

    def test_triggers_when_both_conditions_met(self):
        """문자 수와 메시지 수 모두 조건을 넘으면 요약을 실행한다."""
        client = MagicMock()
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="요약 결과"))]
        )

        mw = conversation_summary_middleware(client, trigger_char_count=100, keep_last_n=2)
        messages = make_long_messages(n=6, chars_per_msg=50)

        request = make_request(messages)
        mw(request, dummy_next())

        client.chat.completions.create.assert_called_once()
        assert request.metadata["conversation_summarized"] is True


# ── 메시지 재구성 테스트 ────────────────────────────────────────────────────────

class TestMessageReconstruction:

    @patch("middlewares.summary_mw.generate_summary", return_value="요약 내용")
    def test_original_system_message_preserved(self, mock_summary):
        """원본 system 메시지가 재구성 후에도 맨 앞에 위치해야 한다."""
        client = MagicMock()
        mw = conversation_summary_middleware(client, trigger_char_count=100, keep_last_n=2)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            *[{"role": "user" if i % 2 == 0 else "assistant", "content": "가" * 60}
              for i in range(6)],
        ]

        request = make_request(messages)
        mw(request, dummy_next())

        assert request.messages[0]["role"] == "system"
        assert request.messages[0]["content"] == "You are a helpful assistant."

    @patch("middlewares.summary_mw.generate_summary", return_value="요약된 내용입니다")
    def test_summary_message_inserted_after_system(self, mock_summary):
        """요약 system 메시지가 원본 system 바로 다음에 삽입된다."""
        client = MagicMock()
        mw = conversation_summary_middleware(client, trigger_char_count=100, keep_last_n=2)

        messages = [
            {"role": "system", "content": "페르소나"},
            *[{"role": "user", "content": "가" * 60}] * 6,
        ]

        request = make_request(messages)
        mw(request, dummy_next())

        assert request.messages[1]["role"] == "system"
        assert "[이전 대화 요약]" in request.messages[1]["content"]
        assert "요약된 내용입니다" in request.messages[1]["content"]

    @patch("middlewares.summary_mw.generate_summary", return_value="요약 내용")
    def test_recent_messages_kept(self, mock_summary):
        """keep_last_n 개의 최근 메시지가 유지된다."""
        client = MagicMock()
        keep_last_n = 3
        mw = conversation_summary_middleware(client, trigger_char_count=100, keep_last_n=keep_last_n)

        user_messages = [{"role": "user", "content": f"메시지{i}" + "가" * 50} for i in range(8)]
        request = make_request(user_messages)
        original_last_n = user_messages[-keep_last_n:]

        mw(request, dummy_next())

        # system(원본) + system(요약) + recent 3개
        recent_in_result = [m for m in request.messages if m.get("role") != "system"]
        assert recent_in_result == original_last_n

    @patch("middlewares.summary_mw.generate_summary", return_value="")
    def test_empty_summary_does_not_modify_messages(self, mock_summary):
        """요약 결과가 빈 문자열이면 messages를 수정하지 않는다."""
        client = MagicMock()
        mw = conversation_summary_middleware(client, trigger_char_count=100, keep_last_n=2)

        original_messages = [{"role": "user", "content": "가" * 60}] * 6
        request = make_request(original_messages[:])

        mw(request, dummy_next())

        assert request.metadata["conversation_summarized"] is False


# ── 에러 처리 테스트 ────────────────────────────────────────────────────────────

class TestErrorHandling:

    @patch("middlewares.summary_mw.generate_summary", side_effect=Exception("API timeout"))
    def test_fallback_on_summary_exception(self, mock_summary):
        """요약 API 실패 시 원본 메시지로 폴백하고 예외를 전파하지 않는다."""
        client = MagicMock()
        mw = conversation_summary_middleware(client, trigger_char_count=100, keep_last_n=2)

        original_messages = [{"role": "user", "content": "가" * 60}] * 6
        request = make_request(original_messages[:])
        original_copy = request.messages[:]

        # 예외가 전파되지 않아야 한다
        response = mw(request, dummy_next())

        assert response is not None
        assert request.metadata["conversation_summarized"] is False
        assert request.messages == original_copy  # 메시지 원본 유지

    @patch("middlewares.summary_mw.generate_summary", side_effect=Exception("rate limit"))
    def test_next_is_called_even_on_summary_failure(self, mock_summary):
        """요약 실패해도 next_ 핸들러는 반드시 호출된다."""
        client = MagicMock()
        mw = conversation_summary_middleware(client, trigger_char_count=100, keep_last_n=2)

        messages = [{"role": "user", "content": "가" * 60}] * 6
        request = make_request(messages)

        next_called = {"called": False}

        def tracking_next(req):
            next_called["called"] = True
            return LLMResponse(content="ok")

        mw(request, tracking_next)
        assert next_called["called"] is True


# ── metadata 테스트 ─────────────────────────────────────────────────────────────

class TestMetadata:

    @patch("middlewares.summary_mw.generate_summary", return_value="요약 내용")
    def test_metadata_set_on_success(self, mock_summary):
        client = MagicMock()
        mw = conversation_summary_middleware(client, trigger_char_count=100, keep_last_n=2)

        messages = [{"role": "user", "content": "가" * 60}] * 6
        request = make_request(messages)
        mw(request, dummy_next())

        assert request.metadata["conversation_summarized"] is True
        assert request.metadata["conversation_summary"] == "요약 내용"

    def test_metadata_set_on_skip(self):
        client = MagicMock()
        mw = conversation_summary_middleware(client, trigger_char_count=9999, keep_last_n=4)

        messages = [{"role": "user", "content": "짧음"}]
        request = make_request(messages)
        mw(request, dummy_next())

        assert request.metadata["conversation_summarized"] is False
        assert request.metadata["conversation_summary"] == ""
