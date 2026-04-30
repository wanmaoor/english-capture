"""System prompts and JSON schemas for the four LLM tasks (w/s/e/grammar).

Prompt wording will be tuned during real-usage iteration; current versions are
the initial drafts that pass the test suite.
"""
from typing import Tuple


WORD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["phrase", "category", "phonetic", "cefr", "translation_zh", "description", "usage_examples"],
    "properties": {
        "phrase": {"type": "string"},
        "category": {
            "type": "string",
            "enum": ["noun", "verb", "adjective", "adverb", "phrasal-verb", "collocation", "idiom"],
        },
        "phonetic": {"type": "string"},
        "cefr": {
            "type": "string",
            "enum": ["A1", "A2", "B1", "B2", "C1", "C2"],
        },
        "translation_zh": {"type": "string"},
        "description": {"type": "string"},
        "usage_examples": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["en", "zh"],
                "properties": {
                    "en": {"type": "string"},
                    "zh": {"type": "string"},
                },
            },
            "minItems": 1,
            "maxItems": 3,
        },
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
        "  - phrase: verbatim or normalized form\n"
        "  - category: noun/verb/adjective/adverb/phrasal-verb/collocation/idiom\n"
        "  - phonetic: IPA pronunciation string (e.g. /ˈwɜːrd/)\n"
        "  - cefr: one of A1/A2/B1/B2/C1/C2\n"
        "  - translation_zh: concise 中文 translation, no romanization\n"
        "  - description: one 中文 paragraph (1-2 sentences) on usage style, register, or a "
        "memorable linguistic note — NOT a definition repeat\n"
        "  - usage_examples: 2 natural example sentences, each with en (English) and zh (中文 "
        "translation); if context is provided use it as the basis for the first example\n"
        "Output strict JSON only, no commentary."
    )
    user = (
        f"PHRASE:\n{phrase}\n\n"
        f"CONTEXT:\n{context if context else '(none provided — produce natural examples)'}"
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
        "The input is always English. Decide if the sentence has any genuine grammar errors "
        "(tense, agreement, article, preposition, word form, run-on, fragment, etc.).\n"
        "\n"
        "DO NOT flag any of the following — they are NOT errors:\n"
        "  - Capitalization issues of any kind (lowercase sentence start, missing capitals on\n"
        "    proper nouns, ALLCAPS, mixed case in identifiers/paths/URLs/code).\n"
        "  - Punctuation style preferences (Oxford comma, em-dash vs hyphen).\n"
        "  - Stylistic / formality preferences (informal abbreviations like 'pro env', 'app',\n"
        "    'repo', etc. are fine in casual prose).\n"
        "  - Code, file paths, URLs, identifiers, command names — treat them as opaque tokens.\n"
        "\n"
        "Return a single JSON object with this exact shape:\n"
        '  {"has_error": bool, "original": str, "corrected": str,\n'
        '   "errors": [{"type": str, "explain": str}, ...]}\n'
        "\n"
        "Field rules:\n"
        "  - has_error: true ONLY when there is a real, non-capitalization grammar mistake.\n"
        "  - original: copy the input verbatim.\n"
        "  - corrected: cleanest natural rewrite. If has_error is false, copy original.\n"
        "  - errors: list of {type, explain}; explain in 中文. Empty list when has_error is false.\n"
        "    Never include any error whose `type` is capitalization-related.\n"
        "\n"
        "Output strict JSON only, no commentary, no markdown fences."
    )
    user = f"SENTENCE:\n{sentence}"
    return system, user
