# English Capture Hook — Design Spec

**Date**: 2026-04-22
**Status**: OpenRouter pivot implemented locally; docs updated to match current code
**Replaces**: `~/projects/english-copilot/hook/` (DeepSeek + Supabase based)

**2026-04-22 pivot history**:
- First design: `claude -p --bare` with Haiku via CC CLI
- First pivot: Gemini REST to avoid CC subscription prompt overhead
- Final pivot for this repo: **OpenRouter OpenAI-compatible chat/completions** with `qwen/qwen3-235b-a22b-2507`

The codebase now treats OpenRouter as the source-of-truth backend. Any remaining Gemini / Haiku references elsewhere are historical only unless explicitly noted.

## Purpose

CC `Stop` hook that automatically extracts high-value English vocabulary, phrases, and grammar corrections from each CC session transcript, filters them via **OpenRouter**, and writes them as atomic markdown flashcards into the user's Obsidian vault at `20-Areas/英语/`.

**Why replace english-copilot**:
- Supabase is no longer the source of truth; the vault is canonical
- The old DeepSeek-based filter quality was not good enough
- Obsidian Spaced Repetition replaces the separate web review app

## Scope

**In scope**:
- CC Stop hook running on each session end
- Transcript last-turn extraction
- OpenRouter-based filtering with strict JSON schema output
- Vault-level dedup by phrase
- Atomic md writes into `20-Areas/英语/{category}/`
- Retry queue for transient upstream failures
- Cross-machine deployment (Mac mini + Mac Studio)

**Out of scope**:
- Retiring old english-copilot infra
- Changes to `/ingest`, `/inbox`, `/evergreen` Obsidian skills
- User profile evolution tooling

## Architecture

### Data flow

```
CC session ends (Stop event fires)
  ↓
capture.py receives {transcript_path} via stdin JSON
  ↓
1. Read transcript JSONL, extract last turn
   → user_input + claude_output
  ↓
2. If both empty → exit silently
  ↓
3. Load config.json fallback + user_profile.md
  ↓
4. Build system prompt (profile + recent phrases + strict schema rules)
  ↓
5. Call OpenRouter chat/completions
   → JSON string in choices[0].message.content
   → parsed to {vocabulary, grammar, skip_count, skip_reasons}
  ↓
6. For each extracted item:
   a. Check dedup against existing vault frontmatter
   b. If found → skip and log "dup"
   c. If not → generate md and write to 20-Areas/英语/{category}/{slug}.md
  ↓
7. Log summary line, exit 0
```

### Failure handling

| Failure | Behavior |
|---|---|
| Transcript file missing | Exit silently |
| Both user_input and claude_output empty | Exit silently |
| OpenRouter request fails (network, timeout, 4xx/5xx, malformed JSON) | Queue raw transcript payload, log WARN, exit 0 |
| Vault path not accessible | Log WARN, exit 0 |
| md write fails for a single item | Log ERROR for that item, continue |
| On next hook invocation | Drain queued items first, then process current session |

Hook should never crash the CC session for non-fatal operational failures.

## Components

### `capture.py`
Entry point. Reads stdin JSON, loads config/profile, drains retry queue, calls the LLM backend, dedups, and writes markdown files.

### `transcript.py`
Parses transcript JSONL and extracts the last meaningful user/assistant turn.

### `openrouter_client.py`
OpenRouter client implemented with stdlib `urllib`.

```python
def extract(
    user_input: str,
    claude_output: str,
    system_prompt: str,
    json_schema: dict,
    api_key: str,
    model: str = "qwen/qwen3-235b-a22b-2507",
) -> dict: ...
```

HTTP request shape:

```json
{
  "model": "qwen/qwen3-235b-a22b-2507",
  "messages": [
    {"role": "system", "content": "<system_prompt>"},
    {"role": "user", "content": "USER_INPUT:\n...\n\nCLAUDE_OUTPUT:\n..."}
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "extraction",
      "strict": true,
      "schema": "<JSON_SCHEMA>"
    }
  }
}
```

Response parsing:
- Parse the HTTP envelope JSON
- Read `choices[0].message.content`
- Parse that nested JSON string into the extraction dict

### `prompt_builder.py`
Builds the system prompt and exports `JSON_SCHEMA`.

