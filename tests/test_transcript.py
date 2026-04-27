"""Tests for transcript.py."""
from pathlib import Path

from transcript import (
    extract_last_user_input,
    is_chinese_dominant,
    read_transcript,
)


def test_read_transcript_missing_file_returns_empty(tmp_path: Path):
    assert read_transcript(str(tmp_path / "nope.jsonl")) == []


def test_read_transcript_skips_malformed_lines(tmp_path: Path):
    p = tmp_path / "t.jsonl"
    p.write_text('{"valid": 1}\nnot-json\n{"valid": 2}\n')
    assert read_transcript(str(p)) == [{"valid": 1}, {"valid": 2}]


def test_extract_last_user_input_string_content():
    messages = [
        {"type": "user", "message": {"content": "first"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "ans"}]}},
        {"type": "user", "message": {"content": "second"}},
    ]
    assert extract_last_user_input(messages) == "second"


def test_extract_last_user_input_skips_tool_result():
    messages = [
        {"type": "user", "message": {"content": "real input"}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
    ]
    assert extract_last_user_input(messages) == "real input"


def test_extract_last_user_input_text_blocks_in_list():
    messages = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "hello world"}]}},
    ]
    assert extract_last_user_input(messages) == "hello world"


def test_extract_last_user_input_no_user_returns_empty():
    messages = [{"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}]}}]
    assert extract_last_user_input(messages) == ""


def test_is_chinese_dominant_pure_chinese():
    assert is_chinese_dominant("你好世界") is True


def test_is_chinese_dominant_pure_english():
    assert is_chinese_dominant("hello world") is False


def test_is_chinese_dominant_mixed_majority_chinese():
    # 5 Chinese chars + "PR" (2) → 5/(5+2) ≈ 71% > 50%
    assert is_chinese_dominant("把这个PR放一放") is True


def test_is_chinese_dominant_mixed_majority_english():
    # 1 Chinese char + 19 English chars → 5%
    assert is_chinese_dominant("the quick brown 狐") is False


def test_is_chinese_dominant_empty_returns_false():
    assert is_chinese_dominant("") is False


def test_is_chinese_dominant_ignores_whitespace_and_punct():
    # whitespace and punctuation are not counted in either side
    assert is_chinese_dominant("你好 world!") is False  # 2 Chinese vs 5 English


def test_extract_last_user_input_from_fixture():
    fixture = Path(__file__).parent / "fixtures" / "sample_cc_transcript.jsonl"
    messages = read_transcript(str(fixture))
    assert extract_last_user_input(messages) == "Help me debug this query"
