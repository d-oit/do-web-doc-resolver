# Agent Prompt Template

```text
You are implementing GitHub Issue #{N}: "{Title}" for the do-web-doc-resolver project.

CONTEXT: The UI layer is in `/workspaces/do-web-doc-resolver/cli/ui/`. Components are CSS-only files with BEM classes prefixed `do-wdr-`.

REQUIREMENTS from the issue:
{issue_body}

EXISTING TOKENS (from design_tokens.css):
{relevant_tokens}

EXISTING COMPONENT CONVENTIONS (from button.css, badge.css):
- Component tokens in `:root {}` block
- BEM: `.do-wdr-{component}`, `.do-wdr-{component}--variant`, `.do-wdr-{component}__element`
- Focus-visible outlines, transitions on colors, prefers-reduced-motion

TASK: Create `/workspaces/do-web-doc-resolver/cli/ui/components/{name}.css`. Max 200 lines. No comments.

Also update `components/README.md` to replace the issue link with `{name}.css`.
```

## Customization

### For CSS Components

- Include token references from `tokens/design_tokens.css`
- Follow BEM naming: `.do-wdr-{component}__{element}--{variant}`
- Max 200 lines per file
- No comments in CSS

### For Python Scripts

- Include relevant imports from `scripts/`
- Follow existing code style
- Add type hints
- Include error handling

### For Rust Code

- Include relevant module imports
- Follow existing error handling patterns
- Use `thiserror` for library errors
- Use `anyhow` at binary boundary

## CRITICAL: Never Merge with Failing CI or Codacy

This is an ABSOLUTE RULE with no exceptions:

- **NEVER** use `gh pr merge --admin` when CI checks are failing
- **NEVER** use `gh pr merge --auto` when required checks are failing
- **NEVER** justify merging with "pre-existing on main" — fix main first
- **NEVER** merge when Codacy shows `ACTION_REQUIRED`
- **ALWAYS** verify ALL checks pass AND Codacy is up to standards before merging:

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

If ANY check fails or Codacy is ACTION_REQUIRED: fix it, close the PR, or escalate to the user. NEVER merge.
