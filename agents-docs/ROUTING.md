# Context-Aware Routing and Outcomes

Routing memory has two key families:

| Key | Example | Ranking |
|---|---|---|
| URL/domain | `docs.rs` | Historical active ranking by success, quality, latency, recency |
| Search query | `q:v2:api_reference:rust:rust:none` | Evidence-gated blended ranking (shadow by default) |

URL keys stay flat for backward compatibility. Search queries are mapped to a
bounded, explainable tuple: `intent`, `topic`, `language`, and `platform`.
Raw query text is never a storage key.

## Key schema

`q:v<schema>:<intent>:<topic>:<language>:<platform>`

- Intents: `troubleshooting`, `release`, `package`, `api_reference`,
  `comparison`, `documentation`, `general`.
- Topics: bounded alias table (`rust`, `python`, `react`, `kubernetes`, …),
  otherwise `general`.
- Language: derived from the topic when it is a programming language, otherwise
  `na`.
- Platform: `github`, `gitlab`, `stackoverflow`, `docsrs`, `readthedocs`,
  `pypi`, `cratesio`, `npm`, or `none`.

Python owns `scripts/routing_context.py`; Rust mirrors it in
`cli/src/routing_context.rs`. Both test against
`tests/fixtures/routing_context_cases.json`.

## Outcome semantics

Each attempt records one outcome:

| Content outcomes | Transport outcomes | Other |
|---|---|---|
| `success`, `low_quality` | `blocked`, `rate_limited`, `timeout`, `auth_error`, `server_error`, `transport_error` | `no_result`, `unknown` |

Only content outcomes update the content success/failure counters and average
quality. A blocked or rate-limited provider is not learned as a bad content
source; availability is a separate ranking input. `success` increments
`contributed` only when the result actually fed the final answer.

## Conservative ranking

Query ranking blends four visible components:

```text
blended = evidence_gate * normalized_learned
        + (1 - evidence_gate) * static_prior
        - (1 - availability) * 0.5
```

- `evidence_gate` is 1 only after `MIN_EVIDENCE = 3` content attempts.
- `static_prior` is a small rank-derived prior (0.3 max), so cold start keeps
  the static order.
- `learned_component` normalizes only providers that pass the evidence gate.
- `availability` discounts transport failures without reclassifying content.

Below the evidence gate, one or two observations cannot promote or demote a
route. `RoutingMemory.explain()` exposes the breakdown, sample count,
confidence, outcome counts, and learned rank for both runtimes.

## Modes and rollout

`DO_WDR_ROUTING_MODE` controls query learning:

| Mode | Behavior |
|---|---|
| `shadow` (default) | Record and explain outcomes, keep the static provider order |
| `active` | Use the evidence-gated learned order |
| `off` | Record nothing in the ranking path and keep the static order |

Domain/URL routing remains active, matching the previous behavior. Enable
`active` only after the evaluation fixture shows no recall regression for your
corpus.

## Persistence migration

Python writes:

```json
{"version": 2, "kind": "routing_memory", "stats": {"<key>": {"<provider>": {}}}}
```

Legacy flat files (`{"<key>": {"<provider>": {...}}}`) migrate on load; their
`success`/`failure` counters are preserved as content evidence. A file with a
newer schema is loaded as empty and is never overwritten.

Rust stores the same `version`/`stats` shape inside `routing_state.json`. Legacy
`domain_stats` snapshots are accepted, migrated in `PersistedState::load`, and
newer schemas disable persistence rather than destroy data.

## Evaluation

```bash
python scripts/evaluate_routing.py
python scripts/evaluate_routing.py --json
```

Fixture: `tests/fixtures/routing_eval.json`. Current result:

| Metric | Static | Learned |
|---|---|---|
| Successful first provider | 0.40 | 1.00 |
| Unique first providers | 1 | 3 |
| Cold start preserves static order | yes | yes |
| One observation preserves static first | yes | yes |

The fixture separates blocked providers from low-quality content and is shared
by Python (`tests/test_routing_evaluation.py`) and Rust
(`cli/tests/routing.rs`). Treat the result as advisory evidence, not proof for
every query family.
