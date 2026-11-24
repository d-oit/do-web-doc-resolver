"""Regression guard for Firecrawl's v1 retirement across all shipped runtimes."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REST_CLIENTS = (
    "web/lib/resolvers/url.ts",
    "cli/src/providers/firecrawl.rs",
    "scripts/diagnose_providers.py",
    "scripts/monitor_providers.py",
)


def test_all_firecrawl_rest_clients_use_v2() -> None:
    for relative_path in REST_CLIENTS:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "https://api.firecrawl.dev/v2/scrape" in source, relative_path
        assert "https://api.firecrawl.dev/v1/scrape" not in source, relative_path


def test_python_sdk_dependency_is_v2_compatible() -> None:
    manifests = (
        ROOT / "pyproject.toml",
        ROOT / ".agents/skills/do-web-doc-resolver/pyproject.toml",
        ROOT / ".agents/skills/do-web-doc-resolver/requirements.txt",
    )
    for manifest in manifests:
        content = manifest.read_text(encoding="utf-8")
        assert "firecrawl-py>=4.57.0" in content, str(manifest)
