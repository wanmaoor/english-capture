# English Capture Hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **2026-04-22 late pivot note:** This plan was originally written for the Gemini REST version. The current repo has since pivoted again to OpenRouter (`openrouter_client.py`, `openrouter_*` config keys, strict JSON schema updates, and `tests/test_openrouter_client.py`). Treat this file as historical task-by-task context; treat the design spec and current code as the authoritative implementation state.

**Goal:** Build a CC Stop hook that extracts high-value English vocabulary and grammar corrections from each session's transcript, filters via **OpenRouter**, and writes atomic flashcard md files into the user's Obsidian vault.

**Architecture:** Python hook installed at `~/.claude/hooks/english-capture/`. Entry point `capture.py` reads CC transcript JSON from stdin, calls OpenRouter chat/completions (via urllib), dedupes against vault, and writes md files to `20-Areas/英语/{category}/`.

**Tech Stack:** Python 3.12 (stdlib only — urllib/json), pytest, grep, git. **No external Python deps.**

**Design pivot note (2026-04-22)**: Original plan used `claude -p --bare`. Task 1 smoke test revealed this requires API key (not subscription) and each non-`--bare` call costs $0.05. Gemini 2.5 Flash Lite smoke test succeeded with 406 tokens/call at $0 in free tier. Task 9 renamed from `haiku_client.py` to `gemini_client.py` with REST-over-urllib implementation.

**Spec:** `~/.claude/hooks/english-capture/docs/superpowers/specs/2026-04-22-english-capture-hook-design.md`

---

## Task 1: Precondition — Gemini REST smoke test ✅ DONE

**Status**: COMPLETED 2026-04-22.

**Outcome**: `claude -p --bare` infeasible for subscription users. Pivoted to Gemini 2.5 Flash Lite REST. Live smoke test succeeded — 406 tokens total, 3.5s, $0, correct extraction quality.

**Response envelope confirmed**: `candidates[0].content.parts[0].text` contains JSON string matching the schema. Must `json.loads()` twice: once for HTTP response, once for the nested `text` field.

**Config location**: `~/.english-capture/config.json` (mode 0600) — already created with API key.

- [x] Smoke test passed
- [x] Proceed to Task 2

---

## Task 2: Project skeleton + deps

**Files:**
- Create: `~/.claude/hooks/english-capture/.gitignore`
- Create: `~/.claude/hooks/english-capture/pyproject.toml`
- Create: `~/.claude/hooks/english-capture/tests/__init__.py`

- [ ] **Step 1: Write .gitignore**

```bash
cat > ~/.claude/hooks/english-capture/.gitignore <<'EOF'
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.egg-info/
EOF
```

- [ ] **Step 2: Write pyproject.toml**

```toml
[project]
name = "english-capture"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Use Write tool to create `~/.claude/hooks/english-capture/pyproject.toml` with content above.

- [ ] **Step 3: Create empty tests package**

```bash
mkdir -p ~/.claude/hooks/english-capture/tests/fixtures
touch ~/.claude/hooks/english-capture/tests/__init__.py
```

- [ ] **Step 4: Verify pytest works**

```bash
cd ~/.claude/hooks/english-capture
pytest --version
```

Expected: pytest version string. If not installed:
```bash
python3 -m pip install --user pytest
```

- [ ] **Step 5: Commit**

```bash
cd ~/.claude/hooks/english-capture
git add .gitignore pyproject.toml tests/__init__.py
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "chore: project skeleton + pytest config"
```

---

## Task 3: Copy legacy modules from Mac Studio

The spec reuses 4 files from `~/projects/english-copilot/hook/` on Mac Studio:
- `transcript.py` — CC transcript reader
- `queue_manager.py` → rename to `queue.py`
- `logger.py` — daily log file
- `user_profile.md` — filter rules

**Files:**
- Create: `~/.claude/hooks/english-capture/transcript.py` (scp from Studio)
- Create: `~/.claude/hooks/english-capture/queue.py` (scp + rename)
- Create: `~/.claude/hooks/english-capture/logger.py` (scp from Studio)
- Create: `~/.claude/hooks/english-capture/user_profile.md` (scp from Studio)
- Create: `~/.claude/hooks/english-capture/tests/test_transcript.py` (copy + adapt)

- [ ] **Step 1: scp the four files from Mac Studio**

```bash
cd ~/.claude/hooks/english-capture
scp macstudio:projects/english-copilot/hook/transcript.py .
scp macstudio:projects/english-copilot/hook/queue_manager.py ./queue.py
scp macstudio:projects/english-copilot/hook/logger.py .
scp "macstudio:.english-copilot/hook/user_profile.md" .
```

If `~/.english-copilot/hook/user_profile.md` doesn't exist on Studio, fall back:
```bash
scp macstudio:projects/english-copilot/hook/user_profile.example.md ./user_profile.md
```

- [ ] **Step 2: Verify files are present and non-empty**

```bash
cd ~/.claude/hooks/english-capture
ls -la transcript.py queue.py logger.py user_profile.md
wc -l transcript.py queue.py logger.py user_profile.md
```

Each file should be > 10 lines.

- [ ] **Step 3: Rename `QueueManager` references if needed**

If queue.py imports itself as `from queue_manager import ...`, that doesn't matter — callers will import `from queue import QueueManager`. No file-internal changes needed unless queue.py has relative imports (unlikely).

```bash
grep -n "from queue_manager\|import queue_manager" ~/.claude/hooks/english-capture/queue.py
```

Expected: no output (file self-contained).

- [ ] **Step 4: scp the existing test file for transcript**

```bash
cd ~/.claude/hooks/english-capture/tests
scp macstudio:projects/english-copilot/hook/test_transcript.py .
```

- [ ] **Step 5: Copy fixtures if they exist**

```bash
mkdir -p ~/.claude/hooks/english-capture/tests/fixtures
scp -r "macstudio:projects/english-copilot/hook/fixtures/*" \
  ~/.claude/hooks/english-capture/tests/fixtures/ 2>/dev/null || echo "no fixtures on Studio, will create later"
