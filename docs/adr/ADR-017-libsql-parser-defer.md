# ADR-017: Defer libsql-sqlite3-parser dependency update

## Status

Accepted (deferred)

## Context

Dependabot reports one remaining open alert, GHSA-8m95-fffc-h4c5 (low severity):
"libsql-sqlite3-parser crash due to invalid UTF-8 input." The affected parser
version is `<= 0.13.0`, reached through:

```text
cli/Cargo.toml
└── chaotic_semantic_memory 0.3.6 (optional; feature enabled by default)
    └── libsql 0.9.30
        └── libsql-sqlite3-parser 0.13.0  (affected)
```

The advisory has no patched version for the `libsql-sqlite3-parser` fork, and
crates.io still lists `0.13.0` as its latest release. Stable `libsql 0.10.0`
does not clear the alert: its published manifest still requires
`libsql-sqlite3-parser ^0.13`. The latest `chaotic_semantic_memory 0.3.8`
continues to require `libsql ^0.9.30`.

The UTF-8 fix shipped in upstream `sqlite3-parser 0.15.0` from
`gwenn/lemon-rs` ([issue #86](https://github.com/gwenn/lemon-rs/issues/86)).
libsql vendors a separate parser fork. Its current source still contains
unchecked UTF-8 conversions; replacing it with upstream or pinning a Git patch
would change the parser dependency and dialect behavior without a published,
reviewed libsql release.

## Decision

Defer this low-severity alert until the libsql fork publishes the fix. Do not
replace the fork or add an unreviewed Git/vendor patch.

Rationale:

1. **Impact is limited** — the advisory describes a local crash when invalid
   UTF-8 reaches the parser; it does not report confidentiality or integrity
   impact.
2. **No fixed fork release exists** — stable `libsql 0.10.0` still depends on
   `libsql-sqlite3-parser ^0.13`, and the latest `chaotic_semantic_memory`
   remains on the `libsql 0.9.x` line.
3. **A local replacement is risky** — libsql's parser is a fork with dialect
   changes; substituting upstream or pinning an unpublished revision would
   bypass the stable dependency contract.

## Consequences

### Positive

- Keeps `semantic-cache` on stable `libsql 0.9.30` without a custom parser patch.
- Avoids replacing libsql's dialect-specific parser with upstream `sqlite3-parser`.

### Negative

- Dependabot continues to show one open alert until a fixed parser release is
  consumed by a stable `libsql` and `chaotic_semantic_memory` dependency chain.

### Neutral

- Revisit when a fixed `libsql-sqlite3-parser` version above `0.13.0` is
  published and available through stable `libsql`. A `cargo update` should
  then pick it up.
