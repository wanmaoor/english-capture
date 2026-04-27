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
git clone https://github.com/wanmaoor/english-capture.git ~/.claude/hooks/english-capture
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
