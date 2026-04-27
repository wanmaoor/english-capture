"""Tests for openrouter.py — mocks urllib.request.urlopen."""
import json
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

import pytest

from openrouter import qwen, OpenRouterError, DEFAULT_MODEL


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["greeting"],
    "properties": {"greeting": {"type": "string"}},
}


def _mock_response(content_json: str):
    """Build a mock urlopen response containing the given message.content payload."""
    envelope = {"choices": [{"message": {"content": content_json}}]}
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps(envelope).encode("utf-8")
    return mock


def test_qwen_happy_path():
    with patch("openrouter.urlopen", return_value=_mock_response('{"greeting": "hi"}')):
        result = qwen(
            system_prompt="be friendly",
            user_message="say hi",
            json_schema=SCHEMA,
            api_key="test-key",
        )
    assert result == {"greeting": "hi"}


def test_qwen_missing_api_key_raises():
    with pytest.raises(OpenRouterError, match="api_key is required"):
        qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="")


def test_qwen_http_error_raises():
    err = HTTPError("https://x", 500, "boom", {}, None)
    err.fp = None
    with patch("openrouter.urlopen", side_effect=err):
        with pytest.raises(OpenRouterError, match="HTTP 500"):
            qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")


def test_qwen_url_error_raises():
    with patch("openrouter.urlopen", side_effect=URLError("timeout")):
        with pytest.raises(OpenRouterError, match="network error"):
            qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")


def test_qwen_invalid_envelope_raises():
    with patch("openrouter.urlopen", return_value=_mock_response("not-json")):
        with pytest.raises(OpenRouterError, match="not valid JSON"):
            qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")


def test_qwen_uses_default_model_when_omitted():
    captured_payload = {}

    def capture_request(req, timeout=None):
        captured_payload.update(json.loads(req.data.decode("utf-8")))
        return _mock_response('{"greeting": "hi"}')

    with patch("openrouter.urlopen", side_effect=capture_request):
        qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")

    assert captured_payload["model"] == DEFAULT_MODEL


def test_qwen_passes_strict_json_schema():
    captured_payload = {}

    def capture_request(req, timeout=None):
        captured_payload.update(json.loads(req.data.decode("utf-8")))
        return _mock_response('{"greeting": "hi"}')

    with patch("openrouter.urlopen", side_effect=capture_request):
        qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")

    rf = captured_payload["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == SCHEMA