```

- [ ] **Step 6: Run transcript tests to verify copy works**

```bash
cd ~/.claude/hooks/english-capture
pytest tests/test_transcript.py -v
```

Expected: all tests pass. If they fail due to fixture paths, adjust the test imports and paths.

- [ ] **Step 7: Commit**

```bash
cd ~/.claude/hooks/english-capture
git add transcript.py queue.py logger.py user_profile.md tests/test_transcript.py tests/fixtures/
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "chore: copy transcript/queue/logger/profile from english-copilot"
```

---

## Task 4: dedup.py — `phrase_exists`

**Files:**
- Create: `~/.claude/hooks/english-capture/dedup.py`
- Create: `~/.claude/hooks/english-capture/tests/test_dedup.py`
- Create: `~/.claude/hooks/english-capture/tests/fixtures/mini-vault/20-Areas/英语/adjective/sample.md`

- [ ] **Step 1: Create fixture vault**

```bash
mkdir -p ~/.claude/hooks/english-capture/tests/fixtures/mini-vault/20-Areas/英语/adjective
mkdir -p ~/.claude/hooks/english-capture/tests/fixtures/mini-vault/20-Areas/英语/noun
```

Create file `tests/fixtures/mini-vault/20-Areas/英语/adjective/sample.md`:
```markdown
---
type: english-vocab
category: adjective
phrase: "Ephemeral"
---

# Ephemeral
```

Create file `tests/fixtures/mini-vault/20-Areas/英语/noun/other.md`:
```markdown
---
type: english-vocab
category: noun
phrase: "paradigm shift"
---

# paradigm shift
```

- [ ] **Step 2: Write the failing test**

Write `tests/test_dedup.py`:

```python
from pathlib import Path
import pytest
from dedup import phrase_exists

FIXTURE = Path(__file__).parent / "fixtures" / "mini-vault"

def test_phrase_exists_case_insensitive():
    assert phrase_exists("ephemeral", FIXTURE) is True
    assert phrase_exists("EPHEMERAL", FIXTURE) is True
    assert phrase_exists("Ephemeral", FIXTURE) is True

def test_phrase_exists_finds_multi_word():
    assert phrase_exists("paradigm shift", FIXTURE) is True

def test_phrase_exists_returns_false_for_absent():
    assert phrase_exists("nonexistent", FIXTURE) is False

def test_phrase_exists_returns_false_for_empty_vault(tmp_path):
    assert phrase_exists("anything", tmp_path) is False
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd ~/.claude/hooks/english-capture
pytest tests/test_dedup.py -v
```

Expected: `ModuleNotFoundError: No module named 'dedup'` or ImportError.

- [ ] **Step 4: Implement `phrase_exists`**

Write `dedup.py`:

```python
"""Vault-level dedup helpers.

Checks whether a given English phrase has already been captured anywhere in the
user's Obsidian English-learning area, by grepping the frontmatter `phrase:` field.

Also provides recent_phrases() for negative few-shot signal to the Haiku filter.
"""
import subprocess
from pathlib import Path
from typing import Union


def phrase_exists(phrase: str, vault_root: Union[str, Path]) -> bool:
    """Return True if any md file under <vault_root>/20-Areas/英语/ has
    frontmatter `phrase: "<phrase>"` (case-insensitive match).

    vault_root may be either the full vault (containing 20-Areas/) or the
    英语 area directory directly; both cases are accepted.
    """
    vault = Path(vault_root)
    for candidate in (vault / "20-Areas" / "英语", vault):
        if candidate.is_dir():
            target_dir = candidate
            break
    else:
        return False

    # Escape phrase for grep: quote it, lowercase for case-insensitive intent
    pattern = f'phrase:.*"{phrase}"'
    result = subprocess.run(
        ["grep", "-rli", "--include=*.md", pattern, str(target_dir)],
        capture_output=True, text=True, timeout=5,
    )
    return bool(result.stdout.strip())
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd ~/.claude/hooks/english-capture
pytest tests/test_dedup.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 6: Commit**

```bash
cd ~/.claude/hooks/english-capture
git add dedup.py tests/test_dedup.py tests/fixtures/mini-vault/
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "feat(dedup): add phrase_exists with case-insensitive grep"
```

---

## Task 5: dedup.py — `recent_phrases`

**Files:**
- Modify: `~/.claude/hooks/english-capture/dedup.py`
- Modify: `~/.claude/hooks/english-capture/tests/test_dedup.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_dedup.py`:

```python
from dedup import recent_phrases


def test_recent_phrases_returns_list(tmp_path):
    """Empty vault returns empty list."""
    assert recent_phrases(tmp_path, limit=10) == []


def test_recent_phrases_extracts_from_frontmatter():
    got = recent_phrases(FIXTURE, limit=10)
    assert "Ephemeral" in got or "ephemeral" in got
    assert "paradigm shift" in got
    assert len(got) == 2
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_dedup.py::test_recent_phrases_returns_list tests/test_dedup.py::test_recent_phrases_extracts_from_frontmatter -v
```

Expected: ImportError for `recent_phrases`.

- [ ] **Step 3: Implement `recent_phrases`**

