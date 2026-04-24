import pytest
from middlewares.summary_mw import (
    collect_summary_target_messages,
    format_messages_for_summary,
    count_text_chars,
)


class TestCollectSummaryTargetMessages:

    def test_system_messages_are_excluded(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "안녕"},
            {"role": "assistant", "content": "안녕하세요!"},
        ]
        result = collect_summary_target_messages(messages)
        roles = [m["role"] for m in result]
        assert "system" not in roles
        assert result == [
            {"role": "user", "content": "안녕"},
            {"role": "assistant", "content": "안녕하세요!"},
        ]

    def test_str_content_passed_through(self):
        messages = [{"role": "user", "content": "hello"}]
        result = collect_summary_target_messages(messages)
        assert result == [{"role": "user", "content": "hello"}]

    def test_list_content_extracts_text_parts(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 이미지를 설명해줘"},
                    {"type": "image_url", "image_url": {"url": "https://static.wikia.nocookie.net/pokemon/images/a/ab/%EB%A1%9C%EC%82%AC%EC%9D%98_%EB%94%B0%EB%9D%BC%ED%81%90.png/revision/latest/scale-to-width-down/1000?cb=20220519110351&path-prefix=ko"}},
                ],
            }
        ]
        result = collect_summary_target_messages(messages)
        assert len(result) == 1
        assert result[0]["content"] == "이 이미지를 설명해줘"

    def test_list_content_multiple_text_parts_joined(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "첫 번째"},
                    {"type": "text", "text": "두 번째"},
                ],
            }
        ]
        result = collect_summary_target_messages(messages)
        assert result[0]["content"] == "첫 번째 두 번째"

    def test_list_content_with_no_text_parts_excluded(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
                ],
            }
        ]
        result = collect_summary_target_messages(messages)
        assert result == []

    def test_none_content_excluded(self):
        messages = [{"role": "user", "content": None}]
        result = collect_summary_target_messages(messages)
        assert result == []

    def test_unknown_role_excluded(self):
        messages = [{"role": "tool", "content": "tool result"}]
        result = collect_summary_target_messages(messages)
        assert result == []

    def test_empty_input(self):
        assert collect_summary_target_messages([]) == []


class TestFormatMessagesForSummary:

    def test_basic_format(self):
        messages = [
            {"role": "user", "content": "안녕"},
            {"role": "assistant", "content": "반갑습니다"},
        ]
        result = format_messages_for_summary(messages)
        assert result == "[user] 안녕\n[assistant] 반갑습니다"

    def test_single_message(self):
        messages = [{"role": "user", "content": "테스트"}]
        result = format_messages_for_summary(messages)
        assert result == "[user] 테스트"

    def test_empty_input(self):
        assert format_messages_for_summary([]) == ""


class TestCountTextChars:

    def test_counts_str_content(self):
        messages = [
            {"role": "user", "content": "안녕"},       # 2
            {"role": "assistant", "content": "반갑습니다"},  # 5
        ]
        assert count_text_chars(messages) == 7

    def test_ignores_non_str_content(self):
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "hi"}]},
            {"role": "user", "content": None},
        ]
        assert count_text_chars(messages) == 0

    def test_empty_input(self):
        assert count_text_chars([]) == 0

    def test_includes_system_messages(self):
        messages = [
            {"role": "system", "content": "12345"},  # 5
            {"role": "user", "content": "ab"},        # 2
        ]
        assert count_text_chars(messages) == 7
