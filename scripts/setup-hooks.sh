#!/bin/bash
# Setup git hooks for the repository
# Installs the hooks from .githooks/: pre-commit (fast local gate),
# commit-msg (commitlint format) and pre-push (CI-parity checks by changed path)

set -e

# --git-path resolves the shared hooks dir in linked worktrees (where .git is a file)
HOOKS_DIR="$(git rev-parse --git-path hooks)"
QUALITY_GATE="scripts/quality_gate.sh"
HOOK_NAMES=("pre-commit" "commit-msg" "pre-push")

if [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ Hooks directory not found: $HOOKS_DIR. Are you in a git repo?"
    exit 1
fi

for hook in "${HOOK_NAMES[@]}"; do
    source_hook=".githooks/$hook"
    if [ ! -f "$source_hook" ]; then
        echo "❌ Source hook not found: $source_hook"
        exit 1
    fi
    cp "$source_hook" "$HOOKS_DIR/$hook"
    chmod +x "$HOOKS_DIR/$hook"
    echo "✅ $hook hook installed at $HOOKS_DIR/$hook"
done

# Validate quality gate script
if [ ! -f "$QUALITY_GATE" ]; then
    echo "❌ Quality gate not found: $QUALITY_GATE"
    exit 1
fi
chmod +x "$QUALITY_GATE"
echo "✅ Quality gate ready: $QUALITY_GATE"

# Validate hook and quality gate syntax
for script in "$QUALITY_GATE" ".githooks/pre-commit" ".githooks/commit-msg" ".githooks/pre-push"; do
    if bash -n "$script"; then
        echo "✅ Syntax OK: $script"
    else
        echo "❌ Syntax errors in $script"
        exit 1
    fi
done

# Summary
echo ""
echo "=== Git hooks setup complete ==="
echo "  Hooks:      $HOOKS_DIR/{pre-commit,commit-msg,pre-push}"
echo "  Quality:    $QUALITY_GATE"
echo "  Pre-commit: markdownlint, quality gate, checkpoint validation"
echo "  Commit-msg: commitlint format check (needs: npm install)"
echo "  Pre-push:   CI-parity checks for changed paths (docs, Python, Rust, web, YAML, markdown, commits)"
