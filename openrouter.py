"""OpenRouter chat/completions client with strict JSON schema output.

Stdlib only (urllib). Default model: qwen/qwen3-235b-a22b-2507.
"""
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = "qwen/qwen3-235b-a22b-2507"
DEFAULT_TIMEOUT = 60
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter call fails or response is unparseable."""


def qwen(
    system_prompt: str,
    user_message: str,
    json_schema: dict,
    api_key: str,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
    schema_name: str = "extraction",
) -> dict[str, Any]:
    """POST to OpenRouter chat/completions with strict json_schema output.

    Returns the parsed `message.content` JSON (already a dict matching `json_schema`).
    Raises OpenRouterError on any network, envelope, or content-parse failure.
    """
    if not api_key:
        raise OpenRouterError("api_key is required")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": json_schema,
            },
        },
    }

    req = Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/wanmaoor/english-capture",
            "X-Title": "english-capture",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.fp.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise OpenRouterError(f"HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise OpenRouterError(f"network error: {exc.reason}") from exc

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"non-JSON response: {raw[:500]}") from exc

    if "error" in envelope:
        raise OpenRouterError(f"API error: {envelope['error']}")

    try:
        content = envelope["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise OpenRouterError(f"unexpected response shape: {envelope}") from exc

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"message.content is not valid JSON: {content[:500]}") from exc
