#!/bin/bash
# Setup git hooks for the repository
# Installs the full pre-commit hook from .githooks/pre-commit

set -e

HOOKS_DIR=".git/hooks"
PRE_COMMIT_HOOK="$HOOKS_DIR/pre-commit"
SOURCE_HOOK=".githooks/pre-commit"
QUALITY_GATE="scripts/quality_gate.sh"

if [ ! -f "$SOURCE_HOOK" ]; then
    echo "❌ Source hook not found: $SOURCE_HOOK"
    exit 1
fi

if [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ .git/hooks directory not found. Are you in a git repo?"
    exit 1
fi

# Install pre-commit hook
cp "$SOURCE_HOOK" "$PRE_COMMIT_HOOK"
chmod +x "$PRE_COMMIT_HOOK"
echo "✅ Pre-commit hook installed at $PRE_COMMIT_HOOK"

# Validate quality gate script
if [ ! -f "$QUALITY_GATE" ]; then
    echo "❌ Quality gate not found: $QUALITY_GATE"
    exit 1
fi
chmod +x "$QUALITY_GATE"
echo "✅ Quality gate ready: $QUALITY_GATE"

# Validate quality gate syntax
if bash -n "$QUALITY_GATE"; then
    echo "✅ Quality gate syntax OK"
else
    echo "❌ Quality gate has syntax errors"
    exit 1
fi

# Summary
echo ""
echo "=== Git hooks setup complete ==="
echo "  Hook:       $PRE_COMMIT_HOOK"
echo "  Quality:    $QUALITY_GATE"
echo "  Checks run: markdownlint, quality gate, checkpoint validation"
