"""Unified LLM adapter for OpenAI-compatible chat/completions providers.

Single `chat_json()` entry point. The provider registry declares each
provider's endpoint, default model, JSON-output capability, and any
extra headers required by that provider.

JSON modes
----------
- "schema": provider supports strict json_schema response_format. The
  server enforces the shape, so callers can trust the result without
  post-validation.
- "object": provider supports only `response_format: {type: "json_object"}`.
  The caller's `json_schema["required"]` keys are validated post-parse;
  the prompt itself must describe the JSON shape (DeepSeek's mode requires
  the word "JSON" in the system prompt).

Adding a provider
-----------------
Append an entry to `PROVIDERS`. The dispatcher needs no other changes
as long as the provider speaks the OpenAI chat-completions wire format.
"""
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT = 60


PROVIDERS: dict[str, dict[str, Any]] = {
    "openrouter": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "qwen/qwen3-235b-a22b-2507",
        "json_mode": "schema",
        "extra_headers": {
            "HTTP-Referer": "https://github.com/wanmaoor/english-capture",
            "X-Title": "english-capture",
        },
    },
    "deepseek": {
        "endpoint": "https://api.deepseek.com/chat/completions",
        "default_model": "deepseek-v4-flash",
        "json_mode": "object",
        "extra_headers": {},
    },
}


class LLMError(RuntimeError):
    """Raised when an LLM call fails or response is unparseable."""


def chat_json(
    provider: str,
    system_prompt: str,
    user_message: str,
    api_key: str,
    json_schema: dict,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    schema_name: str = "extraction",
) -> dict[str, Any]:
    """Call a provider's chat/completions and return parsed JSON content.

    `json_schema` is used as a strict schema if the provider supports it,
    otherwise its `required` field is used for post-parse validation.
    """
    if provider not in PROVIDERS:
        raise LLMError(f"unknown provider: {provider!r}")
    if not api_key:
        raise LLMError("api_key is required")

    spec = PROVIDERS[provider]
    chosen_model = model or spec["default_model"]

    if spec["json_mode"] == "schema":
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": json_schema,
            },
        }
    else:  # "object"
        response_format = {"type": "json_object"}

    payload = {
        "model": chosen_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "response_format": response_format,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **spec["extra_headers"],
    }

    req = Request(
        spec["endpoint"],
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.fp.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise LLMError(f"HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise LLMError(f"network error: {exc.reason}") from exc

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"non-JSON response: {raw[:500]}") from exc

    if "error" in envelope:
        raise LLMError(f"API error: {envelope['error']}")

    try:
        content = envelope["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"unexpected response shape: {envelope}") from exc

    if not content:
        raise LLMError(f"empty content from {provider}")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError(f"message.content is not valid JSON: {content[:500]}") from exc

    if spec["json_mode"] == "object":
        required = json_schema.get("required", [])
        missing = [k for k in required if k not in parsed]
        if missing:
            raise LLMError(f"missing required keys {missing} in: {parsed}")

    return parsed
