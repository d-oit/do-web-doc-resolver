"""Tests for the optional Scrim local-rendering provider (no network, no binary)."""

import subprocess
import sys

import pytest

from scripts.models import ResolvedResult
from scripts.providers import scrim as scrim_mod
from scripts.providers.scrim import (
    ScrimNotInstalled,
    resolve_with_scrim,
    resolve_with_scrim_async,
    scrim_enabled,
    scrim_version,
)


@pytest.fixture(autouse=True)
def reset_caches():
    scrim_mod._scrim_binary.cache_clear()
    scrim_mod.scrim_version.cache_clear()
    yield
    scrim_mod._scrim_binary.cache_clear()
    scrim_mod.scrim_version.cache_clear()


class TestFlag:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("DO_WDR_SCRIM_ENABLED", raising=False)
        assert scrim_enabled() is False

    def test_opt_in(self, monkeypatch):
        monkeypatch.setenv("DO_WDR_SCRIM_ENABLED", "1")
        assert scrim_enabled() is True

    def test_disabled_provider_returns_none_even_with_binary(self, monkeypatch):
        monkeypatch.delenv("DO_WDR_SCRIM_ENABLED", raising=False)
        monkeypatch.setenv("SCRIM_BIN", "/usr/bin/true")
        assert resolve_with_scrim("https://example.com") is None


class TestDetection:
    def test_not_installed_returns_none_and_logs_skip(self, monkeypatch):
        monkeypatch.setenv("DO_WDR_SCRIM_ENABLED", "1")
        monkeypatch.delenv("SCRIM_BIN", raising=False)
        monkeypatch.setattr(scrim_mod.shutil, "which", lambda name: None)
        assert resolve_with_scrim("https://example.com") is None

    def test_scrim_bin_env_takes_precedence(self, monkeypatch, tmp_path):
        binary = tmp_path / "scrim"
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)
        monkeypatch.setenv("DO_WDR_SCRIM_ENABLED", "1")
        monkeypatch.setenv("SCRIM_BIN", str(binary))
        assert scrim_mod._scrim_binary() == str(binary)

    def test_version_probe_runs_argv_array(self, monkeypatch):
        monkeypatch.setenv("SCRIM_BIN", sys.executable)
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="scrim 0.1.1\n", stderr=b"")

        monkeypatch.setattr(scrim_mod.subprocess, "run", fake_run)
        assert scrim_version() == "scrim 0.1.1"
        assert calls == [[sys.executable, "--version"]]


class TestResolve:
    @pytest.fixture
    def enabled(self, monkeypatch):
        monkeypatch.setenv("DO_WDR_SCRIM_ENABLED", "1")
        monkeypatch.setenv("SCRIM_BIN", sys.executable)

    def _patch_run(self, monkeypatch, stdout=b"# Page\n" + b"x" * 500, returncode=0):
        calls = {}

        def fake_run(argv, **kwargs):
            calls.setdefault("argvs", []).append(argv)
            calls["kwargs"] = kwargs
            if argv[-1] == "--version":
                return subprocess.CompletedProcess(argv, 0, stdout="scrim 0.1.1\n", stderr=b"")
            return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=b"")

        monkeypatch.setattr(scrim_mod.subprocess, "run", fake_run)
        return calls

    def test_success_normalizes_to_resolved_result(self, enabled, monkeypatch):
        calls = self._patch_run(monkeypatch)
        result = resolve_with_scrim("https://example.com/docs", max_chars=10000)
        assert isinstance(result, ResolvedResult)
        assert result.source == "scrim"
        assert result.url == "https://example.com/docs"
        assert len(result.content) > 100
        assert result.metadata["renderer"] == "scrim-local"
        assert result.metadata["scrim_version"] == "scrim 0.1.1"
        assert calls["argvs"][0] == [
            sys.executable,
            "fetch",
            "https://example.com/docs",
            "--dump",
            "markdown",
        ]
        assert "shell" not in calls["kwargs"]

    def test_private_url_is_ssrf_blocked(self, enabled, monkeypatch):
        ran = []

        def fake_run(argv, **kwargs):
            ran.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout=b"x" * 500, stderr=b"")

        monkeypatch.setattr(scrim_mod.subprocess, "run", fake_run)
        for url in (
            "http://127.0.0.1:8080/",
            "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.1/",
        ):
            assert resolve_with_scrim(url) is None
        assert ran == []

    def test_short_content_returns_none(self, enabled, monkeypatch):
        self._patch_run(monkeypatch, stdout=b"tiny")
        assert resolve_with_scrim("https://example.com") is None

    def test_nonzero_exit_returns_none(self, enabled, monkeypatch):
        self._patch_run(monkeypatch, returncode=1, stdout=b"")
        assert resolve_with_scrim("https://example.com") is None

    def test_timeout_returns_none(self, enabled, monkeypatch):
        def fake_run(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 30)

        monkeypatch.setattr(scrim_mod.subprocess, "run", fake_run)
        assert resolve_with_scrim("https://example.com") is None

    def test_oversized_output_returns_none(self, enabled, monkeypatch):
        monkeypatch.setenv("SCRIM_MAX_OUTPUT_BYTES", "10")
        self._patch_run(monkeypatch, stdout=b"x" * 100)
        assert resolve_with_scrim("https://example.com") is None

    def test_async_wrapper_runs_in_executor(self, enabled, monkeypatch):
        self._patch_run(monkeypatch)
        import asyncio

        result = asyncio.run(resolve_with_scrim_async("https://example.com"))
        assert isinstance(result, ResolvedResult)


class TestScrimNotInstalled:
    def test_exception_is_internal_marker(self):
        assert issubclass(ScrimNotInstalled, RuntimeError)