Append to `dedup.py`:

```python
import re
from datetime import datetime

_PHRASE_RE = re.compile(r'^phrase:\s*"?([^"\n]+)"?\s*$', re.MULTILINE)


def recent_phrases(vault_root: Union[str, Path], limit: int = 10) -> list[str]:
    """Return up to `limit` most recently modified phrase values from vault
    frontmatter. Used as negative few-shot signal to Haiku ("already captured").
    """
    vault = Path(vault_root)
    for candidate in (vault / "20-Areas" / "英语", vault):
        if candidate.is_dir():
            target_dir = candidate
            break
    else:
        return []

    md_files = list(target_dir.rglob("*.md"))
    md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    out: list[str] = []
    for path in md_files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        match = _PHRASE_RE.search(text[:500])  # frontmatter is at top, cheap scan
        if match:
            out.append(match.group(1).strip())
        if len(out) >= limit:
            break
    return out
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_dedup.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add dedup.py tests/test_dedup.py
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "feat(dedup): add recent_phrases for Haiku negative few-shot"
```

---

## Task 6: md_writer.py — `write_vocab_md`

**Files:**
- Create: `~/.claude/hooks/english-capture/md_writer.py`
- Create: `~/.claude/hooks/english-capture/tests/test_md_writer.py`

- [ ] **Step 1: Write the failing test**

Write `tests/test_md_writer.py`:

```python
from pathlib import Path
import pytest
from md_writer import write_vocab_md


def test_write_vocab_md_creates_flashcard_file(tmp_path):
    item = {
        "phrase": "ephemeral",
        "category": "adjective",
        "cefr": "C1",
        "translation": "短暂的",
        "phonetic": "/ɪˈfemərəl/",
        "context": "The ephemeral nature of containers.",
        "usage_note": "Describes things that are brief.",
    }
    out_path = write_vocab_md(item, tmp_path)
    assert out_path == tmp_path / "20-Areas" / "英语" / "adjective" / "ephemeral.md"
    text = out_path.read_text()

    # Frontmatter checks
    assert 'phrase: "ephemeral"' in text
    assert "category: adjective" in text
    assert "cefr: C1" in text
    assert "source: claude-code-hook" in text
    assert "flashcards/english/vocab" in text

    # Body must have flashcard separator for SR plugin to recognize
    assert "?\n" in text or "\n?\n" in text
    assert "**短暂的**" in text
    assert "ephemeral /ɪˈfemərəl/" in text


def test_write_vocab_md_phrasal_verb_tag(tmp_path):
    item = {
        "phrase": "hand off",
        "category": "phrasal-verb",
        "cefr": "B2",
        "translation": "交接",
        "phonetic": "",
        "context": "",
        "usage_note": "",
    }
    out_path = write_vocab_md(item, tmp_path)
    assert out_path == tmp_path / "20-Areas" / "英语" / "phrasal-verb" / "hand-off.md"
    text = out_path.read_text()
    assert "flashcards/english/phrasal" in text


def test_write_vocab_md_slug_lowercase_hyphenated(tmp_path):
    item = {
        "phrase": "Paradigm Shift",
        "category": "collocation",
        "cefr": "C1",
        "translation": "范式转变",
        "phonetic": "",
        "context": "",
        "usage_note": "",
    }
    out_path = write_vocab_md(item, tmp_path)
    assert out_path.name == "paradigm-shift.md"
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_md_writer.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `write_vocab_md`**

Write `md_writer.py`:

```python
"""Generate Obsidian flashcard md files from filter results.

Output format matches the migration task's template so Spaced Repetition
plugin auto-detects flashcards via the `?` separator.
"""
import re
from datetime import date
from pathlib import Path
from typing import Union


_CATEGORY_TAG_GROUP = {
    "adjective": "vocab",
    "noun": "vocab",
    "verb": "vocab",
    "adverb": "vocab",
    "phrasal-verb": "phrasal",
    "collocation": "collocation",
    "idiom": "idiom",
}


def _slugify(text: str) -> str:
    """Lowercase; non-alphanumerics become hyphens; collapse runs; trim."""
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:40] if s else "untitled"


def write_vocab_md(item: dict, vault_root: Union[str, Path]) -> Path:
    """Write a single vocab md file; return the created path."""
    vault = Path(vault_root)
    category = item["category"]
    group = _CATEGORY_TAG_GROUP.get(category, "vocab")

    target_dir = vault / "20-Areas" / "英语" / category
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(item["phrase"])
    out_path = target_dir / f"{slug}.md"

    phonetic = item.get("phonetic", "") or ""
    phrase_display = f"{item['phrase']} {phonetic}".strip()
    context = item.get("context", "") or "（无）"
    usage = item.get("usage_note", "") or ""

    content = f"""---
type: english-vocab
category: {category}
cefr: {item['cefr']}
phrase: "{item['phrase']}"
phonetic: "{phonetic}"
created: {date.today().isoformat()}
source: claude-code-hook
tags:
  - flashcards/english/{group}
---

# {item['phrase']}

{phrase_display}
?
**{item['translation']}**
"""
    if usage:
        content += f"\n{usage}\n"

    content += f"""
## 原文上下文

{context}
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_md_writer.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add md_writer.py tests/test_md_writer.py
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "feat(md_writer): write vocab flashcard md files to vault"
```

---

## Task 7: md_writer.py — `write_grammar_md`

**Files:**
- Modify: `~/.claude/hooks/english-capture/md_writer.py`
- Modify: `~/.claude/hooks/english-capture/tests/test_md_writer.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_md_writer.py`:

```python
from md_writer import write_grammar_md


def test_write_grammar_md_creates_flashcard(tmp_path):
    item = {
        "original": "more 可读性",
        "corrected": "more readable",
        "error_type": "word_choice",
        "explanation": "与 more 搭配时应使用形容词 readable",
    }
    out_path = write_grammar_md(item, tmp_path)
    assert out_path.parent == tmp_path / "20-Areas" / "英语" / "grammar"
    assert out_path.suffix == ".md"
    text = out_path.read_text()
    assert "type: english-grammar" in text
    assert "category: word_choice" in text
    assert "**more readable**" in text
    assert "more 可读性" in text  # original preserved
    assert "?\n" in text
```

- [ ] **Step 2: Run to confirm fail**

```bash
pytest tests/test_md_writer.py::test_write_grammar_md_creates_flashcard -v
```

Expected: ImportError for `write_grammar_md`.

- [ ] **Step 3: Implement `write_grammar_md`**

Append to `md_writer.py`:

```python
def write_grammar_md(item: dict, vault_root: Union[str, Path]) -> Path:
    """Write a single grammar correction md flashcard."""
    vault = Path(vault_root)
    target_dir = vault / "20-Areas" / "英语" / "grammar"
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(item["original"])
    out_path = target_dir / f"{slug}.md"

    content = f"""---