Important OpenRouter strict-mode requirements:
- `additionalProperties: false` at every object level
- every declared field in nested objects is listed in `required`
- fields such as `phonetic`, `context`, and `usage_note` must be emitted as empty strings when unknown

### `dedup.py`
Checks whether a phrase already exists in the vault and loads recent phrases as a negative few-shot signal.

### `md_writer.py`
Writes vocabulary and grammar flashcards in the existing Obsidian-compatible format.

### `queue.py`
Persists retryable payloads to `~/.english-capture/queue.json`.

### `logger.py`
Appends log lines into `~/.english-capture/logs/YYYY-MM-DD.log`.

## Directory Layout

### Source repo
```
~/.claude/hooks/english-capture/
├── .git/
├── capture.py
├── transcript.py
├── openrouter_client.py
├── prompt_builder.py
├── dedup.py
├── md_writer.py
├── queue.py
├── logger.py
├── user_profile.md
├── config.example.json
├── pyproject.toml
├── tests/
└── docs/
    └── superpowers/specs/
        └── 2026-04-22-english-capture-hook-design.md
```

### Runtime (not in git, per machine)
```
~/.english-capture/
├── config.json
├── queue.json
└── logs/
    └── 2026-04-22.log
```

### Output
```
<vault>/20-Areas/英语/{adjective,noun,verb,adverb,phrasal-verb,collocation,idiom,grammar}/
```

## CC Configuration

`~/.claude/settings.json` on each machine:

```json
{
  "hooks": {
    "Stop": [
      {
        "command": "python ~/.claude/hooks/english-capture/capture.py",
        "timeout": 90
      }
    ]
  }
}
```

`timeout: 90` is a safe upper bound for cold starts and queue draining.

## Prompt Design

### System prompt structure

```
You are an English learning assistant for a Chinese senior developer.

## USER PROFILE
<content of user_profile.md — defines SKIP vs KEEP rules>

## RECENTLY CAPTURED (already in library — DO NOT extract these again)
<last 10 phrases from vault>

## TASK
Given USER_INPUT and CLAUDE_OUTPUT in the user message below, extract:

1. vocabulary — words and phrases worth learning per the USER PROFILE rules
2. grammar — real language lessons only; skip trivial punctuation/spacing/casing fixes

For each vocabulary item, pick category strictly from:
- For words: adjective | noun | verb | adverb
- For phrases: phrasal-verb | collocation | idiom

Default SKIP. Quality > quantity. Target 30-40% keep rate.

## OUTPUT
Return ONLY valid JSON matching the schema.
Do not add prose outside JSON.
If a required string field is unavailable, use an empty string.
This especially applies to phonetic, context, and usage_note.
```

### JSON schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["vocabulary", "grammar", "skip_count", "skip_reasons"],
  "properties": {
    "vocabulary": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["phrase", "category", "cefr", "translation", "phonetic", "context", "usage_note"],
        "properties": {
          "phrase": {"type": "string"},
          "category": {"enum": ["adjective", "noun", "verb", "adverb", "phrasal-verb", "collocation", "idiom"]},
          "cefr": {"enum": ["B1", "B2", "C1", "C2"]},
          "translation": {"type": "string"},
          "phonetic": {"type": "string"},
          "context": {"type": "string"},
          "usage_note": {"type": "string"}
        }
      }
    },
    "grammar": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["original", "corrected", "error_type", "explanation"],
        "properties": {
          "original": {"type": "string"},
          "corrected": {"type": "string"},
          "error_type": {"enum": ["word_choice", "collocation", "grammar"]},
          "explanation": {"type": "string"}
        }
      }
    },
    "skip_count": {"type": "integer"},
    "skip_reasons": {"type": "string"}
  }
}
```

This shape matches OpenRouter `response_format.json_schema.strict = true`.

## Dedup Strategy

Before writing each vocabulary item, check whether the phrase already exists in vault frontmatter.

```python
def phrase_exists(phrase: str, vault_path: str) -> bool:
    ...
```

- If exists → log "dup: <phrase>", skip write
- If not → proceed

User deletions are respected implicitly: if a file is deleted, `phrase_exists()` returns `False`, so the hook may recapture it later.

## Cross-Machine Deployment

### Development / source of truth
Mac mini hosts git repo at `~/.claude/hooks/english-capture/`. All edits happen here.

### Deploy to Mac Studio
**Manual on-demand rsync** after each round of changes (not automatic — user controls when):

```bash
# deploy-to-studio.sh  (save as a helper script in the repo)
rsync -av --exclude .git --exclude __pycache__ \
  ~/.claude/hooks/english-capture/ \
  macstudio:~/.claude/hooks/english-capture/

