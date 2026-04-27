"""Tests for vault.py — phrase_exists, normalize, write_*, append_example."""
from pathlib import Path

from vault import (
    append_example,
    grammar_already_checked,
    normalize_for_dedup,
    phrase_exists,
    recent_phrases,
    write_expression_card,
    write_grammar_card,
    write_sentence_card,
    write_word_card,
)


# ---------- normalize_for_dedup ----------

def test_normalize_lowercases():
    assert normalize_for_dedup("Hello World") == "hello world"


def test_normalize_strips_outer_whitespace():
    assert normalize_for_dedup("  hello  ") == "hello"


def test_normalize_collapses_internal_whitespace():
    assert normalize_for_dedup("hello   world\t\nfoo") == "hello world foo"


def test_normalize_strips_ascii_punctuation():
    assert normalize_for_dedup("hello, world.") == "hello world"


def test_normalize_strips_cjk_punctuation():
    assert normalize_for_dedup("你好，世界。") == "你好 世界"


def test_normalize_idempotent():
    s = "  HELLO,   World!  "
    assert normalize_for_dedup(normalize_for_dedup(s)) == normalize_for_dedup(s)


# ---------- write_word_card ----------

def test_write_word_card_creates_file_in_category_dir(tmp_vault: Path):
    item = {
        "phrase": "cardinality estimation",
        "category": "noun",
        "translation_zh": "基数估计",
        "memory_tip": "数据库查询规划器估算结果行数",
        "context_sentence": "...cardinality estimation errors on the join...",
    }
    path = write_word_card(item, tmp_vault, source="manual_w")
    assert path.exists()
    assert path.parent.name == "noun"
    assert path.parent.parent.name == "英语"
    text = path.read_text(encoding="utf-8")
    assert 'phrase: "cardinality estimation"' in text
    assert "source: manual_w" in text
    assert "基数估计" in text
    assert "?" in text


def test_write_word_card_slugifies_spaces(tmp_vault: Path):
    item = {
        "phrase": "Hello World",
        "category": "noun",
        "translation_zh": "你好世界",
        "memory_tip": "x",
        "context_sentence": "y",
    }
    path = write_word_card(item, tmp_vault, source="manual_w")
    assert path.name == "hello-world.md"


# ---------- write_sentence_card ----------

def test_write_sentence_card(tmp_vault: Path):
    item = {
        "original": "Despite the migration succeeding, downstream consumers reported stale reads.",
        "translation_zh": "尽管迁移成功了，下游消费者还是报告读到了旧数据。",
        "grammar_points": ["Despite + 动名词短语 等价于 Although + 从句"],
        "key_vocab": "stale reads（脏读 / 旧读）",
    }
    path = write_sentence_card(item, tmp_vault, source="manual_s")
    assert path.parent.name == "sentence"
    text = path.read_text(encoding="utf-8")
    assert "type: sentence" in text
    assert "source: manual_s" in text


# ---------- write_expression_card ----------

def test_write_expression_card(tmp_vault: Path):
    item = {
        "chinese": "这个 PR 我先放一放",
        "idiomatic_english": [
            "I'll put this PR on the back burner for now.",
            "Let me park this PR for a bit.",
        ],
        "use_case": "工作中需要暂时搁置某事但不放弃。",
        "anti_example": "I will pause this PR 太字面",
    }
    path = write_expression_card(item, tmp_vault, source="manual_e")
    assert path.parent.name == "expression"
    text = path.read_text(encoding="utf-8")
    assert "type: expression" in text
    assert "back burner" in text


# ---------- write_grammar_card ----------

def test_write_grammar_card(tmp_vault: Path):
    item = {
        "original": "I have went to the store yesterday.",
        "corrected": "I went to the store yesterday.",
        "errors": [{"type": "tense", "explain": "have went → went"}],
    }
    path = write_grammar_card(item, tmp_vault, source="auto_grammar")
    assert path.parent.name == "grammar"
    text = path.read_text(encoding="utf-8")
    assert "type: grammar" in text
    assert "Corrected:" in text


# ---------- phrase_exists ----------

def test_phrase_exists_finds_existing_word_card(tmp_vault: Path):
    item = {
        "phrase": "derive",
        "category": "verb",
        "translation_zh": "得出",
        "memory_tip": "x",
        "context_sentence": "y",
    }
    write_word_card(item, tmp_vault, source="manual_w")
    assert phrase_exists("derive", tmp_vault) is True


