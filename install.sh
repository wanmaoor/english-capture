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
VENV_DIR="$REPO_DIR/.venv"
COMMAND_LINK="$HOME/.claude/commands/eng.md"
SETTINGS_PATH="$HOME/.claude/settings.json"
HOOK_CMD="$VENV_DIR/bin/python $REPO_DIR/grammar_hook.py"
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
        # CC Stop hook schema is nested: hooks.Stop[].hooks[].command
        # Drop any Stop group whose hooks contain a command referencing our grammar_hook.py
        jq --arg path "$REPO_DIR/grammar_hook.py" \
           '.hooks.Stop |= map(select(.hooks // [] | any(.command | contains($path)) | not))' \
           "$SETTINGS_PATH" > "$SETTINGS_PATH.tmp"
        mv "$SETTINGS_PATH.tmp" "$SETTINGS_PATH"
        c_ok "removed Stop hook entry from $SETTINGS_PATH (backup: $SETTINGS_PATH.bak.$TODAY)"
    fi

    c_ok "done. $RUNTIME_DIR/ left intact (config + logs); remove manually if desired."
}

install() {
    c_step "Installing english-capture from $REPO_DIR"

    # 1. Detect dependencies
    c_step "1/7 detecting dependencies"
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

    # 2. Bootstrap venv (fresh-Mac case)
    c_step "2/7 venv bootstrap"
    if [[ ! -x "$VENV_DIR/bin/python" ]]; then
        python3 -m venv "$VENV_DIR"
        c_ok "created $VENV_DIR"
    else
        c_ok "$VENV_DIR exists"
    fi
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -e "$REPO_DIR[dev]"
    c_ok "dev deps installed in venv"

    # 3. Runtime directories
    c_step "3/7 runtime directories"
    mkdir -p "$LOGS_DIR"
    c_ok "$RUNTIME_DIR/{logs}"

    # 4. Config bootstrap
    c_step "4/7 config"
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

    # 5. Slash command symlink
    c_step "5/7 slash command (~/.claude/commands/eng.md)"
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

    # 6. Stop hook registration
    c_step "6/7 Stop hook registration"
    mkdir -p "$(dirname "$SETTINGS_PATH")"
    if [[ ! -f "$SETTINGS_PATH" ]]; then
        echo '{}' > "$SETTINGS_PATH"
    fi
    cp "$SETTINGS_PATH" "$SETTINGS_PATH.bak.$TODAY"

    # CC Stop hook schema is nested: hooks.Stop[].hooks[].command
    EXISTS=$(jq --arg cmd "$HOOK_CMD" \
        '[.hooks.Stop // [] | .[] | .hooks // [] | .[] | select(.command == $cmd)] | length' \
        "$SETTINGS_PATH")
    if [[ "$EXISTS" == "0" ]]; then
        jq --arg cmd "$HOOK_CMD" \
           '.hooks.Stop = ((.hooks.Stop // []) + [{"hooks": [{"type": "command", "command": $cmd, "timeout": 90, "async": true}]}])' \
           "$SETTINGS_PATH" > "$SETTINGS_PATH.tmp"
        mv "$SETTINGS_PATH.tmp" "$SETTINGS_PATH"
        c_ok "added Stop hook entry (backup: $SETTINGS_PATH.bak.$TODAY)"
    else
        c_ok "Stop hook entry already present"
    fi

    # 7. Smoke test
    c_step "7/7 smoke test"
    SAMPLE_EVENT="$REPO_DIR/tests/fixtures/sample_stop_event.json"
    if [[ -f "$SAMPLE_EVENT" ]]; then
        # Run with venv python so deps are present
        if "$VENV_DIR/bin/python" "$REPO_DIR/grammar_hook.py" < "$SAMPLE_EVENT" >/dev/null 2>&1; then
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
