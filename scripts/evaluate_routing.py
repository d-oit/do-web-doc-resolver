#!/usr/bin/env python3
"""Deterministic evaluation of context-aware routing against the static order.

The fixture contains unrelated query families and structured provider outcomes.
This script is advisory: it prints the comparison and exits non-zero only when
the learned route contradicts the fixture contract. It uses no network.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.routing_memory import RoutingMemory  # noqa: E402

DEFAULT_FIXTURE = Path(__file__).parent.parent / "tests/fixtures/routing_eval.json"


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        payload: dict[str, Any] = json.load(fh)
    return payload


def _attempt_summary(attempts: list[list[Any]]) -> dict[str, Any]:
    outcomes = [row[0] for row in attempts]
    successes = [row for row in attempts if row[0] == "success"]
    return {
        "attempts": len(attempts),
        "successes": len(successes),
        "blocked": outcomes.count("blocked"),
        "rate_limited": outcomes.count("rate_limited"),
        "timeouts": outcomes.count("timeout"),
        "low_quality": outcomes.count("low_quality"),
        "mean_success_latency_ms": (
            sum(row[2] for row in successes) / len(successes) if successes else None
        ),
    }


def evaluate(fixture: dict[str, Any]) -> dict[str, Any]:
    providers: list[str] = fixture["providers"]
    cases = fixture["cases"]
    rows: list[dict[str, Any]] = []
    static_successes = 0
    learned_successes = 0
    static_first: list[str] = []
    learned_first: list[str] = []

    for case in cases:
        memory = RoutingMemory(mode="active")
        for provider, attempts in case["attempts"].items():
            for outcome, quality, latency in attempts:
                memory.record_outcome(
                    case["routing_key"], provider, outcome, int(latency), float(quality)
                )
        learned = memory.rank_providers(case["routing_key"], providers, mode="active")
        static = list(providers)
        static_first.append(static[0])
        learned_first.append(learned[0])
        static_ok = any(row[0] == "success" for row in case["attempts"].get(static[0], []))
        learned_ok = any(row[0] == "success" for row in case["attempts"].get(learned[0], []))
        static_successes += int(static_ok)
        learned_successes += int(learned_ok)
        assert (
            learned[0] == case["expected_learned_first"]
        ), f"{case['name']}: learned {learned[0]} != {case['expected_learned_first']}"
        rows.append(
            {
                "case": case["name"],
                "routing_key": case["routing_key"],
                "static_first": static[0],
                "learned_first": learned[0],
                "static_success": static_ok,
                "learned_success": learned_ok,
                "learned_order": learned,
                "provider_attempts": {
                    provider: _attempt_summary(attempts)
                    for provider, attempts in case["attempts"].items()
                },
            }
        )

    return {
        "cases": len(cases),
        "static_success_rate": static_successes / len(cases) if cases else 0.0,
        "learned_success_rate": learned_successes / len(cases) if cases else 0.0,
        "static_unique_first_providers": len(set(static_first)),
        "learned_unique_first_providers": len(set(learned_first)),
        "rows": rows,
    }


def cold_start_and_low_sample(fixture: dict[str, Any]) -> dict[str, Any]:
    providers = fixture["providers"]
    case = fixture["cases"][0]
    cold = RoutingMemory(mode="active")
    cold_order = cold.rank_providers(case["routing_key"], providers, mode="active")
    one = RoutingMemory(mode="active")
    one.record_outcome(case["routing_key"], providers[-1], "success", 100, 0.99)
    one_order = one.rank_providers(case["routing_key"], providers, mode="active")
    return {
        "cold_start_preserves_static_order": cold_order == list(providers),
        "one_observation_preserves_static_first": one_order[0] == list(providers)[0],
        "cold_order": cold_order,
        "one_observation_order": one_order,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    fixture = _load(args.fixture)
    report = evaluate(fixture)
    report.update(cold_start_and_low_sample(fixture))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"static_success_rate={report['static_success_rate']:.2f} "
            f"learned_success_rate={report['learned_success_rate']:.2f} "
            f"cases={report['cases']}"
        )
        for row in report["rows"]:
            print(
                f"{row['case']}: {row['static_first']} -> {row['learned_first']} "
                f"(success {row['static_success']} -> {row['learned_success']})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
