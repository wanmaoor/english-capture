#!/usr/bin/env python3
"""CC Stop hook entry. Grammar-only mode.

Reads {hook_event_name, transcript_path} from stdin (CC convention).
Filters non-applicable inputs, then asks Qwen if there's a grammar error,
and writes a flashcard if so. Drains retry queue first.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from logger import Logger
from openrouter import OpenRouterError, qwen
from prompts import GRAMMAR_SCHEMA, build_grammar_prompt
from queue import QueueManager
from transcript import (
    extract_last_user_input,
    is_chinese_dominant,
    read_transcript,
)
from vault import grammar_already_checked, write_grammar_card


DEFAULT_CONFIG_PATH = os.path.expanduser("~/.english-capture/config.json")
DEFAULT_QUEUE_PATH = os.path.expanduser("~/.english-capture/queue.json")
DEFAULT_LOG_DIR = os.path.expanduser("~/.english-capture/logs")


def load_config() -> dict | None:
    path = os.environ.get("ENGLISH_CAPTURE_CONFIG", DEFAULT_CONFIG_PATH)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def should_skip(text: str, vault_root: Path) -> str | None:
    """Return a skip reason string, or None to proceed."""
    if text.startswith("/"):
        return "slash command"
    if len(text.split()) < 5:
        return "too short"
    if is_chinese_dominant(text):
        return "Chinese-dominant"
    if grammar_already_checked(text, vault_root):
        return "already checked"
    return None


def check_one(text: str, config: dict, logger: Logger, queue: QueueManager, vault_root: Path) -> None:
    """Check one input; write grammar card if has_error; queue on failure."""
    sys_p, user_msg = build_grammar_prompt(text)
    try:
        result = qwen(
            system_prompt=sys_p,
            user_message=user_msg,
            json_schema=GRAMMAR_SCHEMA,
            api_key=config["openrouter_api_key"],
            model=config.get("openrouter_model", "qwen/qwen3-235b-a22b-2507"),
            timeout=config.get("timeout_seconds", 60),
        )
    except OpenRouterError as e:
        queue.add({"type": "grammar", "input": text})
        logger.log("WARN", f"grammar check queued: {e}")
        return

    if not result.get("has_error", False):
        logger.log("INFO", f"no errors in: {text[:60]}")
        return

    try:
        path = write_grammar_card(result, vault_root, source="auto_grammar")
        logger.log("INFO", f"saved grammar/{path.name}")
    except (OSError, KeyError) as e:
        logger.log("ERROR", f"write grammar failed: {e}")


def drain_queue(queue: QueueManager, config: dict, logger: Logger, vault_root: Path) -> None:
    items = queue.load()
    if not items:
        return
    queue.clear()
    remaining = []
    for item in items:
        if item.get("type") != "grammar":
            remaining.append(item)
            continue
        try:
            check_one(item["input"], config, logger, queue, vault_root)
        except Exception as e:
            logger.log("WARN", f"requeue: {e}")
            remaining.append(item)
    for r in remaining:
        queue.add(r)


def main() -> int:
    log_dir = os.environ.get("ENGLISH_CAPTURE_LOGS", DEFAULT_LOG_DIR)
    logger = Logger(log_dir)

    try:
        event = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return 0

    if event.get("hook_event_name") and event["hook_event_name"] != "Stop":
        return 0

    transcript_path = event.get("transcript_path")
    if not transcript_path or not os.path.exists(transcript_path):
        return 0

    messages = read_transcript(transcript_path)
    user_input = extract_last_user_input(messages).strip()
    if not user_input:
        return 0

    config = load_config()
    if config is None:
        logger.log("WARN", "config missing; skipping")
        return 0

    vault_root = Path(os.path.expanduser(config["vault_path"]))
    if not vault_root.exists():
        logger.log("WARN", f"vault unreachable: {vault_root}")
        return 0

    queue_path = os.environ.get("ENGLISH_CAPTURE_QUEUE", DEFAULT_QUEUE_PATH)
    queue = QueueManager(queue_path)

    skip_reason = should_skip(user_input, vault_root)
    if skip_reason:
        logger.log("INFO", f"skipped ({skip_reason}): {user_input[:60]}")
        # still drain queue even if current input is skipped
        drain_queue(queue, config, logger, vault_root)
        return 0

    drain_queue(queue, config, logger, vault_root)
    check_one(user_input, config, logger, queue, vault_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
