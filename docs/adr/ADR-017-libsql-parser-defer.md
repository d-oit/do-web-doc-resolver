# ADR-017: Defer libsql-sqlite3-parser dependency update

## Status

Accepted (deferred)

## Context

Dependabot reports one remaining open alert: GHSA-8m95-fffc-h4c5 (low severity,
"libsql-sqlite3-parser crash due to invalid UTF-8 input"). The vulnerable
component is `libsql-sqlite3-parser` `<= 0.13.0`, a transitive dependency of
the optional `semantic-cache` feature:

```text
cli/Cargo.toml
└── chaotic_semantic_memory 0.3.6 (optional, feature = "semantic-cache")
    └── libsql 0.9.30
        └── libsql-sqlite3-parser 0.13.0  (vulnerable range ≤ 0.13.0)
```

The advisory has **no `first_patched_version`** published. `cargo update` against
the current resolution confirms `libsql-sqlite3-parser 0.13.0` is pinned at the
latest release in the `libsql 0.9.x` line; the only fix exists in the unstable
pre-release `libsql 0.10.0-pre.4`, which would require adopting a pre-release
crate as the `semantic-cache` feature's transitive dependency.

## Decision

Defer the fix. Do not adopt `libsql 0.10.0-pre.4` at this time.

Rationale:

1. **Severity is low** — a parse crash on invalid UTF-8 input; `libsql-sqlite3-parser`
   is only exercised by the optional `semantic-cache` feature, not the default
   resolution path.
2. **No stable fix exists** — patching requires moving to a pre-release version
   (`0.10.0-pre.4`) of a transitive dependency of an optional feature, which
   risks runtime instability in exchange for a low-severity alert.
3. **Upstream-blocked** — the fix must land in a stable `libsql` release, then
   propagate through `chaotic_semantic_memory`. Neither has published a patch.

## Consequences

### Positive

- Keeps the `semantic-cache` feature on the stable `libsql 0.9.30` line.
- No risk of pre-release instability in an on-disk semantic cache backend.

### Negative

- Dependabot continues to show 1 open alert (low severity) until upstream
  publishes a stable `libsql` release containing the parser fix.

### Neutral

- Revisit when `libsql >= 0.10.0` (stable) or `chaotic_semantic_memory` bumps
  its `libsql` dependency. A plain `cargo update` should pick the fix up
  automatically once available.
