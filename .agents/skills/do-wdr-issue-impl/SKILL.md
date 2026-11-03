---
name: do-wdr-issue-impl
description: Implement a single GitHub issue from start to merged PR. Use when the user asks to "implement issue #N", "fix #N", "start on #N", or wants to work on one specific GitHub issue. Covers issue analysis, codebase exploration, implementation, testing, lint fixes, PR creation, CI monitoring, and merge. For batch implementation of multiple issues, use do-wdr-issue-swarm instead.
allowed-tools: Bash(git:*), Bash(gh:*), Bash(python:*), Read, Write, Edit, Glob, Grep, Task
---

# Single Issue Implementation

Implement one GitHub issue through the full lifecycle: issue → code → tests → PR → CI green → merge.

## When to use

- "Implement issue #491"
- "Fix #490"
- "Start on #488"
- Any request to work on a single specific GitHub issue

## Workflow

### 1. Read and understand the issue

```bash
gh issue view {N} --json title,body,labels,state
```

Parse the issue body for:

- Summary and problem statement
- Proposed solution (file changes, new files)
- Acceptance criteria
- Tests required

### 2. Explore codebase context

Use explore agents to understand:

```text
Task(
  description="Explore codebase for issue #{N}",
  prompt="Search for: [specific files/patterns from issue]. Report file paths, line numbers, current implementation.",
  subagent_type="explore"
)
```

Read the key files identified. Understand:

- Current implementation that needs changing
- Related code that might be affected
- Existing patterns to follow

### 3. Implement changes

Create or modify files according to the issue spec:

- Follow existing code conventions (see AGENTS.md)
- Add type annotations (never use `Any` as shortcut)
- Update skills snapshot if changing `scripts/` files
- Keep functions focused and under 500 lines

### 4. Run tests

```bash
python -m pytest -m "not live" -x
```

If tests fail, fix before proceeding. Run targeted tests first:

```bash
python -m pytest tests/test_{related}.py -v
```

### 5. Fix lint and type errors

```bash
python -m ruff check scripts/ tests/ --fix
python -m black scripts/ tests/
python -m mypy scripts/{changed_files}
```

Fix all errors. Never commit with lint failures.

### 6. Commit with conventional format

```bash
git add {files}
git commit -m "{type}({scope}): {description} (#{N})

- Change 1
- Change 2"
```

**Scope must be from allowed enum:** `resolver, cli, web, ci, docs, deps, security, release, agents, test`

**Commitlint rules:**

- Header max 150 chars
- Body lines max 100 chars
- Body max 2000 chars total

### 7. Push and create PR

```bash
git push origin {branch}
gh pr create --title "{type}({scope}): {description}" --body "$(cat <<'EOF'
## Summary
{1-3 bullet points}

## Changes
| File | Change |
|------|--------|

## Test Results
- {test counts}

Closes #{N}
EOF
)"
```

**PR title must match commit format** — same scope-enum rules apply.

### 8. Monitor CI

```bash
gh pr checks {PR} --watch
```

Wait for all checks to complete. Check for failures:

```bash
gh pr checks {PR} | grep -v pass | grep -v skipping
```

### 9. Fix CI failures

If checks fail:

1. **Commitlint/scope error**: Fix PR title with `gh pr edit {PR} --title "..."` then push empty commit to re-trigger
2. **Lint error**: Fix code, commit, push
3. **DeepSource**: Check if pre-existing false positive or real issue. Add ignore rule to `.deepsource.toml` if justified
4. **Test failure**: Fix test or implementation, commit, push

Push empty commit to re-trigger CI:

```bash
git commit --allow-empty --no-verify -m "chore(ci): trigger re-run" && git push
```

### 10. Verify and merge

When all checks pass (or only pre-existing false positives remain):

```bash
gh pr checks {PR} | grep -c "pass"  # Should match total non-skipped
gh pr merge {PR} --squash --auto     # Or --admin if no branch protection
```

Verify merge:

```bash
gh pr view {PR} --json state,mergedAt --jq '"Merged: \(.mergedAt)"'
```

### 11. Switch back to main

```bash
git checkout main && git pull
```

## Guard Rails

1. **Never merge with failing CI** — No exceptions, even "pre-existing" failures
2. **Never use `Any` type** — Always use proper Protocol/Callable types
3. **Always update skills snapshot** — When changing `scripts/`, update `.agents/skills/do-web-doc-resolver/scripts/`
4. **Commitlint scope enum** — `resolver, cli, web, ci, docs, deps, security, release, agents, test`
5. **PR body max 2000 chars** — Squash merge compatibility

## Issue → PR Mapping

| Issue Type | Commit Type | Example |
|------------|-------------|---------|
| New feature | `feat` | `feat(resolver): add FetchTier enum` |
| Bug fix | `fix` | `fix(security): harden BLOCKED_NETWORKS` |
| Performance | `perf` | `perf(resolver): add content-clean mode` |
| Refactor | `refactor` | `refactor(cascade): extract tier sorting` |
| Tests | `test` | `test(resolver): add protocol tests` |
| Docs | `docs` | `docs(agents): update SKILL.md contract` |
| CI/Config | `chore` | `chore(ci): fix DeepSource warnings` |

## References

| Topic | File |
|-------|------|
| Branching & commits | [AGENTS.md § Coding Workflow](../../../AGENTS.md#coding-workflow) |
| CI rules | [AGENTS.md § CI & Codacy Rules](../../../AGENTS.md#ci--codacy-rules-never-skip) |
| Release workflow | [AGENTS.md § Release Workflow](../../../AGENTS.md#release-workflow) |
| PR monitoring | [do-github-pr-sentinel](../do-github-pr-sentinel/SKILL.md) |
