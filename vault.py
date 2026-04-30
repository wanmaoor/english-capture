from __future__ import annotations

"""Obsidian vault operations: read, write, dedup, append-example.

Cards live at <vault_root>/20-Areas/英语/{category}/<slug>.md.
Categories used by this codebase:
  word cards   → noun | verb | adjective | adverb | phrasal-verb | collocation | idiom
  sentence     → sentence/
  expression   → expression/
  grammar      → grammar/
"""
import re
from datetime import date
from pathlib import Path
from typing import Union


_AREA_REL = Path("20-Areas") / "英语"

_ASCII_PUNCT = set('.,;:?!"\'()[]{}')
_CJK_PUNCT = set("。，；：？！“”‘’（）【】《》、")

# Fields that should be quoted in YAML frontmatter (free-text user content).
# Other fields (enums like category/type/source) are written unquoted.
_QUOTED_FIELDS = {"phrase", "original", "chinese", "updated"}

_PHRASE_RE = re.compile(r'^(?:phrase|original|chinese):\s*"?([^"\n]+)"?\s*$', re.MULTILINE)


def normalize_for_dedup(s: str) -> str:
    """Lowercase, strip whitespace, collapse internal spaces, drop ASCII+CJK punctuation.

    Punctuation becomes a space (then collapsed) so e.g. CJK "你好，世界" → "你好 世界".
    """
    s = s.strip().lower()
    out_chars = []
    for ch in s:
        if ch in _ASCII_PUNCT or ch in _CJK_PUNCT:
            ch = " "
        elif ch.isspace():
            ch = " "
        out_chars.append(ch)
    return re.sub(r"\s+", " ", "".join(out_chars)).strip()


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9一-鿿]+", "-", text.lower())
    s = s.strip("-")
    return s[:40] if s else "untitled"


def _area_dir(vault_root: Union[str, Path]) -> Path:
    """Return path to <vault>/20-Areas/英语/. Accepts either full vault or the area dir directly."""
    vault = Path(vault_root)
    if (vault / _AREA_REL).is_dir():
        return vault / _AREA_REL
    if vault.name == "英语":
        return vault
    return vault / _AREA_REL  # let writes create it


def _frontmatter_block(fields: dict) -> str:
    """Render YAML frontmatter from dict.

    Free-text user fields (`_QUOTED_FIELDS`) are double-quoted; enum-like fields
    (category, type, source, created, checked_at) are written unquoted so test
    substrings like ``"category: verb"`` and ``"type: sentence"`` match exactly.
    List values are rendered as YAML sequences.
    """
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for entry in v:
                lines.append(f"  - {entry}")
        elif isinstance(v, str) and k in _QUOTED_FIELDS:
            escaped = v.replace('"', '\\"')
            lines.append(f'{k}: "{escaped}"')
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def write_word_card(item: dict, vault_root: Union[str, Path], source: str, context: str = "") -> Path:
    """Write a vocabulary flashcard to <vault>/20-Areas/英语/<category>/<slug>.md."""
    area = _area_dir(vault_root)
    target_dir = area / item["category"]
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(item["phrase"])
    out_path = target_dir / f"{slug}.md"

    fm = _frontmatter_block({
        "type": "english-vocab",
        "category": item["category"],
        "cefr": item["cefr"],
        "phrase": item["phrase"],
        "phonetic": item["phonetic"],
        "created": date.today().isoformat(),
        "source": source,
        "tags": ["flashcards/english/vocab"],
    })

    examples = "\n".join(
        f"- *{ex['en']}*（{ex['zh']}）" for ex in item["usage_examples"]
    )
    context_section = f"\n## 原文上下文\n\n{context}\n" if context else ""

    body = (
        f"\n# {item['phrase']}\n\n"
        f"{item['phrase']} {item['phonetic']}\n"
        f"?\n"
        f"**{item['translation_zh']}**\n\n"
        f"{item['description']}\n"
        f"{context_section}\n"
        f"## 用法示例\n\n"
        f"{examples}\n"
    )
    out_path.write_text(fm + body, encoding="utf-8")
    return out_path


def write_sentence_card(item: dict, vault_root: Union[str, Path], source: str) -> Path:
    area = _area_dir(vault_root)
    target_dir = area / "sentence"
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(item["original"])
    out_path = target_dir / f"{slug}.md"

    fm = _frontmatter_block({
        "original": item["original"],
        "type": "sentence",
        "created": date.today().isoformat(),
        "source": source,
    })

    grammar_lines = "\n".join(f"- {p}" for p in item.get("grammar_points", []))
    body = f"""
{item['original']}
?
**中文:** {item['translation_zh']}

**语法点:**
{grammar_lines}

**生词:** {item.get('key_vocab', '')}
"""
    out_path.write_text(fm + body, encoding="utf-8")
    return out_path


