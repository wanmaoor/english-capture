"""Parse Claude Code transcript JSONL and extract the last user input.

Also exposes is_chinese_dominant() for filter logic shared by /eng e and grammar hook.
"""
import json
import os


def read_transcript(path: str) -> list[dict]:
    """Read a JSONL file, return list of dicts. Missing → []. Malformed lines skipped."""
    if not os.path.exists(path):
        return []
    messages: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages


def _extract_text_blocks(content) -> str:
    """Pull text out of either a string or a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in parts if p)
    return ""


def _is_tool_result_only(content) -> bool:
    """True when user message content has only tool_result blocks (no human text)."""
    if not isinstance(content, list) or not content:
        return False
    has_text = any(isinstance(b, dict) and b.get("type") == "text" for b in content)
    has_tool_result = any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
    return has_tool_result and not has_text


def extract_last_user_input(messages: list[dict]) -> str:
    """Walk backward; return the most recent human user input as plain text.

    Tool-result-only user messages are skipped. Returns "" if no human input found.
    """
    for m in reversed(messages):
        if m.get("type") != "user":
            continue
        content = m.get("message", {}).get("content")
        if _is_tool_result_only(content):
            continue
        text = _extract_text_blocks(content)
        if text:
            return text
    return ""


def is_chinese_dominant(text: str) -> bool:
    """True if CJK Unicode chars account for >50% of letter-class chars in text.

    Whitespace and punctuation are not counted on either side.
    """
    if not text:
        return False
    chinese = sum(1 for ch in text if "一" <= ch <= "鿿")
    english = sum(1 for ch in text if ch.isalpha() and not ("一" <= ch <= "鿿"))
    total = chinese + english
    if total == 0:
        return False
    return chinese / total > 0.5
