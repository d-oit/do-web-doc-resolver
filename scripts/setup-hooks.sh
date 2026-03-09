#!/bin/bash
# Setup git hooks for the repository

HOOKS_DIR=".git/hooks"
PRE_COMMIT_HOOK="$HOOKS_DIR/pre-commit"

cat > "$PRE_COMMIT_HOOK" << 'EOF'
#!/bin/bash
# Pre-commit hook to validate skill symlink

echo "🔍 Validating skill symlink..."
python scripts/validate_skill_symlink.py

if [ $? -ne 0 ]; then
    echo "❌ Commit blocked: Skill symlink validation failed"
    exit 1
fi

echo "✅ Skill symlink validation passed"
exit 0
EOF

chmod +x "$PRE_COMMIT_HOOK"
echo "✅ Pre-commit hook installed at $PRE_COMMIT_HOOK"
