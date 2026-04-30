#!/usr/bin/env python3
from __future__ import annotations

"""CLI invoked by the /eng slash command. Writes a flashcard to the vault.

Usage:
    add_card.py --type {w,s,e} --phrase "..." --context "..."

Reads config from $ENGLISH_CAPTURE_CONFIG or ~/.english-capture/config.json.
Reads queue path from $ENGLISH_CAPTURE_QUEUE or ~/.english-capture/queue.json.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Ensure sibling modules importable when invoked directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm import LLMError, chat_json
from logger import Logger
from prompts import (
    EXPRESSION_SCHEMA,
    SENTENCE_SCHEMA,
    WORD_SCHEMA,
    build_expression_prompt,
    build_sentence_prompt,
    build_word_prompt,
)
from queue import QueueManager
from transcript import is_chinese_dominant
from vault import (
    append_example,
    phrase_exists,
    write_expression_card,
    write_sentence_card,
    write_word_card,
)


DEFAULT_CONFIG_PATH = os.path.expanduser("~/.english-capture/config.json")
DEFAULT_QUEUE_PATH = os.path.expanduser("~/.english-capture/queue.json")
DEFAULT_LOG_DIR = os.path.expanduser("~/.english-capture/logs")


def load_config() -> dict:
    path = os.environ.get("ENGLISH_CAPTURE_CONFIG", DEFAULT_CONFIG_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_existing_card_path(phrase: str, vault_root: Path, type_letter: str) -> Path | None:
    """If an existing card for `phrase` exists, return its path; else None."""
    from vault import _area_dir, _slugify
    area = _area_dir(vault_root)
    if type_letter == "s":
        candidate = area / "sentence" / f"{_slugify(phrase)}.md"
        return candidate if candidate.exists() else None
    if type_letter == "e":
        candidate = area / "expression" / f"{_slugify(phrase)}.md"
        return candidate if candidate.exists() else None
    # type w — phrase could be in any vocab category dir
    for sub in ("noun", "verb", "adjective", "adverb", "phrasal-verb", "collocation", "idiom"):
        candidate = area / sub / f"{_slugify(phrase)}.md"
        if candidate.exists():
            return candidate
    return None


def _phrase_in_context(phrase: str, context: str) -> bool:
    return bool(context) and phrase.lower() in context.lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add an English-learning flashcard")
    parser.add_argument("--type", choices=["w", "s", "e"], required=True)
    parser.add_argument("--phrase", required=True)
    parser.add_argument("--context", default="")
    args = parser.parse_args(argv)

    # Only use context for word cards when the phrase actually appears in it;
    # otherwise Qwen generates fresh examples and no 原文上下文 is recorded.
    effective_context = (
        args.context
        if args.type != "w" or _phrase_in_context(args.phrase, args.context)
        else ""
    )

    queue_path = os.environ.get("ENGLISH_CAPTURE_QUEUE", DEFAULT_QUEUE_PATH)
    log_dir = os.environ.get("ENGLISH_CAPTURE_LOGS", DEFAULT_LOG_DIR)
    logger = Logger(log_dir)
    queue = QueueManager(queue_path)

    # /eng e validation
    if args.type == "e" and not is_chinese_dominant(args.phrase):
        print("✗ /eng e expects Chinese input", file=sys.stdout)
        logger.log("WARN", f"rejected non-Chinese /eng e: {args.phrase[:60]}")
        return 2

    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"✗ {e}", file=sys.stdout)
        logger.log("ERROR", str(e))
        return 3

    vault_root = Path(os.path.expanduser(config["vault_path"]))
    if not vault_root.exists():
        print(f"✗ vault unreachable: {vault_root}", file=sys.stdout)
        logger.log("ERROR", f"vault unreachable: {vault_root}")
        return 4

    provider = config.get("vocab_provider", "openrouter")
    api_key = config[f"{provider}_api_key"]
    model = config.get(f"{provider}_model")
    timeout = config.get("timeout_seconds", 60)

    # Dedup-then-append (Strategy B)
    existing = find_existing_card_path(args.phrase, vault_root, args.type)
    if existing is not None:
        appended = append_example(existing, effective_context or args.phrase)
        rel = existing.relative_to(vault_root / "20-Areas" / "英语")
        if appended:
            print(f"↳ appended example to {rel}")
            logger.log("INFO", f"appended example to {rel}")
        else:
            print(f"↳ already exists ({rel})")
            logger.log("INFO", f"already exists: {rel}")
        return 0

    # Also check by frontmatter (handles old V2 cards without slug match)
    if phrase_exists(args.phrase, vault_root):
        print(f"↳ already exists in vault (no slug match)")
        logger.log("INFO", f"phrase exists by frontmatter: {args.phrase[:60]}")
        return 0

    # Build prompt + call Qwen
    if args.type == "w":
        sys_p, user_msg = build_word_prompt(args.phrase, effective_context)
        schema = WORD_SCHEMA
    elif args.type == "s":
        sys_p, user_msg = build_sentence_prompt(args.phrase, effective_context)
        schema = SENTENCE_SCHEMA
    else:  # e
        sys_p, user_msg = build_expression_prompt(args.phrase, effective_context)
        schema = EXPRESSION_SCHEMA

    try:
        llm_result = chat_json(
            provider=provider,
            system_prompt=sys_p,
            user_message=user_msg,
            json_schema=schema,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )
    except LLMError as e:
        queue.add({
            "type": args.type,
            "phrase": args.phrase,
            "context": effective_context,
        })
        print(f"✗ queued for retry ({e})")
        logger.log("WARN", f"queued: {args.phrase[:60]} — {e}")
        return 5

    # Write card
    try:
        if args.type == "w":
            path = write_word_card(llm_result, vault_root, source="manual_w", context=effective_context)
        elif args.type == "s":
            path = write_sentence_card(llm_result, vault_root, source="manual_s")
        else:
            path = write_expression_card(llm_result, vault_root, source="manual_e")
    except (OSError, KeyError) as e:
        print(f"✗ write failed: {e}")
        logger.log("ERROR", f"write failed: {e}")
        return 6

    rel = path.relative_to(vault_root / "20-Areas" / "英语")
    print(f"✓ saved {rel}")
    logger.log("INFO", f"saved {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
