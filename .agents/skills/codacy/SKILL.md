---
name: codacy
version: 1.0.0
description: Use Codacy static analysis CLIs to query PR analysis, triage issues, suppress false positives, and run local analysis. Use when Codacy blocks a PR, when asked to fix Codacy issues, suppress false positives, query PR quality data, or integrate Codacy into CI/CD workflows. Also use when the user mentions "Codacy", "static analysis check", "code quality gate", or "Codacy is failing".
license: MIT
metadata:
  author: d-o-hub
  version: 1.0.0
---

# Codacy Static Analysis

Orchestrate static analysis using Codacy Analysis CLI (local) and Codacy Cloud CLI (remote).

## Installation & Auth

```bash
npm i -g @codacy/analysis-cli @codacy/codacy-cloud-cli
export CODACY_API_TOKEN=<your-api-token>
```

## PR Triage Workflow (NEVER SKIP ISSUES)

**CRITICAL RULE: Never skip, suppress, or ignore Codacy issues without following this protocol.**

1. **Get PR analysis**:
   `codacy pull-request gh <org> <repo> <prNumber> --output json > /tmp/codacy-pr.json`
2. **For EACH issue, perform web research**:
   - Search for the pattern ID against official documentation (ESLint, Biome, Semgrep, etc.)
   - Check the rule's purpose, severity, and whether it's enforced by coding standards
   - Determine if it's a genuine code quality concern or a false positive
   - Document findings with links to official docs
3. **Fix FIRST** (always preferred):
   - If the issue is genuine, fix the code
   - Commit, push, re-verify with `codacy pull-request --reanalyze-and-wait`
4. **Ignore ONLY as last resort** (verified false positive):
   - Only after web research confirms it's a false positive
   - Document WHY with links to official docs/best practices
   - Use `codacy pull-request gh <org> <repo> <prNumber> --ignore-issue <numeric-resultDataId> --ignore-reason FalsePositive`
   - Add inline comment explaining the rationale
5. **Verify**: Confirm the fix or ignore resolves the issue without regressions

## Local Analysis

```bash
codacy-analysis init --default
codacy-analysis analyze --pr --output-format json
```

## Known Limitations

| Tool Category | Status | Note |
|---------------|--------|------|
| JS/TS/Shell | ✅ Works | ESLint, Stylelint, ShellCheck |
| Python/Rust | ❌ Fails | Missing runtimes/venv issues or direct support in local CLI |
| Java/PMD | ❌ Fails | Missing Java runtime |

Always cross-reference with Cloud CLI for full PR data.

## Rationalizations

| Rationalization | Reality |
|-----------------|---------|
| "Local analysis shows 0 issues, so we are good." | Analysis CLI has limited local tool support; Cloud CLI is the source of truth. |
| "I'll use the issue hash for suppression." | Codacy CLI requires the numeric `resultDataId` for suppressions. |

## Red Flags

- [ ] Relying solely on local `codacy-analysis` for Python/Rust projects.
- [ ] Attempting to suppress issues without a valid `--ignore-reason`.
- [ ] Ignoring the `resultDataId` field in JSON output in favor of hashes.
- [ ] **NEVER** skip Codacy issues without web research against official docs.
- [ ] **NEVER** assume an issue is false positive without verification.
- [ ] **NEVER** ignore issues as a first response - always fix first.

## References

- `references/output-format.md` - JSON schema for PR analysis
- `references/supported-tools.md` - Local vs Cloud tool availability
- `references/config-format.md` - Codacy configuration file schema (.codacy.yml)
