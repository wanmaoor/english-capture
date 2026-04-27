"""System prompts and JSON schemas for the four LLM tasks (w/s/e/grammar).

Prompt wording will be tuned during real-usage iteration; current versions are
the initial drafts that pass the test suite.
"""
from typing import Tuple


WORD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["phrase", "category", "translation_zh", "memory_tip", "context_sentence"],
    "properties": {
        "phrase": {"type": "string"},
        "category": {
            "type": "string",
            "enum": ["noun", "verb", "adjective", "adverb", "phrasal-verb", "collocation", "idiom"],
        },
        "translation_zh": {"type": "string"},
        "memory_tip": {"type": "string"},
        "context_sentence": {"type": "string"},
    },
}

SENTENCE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["original", "translation_zh", "grammar_points", "key_vocab"],
    "properties": {
        "original": {"type": "string"},
        "translation_zh": {"type": "string"},
        "grammar_points": {"type": "array", "items": {"type": "string"}},
        "key_vocab": {"type": "string"},
    },
}

EXPRESSION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["chinese", "idiomatic_english", "use_case", "anti_example"],
    "properties": {
        "chinese": {"type": "string"},
        "idiomatic_english": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 2,
        },
        "use_case": {"type": "string"},
        "anti_example": {"type": "string"},
    },
}

GRAMMAR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["has_error", "original", "corrected", "errors"],
    "properties": {
        "has_error": {"type": "boolean"},
        "original": {"type": "string"},
        "corrected": {"type": "string"},
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "explain"],
                "properties": {
                    "type": {"type": "string"},
                    "explain": {"type": "string"},
                },
            },
        },
    },
}


def build_word_prompt(phrase: str, context: str) -> Tuple[str, str]:
    """Returns (system_prompt, user_message) for the WORD_SCHEMA Qwen call."""
    system = (
        "You are an English-learning assistant for a Chinese software engineer.\n"
        "Given an English word or fixed phrase plus optional context, produce:\n"
        "  - phrase (verbatim or normalized form)\n"
        "  - category (noun/verb/adjective/adverb/phrasal-verb/collocation/idiom)\n"
        "  - translation_zh (concise 中文 translation, no romanization)\n"
        "  - memory_tip (one sentence in 中文 helping the learner remember)\n"
        "  - context_sentence (a real example sentence — use the provided context if useful, "
        "else write a natural one)\n"
        "Output strict JSON only, no commentary."
    )
    user = (
        f"PHRASE:\n{phrase}\n\n"
        f"CONTEXT:\n{context if context else '(none provided — produce a natural example)'}"
    )
    return system, user


def build_sentence_prompt(sentence: str, context: str) -> Tuple[str, str]:
    system = (
        "You are an English-learning assistant. Given an English sentence (often complex or "
        "long) plus optional surrounding context, produce:\n"
        "  - original (verbatim)\n"
        "  - translation_zh (faithful 中文 translation)\n"
        "  - grammar_points (1-3 bullets in 中文 explaining the key structures)\n"
        "  - key_vocab (any noteworthy words/phrases with their 中文 in parentheses; one line)\n"
        "Output strict JSON only, no commentary."
    )
    user = (
        f"SENTENCE:\n{sentence}\n\n"
        f"CONTEXT:\n{context if context else '(none)'}"
    )
    return system, user


def build_expression_prompt(chinese: str, context: str) -> Tuple[str, str]:
    system = (
        "You are an English-expression coach for a Chinese learner. Given a Chinese phrase and "
        "optional surrounding context (often a question about how to express it in English), "
        "produce:\n"
        "  - chinese (verbatim)\n"
        "  - idiomatic_english (1-2 natural English ways native speakers actually say it)\n"
        "  - use_case (one 中文 sentence describing when this expression fits)\n"
        "  - anti_example (a too-literal English translation a learner might write, with a "
        "brief 中文 note on why it's off)\n"
        "Output strict JSON only, no commentary."
    )
    user = (
        f"CHINESE:\n{chinese}\n\n"
        f"CONTEXT:\n{context if context else '(none)'}"
    )
    return system, user


def build_grammar_prompt(sentence: str) -> Tuple[str, str]:
    system = (
        "You are a strict English grammar checker for a Chinese software engineer's prose.\n"
        "Given a sentence (or short paragraph) the user wrote, decide if it has any genuine "
        "grammar errors (tense, agreement, article, preposition, word form, etc.).\n"
        "  - has_error: true ONLY if there is a real grammar mistake — not stylistic preference.\n"
        "  - corrected: the cleanest natural rewrite. If has_error is false, copy original.\n"
        "  - errors: list of {type, explain} (explain in 中文). Empty list if has_error is false.\n"
        "Output strict JSON only, no commentary."
    )
    user = f"SENTENCE:\n{sentence}"
    return system, user