type: english-grammar
category: {item['error_type']}
created: {date.today().isoformat()}
source: claude-code-hook
tags:
  - flashcards/english/grammar
---

# {item['original']} → {item['corrected']}

## 原句（错 / 中式）
> {item['original']}

## 地道说法
?
**{item['corrected']}**

## 为什么
{item['explanation']}
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_md_writer.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add md_writer.py tests/test_md_writer.py
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "feat(md_writer): write grammar correction flashcard md files"
```

---

## Task 8: prompt_builder.py — `build_system_prompt` + `JSON_SCHEMA`

**Files:**
- Create: `~/.claude/hooks/english-capture/prompt_builder.py`
- Create: `~/.claude/hooks/english-capture/tests/test_prompt_builder.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_prompt_builder.py`:

```python
import json
from prompt_builder import build_system_prompt, JSON_SCHEMA


def test_system_prompt_includes_profile():
    profile = "## USER PROFILE\nI know all CS terms.\n"
    prompt = build_system_prompt(profile_text=profile, recent_phrases=[])
    assert "I know all CS terms" in prompt
    assert "USER PROFILE" in prompt


def test_system_prompt_includes_recent_phrases_as_skip_signal():
    prompt = build_system_prompt(
        profile_text="profile body",
        recent_phrases=["ephemeral", "paradigm shift", "hand off"],
    )
    assert "ephemeral" in prompt
    assert "paradigm shift" in prompt
    assert "hand off" in prompt
    assert "already" in prompt.lower() or "recently" in prompt.lower()


def test_system_prompt_handles_empty_recent_phrases():
    prompt = build_system_prompt(profile_text="profile", recent_phrases=[])
    # Should not crash, should still include profile
    assert "profile" in prompt


def test_json_schema_valid():
    # Parse and validate structure
    schema = json.loads(json.dumps(JSON_SCHEMA))  # round-trip check
    assert schema["type"] == "object"
    assert "vocabulary" in schema["properties"]
    assert "grammar" in schema["properties"]
    v_item = schema["properties"]["vocabulary"]["items"]
    assert "phrase" in v_item["properties"]
    assert "category" in v_item["properties"]
    assert set(v_item["properties"]["category"]["enum"]) >= {
        "adjective", "noun", "verb", "phrasal-verb", "collocation", "idiom"
    }
```

- [ ] **Step 2: Run to confirm fail**

```bash
pytest tests/test_prompt_builder.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement**

Write `prompt_builder.py`:

```python
"""Assemble system prompt and JSON schema for Haiku filter call."""
from typing import Iterable


JSON_SCHEMA = {
    "type": "object",
    "required": ["vocabulary", "grammar", "skip_count", "skip_reasons"],
    "properties": {
        "vocabulary": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["phrase", "category", "cefr", "translation"],
                "properties": {
                    "phrase": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "adjective", "noun", "verb", "adverb",
                            "phrasal-verb", "collocation", "idiom",
                        ],
                    },
                    "cefr": {"type": "string", "enum": ["B1", "B2", "C1", "C2"]},
                    "translation": {"type": "string"},
                    "phonetic": {"type": "string"},
                    "context": {"type": "string"},
                    "usage_note": {"type": "string"},
                },
            },
        },
        "grammar": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["original", "corrected", "error_type", "explanation"],
                "properties": {
                    "original": {"type": "string"},
                    "corrected": {"type": "string"},
                    "error_type": {
                        "type": "string",
                        "enum": ["word_choice", "collocation", "grammar"],
                    },
                    "explanation": {"type": "string"},
                },
            },
        },
        "skip_count": {"type": "integer"},
        "skip_reasons": {"type": "string"},
    },
}


_PROMPT_TEMPLATE = """You are an English learning assistant for a Chinese senior developer.

{profile_section}

{recent_section}

## TASK

Given USER_INPUT and CLAUDE_OUTPUT in the user message below, extract:

1. **vocabulary** — words and phrases worth learning per the USER PROFILE rules.
   For each, pick category strictly from this list (do not invent new ones):
     - For words: adjective | noun | verb | adverb
     - For phrases: phrasal-verb | collocation | idiom

2. **grammar** — real language lessons only (word choice, collocation, grammar).
   Skip trivial punctuation/spacing/casing fixes.

**Default to SKIP. Target 30-40% keep rate. Quality > quantity.**

## OUTPUT

Return ONLY valid JSON matching the provided schema. No prose, no explanations
outside the JSON. Also include integer `skip_count` and a short
`skip_reasons` string (e.g. "cs_jargon: 3, too_common: 2").
"""


def build_system_prompt(profile_text: str, recent_phrases: Iterable[str]) -> str:
    """Compose the system prompt: profile + recent-captured negative few-shot + task."""
    profile_text = (profile_text or "").strip()
    if profile_text:
        profile_section = f"## USER PROFILE\n\n{profile_text}"
    else:
        profile_section = (
            "## USER PROFILE\n\n"
            "(No custom profile. Apply default rule: skip CET-4 and below, "
            "skip CS/tool jargon; extract literary, formal, idiomatic, "
            "academic non-CS vocabulary.)"
        )

    phrases = list(recent_phrases)
    if phrases:
        items = "\n".join(f"- {p}" for p in phrases)
        recent_section = (
            "## RECENTLY CAPTURED (already in library — DO NOT extract these again)\n\n"
            f"{items}"
        )
    else:
        recent_section = ""

    return _PROMPT_TEMPLATE.format(
        profile_section=profile_section,
        recent_section=recent_section,
    )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_prompt_builder.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add prompt_builder.py tests/test_prompt_builder.py
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "feat(prompt): build_system_prompt + JSON_SCHEMA for Haiku filter"
```

