#!/bin/bash
# Git pre-commit hook: auto-fix docs + run quality gate
# Install: cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"

# Step 1: Auto-fix documentation issues
echo "Checking documentation consistency..."
python "$REPO_ROOT/scripts/validate_docs.py" --fix

# Re-stage any files that --fix modified
git add -u

# Step 2: Run quality gate
echo "Running quality gate..."
"$REPO_ROOT/scripts/quality_gate.sh"

echo "Pre-commit checks passed!"
