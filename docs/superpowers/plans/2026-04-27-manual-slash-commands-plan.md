# Manual Slash Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace V2's Stop-hook-driven auto-vocab extraction with three user-initiated slash commands (`/eng w/s/e`), repurpose the Stop hook to grammar-only correction, and ship a cross-device `install.sh` that bootstraps everything on a fresh Mac.

**Architecture:** Slash command template (`eng.md`) lets Claude find context in the current transcript and call a pure Python CLI (`add_card.py`). The Stop hook (`grammar_hook.py`) checks user's last English input for grammar errors and writes a flashcard if errors exist. Both share `openrouter.py` / `transcript.py` / `vault.py` / `prompts.py` / `queue.py` / `logger.py`. All Markdown cards go to the user's Obsidian vault at `20-Areas/英语/{category}/`, picked up by Obsidian Spaced Repetition plugin via iCloud sync.

**Tech Stack:** Python 3.10+ stdlib (urllib, no httpx), pytest for tests, jq for JSON manipulation in `install.sh`, OpenRouter API (model `qwen/qwen3-235b-a22b-2507`).

**Spec:** `~/.claude/hooks/english-capture/docs/superpowers/specs/2026-04-27-manual-slash-commands-design.md`

---

## File structure (final state after all tasks)

```
~/.claude/hooks/english-capture/
├── .git/                         # NEW — created in Task 0.1
├── .gitignore                    # NEW
├── README.md                     # NEW (Task 12)
├── pyproject.toml                # NEW (Task 0.3)
├── install.sh                    # NEW (Task 11)
├── config.example.json           # NEW (Task 10)
├── eng.md                        # NEW (Task 9) — slash command template
│
├── add_card.py                   # NEW (Task 7) — CLI entry
├── grammar_hook.py               # NEW (Task 8) — Stop hook entry
│
├── openrouter.py                 # NEW (Task 1)
├── transcript.py                 # NEW (Task 4)
├── vault.py                      # NEW (Task 5)
├── prompts.py                    # NEW (Task 6)
├── queue.py                      # NEW (Task 3)
├── logger.py                     # NEW (Task 2)
│
├── tests/
│   ├── conftest.py               # NEW
│   ├── fixtures/                 # MIGRATED from V2 (Task 0.2)
│   ├── test_openrouter.py        # NEW (Task 1)
│   ├── test_logger.py            # NEW (Task 2)
│   ├── test_queue.py             # NEW (Task 3)
│   ├── test_transcript.py        # NEW (Task 4)
│   ├── test_vault.py             # NEW (Task 5)
│   ├── test_prompts.py           # NEW (Task 6)
│   ├── test_add_card.py          # NEW (Task 7)
│   └── test_grammar_hook.py      # NEW (Task 8)
│
└── docs/superpowers/             # KEPT — already exists
    ├── plans/
    │   ├── 2026-04-22-english-capture-hook.md  # KEPT (V2 historical)
    │   └── 2026-04-27-manual-slash-commands-plan.md  # this file
    └── specs/
        ├── 2026-04-22-english-capture-hook-design.md  # KEPT (V2 historical)
        └── 2026-04-27-manual-slash-commands-design.md  # KEPT
```

**Out of repo, on user machine** (not committed; created by `install.sh`):
```
~/.english-capture/
├── config.json          # OpenRouter key + vault path (chmod 600)
├── queue.json           # retry queue
└── logs/YYYY-MM-DD.log
~/.claude/commands/eng.md   # symlink → repo/eng.md
~/.claude/settings.json     # Stop hook entry upserted by install.sh
```

---

## Task 0.1: Clean-slate git repo bootstrap

> **REVISED 2026-04-27** (user decision): repo will be **public** at `wanmaoor/english-capture`. To avoid leaking V2's `user_profile.md` (contains personal details — name, role, English level, learning preferences) into git history forever, the V2 archive snapshot is **skipped**. The first commit goes directly into a clean state. The original V2 code is documented elsewhere (the retired `~/projects/english-copilot/` repo's `RETIREMENT.md` covers V2's full architecture history).
>
> This task therefore consolidates the originally-planned Tasks 0.1 + 0.2 (wipe) into a single bootstrap operation: physically delete V2 files first, then `git init` on the clean directory, so V2 code never enters git history.

**Files:**
- Delete: all `.py` files in repo root, `config.example.json`, `user_profile.md`, `pyproject.toml`, `tests/test_*.py`, `tests/__init__.py`, `tests/fixtures/__init__.py`, `__pycache__/`, `.pytest_cache/`
- Keep: `docs/` (contains the spec and this plan), `tests/fixtures/mini-vault/` (reusable test fixture data)
- Create: `.gitignore` (overwrite the existing V2 one)

> Note: the V1 `~/projects/english-copilot/RETIREMENT.md` lives in the *retired* V1 repo, NOT in this hook directory. Earlier drafts of this plan mistakenly listed it as something to keep here.

- [ ] **Step 1: Verify gh CLI is authenticated as `wanmaoor`**

```bash
gh auth status
```

Expected: `✓ Logged in to github.com account wanmaoor`. **If you see a different account or invalid token, STOP and report BLOCKED** — the controller has already verified this. The username is **`wanmaoor`** (note the trailing "or"), not `wanmao`.

- [ ] **Step 2: Sanity-check what will be deleted**

```bash
cd ~/.claude/hooks/english-capture && ls *.py *.json *.md *.toml 2>/dev/null
```

Expected V2 files to disappear: `capture.py`, `dedup.py`, `explicit_terms.py`, `logger.py`, `md_writer.py`, `openrouter_client.py`, `prompt_builder.py`, `queue.py`, `transcript.py`, `config.example.json`, `user_profile.md`, `pyproject.toml`.

- [ ] **Step 3: Physically delete V2 files (regular `rm`, no git involvement yet)**

```bash
cd ~/.claude/hooks/english-capture && rm -f \
  capture.py dedup.py explicit_terms.py logger.py md_writer.py \
  openrouter_client.py prompt_builder.py queue.py transcript.py \
  config.example.json user_profile.md pyproject.toml
```

- [ ] **Step 4: Delete old V2 test files and pycache**

```bash
cd ~/.claude/hooks/english-capture && rm -f tests/test_*.py tests/__init__.py tests/fixtures/__init__.py
cd ~/.claude/hooks/english-capture && rm -rf __pycache__ tests/__pycache__ .pytest_cache
```

- [ ] **Step 5: Verify the surviving file inventory**

```bash
cd ~/.claude/hooks/english-capture && ls -la
ls tests/ tests/fixtures/
```

Expected at root: `docs/`, `tests/`, `.gitignore` (the V2 one — about to be overwritten). Inside `tests/`: only `fixtures/`. Inside `tests/fixtures/`: `mini-vault/` directory (with sample card md files).

- [ ] **Step 6: Overwrite `.gitignore` with the new content**

`~/.claude/hooks/english-capture/.gitignore`:

```
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage
*.egg-info/
.DS_Store

# Runtime config & state — lives in ~/.english-capture/, not in repo
config.json
```

- [ ] **Step 7: git init + initial commit (clean state)**

```bash
cd ~/.claude/hooks/english-capture && git init
cd ~/.claude/hooks/english-capture && git add .
```

Verify what's about to be committed (must NOT include any V2 .py files or user_profile.md):

```bash
cd ~/.claude/hooks/english-capture && git status --short
```

Expected staged additions: `.gitignore`, `docs/...`, `tests/fixtures/mini-vault/...`. Nothing else. **If you see anything unexpected, STOP and report — do not commit.**

Then commit:

