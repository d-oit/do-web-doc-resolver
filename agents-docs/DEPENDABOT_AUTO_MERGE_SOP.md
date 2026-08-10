# Dependabot Auto-Merge: End-to-End Verification SOP

Dependabot groups pip, cargo /cli, npm /web, and github-actions at 06:00 Europe/Berlin every Monday. The fix chain (#564 prefix, #565 dead-entry removal, #566 auto-merge arming + BEHIND sweep) must produce, without human edit, patch/minor PRs that auto-merge with `build(deps):`/single-scope titles and all-green required checks.

Run from repo root, at or after the Monday 06:00 batch.

1. **List dependabot PRs** — expect several; titles match `^build\(deps\):` (single scope) or `^ci\(deps\):` (github-actions). If a title still shows `build(deps)(deps):`, Step 1 of #564 was ineffective: dependabot reads prefix at PR-open time, so reopen a ticket to flip `include: "scope"` → `include: "prefix"` in `.github/dependabot.yml`; never hand-edit the PR.

   ```bash
   gh pr list --repo d-oit/do-web-doc-resolver --author app/dependabot --state open --json number,title
   ```

2. **Wait for title lint + normalize** — `Lint PR title (squash-merge subject)` must show `pass`; confirm the Normalize step ran.

   ```bash
   gh pr checks <N> --repo d-oit/do-web-doc-resolver
   gh run view <commitlint-run-id> --repo d-oit/do-web-doc-resolver --log | grep -i "Normalize dependabot PR metadata"
   ```

3. **Auto-merge arm must exist** → `true`, `squash`. If `false`: check `.github/workflows/dependabot-auto-merge.yml` job log, specifically `Fetch Dependabot metadata` output `update-type`.

   ```bash
   gh api repos/d-oit/do-web-doc-resolver/pulls/<N> --jq '.auto_merge.enabled, .auto_merge.merge_method'
   ```

4. **Wait for required checks** — all of `Lint`, `Sample Run`, `Quality Gate`, `E2E Tests (web)`, `commitlint`, `Lint PR title` → `pass`. If any non-dependabot failure (e.g. flake), re-run that check only. **DO NOT** squash-merge manually — let auto-merge take it.

   ```bash
   gh pr checks <N> --repo d-oit/do-web-doc-resolver
   ```

5. **Staleness** — must not be permanently `dirty`; the autoupdate sweep (`dependabot-branch-autoupdate.yml`, every 30 min) flips it to `behind`/`clean`, then merges. If `dirty` >2 h: refresh once with `gh pr update-branch <N> --repo d-oit/do-web-doc-resolver` and check the sweep's workflow log.

   ```bash
   gh api repos/d-oit/do-web-doc-resolver/pulls/<N> --jq '.mergeable_state'
   ```

6. **Merge completes** → `MERGED` without any hand-run of `gh pr merge`. Verify the commit message: subject `build(deps): bump the … group …` ≤150 chars, no doubled scope, standard 2-line normalized body.

   ```bash
   gh pr view <N> --repo d-oit/do-web-doc-resolver --json state,mergedAt --jq .state
   git fetch origin main && git show -s --format=%B origin/main | head -4
   ```

7. **Main stays green** → `success` and `[]` respectively.

   ```bash
   gh api repos/d-oit/do-web-doc-resolver/commits/main/status --jq '.state'
   gh api repos/d-oit/do-web-doc-resolver/commits/main/check-runs --jq '[.check_runs[] | select(.conclusion=="failure") | .name]'
   ```

**Escalation table**

| Symptom | Guard to check | File/symbol | Owner action |
|---|---|---|---|
| `build(deps)(deps):` title persists | dependabot.yml prefix read by dependabot | `.github/dependabot.yml` lines per group | Reopen ticket to flip `include: "scope"` → `include: "prefix"`; never edit the PR |
| `Normalize dependabot PR metadata` job not run | automated actor match `github.actor == 'dependabot[bot]'` | `.github/workflows/commitlint.yml` `if:` | Check run `actor` via `gh run view --json jobs --jq '.[] | .[] | .actor'`; fix actor if different |
| Auto-merge not armed | `fetch-metadata` `update-type` or `pass` filter | `.github/workflows/dependabot-auto-merge.yml` | If `update-type` is `semver-major`, that's intentional human-review routing — not a bug — do NOT auto-merge |
| PR `dirty` >2 h | autoupdate sweep cron `*/30` | `.github/workflows/dependabot-branch-autoupdate.yml` | Run `gh pr update-branch <N>` once; then check sweep run log for auth failure |
| Any of the 4 required gates red (not dependabot-caused) | flake or real break | the failing check | Fix at root cause; do NOT merge with red CI |
| Squash message doubled scope / >150 chars | Normalize step's `gh pr edit` | `.github/workflows/commitlint.yml` Normalize step | Re-run commitlint workflow; if still bad, debug the sed regex to match the actual title format |

**Out-of-scope**

Do NOT change `commitlint.config.cjs` (shared human gate). If dependabot needs a change, change the dependabot config or the Normalize step — never weaken the config.
