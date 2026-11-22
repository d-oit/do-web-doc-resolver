#!/usr/bin/env python3
"""Offline benchmark for alternative-source discovery.

Compares primary-only recall with discovery recall over the deterministic
fixture corpus and reports the simulated extraction cost. No network.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.discovery import DiscoveryInput, discover_alternatives  # noqa: E402

DEFAULT_FIXTURE = Path(__file__).parent.parent / "tests/fixtures/discovery_cases.json"


class _Validation:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.is_valid = bool(payload.get("is_valid"))
        self.final_url = payload.get("final_url")
        self.redirect_chain = payload.get("redirect_chain", [])


def run(path: Path) -> dict[str, Any]:
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    primary_recall = 0
    discovery_recall = 0
    qualities: list[float] = []
    latencies_ms: list[float] = []
    extraction_attempts = 0
    for case in cases:
        validator_map = case["validator"]

        def validate(url: str, mapping: dict = validator_map) -> _Validation:
            return _Validation(mapping.get(url, {"is_valid": False}))

        if validator_map.get(case["primary_url"], {}).get("is_valid"):
            primary_recall += 1
        started = time.perf_counter()
        report = discover_alternatives(
            DiscoveryInput(
                primary_url=case["primary_url"],
                final_url=case["final_url"],
                html=case["html"],
                llms_txt=case["llms_txt"],
                search_results=case["search_results"],
                query=case["query"],
            ),
            validator=validate,
        )
        latencies_ms.append((time.perf_counter() - started) * 1000)
        if report.selected is not None:
            discovery_recall += 1
            qualities.append(report.selected.scores.get("overall", 0.0))
        extraction_attempts += min(
            2, sum(1 for c in report.candidates if c.verification_state == "verified")
        )

    latencies_ms.sort()
    p95_index = max(0, int(len(latencies_ms) * 0.95) - 1)
    return {
        "cases": len(cases),
        "primary_recall": primary_recall / len(cases) if cases else 0.0,
        "discovery_recall": discovery_recall / len(cases) if cases else 0.0,
        "mean_selected_quality": statistics.fmean(qualities) if qualities else 0.0,
        "median_generation_ms": statistics.median(latencies_ms) if latencies_ms else 0.0,
        "p95_generation_ms": latencies_ms[p95_index] if latencies_ms else 0.0,
        "bounded_extraction_attempts": extraction_attempts,
        "max_extractions_per_case": 2,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run(args.fixture)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"cases={report['cases']} "
            f"primary_recall={report['primary_recall']:.2f} "
            f"discovery_recall={report['discovery_recall']:.2f} "
            f"quality={report['mean_selected_quality']:.2f} "
            f"median={report['median_generation_ms']:.2f}ms "
            f"p95={report['p95_generation_ms']:.2f}ms "
            f"extractions<= {report['max_extractions_per_case']}/case"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
