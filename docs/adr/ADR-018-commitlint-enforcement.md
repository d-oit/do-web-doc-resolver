# ADR-018: Commitlint Enforcement for Authored and Generated Commits

## Status

Accepted

## Context

Commits and PR titles must follow Conventional Commits, enforced by
`.github/workflows/commitlint.yml` using `commitlint.config.cjs`: allowed
`type` and `scope` enums, header ≤ 150 chars, body/footer lines ≤ 100 chars,
and an `ignores` entry for Dependabot commits.

Three properties of that enforcement shaped the design:

1. **Bots bypass local hooks.** Dependabot, Jules and Copilot open PRs without
   running a `commit-msg` hook, so CI must validate the PR title — it becomes
   the squash-merge subject.
2. **Reruns replay stale event payloads.** A failed `lint-pr-title` run
   re-reads `github.event.pull_request.title` from the original trigger, so an
   edited title is checked against its old value and can never pass
   (PR #505, run 27086771117).
3. **Squash bodies are generated text.** GitHub builds the squash commit from
   the PR title and body. Once merged the body cannot be edited, so a
   line-length violation fails the push job with no possible fix (commit
   `3ff4a91`, from PR #682).

## Decision

1. Lint the PR title and body from the live API (`gh pr view`), never from the
   event payload, so reruns and late edits are judged on current values.
2. Normalize Dependabot PR metadata (collapse its doubled scope, replace its
   ~65 KB auto body) instead of exempting it in config; `commitlint.config.cjs`
   remains the strict human gate and is not weakened. See
   `agents-docs/DEPENDABOT_AUTO_MERGE_SOP.md`.
3. Use two configs. `commitlint.config.cjs` lints authored commits — the
   `commit-msg` hook, the pre-push hook, the PR job and `npm run lint:commits`.
   `commitlint.squash.cjs` is used only by the post-merge push job and disables
   exactly `body-max-line-length`, `footer-max-length` and
   `footer-max-line-length`.
4. Pin `wagoid/commitlint-github-action` to v6.2.1 by SHA and let the action
   infer the push/PR range; the v5 `from`/`to` inputs were removed in v6.
5. Treat the PR body as a hard 2000-char limit, with lines over 100 chars
   reported as a warning only.

## Consequences

### Positive

- Squash subjects and PR titles are validated for every author, including bots
  that skip local hooks.
- `main` stays lintable: post-merge runs cannot fail on text nobody can edit.
- Author-written commits keep full line-length enforcement locally (via
  `commit-msg` and pre-push hooks) and in CI.

### Negative

- Long-bodied squash commits land in history without a line-length check.
- The 100-char PR body rule is advisory, so readability depends on reviewer
  attention.

### Neutral

- The push job remains a backstop for PRs merged past failing checks; direct
  pushes to `main` are not line-length checked.
- Historical commits that predate these rules (for example out-of-enum scopes)
  are not re-linted, because each job lints only its own range.