---

## Task 9: gemini_client.py — Gemini REST API wrapper

**Files:**
- Create: `~/.claude/hooks/english-capture/gemini_client.py`
- Create: `~/.claude/hooks/english-capture/tests/test_gemini_client.py`

Implementation uses Python stdlib only: `urllib.request` + `json`. No `requests` dep.

- [ ] **Step 1: Write failing unit test (mocked urlopen)**

Write `tests/test_gemini_client.py`:

```python
import json
from unittest.mock import patch, MagicMock
from io import BytesIO
import pytest
from gemini_client import extract, GeminiError


def _make_gemini_response(inner_json: dict) -> bytes:
    """Gemini wraps response in candidates[].content.parts[].text (as JSON string)."""
    return json.dumps({
        "candidates": [{
            "content": {
                "parts": [{"text": json.dumps(inner_json)}],
                "role": "model"
            },
            "finishReason": "STOP",
        }],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 200},
    }).encode("utf-8")


@patch("gemini_client.urlopen")
def test_extract_parses_nested_json(mock_urlopen):
    inner = {
        "vocabulary": [
            {"phrase": "ephemeral", "category": "adjective", "cefr": "C1", "translation": "短暂"},
        ],
        "grammar": [],
        "skip_count": 3,
        "skip_reasons": "cs_jargon: 3",
    }
    mock_urlopen.return_value.__enter__.return_value.read.return_value = _make_gemini_response(inner)
    result = extract(
        user_input="I use cherry-pick often",
        claude_output="The ephemeral nature of containers",
        system_prompt="system",
        json_schema={"type": "object"},
        api_key="test-key",
    )
    assert result["vocabulary"][0]["phrase"] == "ephemeral"
    assert result["skip_count"] == 3


@patch("gemini_client.urlopen")
def test_extract_raises_on_http_error(mock_urlopen):
    from urllib.error import HTTPError
    mock_urlopen.side_effect = HTTPError(
        url="https://...", code=429, msg="rate limit",
        hdrs=None, fp=BytesIO(b'{"error":"rate limit"}'),
    )
    with pytest.raises(GeminiError):
        extract("in", "out", "sys", {}, "test-key")


@patch("gemini_client.urlopen")
def test_extract_builds_correct_url_and_payload(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = _make_gemini_response({
        "vocabulary": [], "grammar": [], "skip_count": 0, "skip_reasons": ""
    })
    extract("in", "out", "sys", {"type": "object"}, api_key="my-key", model="gemini-2.5-flash-lite")

    call = mock_urlopen.call_args[0][0]  # Request object
    assert "gemini-2.5-flash-lite:generateContent" in call.full_url
    assert "key=my-key" in call.full_url

    body = json.loads(call.data.decode("utf-8"))
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseSchema"] == {"type": "object"}
    # system prompt + user content in contents
    combined_text = body["contents"][0]["parts"][0]["text"]
    assert "sys" in combined_text
    assert "in" in combined_text
    assert "out" in combined_text
```

- [ ] **Step 2: Run to confirm fail**

```bash
cd ~/.claude/hooks/english-capture
pytest tests/test_gemini_client.py -v
```

Expected: ImportError for `gemini_client`.

- [ ] **Step 3: Implement**

Write `gemini_client.py`:

```python
"""Call Google Gemini 2.5 Flash Lite REST API to extract vocab from transcripts.

Uses Python stdlib urllib — no third-party deps.
Free tier: 1500 requests/day, 1M tokens/day. Well within our hook usage.
"""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import Any


DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_TIMEOUT = 30
ENDPOINT_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)


class GeminiError(RuntimeError):
    """Raised when Gemini API call fails or returns unparseable output."""


def extract(
    user_input: str,
    claude_output: str,
    system_prompt: str,
    json_schema: dict,
    api_key: str,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """POST to Gemini generateContent endpoint with response schema.
    
    Returns the parsed JSON dict that matches the schema.
    """
    if not api_key:
        raise GeminiError("api_key is required")

    combined_text = (
        f"{system_prompt}\n\n"
        f"USER_INPUT:\n{user_input}\n\n"
        f"CLAUDE_OUTPUT:\n{claude_output}"
    )

    payload = {
        "contents": [{"parts": [{"text": combined_text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": json_schema,
        },
    }

    url = ENDPOINT_TEMPLATE.format(model=model, key=api_key)
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.fp.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise GeminiError(f"HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise GeminiError(f"network error: {exc.reason}") from exc

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GeminiError(f"non-JSON response: {raw[:500]}") from exc

    try:
        text = envelope["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise GeminiError(f"unexpected response shape: {envelope}") from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeminiError(f"inner text is not valid JSON: {text[:500]}") from exc
```

