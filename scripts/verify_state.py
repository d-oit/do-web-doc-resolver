#!/usr/bin/env python3
"""Verify every persisted routing-memory and cache entry.

The semantic cache stores JSON payloads plus sqlite-vec embeddings; the routing
memory stores versioned provider statistics. Both are optional runtime state, so
this tool reports missing files instead of failing, but any malformed row or
unlinked vector is an entry-level failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.constants import CACHE_DIR  # noqa: E402
from scripts.routing_outcomes import (  # noqa: E402
    migrate_document,
    normalize_stats,
    outcome_counts,
)

DEFAULT_SEMANTIC = os.path.expanduser("~/.cache/do-web-doc-resolver/semantic/semantic_cache.db")
DEFAULT_ROUTING = os.path.join(CACHE_DIR, "routing_memory.json")
DEFAULT_DISK = CACHE_DIR
QUERY_KEY_RE = re.compile(r"^q:v\d+:[a-z_]+:[a-z0-9.+#-]+:[a-z+#]+:[a-z0-9-]+$", re.IGNORECASE)
HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$", re.IGNORECASE)


def _load_sqlite_vec(connection: sqlite3.Connection) -> str | None:
    try:
        import sqlite_vec

        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
        connection.enable_load_extension(False)
        return None
    except Exception as error:  # noqa: BLE001 - report the import/load failure
        return f"sqlite-vec unavailable: {error}"


def verify_semantic_cache(path: str | os.PathLike[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": Path(path).exists(),
        "entries": 0,
        "vectors": 0,
        "invalid": [],
        "warnings": [],
        "integrity": None,
    }
    if not result["exists"]:
        return result
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        load_error = _load_sqlite_vec(connection)
        if load_error:
            result["invalid"].append(load_error)
            return result
        result["integrity"] = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result["integrity"] != "ok":
            result["invalid"].append(f"integrity_check: {result['integrity']}")

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        if "cache_entries" not in tables:
            result["invalid"].append("cache_entries table missing")
            return result

        ids: set[int] = set()
        for row in connection.execute("SELECT * FROM cache_entries"):
            result["entries"] += 1
            entry_id = row["id"]
            ids.add(entry_id)
            if not isinstance(row["query"], str) or not row["query"].strip():
                result["invalid"].append(f"entry {entry_id}: empty query")
            if float(row["timestamp"] or 0) <= 0:
                result["invalid"].append(f"entry {entry_id}: invalid timestamp")
            if int(row["access_count"] or 0) < 0:
                result["invalid"].append(f"entry {entry_id}: negative access_count")
            try:
                payload = json.loads(row["result_json"])
            except (TypeError, ValueError) as error:
                result["invalid"].append(f"entry {entry_id}: result_json {error}")
                continue
            if not isinstance(payload, dict):
                result["invalid"].append(f"entry {entry_id}: result is not an object")
                continue
            if not str(payload.get("content") or "").strip():
                result["invalid"].append(f"entry {entry_id}: empty content")
            if payload.get("source") == "none":
                result["invalid"].append(f"entry {entry_id}: source=none cached")

        if "vec_cache" not in tables:
            result["invalid"].append("vec_cache table missing")
            return result
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'vec_cache'"
        ).fetchone()[0]
        dimension_match = re.search(r"float\[(\d+)\]", table_sql or "")
        dimension = int(dimension_match.group(1)) if dimension_match else None
        columns = {row[1] for row in connection.execute("PRAGMA table_info(vec_cache)")}
        has_entry_id = "entry_id" in columns
        select = "SELECT rowid, length(embedding)"
        select += ", entry_id" if has_entry_id else ", NULL AS entry_id"
        select += " FROM vec_cache"
        vector_ids: set[int] = set()
        null_entry_ids = 0
        for row in connection.execute(select):
            result["vectors"] += 1
            rowid, byte_length, entry_id = row[0], row[1], row[2]
            vector_ids.add(rowid)
            if rowid not in ids:
                result["invalid"].append(f"vector {rowid}: no cache_entries row")
            if entry_id is None:
                null_entry_ids += 1
            elif entry_id != rowid:
                result["invalid"].append(f"vector {rowid}: entry_id {entry_id} mismatch")
            if dimension and byte_length != dimension * 4:
                result["invalid"].append(
                    f"vector {rowid}: {byte_length} bytes, expected {dimension * 4}"
                )
        missing = ids - vector_ids
        for entry_id in sorted(missing):
            result["invalid"].append(f"entry {entry_id}: missing vector")
        if null_entry_ids:
            result["warnings"].append(
                f"{null_entry_ids} vector row(s) use legacy rowid linkage (entry_id NULL)"
            )
    finally:
        connection.close()
    return result


def verify_routing_memory(path: str | os.PathLike[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": Path(path).exists(),
        "entries": 0,
        "invalid": [],
        "warnings": [],
        "schema_version": None,
    }
    if not result["exists"]:
        return result
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        result["invalid"].append(f"unreadable JSON: {error}")
        return result
    stats, version, supported = migrate_document(raw)
    result["schema_version"] = version
    if not supported:
        result["invalid"].append(f"unsupported schema version {version}")
        return result
    for key, providers in stats.items():
        if key == "query":
            result["warnings"].append("legacy 'query' bucket is migratable")
        elif key.startswith("q:v") and not QUERY_KEY_RE.match(key):
            result["invalid"].append(f"invalid query routing key: {key!r}")
        elif not key.startswith("q:v") and not HOST_RE.match(key) and key != "any":
            result["invalid"].append(f"invalid domain routing key: {key!r}")
        for provider, raw_stats in providers.items():
            result["entries"] += 1
            label = f"{key}/{provider}"
            if not provider:
                result["invalid"].append(f"{label}: empty provider")
            stats_entry = normalize_stats(raw_stats)
            success = int(stats_entry["success"])
            failure = int(stats_entry["failure"])
            counts = outcome_counts(stats_entry)
            if sum(counts.values()) < success + failure:
                result["invalid"].append(f"{label}: outcome counts below success+failure")
            if int(stats_entry["contributed"]) > success:
                result["invalid"].append(f"{label}: contributed > success")
            if not 0.0 <= float(stats_entry["avg_quality"]) <= 1.0:
                result["invalid"].append(f"{label}: avg_quality out of range")
            if float(stats_entry["avg_latency_ms"]) < 0:
                result["invalid"].append(f"{label}: negative avg_latency_ms")
    return result


def verify_disk_cache(path: str | os.PathLike[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": Path(path).exists(),
        "entries": 0,
        "invalid": [],
    }
    if not result["exists"]:
        return result
    try:
        import diskcache

        cache = diskcache.Cache(str(path))
        try:
            for key in cache.iterkeys():
                try:
                    cache.get(key)
                    result["entries"] += 1
                except Exception as error:  # noqa: BLE001 - entry-level failure
                    result["invalid"].append(f"{key!r}: {error}")
        finally:
            cache.close()
    except Exception as error:  # noqa: BLE001 - optional cache backend
        result["invalid"].append(f"diskcache unavailable: {error}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-cache", default=DEFAULT_SEMANTIC)
    parser.add_argument("--routing-memory", default=DEFAULT_ROUTING)
    parser.add_argument("--disk-cache", default=DEFAULT_DISK)
    parser.add_argument("--skip-disk-cache", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    sections: dict[str, dict[str, Any]] = {
        "semantic_cache": verify_semantic_cache(args.semantic_cache),
        "routing_memory": verify_routing_memory(args.routing_memory),
        "disk_cache": (
            {"skipped": True} if args.skip_disk_cache else verify_disk_cache(args.disk_cache)
        ),
    }
    invalid = sum(len(section.get("invalid", [])) for section in sections.values())
    report: dict[str, Any] = {**sections, "ok": invalid == 0}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for name, section in sections.items():
            print(
                f"{name}: entries={section.get('entries', 0)} "
                f"invalid={len(section.get('invalid', []))} "
                f"exists={section.get('exists', 'skipped')}"
            )
            for warning in section.get("warnings", []):
                print(f"  warn: {warning}")
            for error in section.get("invalid", []):
                print(f"  invalid: {error}")
    return 0 if invalid == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