```bash
cd ~/.claude/hooks/english-capture && git commit -m "$(cat <<'EOF'
chore: initial commit — clean slate for manual-slash rebuild

Bootstraps a fresh git repo for the manual slash command rewrite per
docs/superpowers/specs/2026-04-27-manual-slash-commands-design.md.

Note: V2 auto-vocab code is intentionally NOT included in git history.
The V2 design (deleted from this directory before this commit) is documented
in the retired ~/projects/english-copilot/RETIREMENT.md as architectural
history. This repo starts clean to avoid baking personal-profile content
into a public git history.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 8: Create GitHub PUBLIC repo and push**

```bash
cd ~/.claude/hooks/english-capture && gh repo create wanmaoor/english-capture --public --source=. --push --description "Manual slash commands for capturing English vocabulary into Obsidian (personal tool)"
```

Expected: `✓ Created repository wanmaoor/english-capture on GitHub` followed by push output.

If the repo name is taken, STOP and report BLOCKED.

- [ ] **Step 9: Verify the remote and the published commit**

```bash
cd ~/.claude/hooks/english-capture && git remote -v
cd ~/.claude/hooks/english-capture && git log --oneline
```

Expected:
- `origin git@github.com:wanmaoor/english-capture.git` (push) — note this will be SSH because `gh` config has `Git operations protocol: ssh`
- Exactly one commit: the "chore: initial commit — clean slate" one

- [ ] **Step 10: Final safety scan (paranoia check)**

```bash
cd ~/.claude/hooks/english-capture && git ls-files | xargs grep -lE "sk-or-v1-[A-Za-z0-9]{40,}|wanmao.*senior software engineer|CET-6 level" 2>/dev/null
```

Expected output: **empty** (no matches). If any file is reported, STOP — that means a sensitive string survived the wipe.

---

## Task 0.2: (REMOVED — folded into Task 0.1)

> Originally "Wipe old V2 code", now consolidated into Task 0.1 step 3-4 to ensure V2 files never enter git history. Skip this task; proceed to Task 0.3.

---

## Task 0.3: Project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "english-capture"
version = "0.2.0"
description = "Manual slash commands for capturing English vocabulary into Obsidian"
requires-python = ">=3.10"
dependencies = []  # stdlib only at runtime

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures."""
import json
import os
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Empty Obsidian vault rooted at tmp_path; create the 20-Areas/英语 dir."""
    area = tmp_path / "20-Areas" / "英语"
    area.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_config(tmp_path: Path) -> dict:
    """Minimal config dict for tests that need one."""
    return {
        "openrouter_api_key": "test-key",
        "openrouter_model": "qwen/qwen3-235b-a22b-2507",
        "vault_path": str(tmp_path),
        "timeout_seconds": 30,
    }
```

- [ ] **Step 3: Install dev dependencies and verify pytest runs**

```bash
cd ~/.claude/hooks/english-capture
pip install -e ".[dev]"
pytest --collect-only
```

Expected: `collected 0 items` (no tests yet, but pytest is configured).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tests/conftest.py
git commit -m "$(cat <<'EOF'
chore: project skeleton (pyproject + conftest)

Stdlib-only runtime; pytest as the only dev dep. conftest exposes tmp_vault and
sample_config fixtures shared across module tests.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push
```

---

## Task 1: `openrouter.py` — Qwen API client

**Files:**
- Create: `openrouter.py`
- Create: `tests/test_openrouter.py`

**Reuses know-how from V2's `openrouter_client.py`** (urllib stdlib, json_schema strict, error envelope handling) but rewrites the public surface to be schema-agnostic (one `qwen()` function takes any schema, returns parsed dict).

- [ ] **Step 1: Write failing tests**

`tests/test_openrouter.py`:

```python
"""Tests for openrouter.py — mocks urllib.request.urlopen."""
import json
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

import pytest

from openrouter import qwen, OpenRouterError, DEFAULT_MODEL


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["greeting"],
    "properties": {"greeting": {"type": "string"}},
}


def _mock_response(content_json: str):
    """Build a mock urlopen response containing the given message.content payload."""
    envelope = {"choices": [{"message": {"content": content_json}}]}
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps(envelope).encode("utf-8")
    return mock


def test_qwen_happy_path():
    with patch("openrouter.urlopen", return_value=_mock_response('{"greeting": "hi"}')):
        result = qwen(
            system_prompt="be friendly",
            user_message="say hi",
            json_schema=SCHEMA,
            api_key="test-key",
        )
    assert result == {"greeting": "hi"}


def test_qwen_missing_api_key_raises():
    with pytest.raises(OpenRouterError, match="api_key is required"):
        qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="")


def test_qwen_http_error_raises():
    err = HTTPError("https://x", 500, "boom", {}, None)
    err.fp = None
    with patch("openrouter.urlopen", side_effect=err):
        with pytest.raises(OpenRouterError, match="HTTP 500"):
            qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")


def test_qwen_url_error_raises():
    with patch("openrouter.urlopen", side_effect=URLError("timeout")):
        with pytest.raises(OpenRouterError, match="network error"):
            qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")


def test_qwen_invalid_envelope_raises():
    with patch("openrouter.urlopen", return_value=_mock_response("not-json")):
        with pytest.raises(OpenRouterError, match="not valid JSON"):
            qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")


def test_qwen_uses_default_model_when_omitted():
    captured_payload = {}

    def capture_request(req, timeout=None):
        captured_payload.update(json.loads(req.data.decode("utf-8")))
        return _mock_response('{"greeting": "hi"}')

    with patch("openrouter.urlopen", side_effect=capture_request):
        qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")

    assert captured_payload["model"] == DEFAULT_MODEL


