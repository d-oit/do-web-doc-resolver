# Wave Execution Strategy

## Dependency Analysis

Parse each issue body for "Blocked by" lines to build the dependency graph.

```bash
gh issue list --state open --json number,title,body,labels
```

## Wave Grouping

Group issues by dependency depth. Issues with no blockers go in Wave 1, issues depending only on Wave 1 go in Wave 2, etc.

| Wave | Description | Example |
|------|-------------|---------|
| 0 | Foundation, no blockers | Tokens, base styles |
| 1 | Depend only on Wave 0 | Basic components |
| 2 | Depend on Wave 0 + Wave 1 | Complex components |
| 3+ | Depend on multiple waves | Integration components |

## Parallel Agent Launch

For each issue in a wave, launch a specialist agent via the Task tool:

```text
Task(
  description="Implement #{N} {Title}",
  prompt="You are implementing GitHub Issue #{N}... [full issue body + context]",
  subagent_type="general"
)
```

Each agent receives:

- Full issue body from `gh issue view {N} --json body`
- List of existing tokens from `tokens/design_tokens.css`
- Convention examples from 1-2 existing components
- Exact file path to create

## Wave Completion Verification

After all agents in a wave complete, verify outputs:

```bash
ls -la cli/ui/components/*.css  # Verify new files exist
wc -l cli/ui/components/*.css   # Verify <200 lines each
```

## Tips

- Read existing components before writing to match conventions exactly
- Max 4 parallel agents to avoid context window pressure
- Each wave is independent — can push after each wave
- Always verify `wc -l < 200` before committing

## Merge Guard Rails (MANDATORY)

**NEVER merge with failing CI or Codacy — NO EXCEPTIONS.**

Before any merge, verify ALL checks pass AND Codacy is up to standards:

```bash
# Check CI
gh pr view {N} --json statusCheckRollup | python3 -c "
import json, sys
data = json.load(sys.stdin)
failed = [c for c in data.get('statusCheckRollup', []) if c.get('conclusion') == 'FAILURE']
if failed:
    print(f'BLOCKED: {len(failed)} failing checks:')
    for c in failed:
        print(f'  - {c.get(\"name\", \"unknown\")}')
    sys.exit(1)
print('All CI checks passing')
"

# Check Codacy
codacy pull-request gh <org> <repo> {N} --output json | python3 -c "
import json, sys
data = json.load(sys.stdin)
quality = data.get('pullRequest', {}).get('quality', {})
if not quality.get('isUpToStandards', True):
    print(f'BLOCKED: Codacy ACTION_REQUIRED')
    sys.exit(1)
print('Codacy up to standards')
"
```

- `gh pr merge --admin` is FORBIDDEN when CI or Codacy is failing
- "Pre-existing on main" is NOT a valid justification
- If CI or Codacy fails: fix it, close the PR, or escalate to user
- Use `codacy pull-request --ignore-issue <resultDataId> --ignore-reason FalsePositive` for false positives
