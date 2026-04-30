"""Integration tests for add_card.py CLI."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import add_card


FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parent.parent


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def fake_config(tmp_vault: Path, monkeypatch, tmp_path: Path):
    """Patch add_card to use a tmp config + tmp vault."""
    cfg = {
        "openrouter_api_key": "test-key",
        "openrouter_model": "qwen/qwen3-235b-a22b-2507",
        "vault_path": str(tmp_vault),
        "timeout_seconds": 30,
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    monkeypatch.setenv("ENGLISH_CAPTURE_CONFIG", str(cfg_path))
    return cfg


def test_word_type_writes_card(fake_config, tmp_vault: Path, capsys):
    fake_response = _load_fixture("sample_qwen_word_response.json")
    with patch("add_card.chat_json", return_value=fake_response):
        rc = add_card.main([
            "--type", "w",
            "--phrase", "cardinality estimation",
            "--context", "This query suffers from cardinality estimation errors on the join.",
        ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "✓ saved" in out
    assert "noun/cardinality-estimation.md" in out
    card = tmp_vault / "20-Areas" / "英语" / "noun" / "cardinality-estimation.md"
    assert card.exists()


def test_word_dedup_appends_example(fake_config, tmp_vault: Path, capsys):
    fake_response = _load_fixture("sample_qwen_word_response.json")
    # First call: write
    with patch("add_card.chat_json", return_value=fake_response):
        add_card.main([
            "--type", "w", "--phrase", "cardinality estimation",
            "--context", "cardinality estimation errors caused slow joins.",
        ])
    capsys.readouterr()
    # Second call: should hit dedup path (no Qwen call expected)
    with patch("add_card.chat_json") as mock_llm:
        rc = add_card.main([
            "--type", "w", "--phrase", "cardinality estimation",
            "--context", "poor cardinality estimation led to a bad plan.",
        ])
        mock_llm.assert_not_called()
    assert rc == 0
    out = capsys.readouterr().out
    assert "↳ appended example" in out
    card = tmp_vault / "20-Areas" / "英语" / "noun" / "cardinality-estimation.md"
    assert "poor cardinality estimation" in card.read_text()


def test_sentence_type_writes_card(fake_config, tmp_vault: Path, capsys):
    fake_response = _load_fixture("sample_qwen_sentence_response.json")
    with patch("add_card.chat_json", return_value=fake_response):
        rc = add_card.main([
            "--type", "s",
            "--phrase", "Despite the migration succeeding, downstream consumers reported stale reads.",
            "--context", "discussing failed migrations",
        ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "✓ saved" in out
    assert "sentence/" in out


def test_expression_type_writes_card(fake_config, tmp_vault: Path, capsys):
    fake_response = _load_fixture("sample_qwen_expression_response.json")
    with patch("add_card.chat_json", return_value=fake_response):
        rc = add_card.main([
            "--type", "e",
            "--phrase", "这个 PR 我先放一放",
            "--context", "",
        ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "✓ saved" in out
    assert "expression/" in out


def test_word_context_without_phrase_is_dropped(fake_config, tmp_vault: Path, capsys):
    """Context that doesn't contain the phrase should not appear in the card."""
    fake_response = _load_fixture("sample_qwen_word_response.json")
    with patch("add_card.chat_json", return_value=fake_response):
        rc = add_card.main([
            "--type", "w",
            "--phrase", "cardinality estimation",
            "--context", "some unrelated sentence about databases.",
        ])
    assert rc == 0
    card = tmp_vault / "20-Areas" / "英语" / "noun" / "cardinality-estimation.md"
    text = card.read_text()
    assert "unrelated sentence" not in text
    assert "原文上下文" not in text


def test_expression_rejects_non_chinese(fake_config, capsys):
    rc = add_card.main([
        "--type", "e",
        "--phrase", "park this PR for a bit",
        "--context", "",
    ])
    assert rc != 0
    out = capsys.readouterr().out
    assert "expects Chinese" in out


def test_llm_failure_queues_and_reports(fake_config, capsys, tmp_path: Path, monkeypatch):
    queue_path = tmp_path / "queue.json"
    monkeypatch.setenv("ENGLISH_CAPTURE_QUEUE", str(queue_path))
    from llm import LLMError
    with patch("add_card.chat_json", side_effect=LLMError("timeout")):
        rc = add_card.main([
            "--type", "w", "--phrase", "novel-word",
            "--context", "...",
        ])
    assert rc != 0
    out = capsys.readouterr().out
    assert "queued" in out
    assert queue_path.exists()
    queued = json.loads(queue_path.read_text())
    assert any(q["phrase"] == "novel-word" for q in queued)


def test_unknown_type_errors(fake_config, capsys):
    with pytest.raises(SystemExit):
        add_card.main(["--type", "x", "--phrase", "foo", "--context", ""])


def test_cli_runnable_via_subprocess(fake_config, tmp_path: Path):
    """Smoke test: the script's __main__ guard is wired up correctly."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "add_card.py")],
        capture_output=True, text=True,
    )
    # No args → argparse prints usage and exits non-zero
    assert result.returncode != 0