- [ ] **Step 4: Run unit tests to verify pass**

```bash
pytest tests/test_gemini_client.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Live smoke test (real Gemini API call)**

```bash
cd ~/.claude/hooks/english-capture
API_KEY=$(python3 -c "import json; print(json.load(open('/Users/wanmao/.english-capture/config.json'))['gemini_api_key'])")
python3 -c "
from gemini_client import extract
from prompt_builder import build_system_prompt, JSON_SCHEMA
import os, json

sys_prompt = build_system_prompt(
    profile_text='Skip CS terms. Keep literary/formal words.',
    recent_phrases=[],
)
result = extract(
    user_input='我之前都是 cherry-pick',
    claude_output='The ephemeral nature of containers means they can be destroyed easily.',
    system_prompt=sys_prompt,
    json_schema=JSON_SCHEMA,
    api_key=os.environ['API_KEY'],
)
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

Expected: valid JSON with `ephemeral` extracted and `cherry-pick` skipped. If this fails, debug.

- [ ] **Step 6: Commit**

```bash
git add gemini_client.py tests/test_gemini_client.py
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "feat(gemini_client): REST API wrapper for Gemini 2.5 Flash Lite"
```

---

## Task 10: capture.py — orchestrator

**Files:**
- Create: `~/.claude/hooks/english-capture/capture.py`
- Create: `~/.claude/hooks/english-capture/config.example.json`
- Create: `~/.claude/hooks/english-capture/tests/test_capture_integration.py`

- [ ] **Step 1: Write config.example.json**

```json
{
  "vault_path": "/Users/wanmao/Library/Mobile Documents/iCloud~md~obsidian/Documents",
  "llm_provider": "gemini",
  "gemini_api_key": "PASTE_YOUR_KEY_HERE",
  "gemini_model": "gemini-2.5-flash-lite",
  "timeout_seconds": 30,
  "log_level": "INFO"
}
```

Runtime config `~/.english-capture/config.json` should be mode 0600 (already created).

- [ ] **Step 2: Write capture.py**

```python
#!/usr/bin/env python3
"""CC Stop hook entry point: read transcript, filter via Haiku, write md flashcards."""
import json
import os
import sys
from datetime import date
from pathlib import Path

# Make sibling modules importable when invoked as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript import read_transcript, extract_last_turn
from prompt_builder import build_system_prompt, JSON_SCHEMA
from gemini_client import extract as gemini_extract, GeminiError
from dedup import phrase_exists, recent_phrases
from md_writer import write_vocab_md, write_grammar_md
from queue import QueueManager
from logger import Logger


BASE_DIR = Path(os.path.expanduser("~/.english-capture"))
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
FALLBACK_CONFIG = Path(__file__).resolve().parent / "config.example.json"
USER_PROFILE_PATH = Path(__file__).resolve().parent / "user_profile.md"
QUEUE_PATH = BASE_DIR / "queue.json"
LOG_DIR = BASE_DIR / "logs"


def load_config() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else FALLBACK_CONFIG
    return json.loads(path.read_text())


def read_stdin_event() -> dict:
    """CC passes event JSON on stdin."""
    try:
        return json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return {}


def process_extraction(result: dict, vault_root: Path, logger: Logger) -> dict:
    """Write md files for each kept item; return stats dict."""
    saved = 0
    dup = 0
    errors = 0

    for item in result.get("vocabulary", []):
        phrase = item.get("phrase", "").strip()
        if not phrase:
            continue
        if phrase_exists(phrase, vault_root):
            dup += 1
            logger.log("INFO", f"dup: {phrase}")
            continue
        try:
            path = write_vocab_md(item, vault_root)
            saved += 1
            logger.log("INFO", f"saved vocab: {phrase} → {path.name}")
        except Exception as e:
            errors += 1
            logger.log("ERROR", f"write vocab failed for '{phrase}': {e}")

    for item in result.get("grammar", []):
        original = item.get("original", "").strip()
        if not original:
            continue
        try:
            path = write_grammar_md(item, vault_root)
            saved += 1
            logger.log("INFO", f"saved grammar: {original[:30]} → {path.name}")
        except Exception as e:
            errors += 1
            logger.log("ERROR", f"write grammar failed: {e}")

    return {"saved": saved, "dup": dup, "errors": errors}


def main() -> int:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = Logger(str(LOG_DIR))

    event = read_stdin_event()
    if event.get("hook_event_name") and event["hook_event_name"] != "Stop":
        return 0

    transcript_path = event.get("transcript_path")
    if not transcript_path or not os.path.exists(transcript_path):
        return 0

    messages = read_transcript(transcript_path)
    user_input, claude_output = extract_last_turn(messages)
    if not user_input.strip() and not claude_output.strip():
        return 0

    config = load_config()
    vault_root = Path(os.path.expanduser(config["vault_path"]))
    if not vault_root.exists():
        logger.log("WARN", f"vault path not accessible: {vault_root}")
        return 0

    try:
        profile_text = USER_PROFILE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        profile_text = ""
        logger.log("WARN", "user_profile.md not found; using defaults")

    recent = recent_phrases(vault_root, limit=10)
    system_prompt = build_system_prompt(profile_text, recent)

    queue = QueueManager(str(QUEUE_PATH))

    api_key = config.get("gemini_api_key", "")
    model = config.get("gemini_model", "gemini-2.5-flash-lite")
    timeout = config.get("timeout_seconds", 30)

    # Drain queue first
    queued = queue.load()
    remaining = []
    for q_item in queued:
        try:
            result = gemini_extract(
                q_item["user_input"], q_item["claude_output"],
                system_prompt, JSON_SCHEMA,
                api_key=api_key, model=model, timeout=timeout,
            )
            stats = process_extraction(result, vault_root, logger)
            logger.log("INFO", f"queue drained: {stats}")
        except GeminiError as e:
            logger.log("WARN", f"queue item failed again: {e}")
            remaining.append(q_item)
    queue.clear()
    for q_item in remaining:
        queue.add(q_item)

    # Current session
    try:
        result = gemini_extract(
            user_input, claude_output, system_prompt, JSON_SCHEMA,
            api_key=api_key, model=model, timeout=timeout,
        )
        stats = process_extraction(result, vault_root, logger)
        skip_count = result.get("skip_count", 0)
        logger.log(
            "INFO",
            f"extracted: saved={stats['saved']} dup={stats['dup']} skip={skip_count}",
        )
    except GeminiError as e:
        logger.log("WARN", f"haiku failed, queueing: {e}")
        queue.add({"user_input": user_input, "claude_output": claude_output})

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Write integration test (mocked Haiku)**

Write `tests/test_capture_integration.py`:

```python
import json
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parent.parent