def test_qwen_passes_strict_json_schema():
    captured_payload = {}

    def capture_request(req, timeout=None):
        captured_payload.update(json.loads(req.data.decode("utf-8")))
        return _mock_response('{"greeting": "hi"}')

    with patch("openrouter.urlopen", side_effect=capture_request):
        qwen(system_prompt="x", user_message="x", json_schema=SCHEMA, api_key="k")

    rf = captured_payload["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == SCHEMA
```

- [ ] **Step 2: Run tests — expect import failure**

```bash
pytest tests/test_openrouter.py -v
```

Expected: `ModuleNotFoundError: No module named 'openrouter'`.

- [ ] **Step 3: Implement `openrouter.py`**

```python
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
            "HTTP-Referer": "https://github.com/wanmao/english-capture",
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_openrouter.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add openrouter.py tests/test_openrouter.py
git commit -m "$(cat <<'EOF'
feat(openrouter): schema-agnostic Qwen client

Single qwen() function takes any JSON schema; returns parsed dict.
Stdlib-only (urllib). Mirrors V2's error-handling shape.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `logger.py` — daily file logger

**Files:**
- Create: `logger.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: Write failing tests**

`tests/test_logger.py`:

```python
"""Tests for logger.py."""
from datetime import datetime
from pathlib import Path

from logger import Logger


def test_log_creates_file_in_log_dir(tmp_path: Path):
    log_dir = tmp_path / "logs"
    logger = Logger(str(log_dir))
    logger.log("INFO", "hello")

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.log"
    assert log_file.exists()
    assert "hello" in log_file.read_text()


def test_log_includes_level_and_timestamp(tmp_path: Path):
    log_dir = tmp_path / "logs"
    logger = Logger(str(log_dir))
    logger.log("WARN", "watch out")

    today = datetime.now().strftime("%Y-%m-%d")
    content = (log_dir / f"{today}.log").read_text()
    assert "[WARN]" in content
    assert "watch out" in content
    assert content.startswith("[")  # ISO timestamp


def test_log_appends_multiple_entries(tmp_path: Path):
    log_dir = tmp_path / "logs"
    logger = Logger(str(log_dir))
    logger.log("INFO", "first")
    logger.log("INFO", "second")

    today = datetime.now().strftime("%Y-%m-%d")
    content = (log_dir / f"{today}.log").read_text()
    assert content.count("INFO") == 2


def test_log_dir_created_on_init(tmp_path: Path):
    log_dir = tmp_path / "deep" / "logs"
    Logger(str(log_dir))
    assert log_dir.exists()
```

- [ ] **Step 2: Run tests — expect import failure**

```bash
pytest tests/test_logger.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `logger.py`**

```python
"""Daily-file logger writing to <log_dir>/YYYY-MM-DD.log."""
import os
from datetime import datetime


class Logger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def log(self, level: str, message: str) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(self.log_dir, f"{today}.log")
        timestamp = datetime.now().isoformat()
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
```

- [ ] **Step 4: Run tests — expect 4 passed**

```bash
pytest tests/test_logger.py -v
```

- [ ] **Step 5: Commit**

```bash
git add logger.py tests/test_logger.py
git commit -m "$(cat <<'EOF'
feat(logger): daily file logger

Same shape as V2 logger; rewrite for clean repo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `queue.py` — retry queue

**Files:**
- Create: `queue.py`
- Create: `tests/test_queue.py`

- [ ] **Step 1: Write failing tests**

`tests/test_queue.py`:

```python
"""Tests for queue.py."""
from pathlib import Path

from queue import QueueManager


def test_load_returns_empty_when_file_missing(tmp_path: Path):
    q = QueueManager(str(tmp_path / "queue.json"))
    assert q.load() == []


def test_add_persists_item(tmp_path: Path):
    path = tmp_path / "queue.json"
    q = QueueManager(str(path))
    q.add({"input": "hello"})

    q2 = QueueManager(str(path))
    assert q2.load() == [{"input": "hello"}]


def test_add_appends_to_existing(tmp_path: Path):
    path = tmp_path / "queue.json"
    q = QueueManager(str(path))
    q.add({"a": 1})
    q.add({"b": 2})
    assert q.load() == [{"a": 1}, {"b": 2}]


def test_clear_removes_file(tmp_path: Path):
    path = tmp_path / "queue.json"
    q = QueueManager(str(path))
    q.add({"x": 1})
    q.clear()
    assert not path.exists()
    assert q.load() == []


def test_add_creates_parent_dir(tmp_path: Path):
    path = tmp_path / "deep" / "nested" / "queue.json"
    q = QueueManager(str(path))
    q.add({"x": 1})
    assert path.exists()
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_queue.py -v
```

- [ ] **Step 3: Implement `queue.py`**

```python
"""File-backed retry queue for failed OpenRouter calls."""
import json
import os
from typing import Any


class QueueManager:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def add(self, item: dict[str, Any]) -> None:
        items = self.load()
        items.append(item)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def clear(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)
```

**Note on Python's stdlib `queue` shadow:** the Python stdlib has a `queue` module too, but in this repo we run from the project root so the local `queue.py` wins on `pythonpath = ["."]` from `pyproject.toml`. Tests will fail loudly if this assumption breaks.

- [ ] **Step 4: Run tests — expect 5 passed**

```bash
pytest tests/test_queue.py -v
```

- [ ] **Step 5: Commit**

```bash
git add queue.py tests/test_queue.py
git commit -m "$(cat <<'EOF'
feat(queue): file-backed retry queue

Same surface as V2 (load/add/clear). Adds parent-dir creation safety
and pretty JSON output.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `transcript.py` — CC transcript parser + Chinese detection

**Files:**
- Create: `transcript.py`
- Create: `tests/test_transcript.py`
- Create: `tests/fixtures/sample_cc_transcript.jsonl` (if not already present in fixtures/)

**Reuses know-how from V2's `transcript.py`** (read_transcript, extract_last_turn, tool_result filtering) plus a new `is_chinese_dominant` helper used by the grammar hook filter and `/eng e` validation.

- [ ] **Step 1: Check existing fixtures and add fallback if missing**

```bash
ls tests/fixtures/ 2>/dev/null
```

If `sample_cc_transcript.jsonl` exists, reuse it. Otherwise create:

`tests/fixtures/sample_cc_transcript.jsonl`:

```jsonl
{"type": "user", "message": {"content": "Help me debug this query"}}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "This query suffers from cardinality estimation errors."}]}}
{"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "After tool result, here is more analysis."}]}}
```

- [ ] **Step 2: Write failing tests**

`tests/test_transcript.py`:

```python
"""Tests for transcript.py."""
from pathlib import Path

from transcript import (
    extract_last_user_input,
    is_chinese_dominant,
    read_transcript,
)


def test_read_transcript_missing_file_returns_empty(tmp_path: Path):
    assert read_transcript(str(tmp_path / "nope.jsonl")) == []


def test_read_transcript_skips_malformed_lines(tmp_path: Path):
    p = tmp_path / "t.jsonl"
    p.write_text('{"valid": 1}\nnot-json\n{"valid": 2}\n')
    assert read_transcript(str(p)) == [{"valid": 1}, {"valid": 2}]


def test_extract_last_user_input_string_content():
    messages = [
        {"type": "user", "message": {"content": "first"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "ans"}]}},
        {"type": "user", "message": {"content": "second"}},
    ]
    assert extract_last_user_input(messages) == "second"


def test_extract_last_user_input_skips_tool_result():
    messages = [
        {"type": "user", "message": {"content": "real input"}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
    ]
    assert extract_last_user_input(messages) == "real input"


def test_extract_last_user_input_text_blocks_in_list():
    messages = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "hello world"}]}},
    ]
    assert extract_last_user_input(messages) == "hello world"


def test_extract_last_user_input_no_user_returns_empty():
    messages = [{"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}]}}]
    assert extract_last_user_input(messages) == ""


def test_is_chinese_dominant_pure_chinese():
    assert is_chinese_dominant("你好世界") is True


def test_is_chinese_dominant_pure_english():
    assert is_chinese_dominant("hello world") is False


def test_is_chinese_dominant_mixed_majority_chinese():
    # 5 Chinese chars + "PR" (2) → 5/(5+2) ≈ 71% > 50%
    assert is_chinese_dominant("把这个PR放一放") is True


def test_is_chinese_dominant_mixed_majority_english():
    # 1 Chinese char + 19 English chars → 5%
    assert is_chinese_dominant("the quick brown 狐") is False


def test_is_chinese_dominant_empty_returns_false():
    assert is_chinese_dominant("") is False


def test_is_chinese_dominant_ignores_whitespace_and_punct():
    # whitespace and punctuation are not counted in either side
    assert is_chinese_dominant("你好 world!") is False  # 2 Chinese vs 5 English


def test_extract_last_user_input_from_fixture():
    fixture = Path(__file__).parent / "fixtures" / "sample_cc_transcript.jsonl"
    messages = read_transcript(str(fixture))
    # Last human input is the first message; later "user" entry is tool_result.
    # Actually the fixture above only has one human user message.
    assert extract_last_user_input(messages) == "Help me debug this query"
```

- [ ] **Step 3: Run tests — expect import failure**

```bash
pytest tests/test_transcript.py -v
```

- [ ] **Step 4: Implement `transcript.py`**

```python
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
    # Count "letter-class" non-whitespace, non-punctuation alphabetic chars on the other side
    english = sum(1 for ch in text if ch.isalpha() and not ("一" <= ch <= "鿿"))
    total = chinese + english
    if total == 0:
        return False
    return chinese / total > 0.5
```

- [ ] **Step 5: Run tests — expect 13 passed**

```bash
pytest tests/test_transcript.py -v
```

- [ ] **Step 6: Commit**

```bash
git add transcript.py tests/test_transcript.py tests/fixtures/sample_cc_transcript.jsonl
git commit -m "$(cat <<'EOF'
feat(transcript): JSONL parser + is_chinese_dominant helper

Simplified from V2 (no Codex branch needed for slash commands; CC-only).
Adds is_chinese_dominant() used by /eng e validation and grammar hook filter.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `vault.py` — md read/write/dedup/append

**Files:**
- Create: `vault.py`
- Create: `tests/test_vault.py`

**Reuses know-how from V2's `dedup.py` and `md_writer.py`** but consolidates into one module with new `normalize_for_dedup` and `append_example` capabilities per spec dedup-strategy-B.

- [ ] **Step 1: Write failing tests**

`tests/test_vault.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect import failure**

```bash
pytest tests/test_vault.py -v
```

- [ ] **Step 3: Implement `vault.py`**

```python
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
_CJK_PUNCT = set("。，；：？！“”‘’（）【】《》")

_PHRASE_RE = re.compile(r'^(?:phrase|original|chinese):\s*"?([^"\n]+)"?\s*$', re.MULTILINE)


def normalize_for_dedup(s: str) -> str:
    """Lowercase, strip whitespace, collapse internal spaces, drop ASCII+CJK punctuation."""
    s = s.strip().lower()
    out_chars = []
    for ch in s:
        if ch in _ASCII_PUNCT or ch in _CJK_PUNCT:
            continue
        if ch.isspace():
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


def _frontmatter_block(fields: dict[str, str]) -> str:
    """Render YAML frontmatter from dict; quotes string values."""
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, str):
            # Always quote strings to avoid yaml gotchas (colons, special chars)
            escaped = v.replace('"', '\\"')
            lines.append(f'{k}: "{escaped}"')
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def write_word_card(item: dict, vault_root: Union[str, Path], source: str) -> Path:
    """Write a vocabulary flashcard to <vault>/20-Areas/英语/<category>/<slug>.md."""
    area = _area_dir(vault_root)
    target_dir = area / item["category"]
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(item["phrase"])
    out_path = target_dir / f"{slug}.md"

    fm = _frontmatter_block({
        "phrase": item["phrase"],
        "category": item["category"],
        "created": date.today().isoformat(),
        "source": source,
    })

    body = f"""
{item['phrase']}
?
**中文:** {item['translation_zh']}

**记忆点:** {item['memory_tip']}

**例句:**
- {item['context_sentence']}
"""
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

    # Update frontmatter: insert/refresh `updated:`
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

    # Find **例句:** block and append; if missing, add it
    if "**例句:**" in text:
        # Append a new bullet after the last existing bullet under **例句:**
        # Strategy: find **例句:** then append `\n- {new_example}` at end of file or after last bullet
        text = text.rstrip() + f"\n- {new_example}\n"
    else:
        text = text.rstrip() + f"\n\n**例句:**\n- {new_example}\n"

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
```

- [ ] **Step 4: Run tests — expect 22 passed**

```bash
pytest tests/test_vault.py -v
```

If `test_append_example_adds_updated_field` fails because the regex didn't insert before a frontmatter that lacks a trailing `\n---\n`, debug by checking the actual frontmatter format produced by `_frontmatter_block` — adjust the regex to match `\n---\n` exactly (which is what `_frontmatter_block` produces).

- [ ] **Step 5: Commit**

```bash
git add vault.py tests/test_vault.py
git commit -m "$(cat <<'EOF'
feat(vault): consolidated md operations (write/exists/append)

Replaces V2's split dedup.py + md_writer.py. Adds:
- normalize_for_dedup() — punctuation/case/whitespace insensitive
- 4 write_*_card functions (word/sentence/expression/grammar)
- append_example() implementing dedup strategy B (append context to existing card)
- grammar_already_checked() for grammar hook filter

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `prompts.py` — 4 system prompts + JSON schemas

**Files:**
- Create: `prompts.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write failing tests**

`tests/test_prompts.py`:

```python
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
    assert sys_p  # non-empty system prompt


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
    # Either the system prompt or the implicit schema enforces it; system prompt
    # should at least mention Chinese translation as a goal.
    assert "中文" in sys_p or "Chinese" in sys_p


def test_grammar_prompt_asks_for_has_error_judgment():
    sys_p, _ = build_grammar_prompt("x")
    assert "has_error" in sys_p or "grammar" in sys_p.lower()
```

- [ ] **Step 2: Run tests — expect import failure**

```bash
pytest tests/test_prompts.py -v
```

- [ ] **Step 3: Implement `prompts.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect 12 passed**

```bash
pytest tests/test_prompts.py -v
```

- [ ] **Step 5: Commit**

```bash
git add prompts.py tests/test_prompts.py
git commit -m "$(cat <<'EOF'
feat(prompts): 4 system prompts + strict JSON schemas (w/s/e/grammar)

Initial drafts; wording will be iterated based on real-usage feedback.
Schemas cover the exact field shape consumed by vault.write_*_card().

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `add_card.py` — slash command CLI entry

**Files:**
- Create: `add_card.py`
- Create: `tests/test_add_card.py`
- Create: `tests/fixtures/sample_qwen_word_response.json`
- Create: `tests/fixtures/sample_qwen_sentence_response.json`
- Create: `tests/fixtures/sample_qwen_expression_response.json`

- [ ] **Step 1: Create fixture files**

`tests/fixtures/sample_qwen_word_response.json`:

```json
{
  "phrase": "cardinality estimation",
  "category": "noun",
  "translation_zh": "基数估计",
  "memory_tip": "数据库查询规划器估算结果行数。",
  "context_sentence": "This query suffers from cardinality estimation errors on the join."
}
```

`tests/fixtures/sample_qwen_sentence_response.json`:

```json
{
  "original": "Despite the migration succeeding, downstream consumers reported stale reads.",
  "translation_zh": "尽管迁移成功了，下游消费者还是报告读到了旧数据。",
  "grammar_points": ["Despite + 动名词短语 等价于 Although + 从句"],
  "key_vocab": "stale reads（脏读 / 旧读）"
}
```

`tests/fixtures/sample_qwen_expression_response.json`:

```json
{
  "chinese": "这个 PR 我先放一放",
  "idiomatic_english": [
    "I'll put this PR on the back burner for now.",
    "Let me park this PR for a bit."
  ],
  "use_case": "工作中需要暂时搁置某事但不放弃。",
  "anti_example": "I will pause this PR — 太字面，母语者更偏好 back burner / park。"
}
```

- [ ] **Step 2: Write failing tests**

`tests/test_add_card.py`:

```python
"""Integration tests for add_card.py CLI."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import add_card


FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parent.parent


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def fake_config(tmp_vault: Path, monkeypatch, tmp_path: Path):
    """Patch add_card to use a tmp config + tmp vault."""
    cfg = {
        "openrouter_api_key": "test-key",
        "openrouter_model": "qwen/qwen3-235b-a22b-2507",
        "vault_path": str(tmp_vault),
        "timeout_seconds": 30,
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    monkeypatch.setenv("ENGLISH_CAPTURE_CONFIG", str(cfg_path))
    return cfg


def test_word_type_writes_card(fake_config, tmp_vault: Path, capsys):
    fake_response = _load_fixture("sample_qwen_word_response.json")
    with patch("add_card.qwen", return_value=fake_response):
        rc = add_card.main([
            "--type", "w",
            "--phrase", "cardinality estimation",
            "--context", "This query suffers from cardinality estimation errors on the join.",
        ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "✓ saved" in out
    assert "noun/cardinality-estimation.md" in out
    card = tmp_vault / "20-Areas" / "英语" / "noun" / "cardinality-estimation.md"
    assert card.exists()


def test_word_dedup_appends_example(fake_config, tmp_vault: Path, capsys):
    fake_response = _load_fixture("sample_qwen_word_response.json")
    # First call: write
    with patch("add_card.qwen", return_value=fake_response):
        add_card.main([
            "--type", "w", "--phrase", "cardinality estimation",
            "--context", "first usage of the term here.",
        ])
    capsys.readouterr()
    # Second call: should hit dedup path (no Qwen call expected)
    with patch("add_card.qwen") as mock_qwen:
        rc = add_card.main([
            "--type", "w", "--phrase", "cardinality estimation",
            "--context", "second different usage in another query.",
        ])
        mock_qwen.assert_not_called()
    assert rc == 0
    out = capsys.readouterr().out
    assert "↳ appended example" in out
    card = tmp_vault / "20-Areas" / "英语" / "noun" / "cardinality-estimation.md"
    assert "second different usage" in card.read_text()


def test_sentence_type_writes_card(fake_config, tmp_vault: Path, capsys):
    fake_response = _load_fixture("sample_qwen_sentence_response.json")
    with patch("add_card.qwen", return_value=fake_response):
        rc = add_card.main([
            "--type", "s",
            "--phrase", "Despite the migration succeeding, downstream consumers reported stale reads.",
            "--context", "discussing failed migrations",
        ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "✓ saved" in out
    assert "sentence/" in out


def test_expression_type_writes_card(fake_config, tmp_vault: Path, capsys):
    fake_response = _load_fixture("sample_qwen_expression_response.json")
    with patch("add_card.qwen", return_value=fake_response):
        rc = add_card.main([
            "--type", "e",
            "--phrase", "这个 PR 我先放一放",
            "--context", "",
        ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "✓ saved" in out
    assert "expression/" in out


def test_expression_rejects_non_chinese(fake_config, capsys):
    rc = add_card.main([
        "--type", "e",
        "--phrase", "park this PR for a bit",
        "--context", "",
    ])
    assert rc != 0
    out = capsys.readouterr().out
    assert "expects Chinese" in out


def test_openrouter_failure_queues_and_reports(fake_config, capsys, tmp_path: Path, monkeypatch):
    queue_path = tmp_path / "queue.json"
    monkeypatch.setenv("ENGLISH_CAPTURE_QUEUE", str(queue_path))
    from openrouter import OpenRouterError
    with patch("add_card.qwen", side_effect=OpenRouterError("timeout")):
        rc = add_card.main([
            "--type", "w", "--phrase", "novel-word",
            "--context", "...",
        ])
    assert rc != 0
    out = capsys.readouterr().out
    assert "queued" in out
    assert queue_path.exists()
    queued = json.loads(queue_path.read_text())
    assert any(q["phrase"] == "novel-word" for q in queued)


def test_unknown_type_errors(fake_config, capsys):
    rc = add_card.main(["--type", "x", "--phrase", "foo", "--context", ""])
    assert rc != 0


def test_cli_runnable_via_subprocess(fake_config, tmp_path: Path):
    """Smoke test: the script's __main__ guard is wired up correctly."""
    # We don't actually call the API in subprocess; just make sure the script
    # can be invoked and exit with usage error on no args.
    result = subprocess.run(
        [sys.executable, str(ROOT / "add_card.py")],
        capture_output=True, text=True,
    )
    # No args → argparse prints usage and exits non-zero
    assert result.returncode != 0
```

- [ ] **Step 3: Run tests — expect import failure**

```bash
pytest tests/test_add_card.py -v
```

- [ ] **Step 4: Implement `add_card.py`**

```python
#!/usr/bin/env python3
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

from logger import Logger  # noqa: E402
from openrouter import OpenRouterError, qwen  # noqa: E402
from prompts import (  # noqa: E402
    EXPRESSION_SCHEMA,
    SENTENCE_SCHEMA,
    WORD_SCHEMA,
    build_expression_prompt,
    build_sentence_prompt,
    build_word_prompt,
)
from queue import QueueManager  # noqa: E402
from transcript import is_chinese_dominant  # noqa: E402
from vault import (  # noqa: E402
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
    from vault import _area_dir, _slugify  # local import to keep public surface tight
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add an English-learning flashcard")
    parser.add_argument("--type", choices=["w", "s", "e"], required=True)
    parser.add_argument("--phrase", required=True)
    parser.add_argument("--context", default="")
    args = parser.parse_args(argv)

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

    api_key = config["openrouter_api_key"]
    model = config.get("openrouter_model", "qwen/qwen3-235b-a22b-2507")
    timeout = config.get("timeout_seconds", 60)

    # Dedup-then-append (Strategy B)
    existing = find_existing_card_path(args.phrase, vault_root, args.type)
    if existing is not None:
        appended = append_example(existing, args.context or args.phrase)
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
        sys_p, user_msg = build_word_prompt(args.phrase, args.context)
        schema = WORD_SCHEMA
    elif args.type == "s":
        sys_p, user_msg = build_sentence_prompt(args.phrase, args.context)
        schema = SENTENCE_SCHEMA
    else:  # e
        sys_p, user_msg = build_expression_prompt(args.phrase, args.context)
        schema = EXPRESSION_SCHEMA

    try:
        qwen_result = qwen(
            system_prompt=sys_p,
            user_message=user_msg,
            json_schema=schema,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )
    except OpenRouterError as e:
        queue.add({
            "type": args.type,
            "phrase": args.phrase,
            "context": args.context,
        })
        print(f"✗ queued for retry ({e})")
        logger.log("WARN", f"queued: {args.phrase[:60]} — {e}")
        return 5

    # Write card
    try:
        if args.type == "w":
            path = write_word_card(qwen_result, vault_root, source="manual_w")
        elif args.type == "s":
            path = write_sentence_card(qwen_result, vault_root, source="manual_s")
        else:
            path = write_expression_card(qwen_result, vault_root, source="manual_e")
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
```

- [ ] **Step 5: Run tests — expect 8 passed**

```bash
pytest tests/test_add_card.py -v
```

If `test_word_dedup_appends_example` fails because `find_existing_card_path` doesn't match (slug mismatch between phrase and existing file), check that `_slugify` deterministically maps "cardinality estimation" → "cardinality-estimation".

- [ ] **Step 6: Commit**

```bash
git add add_card.py tests/test_add_card.py tests/fixtures/sample_qwen_*.json
git commit -m "$(cat <<'EOF'
feat(add_card): slash command CLI for /eng w/s/e

Implements dedup strategy B (append example to existing card), Chinese
validation for /eng e, queue-on-failure for OpenRouter errors, and one-line
human-readable stdout (✓/↳/✗) consumed by the eng.md template.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `grammar_hook.py` — Stop hook entry

**Files:**
- Create: `grammar_hook.py`
- Create: `tests/test_grammar_hook.py`
- Create: `tests/fixtures/sample_stop_event.json`
- Create: `tests/fixtures/sample_qwen_grammar_response.json`

- [ ] **Step 1: Create fixtures**

`tests/fixtures/sample_stop_event.json`:

```json
{
  "hook_event_name": "Stop",
  "transcript_path": "tests/fixtures/sample_cc_transcript.jsonl"
}
```

`tests/fixtures/sample_qwen_grammar_response.json`:

```json
{
  "has_error": true,
  "original": "I have went to the store yesterday.",
  "corrected": "I went to the store yesterday.",
  "errors": [{"type": "tense", "explain": "have went → went：过去时不应使用 have + 过去分词。"}]
}
```

- [ ] **Step 2: Write failing tests**

`tests/test_grammar_hook.py`:

```python
"""Tests for grammar_hook.py."""
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import grammar_hook


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_env(tmp_vault: Path, tmp_path: Path, monkeypatch):
    cfg = {
        "openrouter_api_key": "test-key",
        "openrouter_model": "qwen/qwen3-235b-a22b-2507",
        "vault_path": str(tmp_vault),
        "timeout_seconds": 30,
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    monkeypatch.setenv("ENGLISH_CAPTURE_CONFIG", str(cfg_path))
    monkeypatch.setenv("ENGLISH_CAPTURE_QUEUE", str(tmp_path / "queue.json"))
    monkeypatch.setenv("ENGLISH_CAPTURE_LOGS", str(tmp_path / "logs"))
    return tmp_path


def _stdin_event(content: dict) -> io.StringIO:
    return io.StringIO(json.dumps(content))


def _make_transcript(tmp_path: Path, last_user_input: str) -> Path:
    """Make a one-message transcript file."""
    p = tmp_path / "transcript.jsonl"
    p.write_text(json.dumps({"type": "user", "message": {"content": last_user_input}}) + "\n")
    return p


def test_skips_non_stop_event(fake_env, tmp_path: Path, monkeypatch):
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "PreToolUse"}))
    rc = grammar_hook.main()
    assert rc == 0


