# Manual Slash Commands — Design Spec

**Date**: 2026-04-27
**Status**: APPROVED (pending user spec review)
**Replaces (functionally)**: the auto-vocab path of `2026-04-22-english-capture-hook-design.md`. The Stop hook is repurposed to grammar-only.

## Purpose

Replace the Stop-hook-driven auto vocabulary extraction with **user-initiated slash commands** in Claude Code, so the user (sole judge of "what's worth learning") explicitly picks every vocabulary item. The Stop hook continues to run, but its only job becomes **grammar correction of the user's recent English input** — an objective task suited to automation.

## Motivation

The auto extraction produced two persistent failure modes:
1. **Noise**: too many CET-4-and-below or contextually trivial words kept (the user's filter rules in `user_profile.md` could not fully eliminate this)
2. **Misses**: words the user *did* find valuable were silently dropped because the LLM judged them too common

The user's own judgment in the moment ("yes, I want to learn this") is the only reliable signal. Slash commands surface that signal directly.

The split between automatic and manual is **by judgment subjectivity**, not by data type:
- Vocabulary value is subjective → human (slash command)
- Grammar correctness is objective → machine (Stop hook)

## Scope

**In scope**:
- Three slash commands: `/eng w`, `/eng s`, `/eng e` (single template `eng.md` with arg dispatch)
- Stop hook repurposed to grammar-only correction of last user input
- Cross-device install script (`install.sh`) that handles config, slash command symlink, Stop hook registration in `~/.claude/settings.json`
- Vault dedup: word/sentence types append example to existing card; grammar uses normalized-original dedup
- Reuse of OpenRouter Qwen backend, transcript parsing, vault md format from V2

**Out of scope**:
- Cards review UI (Obsidian Spaced Repetition plugin already covers this)
- Migration of existing 260+ cards (no schema change to the cards themselves)
- Listing / searching / deleting cards from CLI (Obsidian native search covers it)
- Daily stats of grammar checks performed (explicitly declined by user)
- Undo / removal commands (explicitly declined by user)

## Architecture

### Directory layout

`~/.claude/hooks/english-capture/` is rebuilt clean. Old V2 files are physically removed; reusable implementations are rewritten with the same know-how (OpenRouter call shape, transcript jsonl parsing, md frontmatter format, Obsidian SR `?` flashcard syntax).

```
~/.claude/hooks/english-capture/
├── README.md                    # install + usage
├── install.sh                   # idempotent cross-device installer
├── config.example.json          # OpenRouter key + vault path template
├── eng.md                       # slash command template (symlinked into ~/.claude/commands/)
│
├── add_card.py                  # CLI invoked by slash command (handles w/s/e)
├── grammar_hook.py              # Stop hook entry (grammar-only)
│
├── openrouter.py                # OpenRouter Qwen client
├── transcript.py                # CC transcript jsonl parser
├── vault.py                     # md read/write/dedup/append
├── prompts.py                   # 4 system prompts + JSON schemas (w/s/e/grammar)
├── queue.py                     # retry queue
├── logger.py                    # daily file logger
│
├── tests/
│   ├── test_transcript.py
│   ├── test_vault.py
│   ├── test_prompts.py
│   ├── test_openrouter.py
│   ├── test_add_card.py
│   ├── test_grammar_hook.py
│   └── fixtures/
└── pyproject.toml
```

`explicit_terms.py` from V2 is deleted — manual mode makes its "force-keep explicitly queried terms" purpose obsolete.

### Component responsibilities

| Module | Responsibility |
|---|---|
| `eng.md` | Prompt template. Parses `$ARGUMENTS`, finds context in current transcript, calls `add_card.py`. |
| `add_card.py` | CLI: `--type {w,s,e} --phrase ... --context ...`. Calls Qwen, dedups, writes md, prints one-line result. |
| `grammar_hook.py` | Stop hook: filter → Qwen grammar check → write grammar md (only if errors). |
| `openrouter.py` | HTTP client for OpenRouter chat/completions with strict JSON schema. |
| `transcript.py` | Read CC jsonl; extract last user input; helpers for grep/dedup. |
| `vault.py` | `phrase_exists`, `append_example`, `write_card`, `write_grammar_card`, `recent_phrases`, `normalize_for_dedup`. |
| `prompts.py` | 4 system prompts and 4 JSON schemas: `WORD_SCHEMA`, `SENTENCE_SCHEMA`, `EXPRESSION_SCHEMA`, `GRAMMAR_SCHEMA`. |
| `queue.py` | Same as V2 — file-backed retry queue; drained on next hook fire. |
| `logger.py` | Same as V2 — daily log files in `~/.english-capture/logs/`. |

### Slash command flow

User input: `/eng w 'cardinality estimation'`

```
1. CC reads ~/.claude/commands/eng.md, fills $ARGUMENTS = "w 'cardinality estimation'"
2. Claude executes the prompt template:
   a. Parse: type = "w", phrase = "cardinality estimation"
   b. Search current session transcript for the phrase:
      - exact match first (most recent occurrence)
      - case-insensitive / punctuation-stripped match next
      - if not found: context = ""
   c. Extract surrounding 2-4 sentences as context
   d. Run: python3 ~/.claude/hooks/english-capture/add_card.py \
        --type w --phrase "cardinality estimation" \
        --context "...This query suffers from cardinality estimation errors on the join..."
3. add_card.py:
   a. vault.phrase_exists(phrase) ?
      - true  → vault.append_example(card_path, context); print "↳ appended example to noun/cardinality-estimation.md"
      - false → continue
   b. openrouter.qwen(prompts.WORD_SCHEMA, phrase, context) →
      { phrase, category, translation_zh, memory_tip, context_sentence }
   c. vault.write_card(noun/cardinality-estimation.md, qwen_result)
   d. print "✓ saved noun/cardinality-estimation.md"
4. Claude echoes CLI stdout to user
```

### Type-specific behavior of `add_card.py`

| `--type` | phrase content | context source | Qwen output fields |
|---|---|---|---|
| `w` | English word or fixed phrase | transcript paragraph containing phrase | `phrase, category, translation_zh, memory_tip, context_sentence` |
| `s` | Long / hard English sentence | transcript paragraph containing sentence | `original, translation_zh, grammar_points, key_vocab` |
| `e` | **Chinese** expression | recent user-question + Claude-answer about how to express it (if any) | `chinese, idiomatic_english (1-2 options), use_case, anti_example` |

`/eng e` rejects non-Chinese input with `✗ /eng e expects Chinese input`. Detection: ratio of CJK Unicode chars > 50%.

### Grammar hook flow (`grammar_hook.py`)

```
CC Stop event
  ↓
Read stdin → {hook_event_name, transcript_path}
  ↓
Skip if hook_event_name != "Stop"
  ↓
transcript.read() → last user_input
  ↓
Filter (any hit → exit 0):
  - input.startswith("/")           # slash command itself
  - len(input.split()) < 5          # too short
  - is_chinese_dominant(input)      # CJK ratio > 50%
  - vault.grammar_already_checked(normalize(input))
  ↓
queue.drain()  # retry past failures first
  ↓
openrouter.qwen(GRAMMAR_SCHEMA, input) →
  { has_error: bool, original, corrected, errors: [{type, explain}] }
  ↓
has_error == false → log INFO "no errors", exit 0
has_error == true  → vault.write_grammar_card(...); log INFO "saved grammar/{slug}.md"
  ↓
Any OpenRouter failure → queue.add(input)
```

### Card formats

**Vocabulary card** (`20-Areas/英语/{category}/{slug}.md`):

```markdown
---
phrase: "cardinality estimation"
category: noun
created: 2026-04-27
source: manual_w
---

cardinality estimation
?
**中文:** 基数估计

**记忆点:** 数据库查询规划器估算结果行数。

**例句:**
- This query suffers from cardinality estimation errors on the join.
```

When dedup hits and `append_example` fires, only the `**例句:**` list grows. Frontmatter `created` is preserved; an `updated` field is added/refreshed.

**Sentence card** (`20-Areas/英语/sentence/{slug}.md`):

```markdown
---
original: "Despite the migration succeeding, downstream consumers reported stale reads."
type: sentence
created: 2026-04-27
source: manual_s
---

Despite the migration succeeding, downstream consumers reported stale reads.
?
**中文:** 尽管迁移成功了，下游消费者还是报告读到了旧数据。

**语法点:**
- `Despite + 动名词短语` 等价于 `Although + 从句`

**生词:** stale reads（脏读 / 旧读）
```

**Expression card** (`20-Areas/英语/expression/{slug}.md`):

```markdown
---
chinese: "这个 PR 我先放一放"
type: expression
created: 2026-04-27
source: manual_e
---

这个 PR 我先放一放
?
**地道表达:**
1. I'll put this PR on the back burner for now.
2. Let me park this PR for a bit.

**使用场景:** 工作中需要暂时搁置某事但不放弃。

**反例:** "I will pause this PR" 太字面，母语者更偏好 back burner / park 这种隐喻。
```

**Grammar card** (`20-Areas/英语/grammar/{slug}.md`):

```markdown
---
original: "I have went to the store yesterday."
checked_at: 2026-04-27
type: grammar
source: auto_grammar
---

I have went to the store yesterday.
?
**Corrected:** I went to the store yesterday.

**错误点:**
- `have went` → `went`：过去时不能用 have + 过去分词的完成时形式来表达单纯过去事件。
```

### Dedup details

`vault.normalize_for_dedup(s)`:
- lowercase
- strip leading/trailing whitespace
- collapse internal whitespace runs to single space
- strip ASCII punctuation: `. , ; : ? ! " '`
- strip CJK punctuation: `。 ， ； ： ？ ！ " "`

For vocabulary/sentence: `phrase_exists` greps frontmatter `phrase:` / `original:` of all md in the relevant category dir, normalizes both sides, compares for equality.

For grammar: `grammar_already_checked` greps `original:` in `grammar/`, same normalize comparison. **Once normalized-equal, never re-check** — even across days.

For dedup hit on `w` and `s`: append the new context sentence to the `**例句:**` list, deduped by exact-string within that list.

For `e`: dedup is on the `chinese` frontmatter field. On hit, append the new idiomatic_english option to the existing list.

### Error matrix

| Failure | Behavior |
|---|---|
| Phrase not in transcript | context = ""; Qwen invents an example; WARN log |
| OpenRouter timeout / 5xx | `queue.add()`; CLI prints `✗ queued for retry` |
| OpenRouter returns invalid JSON / schema mismatch | retry once; still fail → queue, CLI `✗ schema mismatch (queued)` |
| Vault path not writable | CLI `✗ vault unreachable`; **not queued** (retrying won't fix disk-level failures) |
| `/eng e` input not Chinese | CLI `✗ /eng e expects Chinese input`; no Qwen call |
| iCloud conflict on simultaneous Mac writes | iCloud handles natively (`(Mac mini's conflicted copy).md`); not in our error path |
| Stop hook fires while CLI is mid-write | extremely unlikely (different categories — grammar hook only writes `grammar/`, slash command writes `noun/verb/sentence/expression/`). If a same-file race ever occurs, last-writer-wins is acceptable for this single-user system. |

## Cross-device install (`install.sh`)

Goal: from a fresh Mac with CC installed, `git clone <repo> ~/.claude/hooks/english-capture && cd $_ && ./install.sh` produces a working setup.

Steps (idempotent — safe to re-run):
1. **Detect dependencies**: python3 ≥ 3.10, jq, Obsidian vault path. Vault not found → instruct user to install Obsidian + iCloud sync first; exit non-zero.
2. **Runtime dirs**: `mkdir -p ~/.english-capture/logs`.
3. **Config**: if `~/.english-capture/config.json` missing, copy from `config.example.json`; prompt interactively for OpenRouter API key and vault path (defaults pre-filled); chmod 0600.
4. **Slash command**: symlink `eng.md` → `~/.claude/commands/eng.md`. If existing file present, back up to `eng.md.bak.YYYYMMDD`.
5. **Stop hook registration**: back up `~/.claude/settings.json` to `settings.json.bak.YYYYMMDD`; use jq to upsert a `Stop[]` entry running `python3 ~/.claude/hooks/english-capture/grammar_hook.py`. Detect existing entry by command-string match.
6. **Smoke test**: run `python3 grammar_hook.py < tests/fixtures/sample_stop_event.json`; verify OpenRouter reachable + vault writable; print `✓ ready` or `✗ <step>`.
7. **Closing message**: instruct user to try `/eng w 'serendipity'` in any CC session.

**Uninstall**: `./install.sh --uninstall` removes the slash command symlink, removes the Stop hook entry from `settings.json`, leaves `~/.english-capture/` (config + logs) intact for user to clean manually.

**Dependencies kept minimal**: stdlib + `urllib` only at runtime; `jq` is the one external tool needed by `install.sh`. Dev-only dependency: `pytest` declared in `pyproject.toml`.

## Testing strategy

Sustains the V2 TDD pattern. Targets: lib modules ≥ 90% line coverage, entry scripts ≥ 70% (integration-test heavy).

| Test file | Covers |
|---|---|
| `test_transcript.py` | jsonl parsing, last-input extraction, CJK ratio detection |
| `test_vault.py` | `phrase_exists`, `normalize_for_dedup`, `append_example` (preserves frontmatter, dedups within list), card creation atomicity |
| `test_prompts.py` | 4 schemas validate sample Qwen responses; 4 system prompts contain non-empty user_profile + recent_phrases interpolation |
| `test_openrouter.py` | mock httpx: 200 happy path, timeout, 5xx, schema-mismatched response triggers single retry |
| `test_add_card.py` | CLI integration: each `--type` end-to-end with mocked openrouter and tmp vault; dedup-append path; `/eng e` non-Chinese rejection |
| `test_grammar_hook.py` | Stop event → grammar card; each filter rule individually; queue drain; queue add on failure |

`eng.md` template itself is **not unit-tested** — it is a prompt, behavior is judged by Claude execution; iteration is by lived usage feedback (same convention as V2's untested user-facing prompts).

## Migration plan

0. **Git repo bootstrap** (V2 is currently not under git):
   - `cd ~/.claude/hooks/english-capture && git init`
   - Create a private GitHub repo (e.g. `english-capture`)
   - Add `.gitignore`: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `config.json` (the runtime config in `~/.english-capture/` is already outside the repo)
   - Initial commit captures the V2 state for history; immediately followed by a "wipe" commit (see step 1)
   - Push to GitHub
1. **Wipe old V2 code** per "洁癖派" decision: delete all current `.py` files and obsolete configs; **no backup** (user explicitly declined). Keep `docs/`, `tests/fixtures/` only if reusable. Commit as "wipe: clear V2 auto-vocab implementation, prepare for manual-slash rebuild".
2. **Freeze** the V2 Stop hook by removing its entry from `~/.claude/settings.json` — no new auto-vocab cards from this point.
3. **Build** the new code per the implementation plan (next step).
4. **Smoke test** on the dev Mac via `install.sh` and a few real `/eng w/s/e` invocations + a few real Stop-event grammar checks.
5. **Replicate** to the second Mac: `git clone <github-url> ~/.claude/hooks/english-capture && cd $_ && ./install.sh`.
6. **Existing 260+ cards** stay untouched in place. Backward compatibility:
   - Old cards have no `source` frontmatter field → `vault.phrase_exists` matches purely on `phrase:` / `original:`, ignoring `source`
   - Old cards' Obsidian SR `?` flashcard format is unchanged
   - New cards add `source: manual_w | manual_s | manual_e | auto_grammar` for future analytics, but no current code path reads it
   Obsidian SR continues uninterrupted.

## Open questions deferred to implementation plan

- Exact wording of the four system prompts (will be tuned during TDD)
- Whether `add_card.py` should support `--quiet` for silent dedup hits
- Whether `install.sh` should also offer `--dry-run`