def test_capture_main_no_op_on_empty_stdin(tmp_path, monkeypatch):
    """Empty stdin → exit 0, no side effects."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = subprocess.run(
        ["python3", str(REPO / "capture.py")],
        input="", capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0


def test_capture_main_no_op_on_missing_transcript(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    payload = json.dumps({
        "hook_event_name": "Stop",
        "transcript_path": "/does/not/exist.jsonl",
    })
    result = subprocess.run(
        ["python3", str(REPO / "capture.py")],
        input=payload, capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_capture_integration.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Write `config.json` (actual runtime config)**

**Don't commit this file — it's per-machine.**

```bash
mkdir -p ~/.english-capture
cp ~/.claude/hooks/english-capture/config.example.json ~/.english-capture/config.json
# Edit if paths differ from defaults
```

Also, copy it into the hook repo as `config.json` for import (but add to .gitignore):

```bash
# .gitignore already has this pattern? If not:
echo "config.json" >> ~/.claude/hooks/english-capture/.gitignore
cp ~/.claude/hooks/english-capture/config.example.json ~/.claude/hooks/english-capture/config.json
```

Actually: the code reads `config.json` next to the script OR falls back to `config.example.json`. So we can just use `config.example.json` for now. Skip the copy — **remove the above cp commands if you already have the fallback working**.

- [ ] **Step 6: End-to-end manual test with a real transcript**

Find a real CC transcript to test with:

```bash
ls ~/.claude/projects/*/sessions/*.jsonl 2>/dev/null | head -3
```

Pick one and run:

```bash
REAL_TRANSCRIPT=$(ls ~/.claude/projects/*/sessions/*.jsonl | head -1)
echo "{\"hook_event_name\": \"Stop\", \"transcript_path\": \"$REAL_TRANSCRIPT\"}" | \
  python3 ~/.claude/hooks/english-capture/capture.py
```

Expected: exit 0, see log entries in `~/.english-capture/logs/<today>.log`, possibly new md files in vault.

Inspect:
```bash
cat ~/.english-capture/logs/$(date +%Y-%m-%d).log
find ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/20-Areas/英语/ \
  -newer ~/.claude/hooks/english-capture/capture.py -type f
```

- [ ] **Step 7: Commit**

```bash
cd ~/.claude/hooks/english-capture
git add capture.py config.example.json tests/test_capture_integration.py .gitignore
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "feat(capture): main orchestrator + integration tests"
```

---

## Task 11: Enable the Stop hook in CC settings

**Files:**
- Modify: `~/.claude/settings.json`

- [ ] **Step 1: Inspect existing hooks**

```bash
cat ~/.claude/settings.json 2>/dev/null || echo "{}"
```

- [ ] **Step 2: Add the Stop hook entry**

If `~/.claude/settings.json` doesn't exist, create it:

```json
{
  "hooks": {
    "Stop": [
      {
        "command": "python3 /Users/wanmao/.claude/hooks/english-capture/capture.py",
        "timeout": 90
      }
    ]
  }
}
```

If it exists with other hooks, **manually merge** — preserve existing hooks and add this Stop entry.

**Use update-config skill** to do this properly (merge safely).

- [ ] **Step 3: Test the hook by ending a real CC session**

Open a new terminal, run `claude`, ask a trivial question with some English content (e.g., "what does 'serendipity' mean?"), then exit with `/exit`.

Within 60 seconds, check:
```bash
cat ~/.english-capture/logs/$(date +%Y-%m-%d).log
```

Expected: log entries showing extraction was attempted.

- [ ] **Step 4: Verify no recursion**

Check the log for infinite loops (same timestamp repeated many times). If you see this, `--bare` isn't suppressing hooks — investigate.

- [ ] **Step 5: No commit** (this task modifies user-level CC config, not the hook repo)

---

## Task 12: Deploy script + README

**Files:**
- Create: `~/.claude/hooks/english-capture/deploy-to-studio.sh`
- Create: `~/.claude/hooks/english-capture/README.md`

- [ ] **Step 1: Write deploy script**

```bash
cat > ~/.claude/hooks/english-capture/deploy-to-studio.sh <<'EOF'
#!/usr/bin/env bash
# Deploy the hook source to Mac Studio via rsync.
# Runtime config (~/.english-capture/) is NOT synced — each machine has its own.
set -euo pipefail

SRC="$HOME/.claude/hooks/english-capture/"
DST="macstudio:.claude/hooks/english-capture/"

rsync -av \
  --exclude .git \
  --exclude __pycache__ \
  --exclude ".pytest_cache" \
  --exclude "config.json" \
  "$SRC" "$DST"

echo ""
echo "✅ Deployed to Mac Studio."
echo ""
echo "⚠️  On first install, also:"
echo "    1. ssh macstudio"
echo "    2. mkdir -p ~/.english-capture && cp ~/.claude/hooks/english-capture/config.example.json ~/.english-capture/config.json"
echo "    3. Edit vault_path in config.json if needed"
echo "    4. Add Stop hook entry to ~/.claude/settings.json on Studio"
EOF
chmod +x ~/.claude/hooks/english-capture/deploy-to-studio.sh
```

- [ ] **Step 2: Write README**

```markdown
# english-capture — CC Stop hook for auto-capturing English vocab

Extracts high-value English vocabulary and grammar corrections from every CC session's transcript; writes atomic flashcard md files into the Obsidian vault at `20-Areas/英语/`.

## How it works

1. CC Stop event fires → `capture.py` runs in background
2. Reads last turn of transcript (user_input + claude_output)
3. Calls Haiku via `claude -p --bare` (no API key; uses subscription)
4. Haiku filters per `user_profile.md` rules + recent-captured skip list
5. For each kept item: dedup against vault, write new md file to `20-Areas/英语/{category}/`
6. Obsidian SR plugin picks up new cards on next open

## Installation (per machine)

```bash
# 1. Clone / copy this directory to ~/.claude/hooks/english-capture/
# 2. Set up runtime config
mkdir -p ~/.english-capture
cp ~/.claude/hooks/english-capture/config.example.json ~/.english-capture/config.json
# 3. Edit vault_path in config.json if different
# 4. Add Stop hook to ~/.claude/settings.json:
#    "hooks": {
#      "Stop": [{"command": "python3 ~/.claude/hooks/english-capture/capture.py", "timeout": 90}]
#    }
```

## Cross-machine sync

```bash
# From Mac mini (source of truth):
./deploy-to-studio.sh
```

Source is in git (local repo, no remote by default).

## Editing filter rules

`user_profile.md` — what to SKIP vs KEEP. Edit this and commit to refine filter over time.

## Logs

`~/.english-capture/logs/YYYY-MM-DD.log`

## Tests

```bash
cd ~/.claude/hooks/english-capture
pytest -v
```
```

- [ ] **Step 3: Commit**

```bash
cd ~/.claude/hooks/english-capture
git add deploy-to-studio.sh README.md
git -c user.email=wequart@gmail.com -c user.name=wanmao \
  commit -m "docs: README + deploy-to-studio helper"
```

---

## Task 13: Live shakedown — 24h on Mac mini before rolling out

**Files:** None (operational task).

- [ ] **Step 1: Leave Mac mini running with hook enabled for 24h of normal use**

Use CC as you normally would. Let multiple Stop events fire.

- [ ] **Step 2: Inspect log after 24h**

```bash
cat ~/.english-capture/logs/$(date +%Y-%m-%d).log | tail -50
```

Look for:
- `extracted: saved=N dup=M skip=K` lines — normal operation
- `WARN` / `ERROR` lines — investigate
- Repeated infinite-style loops — indicates recursion issue

- [ ] **Step 3: Inspect vault additions**

```bash
find ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/20-Areas/英语/ \
  -type f -name "*.md" -newer ~/.claude/hooks/english-capture/capture.py | wc -l
```

How many new files appeared? Spot-check a few: do they look like good flashcards?

- [ ] **Step 4: Quality check**

Open 5 random new md files in Obsidian. Ask:
- Does the phrase look worth learning?
- Is it something you already knew (should have been skipped)?
- Is the translation accurate?

If quality is poor → revise `user_profile.md` with more examples, or tighten `prompt_builder.py` rules. Re-commit.

- [ ] **Step 5: Only when satisfied, deploy to Studio**

```bash
~/.claude/hooks/english-capture/deploy-to-studio.sh
```

Then SSH to Studio and add the Stop hook entry on that side (see deploy script output).

**No commit in this task.**

---

## Self-Review

This plan was checked for:

- **Spec coverage**: all 6 Python modules from spec have implementing tasks (transcript, dedup, md_writer, prompt_builder, haiku_client, capture). logger + queue copied verbatim. user_profile.md reused. JSON schema defined. Dedup mechanism specified. Cross-machine deployment covered.
- **Placeholder scan**: no TBD/TODO. Each step has exact code or exact commands.
- **Type consistency**: `phrase_exists(phrase, vault_root)` signature consistent across spec, dedup.py, capture.py, tests. `write_vocab_md(item, vault_root)` likewise. `GeminiError` is defined in gemini_client.py and caught in capture.py.

One gap caught during review: Task 10 Step 5 was ambiguous about whether to copy `config.example.json` to `config.json` in the repo itself. Clarified: use fallback to `config.example.json`; don't maintain a separate `config.json` in repo. Per-machine runtime config lives in `~/.english-capture/config.json` (outside repo).