def test_skips_when_transcript_missing(fake_env, monkeypatch):
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": "/tmp/nope.jsonl"}))
    rc = grammar_hook.main()
    assert rc == 0


def test_skips_slash_command_input(fake_env, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "/eng w 'foo'")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    with patch("grammar_hook.qwen") as mock_qwen:
        rc = grammar_hook.main()
        mock_qwen.assert_not_called()
    assert rc == 0


def test_skips_short_input(fake_env, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "yes do it")  # 3 words
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    with patch("grammar_hook.qwen") as mock_qwen:
        rc = grammar_hook.main()
        mock_qwen.assert_not_called()
    assert rc == 0


def test_skips_chinese_input(fake_env, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "请帮我修复这个数据库查询的性能问题")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    with patch("grammar_hook.qwen") as mock_qwen:
        rc = grammar_hook.main()
        mock_qwen.assert_not_called()
    assert rc == 0


def test_writes_grammar_card_when_error(fake_env, tmp_vault: Path, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "I have went to the store yesterday morning.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    fake = json.loads((FIXTURES / "sample_qwen_grammar_response.json").read_text())
    with patch("grammar_hook.qwen", return_value=fake):
        rc = grammar_hook.main()
    assert rc == 0
    grammar_dir = tmp_vault / "20-Areas" / "英语" / "grammar"
    cards = list(grammar_dir.glob("*.md"))
    assert len(cards) == 1
    assert "Corrected:" in cards[0].read_text()


def test_no_card_when_no_error(fake_env, tmp_vault: Path, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "I went to the store yesterday morning successfully.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    no_error_response = {
        "has_error": False,
        "original": "I went to the store yesterday morning successfully.",
        "corrected": "I went to the store yesterday morning successfully.",
        "errors": [],
    }
    with patch("grammar_hook.qwen", return_value=no_error_response):
        rc = grammar_hook.main()
    assert rc == 0
    grammar_dir = tmp_vault / "20-Areas" / "英语" / "grammar"
    assert not list(grammar_dir.glob("*.md"))


def test_skips_already_checked(fake_env, tmp_vault: Path, tmp_path: Path, monkeypatch):
    # Pre-populate a grammar card for the same input (normalized)
    from vault import write_grammar_card
    write_grammar_card(
        {"original": "I have went to the store yesterday morning.",
         "corrected": "I went to the store yesterday morning.",
         "errors": []},
        tmp_vault, source="auto_grammar",
    )
    t = _make_transcript(tmp_path, "I have went to the store yesterday morning.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    with patch("grammar_hook.qwen") as mock_qwen:
        rc = grammar_hook.main()
        mock_qwen.assert_not_called()
    assert rc == 0


def test_queues_on_openrouter_failure(fake_env, tmp_path: Path, monkeypatch):
    t = _make_transcript(tmp_path, "I have went to the store yesterday morning.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    from openrouter import OpenRouterError
    with patch("grammar_hook.qwen", side_effect=OpenRouterError("timeout")):
        rc = grammar_hook.main()
    assert rc == 0  # hook always returns 0 to not block CC
    queue_path = Path(os.environ["ENGLISH_CAPTURE_QUEUE"])
    assert queue_path.exists()
    queued = json.loads(queue_path.read_text())
    assert len(queued) == 1


def test_drains_queue_first(fake_env, tmp_path: Path, tmp_vault: Path, monkeypatch):
    queue_path = Path(os.environ["ENGLISH_CAPTURE_QUEUE"])
    queue_path.write_text(json.dumps([
        {"type": "grammar", "input": "I am go to school yesterday morning."}
    ]))
    t = _make_transcript(tmp_path, "I has been working here since 2020 happily.")
    monkeypatch.setattr("sys.stdin", _stdin_event({"hook_event_name": "Stop", "transcript_path": str(t)}))
    fake = json.loads((FIXTURES / "sample_qwen_grammar_response.json").read_text())
    with patch("grammar_hook.qwen", return_value=fake) as mock_qwen:
        rc = grammar_hook.main()
        # Once for queue drain, once for current input
        assert mock_qwen.call_count == 2
    assert rc == 0
    # Queue should be empty after successful drain
    if queue_path.exists():
        assert json.loads(queue_path.read_text()) == []
```

- [ ] **Step 3: Run tests — expect import failure**

```bash
pytest tests/test_grammar_hook.py -v
```

- [ ] **Step 4: Implement `grammar_hook.py`**

```python
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

from logger import Logger  # noqa: E402
from openrouter import OpenRouterError, qwen  # noqa: E402
from prompts import GRAMMAR_SCHEMA, build_grammar_prompt  # noqa: E402
from queue import QueueManager  # noqa: E402
from transcript import (  # noqa: E402
    extract_last_user_input,
    is_chinese_dominant,
    read_transcript,
)
from vault import grammar_already_checked, write_grammar_card  # noqa: E402


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
```

- [ ] **Step 5: Run tests — expect 10 passed**

```bash
pytest tests/test_grammar_hook.py -v
```

- [ ] **Step 6: Commit**

```bash
git add grammar_hook.py tests/test_grammar_hook.py tests/fixtures/sample_stop_event.json tests/fixtures/sample_qwen_grammar_response.json
git commit -m "$(cat <<'EOF'
feat(grammar_hook): Stop hook for grammar-only correction

Filters slash commands, short inputs, Chinese-dominant inputs, and
already-checked sentences. Drains retry queue. Always returns 0 to avoid
blocking CC.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `eng.md` — slash command template

**Files:**
- Create: `eng.md`

This is a Claude Code slash command template (Markdown with `$ARGUMENTS` placeholder). It is **not unit-tested** per spec testing-strategy decision.

- [ ] **Step 1: Create `eng.md`**

```markdown
---
description: Add an English-learning flashcard to your Obsidian vault. Usage: /eng w 'word' | /eng s 'sentence' | /eng e '中文'
---

You are processing an English-learning capture command. The user invoked:

```
/eng $ARGUMENTS
```

## Step 1: Parse the arguments

Parse `$ARGUMENTS` as `<type> <quoted_phrase>` where:
- `type` is exactly one of: `w` (word), `s` (sentence/long-difficult), `e` (Chinese expression)
- `quoted_phrase` is the content inside single or double quotes (preserve exactly)

If parsing fails, print `✗ usage: /eng {w|s|e} '<phrase>'` and stop.

## Step 2: Find context in this session

Search the **current Claude Code session transcript (this conversation)** for the most recent occurrence of the phrase:
- For type `w` and `s`: search for the exact phrase string. If not found, try case-insensitive and punctuation-insensitive matching. Look in **assistant** messages first (the most common case is "Claude said something I want to learn"), then in user messages.
- For type `e`: the phrase is Chinese, so it likely won't appear verbatim in an English-only conversation. Instead, look for a recent **user question** like "X 用英文怎么说" or "how to say X in English" where X relates to the Chinese phrase. If found, include both the user question and Claude's response. If nothing relevant, leave context empty.

When you find a match, extract the surrounding **2-4 sentences** (1-2 sentences before and 1-2 after the match) as the context. Aim for ~200-400 characters total.

If no match is found, set context to empty string.

## Step 3: Call the CLI

Run this exact command (substitute `<TYPE>`, `<PHRASE>`, `<CONTEXT>` with the parsed values; properly shell-quote each argument):

```bash
python3 ~/.claude/hooks/english-capture/add_card.py \
  --type <TYPE> \
  --phrase <PHRASE> \
  --context <CONTEXT>
```

## Step 4: Echo the result

Print the CLI's stdout verbatim to the user. It will be one of:
- `✓ saved <category>/<slug>.md` — new card created
- `↳ appended example to <category>/<slug>.md` — dedup hit, example added
- `↳ already exists ...` — dedup hit but exact-string already in card
- `✗ /eng e expects Chinese input` — wrong type for input
- `✗ queued for retry (...)` — OpenRouter failed, will retry on next hook fire
- `✗ vault unreachable: ...` — iCloud/path issue
- `✗ <other failure>` — see logs at `~/.english-capture/logs/`

Do not add any commentary unless the CLI returned a non-zero exit code, in which case briefly suggest the user check `~/.english-capture/logs/$(date +%Y-%m-%d).log` for details.
```

- [ ] **Step 2: Verify shell quoting safety mentally**

Re-read step 3 of the template. The instructions say "properly shell-quote each argument" — this is critical because the phrase may contain single quotes, backticks, or `$`. Claude executing the template should use Python's `shlex.quote()` mental model (i.e. wrap in single quotes and escape any embedded single quotes as `'\''`).

- [ ] **Step 3: Commit**

```bash
git add eng.md
git commit -m "$(cat <<'EOF'
feat(eng.md): slash command template for /eng w/s/e

Prompts Claude to parse args, locate context in current transcript, and call
add_card.py CLI. No unit tests — prompt behavior is iterated via lived usage.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: `config.example.json`

**Files:**
- Create: `config.example.json`

- [ ] **Step 1: Create the file**

```json
{
  "openrouter_api_key": "sk-or-v1-REPLACE-ME",
  "openrouter_model": "qwen/qwen3-235b-a22b-2507",
  "vault_path": "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/<YOUR_VAULT_NAME>",
  "timeout_seconds": 60
}
```

- [ ] **Step 2: Commit**

```bash
git add config.example.json
git commit -m "$(cat <<'EOF'
chore: config.example.json template

install.sh copies this to ~/.english-capture/config.json on first run if missing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: `install.sh` — cross-device installer

**Files:**
- Create: `install.sh` (chmod +x)

Manual integration test only (no automated tests for shell script). The smoke test step in install.sh itself is the verification.

- [ ] **Step 1: Create `install.sh`**

```bash
#!/usr/bin/env bash
# english-capture installer — idempotent.
#
# Usage:
#   ./install.sh             # install / re-run safely
#   ./install.sh --uninstall # remove slash-command symlink and Stop hook entry
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$HOME/.english-capture"
CONFIG_PATH="$RUNTIME_DIR/config.json"
LOGS_DIR="$RUNTIME_DIR/logs"
COMMAND_LINK="$HOME/.claude/commands/eng.md"
SETTINGS_PATH="$HOME/.claude/settings.json"
HOOK_CMD="python3 $REPO_DIR/grammar_hook.py"
TODAY=$(date +%Y-%m-%d)

c_ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
c_warn() { printf "  \033[33m⚠\033[0m %s\n" "$1"; }
c_err()  { printf "  \033[31m✗\033[0m %s\n" "$1"; }
c_step() { printf "\n\033[1m▸ %s\033[0m\n" "$1"; }

uninstall() {
    c_step "Uninstalling english-capture"

    if [[ -L "$COMMAND_LINK" ]]; then
        rm "$COMMAND_LINK"
        c_ok "removed $COMMAND_LINK"
    else
        c_warn "no symlink at $COMMAND_LINK"
    fi

    if [[ -f "$SETTINGS_PATH" ]] && command -v jq >/dev/null; then
        cp "$SETTINGS_PATH" "$SETTINGS_PATH.bak.$TODAY"
        jq --arg cmd "$HOOK_CMD" \
           '(.hooks.Stop // []) |= map(select(.command != $cmd))' \
           "$SETTINGS_PATH" > "$SETTINGS_PATH.tmp"
        mv "$SETTINGS_PATH.tmp" "$SETTINGS_PATH"
        c_ok "removed Stop hook entry from $SETTINGS_PATH (backup: $SETTINGS_PATH.bak.$TODAY)"
    fi

    c_ok "done. $RUNTIME_DIR/ left intact (config + logs); remove manually if desired."
}

install() {
    c_step "Installing english-capture from $REPO_DIR"

    # 1. Detect dependencies
    c_step "1/6 detecting dependencies"
    command -v python3 >/dev/null || { c_err "python3 not found"; exit 1; }
    PY_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    c_ok "python3 ($PY_VER)"
    command -v jq >/dev/null || { c_err "jq not found — install via 'brew install jq'"; exit 1; }
    c_ok "jq"

    # Auto-detect Obsidian vault under iCloud
    OBSIDIAN_BASE="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"
    if [[ ! -d "$OBSIDIAN_BASE" ]]; then
        c_err "Obsidian iCloud directory not found at:"
        c_err "  $OBSIDIAN_BASE"
        c_err "Set up Obsidian + iCloud sync first, then re-run."
        exit 1
    fi
    DEFAULT_VAULT=$(find "$OBSIDIAN_BASE" -maxdepth 1 -mindepth 1 -type d | head -n 1)
    c_ok "Obsidian vault detected: $DEFAULT_VAULT"

    # 2. Runtime directories
    c_step "2/6 runtime directories"
    mkdir -p "$LOGS_DIR"
    c_ok "$RUNTIME_DIR/{logs}"

    # 3. Config bootstrap
    c_step "3/6 config"
    if [[ -f "$CONFIG_PATH" ]]; then
        c_ok "$CONFIG_PATH already exists; leaving it untouched"
    else
        cp "$REPO_DIR/config.example.json" "$CONFIG_PATH"
        echo
        printf "  OpenRouter API key (sk-or-v1-...): "
        read -r API_KEY
        printf "  Vault path [%s]: " "$DEFAULT_VAULT"
        read -r VAULT_INPUT
        VAULT_PATH="${VAULT_INPUT:-$DEFAULT_VAULT}"

        jq --arg key "$API_KEY" --arg vault "$VAULT_PATH" \
           '.openrouter_api_key = $key | .vault_path = $vault' \
           "$CONFIG_PATH" > "$CONFIG_PATH.tmp"
        mv "$CONFIG_PATH.tmp" "$CONFIG_PATH"
        chmod 0600 "$CONFIG_PATH"
        c_ok "wrote $CONFIG_PATH (chmod 600)"
    fi

    # 4. Slash command symlink
    c_step "4/6 slash command (~/.claude/commands/eng.md)"
    mkdir -p "$(dirname "$COMMAND_LINK")"
    if [[ -L "$COMMAND_LINK" && "$(readlink "$COMMAND_LINK")" == "$REPO_DIR/eng.md" ]]; then
        c_ok "already linked"
    else
        if [[ -e "$COMMAND_LINK" ]]; then
            mv "$COMMAND_LINK" "$COMMAND_LINK.bak.$TODAY"
            c_warn "backed up existing eng.md → eng.md.bak.$TODAY"
        fi
        ln -sf "$REPO_DIR/eng.md" "$COMMAND_LINK"
        c_ok "linked $COMMAND_LINK → $REPO_DIR/eng.md"
    fi

    # 5. Stop hook registration
    c_step "5/6 Stop hook registration"
    mkdir -p "$(dirname "$SETTINGS_PATH")"
    if [[ ! -f "$SETTINGS_PATH" ]]; then
        echo '{}' > "$SETTINGS_PATH"
    fi
    cp "$SETTINGS_PATH" "$SETTINGS_PATH.bak.$TODAY"

    EXISTS=$(jq --arg cmd "$HOOK_CMD" \
        '[.hooks.Stop // [] | .[] | select(.command == $cmd)] | length' \
        "$SETTINGS_PATH")
    if [[ "$EXISTS" == "0" ]]; then
        jq --arg cmd "$HOOK_CMD" \
           '.hooks.Stop = ((.hooks.Stop // []) + [{"command": $cmd}])' \
           "$SETTINGS_PATH" > "$SETTINGS_PATH.tmp"
        mv "$SETTINGS_PATH.tmp" "$SETTINGS_PATH"
        c_ok "added Stop hook entry (backup: $SETTINGS_PATH.bak.$TODAY)"
    else
        c_ok "Stop hook entry already present"
    fi

    # 6. Smoke test
    c_step "6/6 smoke test"
    SAMPLE_EVENT="$REPO_DIR/tests/fixtures/sample_stop_event.json"
    if [[ -f "$SAMPLE_EVENT" ]]; then
        if python3 "$REPO_DIR/grammar_hook.py" < "$SAMPLE_EVENT" >/dev/null 2>&1; then
            c_ok "grammar_hook.py executes without crash"
        else
            c_err "grammar_hook.py crashed — check $LOGS_DIR/$TODAY.log"
            exit 2
        fi
    else
        c_warn "no smoke-test fixture; skipping"
    fi

    echo
    c_step "✓ ready"
    echo "    Try in any Claude Code session:"
    echo "      /eng w 'serendipity'"
    echo "      /eng s 'Despite the migration succeeding, downstream consumers reported stale reads.'"
    echo "      /eng e '这个 PR 我先放一放'"
    echo
    echo "    Logs: $LOGS_DIR/$(date +%Y-%m-%d).log"
}

case "${1:-}" in
    --uninstall) uninstall ;;
    "") install ;;
    *) c_err "unknown arg: $1"; echo "usage: $0 [--uninstall]"; exit 1 ;;