# First install only: also manually append the Stop hook snippet to
# Mac Studio's ~/.claude/settings.json (same as mini)
```

**`user_profile.md`** is the one piece of content that moves with the hook (not runtime config). On first install, copy the current one from `~/projects/english-copilot/hook/user_profile.md` or `~/.english-copilot/hook/user_profile.md` into the new repo.

### Config per machine
`~/.english-capture/config.json` is NOT in git and has mode 0600. Each machine has its own:

```json
{
  "vault_path": "/Users/wanmao/Library/Mobile Documents/iCloud~md~obsidian/Documents",
  "llm_provider": "openrouter",
  "openrouter_api_key": "sk-or-...",
  "openrouter_model": "qwen/qwen3-235b-a22b-2507",
  "timeout_seconds": 60,
  "log_level": "INFO"
}
```

`config.example.json` in the repo mirrors these keys and acts as a fallback when runtime config is absent.

## Cost Estimate

- OpenRouter + Qwen3 is expected to be materially cheaper than the original `claude -p` path because it avoids the huge base system prompt overhead
- The exact bill depends on model pricing and session volume
- Model name stays config-driven so backend economics can be revisited without changing code

## Success Criteria

1. Hook fires on every CC Stop event without user intervention
2. 95%+ of Stop events complete within 10 seconds
3. Vocab captured rate ≤ 5 new items per session (filter is strict)
4. Zero duplicates in vault after 1 month of use
5. Quality bar: captured items should look like the 225 migrated ones (no CS jargon, no CET-4 noise)
6. Retry queue drains within 3 subsequent invocations when transient failures happen
7. Works identically on Mac mini and Mac Studio

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OpenRouter rate limit hit (429) | Retry queue handles transients |
| OpenRouter API key invalid / revoked | Log WARN, queue items, rotate key in config |
| Model deprecated / renamed | Model is config-driven, not hardcoded in call sites |
| Vault not iCloud-synced when hook fires | Check vault readable; if not, queue and retry |
| Recursion via nested CC sessions | Not a risk; the hook calls OpenRouter directly |
| User runs hook on both machines simultaneously, race on same filename | Unlikely in practice; worst case one overwrites; no data loss since both have same content |
| Provider returns bad JSON | Strict schema + nested JSON parse validation; otherwise log and queue |
| Backend economics change | Switch model in config, or change provider behind `openrouter_client.py` |

## Out of Scope Future Enhancements

- Batch mode to process multiple sessions / backfill
- Web UI for review analytics (dataview queries in Obsidian may suffice)
- Sentiment / difficulty auto-adjustment
- Integration with `/inbox` flow (might merge if overlap emerges)

## Implementation Order

1. Keep `transcript.py`, `dedup.py`, `md_writer.py`, `queue.py`, and `logger.py` unchanged unless required by new backend behavior
2. Replace `gemini_client.py` with `openrouter_client.py`
3. Tighten `prompt_builder.JSON_SCHEMA` for OpenRouter strict mode
4. Update `capture.py` imports, config keys, and error handling to use OpenRouter
5. Rename and rewrite client tests to match OpenRouter response envelopes
6. Update `config.example.json`
7. Verify with pytest, then run a real hook smoke test against a transcript fixture or live transcript

## Implementation Delta (Task 14)

The concrete late-pivot work for Task 14 is:

1. `gemini_client.py` → `openrouter_client.py` using the OpenAI-compatible payload shape
2. `prompt_builder.py` strict schema updates:
   - `additionalProperties: false` at every object level
   - all nested properties listed in `required`
   - prompt explicitly instructs empty-string fallbacks for required optional-looking fields
3. `capture.py` updates:
   - import `openrouter_client`
   - read `openrouter_api_key` and `openrouter_model`
   - catch `OpenRouterError`
4. Test migration:
   - `tests/test_gemini_client.py` → `tests/test_openrouter_client.py`
   - mock the OpenRouter `choices[0].message.content` response envelope
5. `config.example.json` updates:
   - `llm_provider: "openrouter"`
   - `openrouter_*` config keys