def test_phrase_exists_normalizes(tmp_vault: Path):
    item = {
        "phrase": "stale reads",
        "category": "noun",
        "translation_zh": "脏读",
        "memory_tip": "x",
        "context_sentence": "y",
    }
    write_word_card(item, tmp_vault, source="manual_w")
    assert phrase_exists("Stale Reads.", tmp_vault) is True
    assert phrase_exists("STALE  READS", tmp_vault) is True


def test_phrase_exists_returns_false_for_unknown(tmp_vault: Path):
    assert phrase_exists("never-seen", tmp_vault) is False


def test_phrase_exists_finds_sentence_card_via_original(tmp_vault: Path):
    item = {
        "original": "Despite the migration succeeding.",
        "translation_zh": "x",
        "grammar_points": [],
        "key_vocab": "",
    }
    write_sentence_card(item, tmp_vault, source="manual_s")
    assert phrase_exists("Despite the migration succeeding.", tmp_vault) is True


def test_phrase_exists_finds_expression_card_via_chinese(tmp_vault: Path):
    item = {
        "chinese": "这个 PR 我先放一放",
        "idiomatic_english": ["x"],
        "use_case": "x",
        "anti_example": "x",
    }
    write_expression_card(item, tmp_vault, source="manual_e")
    assert phrase_exists("这个 PR 我先放一放", tmp_vault) is True


# ---------- append_example ----------

def test_append_example_adds_to_existing_card(tmp_vault: Path):
    item = {
        "phrase": "derive",
        "category": "verb",
        "translation_zh": "得出",
        "memory_tip": "x",
        "context_sentence": "first usage",
    }
    path = write_word_card(item, tmp_vault, source="manual_w")
    appended = append_example(path, "second usage")
    assert appended is True
    text = path.read_text(encoding="utf-8")
    assert "first usage" in text
    assert "second usage" in text
    # Both bullets present
    assert text.count("\n- ") >= 2


def test_append_example_preserves_frontmatter(tmp_vault: Path):
    item = {
        "phrase": "derive",
        "category": "verb",
        "translation_zh": "得出",
        "memory_tip": "x",
        "context_sentence": "first",
    }
    path = write_word_card(item, tmp_vault, source="manual_w")
    append_example(path, "second")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert 'phrase: "derive"' in text
    assert "category: verb" in text


def test_append_example_dedups_within_list(tmp_vault: Path):
    item = {
        "phrase": "derive",
        "category": "verb",
        "translation_zh": "得出",
        "memory_tip": "x",
        "context_sentence": "same usage",
    }
    path = write_word_card(item, tmp_vault, source="manual_w")
    appended = append_example(path, "same usage")
    assert appended is False
    text = path.read_text(encoding="utf-8")
    assert text.count("same usage") == 1


def test_append_example_adds_updated_field(tmp_vault: Path):
    item = {
        "phrase": "derive",
        "category": "verb",
        "translation_zh": "得出",
        "memory_tip": "x",
        "context_sentence": "first",
    }
    path = write_word_card(item, tmp_vault, source="manual_w")
    append_example(path, "second")
    text = path.read_text(encoding="utf-8")
    assert "updated:" in text


# ---------- grammar_already_checked ----------

def test_grammar_already_checked_true_after_write(tmp_vault: Path):
    item = {
        "original": "I have went home.",
        "corrected": "I went home.",
        "errors": [],
    }
    write_grammar_card(item, tmp_vault, source="auto_grammar")
    assert grammar_already_checked("I have went home.", tmp_vault) is True


def test_grammar_already_checked_normalizes(tmp_vault: Path):
    item = {
        "original": "I have went home.",
        "corrected": "I went home.",
        "errors": [],
    }
    write_grammar_card(item, tmp_vault, source="auto_grammar")
    assert grammar_already_checked("i have went home", tmp_vault) is True
    assert grammar_already_checked("I have   went home!", tmp_vault) is True


def test_grammar_already_checked_false_for_unseen(tmp_vault: Path):
    assert grammar_already_checked("brand new sentence", tmp_vault) is False


# ---------- recent_phrases ----------

def test_recent_phrases_returns_most_recent(tmp_vault: Path):
    for i, word in enumerate(["apple", "banana", "cherry"]):
        item = {
            "phrase": word,
            "category": "noun",
            "translation_zh": "x",
            "memory_tip": "x",
            "context_sentence": "x",
        }
        write_word_card(item, tmp_vault, source="manual_w")
    result = recent_phrases(tmp_vault, limit=10)
    assert set(result) >= {"apple", "banana", "cherry"}
