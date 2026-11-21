"""Entry-level verification for persisted routing and cache state."""

from __future__ import annotations

import json
import sqlite3
import struct

import pytest

from scripts.verify_state import (
    verify_disk_cache,
    verify_routing_memory,
    verify_semantic_cache,
)

sqlite_vec = pytest.importorskip("sqlite_vec")


def _semantic_db(path):
    connection = sqlite3.connect(path)
    connection.enable_load_extension(True)
    sqlite_vec.load(connection)
    connection.enable_load_extension(False)
    connection.execute("""
        CREATE TABLE cache_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT UNIQUE NOT NULL,
            result_json TEXT NOT NULL,
            timestamp REAL NOT NULL,
            access_count INTEGER DEFAULT 1,
            last_accessed REAL NOT NULL
        )
        """)
    connection.execute(
        "CREATE VIRTUAL TABLE vec_cache USING vec0(embedding float[384], +entry_id INTEGER)"
    )
    return connection


def _insert(connection, query, payload, *, vector=True, entry_id=None):
    cursor = connection.execute(
        "INSERT INTO cache_entries (query, result_json, timestamp, last_accessed) "
        "VALUES (?, ?, 1.0, 1.0)",
        (query, json.dumps(payload)),
    )
    entry_id_value = cursor.lastrowid if entry_id is None else entry_id
    if vector:
        embedding = struct.pack("<384f", *([0.0] * 384))
        connection.execute(
            "INSERT INTO vec_cache (rowid, embedding, entry_id) VALUES (?, ?, ?)",
            (cursor.lastrowid, embedding, entry_id_value),
        )
    connection.commit()
    return cursor.lastrowid


def test_semantic_cache_valid_entries_pass(tmp_path):
    path = tmp_path / "semantic.db"
    connection = _semantic_db(path)
    _insert(connection, "python docs", {"source": "jina", "content": "Useful docs"})
    connection.close()
    report = verify_semantic_cache(path)
    assert report["invalid"] == []
    assert report["entries"] == 1
    assert report["vectors"] == 1


def test_semantic_cache_detects_bad_payload_and_missing_vector(tmp_path):
    path = tmp_path / "semantic.db"
    connection = _semantic_db(path)
    _insert(connection, "bad payload", {"source": "jina", "content": ""})
    _insert(connection, "no vector", {"source": "jina", "content": "ok"}, vector=False)
    connection.close()
    report = verify_semantic_cache(path)
    assert len(report["invalid"]) >= 2
    assert any("empty content" in error for error in report["invalid"])
    assert any("missing vector" in error for error in report["invalid"])


def test_semantic_cache_detects_orphan_vector(tmp_path):
    path = tmp_path / "semantic.db"
    connection = _semantic_db(path)
    embedding = struct.pack("<384f", *([0.0] * 384))
    connection.execute(
        "INSERT INTO vec_cache (rowid, embedding, entry_id) VALUES (99, ?, 99)",
        (embedding,),
    )
    connection.commit()
    connection.close()
    report = verify_semantic_cache(path)
    assert any("no cache_entries row" in error for error in report["invalid"])


def test_routing_memory_valid_and_invalid_keys(tmp_path):
    path = tmp_path / "routing.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "kind": "routing_memory",
                "stats": {
                    "docs.rs": {
                        "jina": {
                            "success": 3,
                            "failure": 0,
                            "outcomes": {"success": 3},
                            "avg_latency_ms": 100,
                            "avg_quality": 0.9,
                        }
                    },
                    "q:v2:documentation:python:python:none": {
                        "exa": {
                            "success": 3,
                            "failure": 0,
                            "outcomes": {"success": 3},
                            "avg_latency_ms": 100,
                            "avg_quality": 0.9,
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    report = verify_routing_memory(path)
    assert report["invalid"] == []
    assert report["entries"] == 2

    path.write_text(
        json.dumps({"version": 2, "stats": {"not a domain": {"bad": {"success": 1}}}}),
        encoding="utf-8",
    )
    report = verify_routing_memory(path)
    assert any("invalid domain" in error for error in report["invalid"])


def test_routing_memory_reports_legacy_query_bucket(tmp_path):
    path = tmp_path / "routing.json"
    path.write_text(json.dumps({"query": {"exa": {"success": 1, "failure": 0}}}), encoding="utf-8")
    report = verify_routing_memory(path)
    assert report["invalid"] == []
    assert any("legacy" in warning for warning in report["warnings"])


def test_disk_cache_entries_are_readable(tmp_path):
    diskcache = pytest.importorskip("diskcache")
    path = tmp_path / "cache.db"
    cache = diskcache.Cache(str(path))
    cache.set("key", {"value": 1})
    cache.close()
    report = verify_disk_cache(path)
    assert report["invalid"] == []
    assert report["entries"] == 1
