"""Tests for llm.py — mocks urllib.request.urlopen.

Covers both json_mode capabilities:
  - schema mode (openrouter): server-side strict json_schema enforcement
  - object mode (deepseek):    json_object + post-validate required keys
"""
import json
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

import pytest

from llm import chat_json, LLMError, PROVIDERS


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["greeting"],
    "properties": {"greeting": {"type": "string"}},
}


def _mock_response(content_json: str):
    envelope = {"choices": [{"message": {"content": content_json}}]}
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps(envelope).encode("utf-8")
    return mock


# ---------- shared error paths ----------


def test_unknown_provider_raises():
    with pytest.raises(LLMError, match="unknown provider"):
        chat_json(
            provider="nope",
            system_prompt="x", user_message="x",
            api_key="k", json_schema=SCHEMA,
        )


def test_missing_api_key_raises():
    with pytest.raises(LLMError, match="api_key is required"):
        chat_json(
            provider="openrouter",
            system_prompt="x", user_message="x",
            api_key="", json_schema=SCHEMA,
        )


def test_http_error_raises():
    err = HTTPError("https://x", 500, "boom", {}, None)
    err.fp = None
    with patch("llm.urlopen", side_effect=err):
        with pytest.raises(LLMError, match="HTTP 500"):
            chat_json(
                provider="openrouter",
                system_prompt="x", user_message="x",
                api_key="k", json_schema=SCHEMA,
            )


def test_url_error_raises():
    with patch("llm.urlopen", side_effect=URLError("timeout")):
        with pytest.raises(LLMError, match="network error"):
            chat_json(
                provider="deepseek",
                system_prompt="x", user_message="x",
                api_key="k", json_schema=SCHEMA,
            )


def test_invalid_content_raises():
    with patch("llm.urlopen", return_value=_mock_response("not-json")):
        with pytest.raises(LLMError, match="not valid JSON"):
            chat_json(
                provider="deepseek",
                system_prompt="x", user_message="x",
                api_key="k", json_schema=SCHEMA,
            )


def test_empty_content_raises():
    with patch("llm.urlopen", return_value=_mock_response("")):
        with pytest.raises(LLMError, match="empty content"):
            chat_json(
                provider="deepseek",
                system_prompt="x", user_message="x",
                api_key="k", json_schema=SCHEMA,
            )


# ---------- schema mode (openrouter) ----------


def test_openrouter_happy_path_uses_strict_schema():
    captured = {}

    def capture_request(req, timeout=None):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        return _mock_response('{"greeting": "hi"}')

    with patch("llm.urlopen", side_effect=capture_request):
        result = chat_json(
            provider="openrouter",
            system_prompt="be friendly",
            user_message="say hi",
            api_key="test-key",
            json_schema=SCHEMA,
        )

    assert result == {"greeting": "hi"}
    rf = captured["payload"]["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == SCHEMA
    assert captured["url"] == PROVIDERS["openrouter"]["endpoint"]
    # Provider-specific extra headers must be sent.
    assert captured["headers"].get("Http-referer") == "https://github.com/wanmaoor/english-capture"
    assert captured["headers"].get("X-title") == "english-capture"


def test_openrouter_skips_post_validation():
    """Schema-mode trusts the server. Even if `greeting` is missing the
    adapter does not raise — that's the server's job."""
    with patch("llm.urlopen", return_value=_mock_response('{"other": "x"}')):
        out = chat_json(
            provider="openrouter",
            system_prompt="x", user_message="x",
            api_key="k", json_schema=SCHEMA,
        )
    assert out == {"other": "x"}


def test_openrouter_default_model():
    captured = {}

    def capture_request(req, timeout=None):
        captured.update(json.loads(req.data.decode("utf-8")))
        return _mock_response('{"greeting": "hi"}')

    with patch("llm.urlopen", side_effect=capture_request):
        chat_json(
            provider="openrouter",
            system_prompt="x", user_message="x",
            api_key="k", json_schema=SCHEMA,
        )

    assert captured["model"] == PROVIDERS["openrouter"]["default_model"]


# ---------- object mode (deepseek) ----------


def test_deepseek_happy_path_uses_json_object():
    captured = {}

    def capture_request(req, timeout=None):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["url"] = req.full_url
        return _mock_response('{"greeting": "hi"}')

    with patch("llm.urlopen", side_effect=capture_request):
        result = chat_json(
            provider="deepseek",
            system_prompt="output JSON",
            user_message="say hi",
            api_key="test-key",
            json_schema=SCHEMA,
        )

    assert result == {"greeting": "hi"}
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["url"] == "https://api.deepseek.com/chat/completions"


def test_deepseek_validates_required_keys():
    """Object-mode does NOT have server-side schema, so adapter validates."""
    with patch("llm.urlopen", return_value=_mock_response('{"other": 1}')):
        with pytest.raises(LLMError, match="missing required keys"):
            chat_json(
                provider="deepseek",
                system_prompt="x", user_message="x",
                api_key="k", json_schema=SCHEMA,
            )


def test_deepseek_default_model_is_v4_flash():
    captured = {}

    def capture_request(req, timeout=None):
        captured.update(json.loads(req.data.decode("utf-8")))
        return _mock_response('{"greeting": "hi"}')

    with patch("llm.urlopen", side_effect=capture_request):
        chat_json(
            provider="deepseek",
            system_prompt="x", user_message="x",
            api_key="k", json_schema=SCHEMA,
        )

    assert captured["model"] == "deepseek-v4-flash"


def test_explicit_model_overrides_default():
    captured = {}

    def capture_request(req, timeout=None):
        captured.update(json.loads(req.data.decode("utf-8")))
        return _mock_response('{"greeting": "hi"}')

    with patch("llm.urlopen", side_effect=capture_request):
        chat_json(
            provider="deepseek",
            system_prompt="x", user_message="x",
            api_key="k", json_schema=SCHEMA,
            model="deepseek-v4-pro",
        )

    assert captured["model"] == "deepseek-v4-pro"
