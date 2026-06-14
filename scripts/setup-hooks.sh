#!/bin/bash
# Setup git hooks for the repository
# Installs the full pre-commit hook from .githooks/pre-commit

HOOKS_DIR=".git/hooks"
PRE_COMMIT_HOOK="$HOOKS_DIR/pre-commit"
SOURCE_HOOK=".githooks/pre-commit"

if [ ! -f "$SOURCE_HOOK" ]; then
    echo "❌ Source hook not found: $SOURCE_HOOK"
    exit 1
fi

cp "$SOURCE_HOOK" "$PRE_COMMIT_HOOK"
chmod +x "$PRE_COMMIT_HOOK"
echo "✅ Pre-commit hook installed at $PRE_COMMIT_HOOK"
