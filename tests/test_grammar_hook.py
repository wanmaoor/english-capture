"""Tests for grammar_hook.py."""
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import grammar_hook


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_env(tmp_vault: Path, tmp_path: Path, monkeypatch):
    cfg = {
        "openrouter_api_key": "test-key",
        "openrouter_model": "qwen/qwen3-235b-a22b-2507",
        "vault_path": str(tmp_vault),
        "timeout_seconds": 30,
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    monkeypatch.setenv("ENGLISH_CAPTURE_CONFIG", str(cfg_path))
    monkeypatch.setenv("ENGLISH_CAPTURE_QUEUE", str(tmp_path / "queue.json"))
    monkeypatch.setenv("ENGLISH_CAPTURE_LOGS", str(tmp_path / "logs"))
    return tmp_path


def _stdin_event(content: dict) -> io.StringIO:
    return io.StringIO(json.dumps(content))


def _make_transcript(tmp_path: Path, last_user_input: str) -> Path:
    """Make a one-message transcript file."""
    p = tmp_path / "transcript.jsonl"
    p.write_text(json.dumps({"type": "user", "message": {"content": last_user_input}}) + "\n")
    return p


def test_skips_non_stop_event(fake_env, tmp_path: Path, monkeypatch):
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "PreToolUse"}))
    rc = grammar_hook.main()
    assert rc == 0


def test_skips_when_transcript_missing(fake_env, monkeypatch):
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": "/tmp/nope.jsonl"}))
    rc = grammar_hook.main()
    assert rc == 0


def test_skips_slash_command_input(fake_env, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "/eng w 'foo'")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    with patch("grammar_hook.qwen") as mock_qwen:
        rc = grammar_hook.main()
        mock_qwen.assert_not_called()
    assert rc == 0


def test_skips_short_input(fake_env, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "yes do it")  # 3 words
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    with patch("grammar_hook.qwen") as mock_qwen:
        rc = grammar_hook.main()
        mock_qwen.assert_not_called()
    assert rc == 0


def test_skips_chinese_input(fake_env, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "请帮我修复这个数据库查询的性能问题")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    with patch("grammar_hook.qwen") as mock_qwen:
        rc = grammar_hook.main()
        mock_qwen.assert_not_called()
    assert rc == 0


def test_writes_grammar_card_when_error(fake_env, tmp_vault: Path, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "I have went to the store yesterday morning.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    fake = json.loads((FIXTURES / "sample_qwen_grammar_response.json").read_text())
    with patch("grammar_hook.qwen", return_value=fake):
        rc = grammar_hook.main()
    assert rc == 0
    grammar_dir = tmp_vault / "20-Areas" / "英语" / "grammar"
    cards = list(grammar_dir.glob("*.md"))
    assert len(cards) == 1
    assert "Corrected:" in cards[0].read_text()


def test_no_card_when_no_error(fake_env, tmp_vault: Path, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "I went to the store yesterday morning successfully.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    no_error_response = {
        "has_error": False,
        "original": "I went to the store yesterday morning successfully.",
        "corrected": "I went to the store yesterday morning successfully.",
        "errors": [],
    }
    with patch("grammar_hook.qwen", return_value=no_error_response):
        rc = grammar_hook.main()
    assert rc == 0
    grammar_dir = tmp_vault / "20-Areas" / "英语" / "grammar"
    assert not list(grammar_dir.glob("*.md"))


def test_skips_already_checked(fake_env, tmp_vault: Path, tmp_path: Path, monkeypatch):
    # Pre-populate a grammar card for the same input (normalized)
    from vault import write_grammar_card
    write_grammar_card(
        {"original": "I have went to the store yesterday morning.",
         "corrected": "I went to the store yesterday morning.",
         "errors": []},
        tmp_vault, source="auto_grammar",
    )
    t = _make_transcript(tmp_path, "I have went to the store yesterday morning.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    with patch("grammar_hook.qwen") as mock_qwen:
        rc = grammar_hook.main()
        mock_qwen.assert_not_called()
    assert rc == 0


def test_queues_on_openrouter_failure(fake_env, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "I have went to the store yesterday morning.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    from openrouter import OpenRouterError
    with patch("grammar_hook.qwen", side_effect=OpenRouterError("timeout")):
        rc = grammar_hook.main()
    assert rc == 0  # hook always returns 0 to not block CC
    queue_path = Path(os.environ["ENGLISH_CAPTURE_QUEUE"])
    assert queue_path.exists()
    queued = json.loads(queue_path.read_text())
    assert len(queued) == 1


def test_drains_queue_first(fake_env, tmp_path: Path, tmp_vault: Path, monkeypatch):
    queue_path = Path(os.environ["ENGLISH_CAPTURE_QUEUE"])
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps([
        {"type": "grammar", "input": "I am go to school yesterday morning."}
    ]))
    t = _make_transcript(tmp_path, "I has been working here since 2020 happily.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    fake = json.loads((FIXTURES / "sample_qwen_grammar_response.json").read_text())
    with patch("grammar_hook.qwen", return_value=fake) as mock_qwen:
        rc = grammar_hook.main()
        # Once for queue drain, once for current input
        assert mock_qwen.call_count == 2
    assert rc == 0
    # Queue should be empty after successful drain
    if queue_path.exists():
        assert json.loads(queue_path.read_text()) == []
