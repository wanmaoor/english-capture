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

Run this exact command (substitute `<TYPE>`, `<PHRASE>`, `<CONTEXT>` with the parsed values; properly shell-quote each argument — wrap in single quotes and escape any embedded single quotes as `'\''`):

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