esac
```

- [ ] **Step 2: Make executable**

```bash
chmod +x install.sh
```

- [ ] **Step 3: Lint with shellcheck (if available)**

```bash
command -v shellcheck >/dev/null && shellcheck install.sh || echo "shellcheck not available; skipping"
```

Fix any errors flagged. Warnings about `read -r` in interactive prompts are acceptable.

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "$(cat <<'EOF'
feat(install.sh): cross-device installer (idempotent)

Detects deps, prompts for OpenRouter key + vault path, installs slash command
symlink, registers Stop hook in ~/.claude/settings.json (backed up before edit),
runs smoke test. --uninstall removes hook entry and slash command symlink but
preserves ~/.english-capture/.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: `README.md`

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# english-capture

Manual slash commands for capturing English vocabulary into your Obsidian vault, with an automatic grammar checker for what you write to Claude Code.

> **Personal tool** — built for and used only by wanmao. Not a product.

## What it does

Three slash commands you run inside any Claude Code session:

```
/eng w 'cardinality estimation'                  # save a word/phrase
/eng s 'Despite the migration succeeding...'     # save a long sentence
/eng e '这个 PR 我先放一放'                       # save a Chinese-to-English expression
```

Each command pulls the surrounding context from your current Claude Code conversation, asks Qwen for a Chinese translation + memory tip + a natural example sentence, and writes a Markdown flashcard to your Obsidian vault under `20-Areas/英语/{category}/`. The Obsidian Spaced Repetition plugin picks them up automatically and syncs across iPhone / iPad / both Macs via iCloud.

A separate background hook (`grammar_hook.py`) fires on every Claude Code Stop event. If your most recent input has a real grammar error, it writes a grammar correction flashcard. No noise — only writes when there's a genuine error.

## Install

```bash
git clone https://github.com/wanmao/english-capture.git ~/.claude/hooks/english-capture
cd ~/.claude/hooks/english-capture
./install.sh
```

The installer will:
1. Check that python3, jq, and an Obsidian iCloud vault exist
2. Prompt for your OpenRouter API key (get one at https://openrouter.ai/)
3. Prompt for the vault path (auto-detects the first vault under iCloud)
4. Create `~/.english-capture/config.json` (chmod 0600)
5. Symlink `eng.md` → `~/.claude/commands/eng.md`
6. Register the Stop hook in `~/.claude/settings.json`
7. Run a smoke test to confirm everything works

Re-running `./install.sh` is safe — every step is idempotent.

## Daily usage

In any Claude Code session, just type the command. Claude will:
1. Find where the phrase appeared in this conversation
2. Extract surrounding sentences as context
3. Call the local CLI to write the card
4. Echo the result back

Output looks like:
```
✓ saved noun/cardinality-estimation.md
```

If you've already saved this phrase, the new context is appended as another example to the existing card:
```
↳ appended example to noun/cardinality-estimation.md
```

## Uninstall

```bash
./install.sh --uninstall
```

This removes the slash command symlink and the Stop hook entry from `~/.claude/settings.json`. Your `~/.english-capture/` directory (config + logs) and your Obsidian vault are left untouched.

## Files

| Purpose | Location |
|---|---|
| Code (this repo) | `~/.claude/hooks/english-capture/` |
| Runtime config | `~/.english-capture/config.json` (chmod 0600) |
| Logs | `~/.english-capture/logs/YYYY-MM-DD.log` |
| Retry queue | `~/.english-capture/queue.json` |
| Slash command (symlink) | `~/.claude/commands/eng.md` |
| Stop hook entry | `~/.claude/settings.json` (managed by `install.sh`) |
| Flashcards | `<vault>/20-Areas/英语/{category}/*.md` |

## Costs

OpenRouter Qwen3-235B-A22B-2507: about $0.07 per million input tokens. Typical usage (a few `/eng` commands per day + grammar checks on each session end) is well under $0.30/month.

## Spec & plan

See `docs/superpowers/specs/2026-04-27-manual-slash-commands-design.md` and `docs/superpowers/plans/2026-04-27-manual-slash-commands-plan.md`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: README with install + daily usage

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push
```

---

## Task 13: Freeze the existing V2 Stop hook entry

**Goal:** before running the new `install.sh`, make sure the old V2 Stop hook (which would call the now-deleted `capture.py`) is removed from `~/.claude/settings.json` so it doesn't error on every session end.

- [ ] **Step 1: Inspect current settings.json**

```bash
jq '.hooks.Stop' ~/.claude/settings.json
```

- [ ] **Step 2: Identify the V2 entry**

Look for any entry with `command` matching `*english-capture/capture.py*` or similar. Note its full string.

- [ ] **Step 3: Remove it (after backing up)**

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak.pre-rebuild
jq 'del(.hooks.Stop[] | select(.command | contains("capture.py")))' \
   ~/.claude/settings.json > /tmp/settings.json.tmp
mv /tmp/settings.json.tmp ~/.claude/settings.json
```

- [ ] **Step 4: Verify**

```bash
jq '.hooks.Stop' ~/.claude/settings.json
```

Expected: array no longer contains an entry referencing `capture.py`.

- [ ] **Step 5: Confirm CC still works**

In a separate Claude Code session: type any short prompt and let it complete. Verify there are no errors in the CC startup output and `~/.english-capture/logs/$(date +%Y-%m-%d).log` shows no new error entries.

---

## Task 14: Run `install.sh` on the dev Mac

- [ ] **Step 1: Run installer**

```bash
cd ~/.claude/hooks/english-capture
./install.sh
```

When prompted:
- OpenRouter API key: paste your key from `~/.english-capture/config.json` (the V2 config — should still exist) or get a fresh one at https://openrouter.ai/
- Vault path: accept the default if it points to your real vault

- [ ] **Step 2: Verify installer output ends with `✓ ready`**

If any step shows `✗`, check `~/.english-capture/logs/$(date +%Y-%m-%d).log` and fix before proceeding.

- [ ] **Step 3: Verify the Stop hook is registered**

```bash
jq '.hooks.Stop' ~/.claude/settings.json
```

Expected: an entry with `"command": "python3 /Users/wanmao/.claude/hooks/english-capture/grammar_hook.py"`.

- [ ] **Step 4: Verify the slash command symlink**

```bash
ls -la ~/.claude/commands/eng.md
```

Expected: symlink pointing to `~/.claude/hooks/english-capture/eng.md`.

---

## Task 15: Manual smoke test in a real CC session

- [ ] **Step 1: Open a new Claude Code session in any project**

- [ ] **Step 2: Test `/eng w`**

In the session, ask Claude to discuss a topic that uses an unfamiliar word. Then run:

```
/eng w 'serendipity'
```

(Use a word that didn't appear in conversation; this exercises the "context not found" path.) Then:

```
/eng w 'a-word-that-DID-appear-in-claude-output'
```

Verify both:
- The command returns `✓ saved <category>/<slug>.md` for each
- The card file exists in the vault at the printed path
- The first one (no context) has a Qwen-invented example
- The second has the real conversation context as the example

- [ ] **Step 3: Test dedup append**

```
/eng w 'a-word-that-DID-appear-in-claude-output'
```

(same word as before). Verify:
- Output: `↳ appended example to <category>/<slug>.md`
- The card now has two bullets under `**例句:**`
- The card frontmatter has an `updated:` field

- [ ] **Step 4: Test `/eng s`**

```
/eng s 'A long English sentence Claude said somewhere in this conversation.'
```

Verify card lands in `sentence/` with grammar_points.

- [ ] **Step 5: Test `/eng e`**

```
/eng e '这个 PR 我先放一放'
```

Verify card lands in `expression/` with two idiomatic English options.

- [ ] **Step 6: Test `/eng e` with non-Chinese input**

```
/eng e 'park this PR for now'
```

Verify output: `✗ /eng e expects Chinese input`.

- [ ] **Step 7: Test grammar hook fires on Stop**

In a new CC session, type a sentence with a deliberate grammar error:

```
I have went to the store yesterday morning to buy some milk.
```

Let Claude respond. Then end the session (Ctrl+D or `/exit`). Wait a few seconds for the hook to complete (it runs in the background; `~/.english-capture/logs/$(date +%Y-%m-%d).log` will show the activity). Verify a new card appears at `<vault>/20-Areas/英语/grammar/` with the corrected sentence.

- [ ] **Step 8: Test grammar hook skips correct input**

In another session, type a grammatically correct longer sentence:

```
I went to the store yesterday morning and bought some milk for the family.
```

End session. Verify NO new grammar card is written; logs show "no errors in: ...".

- [ ] **Step 9: Test grammar hook skips Chinese**

Type a Chinese sentence like `请帮我修复这个数据库查询的性能问题`, end session. Verify logs show "skipped (Chinese-dominant)" and no card.

- [ ] **Step 10: Test grammar hook skips short input**

Type `yes do that please`. End session. Verify logs show "skipped (too short)".

If all 10 steps pass, the dev-Mac install is verified. Commit a note:

```bash
cd ~/.claude/hooks/english-capture
git commit --allow-empty -m "$(cat <<'EOF'
test: dev Mac smoke test passed

Verified all 10 manual smoke test scenarios from the implementation plan
Task 15 on Mac mini / Mac Studio (whichever ran first).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push
```

---

## Task 16: Replicate to second Mac

- [ ] **Step 1: SSH or sit at the second Mac**

- [ ] **Step 2: Remove the V2 Stop hook entry there too**

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak.pre-rebuild
jq 'del(.hooks.Stop[] | select(.command | contains("capture.py")))' \
   ~/.claude/settings.json > /tmp/settings.json.tmp
mv /tmp/settings.json.tmp ~/.claude/settings.json
```

- [ ] **Step 3: Wipe the existing V2 directory and clone fresh**

```bash
rm -rf ~/.claude/hooks/english-capture
git clone https://github.com/wanmao/english-capture.git ~/.claude/hooks/english-capture
cd ~/.claude/hooks/english-capture
./install.sh
```

When prompted, paste the same OpenRouter API key. Vault path should auto-detect to the same iCloud vault.

- [ ] **Step 4: Run a single smoke test on this Mac**

```
/eng w 'cross-device-test'
```

Verify the card appears in the vault. Within a few seconds it should also be visible from the dev Mac (iCloud sync).

- [ ] **Step 5: Verify Obsidian SR sees new cards**

Open Obsidian on iPhone or iPad. Pull-to-refresh, then open Spaced Repetition plugin. New cards from today should appear in the review queue.

---

## Self-Review (run inline, fix issues, then proceed)

**1. Spec coverage:**

| Spec section | Implemented in task |
|---|---|
| 3 slash commands `/eng w/s/e` | Tasks 7, 9 |
| Stop hook → grammar-only | Task 8 |
| `install.sh` for cross-device | Task 11 |
| Vault dedup strategy B (append example) | Tasks 5, 7 |
| Reuse OpenRouter / transcript / md format know-how | Tasks 1, 4, 5 (rewrite, not copy) |
| Out-of-scope: review UI, listing/searching, daily stats, undo | not implemented (correct) |
| Card formats (4 types) | Task 5 |
| Dedup details (normalize_for_dedup, phrase_exists, grammar_already_checked) | Task 5 |
| Error matrix (queue on Qwen failure, vault unreachable, /eng e Chinese check) | Tasks 7, 8 |
| `eng.md` template | Task 9 |
| Migration plan: git init + push | Task 0.1 |
| Migration plan: wipe old code | Task 0.2 |
| Migration plan: freeze V2 Stop hook | Task 13 |
| Migration plan: smoke test dev Mac | Tasks 14, 15 |
| Migration plan: replicate to 2nd Mac | Task 16 |
| Backward compat: old cards have no `source` field, `phrase_exists` ignores it | Task 5 (`_PHRASE_RE` regex matches phrase/original/chinese without requiring `source`) |
| Testing strategy table | Tasks 1-8 each create their test_*.py |

**2. Placeholder scan:**

- ✅ No "TBD", "TODO", "implement later" in step bodies
- ✅ Every code step shows full code blocks
- ✅ All commands have expected output stated where applicable
- ⚠️ Task 9 (`eng.md`) is a prompt template — its quoting safety relies on Claude executing it correctly. The instruction in step 2 ("verify quoting mentally") is a meta-step, not a placeholder. Acceptable.

**3. Type consistency:**

- ✅ `qwen()` signature in Task 1 matches all callsites in Tasks 7, 8
- ✅ `phrase_exists`, `grammar_already_checked`, `append_example`, `write_*_card` signatures in Task 5 match callsites in Tasks 7, 8
- ✅ `extract_last_user_input` (Task 4) matches use in Task 8
- ✅ `is_chinese_dominant` (Task 4) matches use in Tasks 7, 8
- ✅ `WORD_SCHEMA`/`SENTENCE_SCHEMA`/etc. names consistent across Tasks 6, 7

No issues found.

**4. Open spec questions deferred to plan, addressed:**

- "Exact wording of system prompts" → Task 6 ships initial drafts; will iterate via lived usage feedback (no code change needed for tuning)
- "Whether `add_card.py` should support `--quiet`" → not implemented (YAGNI; user can `>/dev/null` if needed)
- "Whether `install.sh` should offer `--dry-run`" → not implemented (YAGNI; the smoke-test step + idempotency cover the same need)

---

## Execution Handoff

Plan complete and saved to `~/.claude/hooks/english-capture/docs/superpowers/plans/2026-04-27-manual-slash-commands-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for this plan because each task is small and isolated; subagents can finish in parallel where dependencies allow.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

Which approach?