def write_expression_card(item: dict, vault_root: Union[str, Path], source: str) -> Path:
    area = _area_dir(vault_root)
    target_dir = area / "expression"
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(item["chinese"])
    out_path = target_dir / f"{slug}.md"

    fm = _frontmatter_block({
        "chinese": item["chinese"],
        "type": "expression",
        "created": date.today().isoformat(),
        "source": source,
    })

    options = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(item["idiomatic_english"]))
    body = f"""
{item['chinese']}
?
**地道表达:**
{options}

**使用场景:** {item['use_case']}

**反例:** {item['anti_example']}
"""
    out_path.write_text(fm + body, encoding="utf-8")
    return out_path


def write_grammar_card(item: dict, vault_root: Union[str, Path], source: str) -> Path:
    area = _area_dir(vault_root)
    target_dir = area / "grammar"
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(item["original"])
    out_path = target_dir / f"{slug}.md"

    fm = _frontmatter_block({
        "original": item["original"],
        "checked_at": date.today().isoformat(),
        "type": "grammar",
        "source": source,
    })

    error_lines = "\n".join(f"- `{e['type']}`：{e['explain']}" for e in item.get("errors", []))
    body = f"""
{item['original']}
?
**Corrected:** {item['corrected']}

**错误点:**
{error_lines}
"""
    out_path.write_text(fm + body, encoding="utf-8")
    return out_path


def phrase_exists(phrase: str, vault_root: Union[str, Path]) -> bool:
    """Search every .md under area for a frontmatter phrase/original/chinese matching `phrase`.

    Comparison uses normalize_for_dedup() on both sides.
    """
    area = _area_dir(vault_root)
    if not area.is_dir():
        return False
    target_norm = normalize_for_dedup(phrase)
    for md in area.rglob("*.md"):
        if md.parent.name == "grammar":
            continue  # grammar uses different field set; checked separately
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        front = text[:1000]
        for match in _PHRASE_RE.finditer(front):
            if normalize_for_dedup(match.group(1)) == target_norm:
                return True
    return False


def grammar_already_checked(original: str, vault_root: Union[str, Path]) -> bool:
    """Search grammar/ dir for a frontmatter `original:` matching `original` (normalized)."""
    area = _area_dir(vault_root)
    grammar_dir = area / "grammar"
    if not grammar_dir.is_dir():
        return False
    target_norm = normalize_for_dedup(original)
    for md in grammar_dir.glob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        front = text[:500]
        for match in _PHRASE_RE.finditer(front):
            if normalize_for_dedup(match.group(1)) == target_norm:
                return True
    return False


def append_example(card_path: Path, new_example: str) -> bool:
    """Append `new_example` to the **例句:** list of an existing word card.

    Returns False if `new_example` already present (dedup); True if appended.
    Also updates/inserts an `updated:` frontmatter field.
    """
    text = card_path.read_text(encoding="utf-8")
    if new_example in text:
        return False  # exact-string dedup within file

    today = date.today().isoformat()
    if re.search(r"^updated:", text, re.MULTILINE):
        text = re.sub(r"^updated:.*$", f'updated: "{today}"', text, count=1, flags=re.MULTILINE)
    else:
        # Insert before closing --- of frontmatter
        text = re.sub(
            r"(\n---\n)",
            f'\nupdated: "{today}"\\1',
            text,
            count=1,
        )

    if "## 用法示例" in text or "**例句:**" in text:
        text = text.rstrip() + f"\n- {new_example}\n"
    else:
        text = text.rstrip() + f"\n\n## 用法示例\n\n- {new_example}\n"

    card_path.write_text(text, encoding="utf-8")
    return True


def recent_phrases(vault_root: Union[str, Path], limit: int = 10) -> list[str]:
    """Return up to `limit` most-recently-modified phrase/original/chinese values."""
    area = _area_dir(vault_root)
    if not area.is_dir():
        return []
    md_files = list(area.rglob("*.md"))
    md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    out: list[str] = []
    for md in md_files:
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        match = _PHRASE_RE.search(text[:1000])
        if match:
            out.append(match.group(1).strip())
        if len(out) >= limit:
            break
    return out
