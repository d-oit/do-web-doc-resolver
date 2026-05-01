# Plan: Fix GitHub Actions CI Failures

## Goal
Fix all GitHub Actions CI warnings and failures including pre-existing issues.

## Issues Identified

### 1. CI UI Workflow - npm peer dependency conflict (FAILING)
- **Error**: `npm ci` fails due to `eslint@10` vs `eslint-plugin-react-hooks@5.2.0` peer conflict
- **Affected jobs**: web-lint, web-typecheck, web-test, web-build, web-e2e
- **Fix**: Change `npm ci` to `npm ci --legacy-peer-deps` in all web jobs
- **File**: `.github/workflows/ci-ui.yml`

### 2. Dependabot PR #289 - needs rebase (requested)

## Implementation Steps

1. Update `.github/workflows/ci-ui.yml`:
   - Replace all `npm ci` with `npm ci --legacy-peer-deps` for web directory jobs
   - Lines: 77, 96, 115, 134, 155

2. Commit and push changes

3. Verify CI passes on next run

## Success Criteria
- CI UI workflow passes on main branch
- All jobs complete successfully
- No pre-existing failures remain