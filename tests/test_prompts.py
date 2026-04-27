"""Tests for prompts.py — schema shapes and prompt content."""
import json

import pytest

from prompts import (
    EXPRESSION_SCHEMA,
    GRAMMAR_SCHEMA,
    SENTENCE_SCHEMA,
    WORD_SCHEMA,
    build_expression_prompt,
    build_grammar_prompt,
    build_sentence_prompt,
    build_word_prompt,
)


def _has_json_schema_shape(schema: dict) -> bool:
    """Strict JSON schema must declare type, additionalProperties, required, properties."""
    return (
        schema.get("type") == "object"
        and schema.get("additionalProperties") is False
        and "required" in schema
        and "properties" in schema
    )


def test_word_schema_shape():
    assert _has_json_schema_shape(WORD_SCHEMA)
    expected = {"phrase", "category", "translation_zh", "memory_tip", "context_sentence"}
    assert set(WORD_SCHEMA["required"]) == expected


def test_sentence_schema_shape():
    assert _has_json_schema_shape(SENTENCE_SCHEMA)
    expected = {"original", "translation_zh", "grammar_points", "key_vocab"}
    assert set(SENTENCE_SCHEMA["required"]) == expected


def test_expression_schema_shape():
    assert _has_json_schema_shape(EXPRESSION_SCHEMA)
    expected = {"chinese", "idiomatic_english", "use_case", "anti_example"}
    assert set(EXPRESSION_SCHEMA["required"]) == expected


def test_grammar_schema_shape():
    assert _has_json_schema_shape(GRAMMAR_SCHEMA)
    expected = {"has_error", "original", "corrected", "errors"}
    assert set(GRAMMAR_SCHEMA["required"]) == expected


def test_word_schema_category_enum():
    cats = WORD_SCHEMA["properties"]["category"]["enum"]
    assert "noun" in cats and "verb" in cats and "phrasal-verb" in cats and "idiom" in cats


def test_build_word_prompt_includes_phrase_and_context():
    sys_p, user_msg = build_word_prompt("derive", "from this we can derive...")
    assert "derive" in user_msg
    assert "from this we can derive" in user_msg
    assert sys_p


def test_build_word_prompt_handles_empty_context():
    sys_p, user_msg = build_word_prompt("derive", "")
    assert "derive" in user_msg


def test_build_sentence_prompt():
    sys_p, user_msg = build_sentence_prompt("Despite the rain, we left.", "context here")
    assert "Despite the rain" in user_msg
    assert sys_p


def test_build_expression_prompt():
    sys_p, user_msg = build_expression_prompt("我先放一放", "context here")
    assert "我先放一放" in user_msg
    assert sys_p


def test_build_grammar_prompt():
    sys_p, user_msg = build_grammar_prompt("I have went home.")
    assert "I have went home" in user_msg
    assert sys_p


def test_word_prompt_asks_for_chinese_translation():
    sys_p, _ = build_word_prompt("x", "y")
    assert "中文" in sys_p or "Chinese" in sys_p


def test_grammar_prompt_asks_for_has_error_judgment():
    sys_p, _ = build_grammar_prompt("x")
    assert "has_error" in sys_p or "grammar" in sys_p.lower()
