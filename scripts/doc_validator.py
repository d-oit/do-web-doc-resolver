#!/usr/bin/env python3
"""
Unified documentation validation logic: checkers and fixers.
"""

import json
import re
from pathlib import Path

from scripts.doc_models import (
    Report,
    extract_code_blocks,
    extract_markdown_links,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- Checkers ---


def check_file_references(report: Report, doc_name: str, content: str):
    """Verify that markdown links point to files that actually exist."""
    for line_no, _text, target in extract_markdown_links(content):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue

        # Clean anchor from path
        path_part = target.split("#")[0]
        if not path_part:
            continue

        target_path = REPO_ROOT / path_part
        if not target_path.exists():
            report.add(
                "warning", "broken-link", doc_name, f"Link target missing: {target}", line_no
            )


def check_shell_commands(report: Report, doc_name: str, content: str):
    """Verify scripts referenced in code blocks exist."""
    for line_no, lang, code in extract_code_blocks(content):
        if lang not in ("bash", "sh", "shell", "powershell"):
            continue

        # Look for script patterns
        for match in re.finditer(r"(?:python3? |./)(scripts/\w+\.(?:py|sh))", code):
            script_path = REPO_ROOT / match.group(1)
            if not script_path.exists():
                report.add(
                    "error",
                    "missing-script",
                    doc_name,
                    f"Referenced script missing: {match.group(1)}",
                    line_no,
                )

        for match in re.finditer(r"python3? -m (scripts\.\w+)", code):
            mod_path = REPO_ROOT / match.group(1).replace(".", "/")
            if not (mod_path.with_suffix(".py").exists() or (mod_path / "__init__.py").exists()):
                report.add(
                    "error",
                    "missing-module",
                    doc_name,
                    f"Referenced module missing: {match.group(1)}",
                    line_no,
                )


def check_python_cli(report: Report):
    """Verify scripts/cli.py help text appears in README.md."""
    cli_path = REPO_ROOT / "scripts/cli.py"
    if not cli_path.exists():
        return

    content = cli_path.read_text()
    readme = (REPO_ROOT / "README.md").read_text()
    for line_no, line in enumerate(content.splitlines(), 1):
        for match in re.finditer(r"help=['\"]([^'\"]+)['\"]", line):
            help_text = match.group(1)
            if help_text not in readme and len(help_text) > 10:
                report.add(
                    "warning",
                    "cli-help-doc-sync",
                    "scripts/cli.py",
                    f"Help text not documented in README: '{help_text}'",
                    line_no,
                )


def check_rust_cli_flags(report: Report):
    """Verify Rust CLI flags in src/cli.rs match references in RUST_CLI.md."""
    cli_rs = REPO_ROOT / "cli/src/cli.rs"
    rust_cli_md = REPO_ROOT / ".agents/skills/do-web-doc-resolver/references/RUST_CLI.md"

    if not (cli_rs.exists() and rust_cli_md.exists()):
        return

    rs_content = cli_rs.read_text()
    md_content = rust_cli_md.read_text()

    flags = set(re.findall(r'long = "([^"]+)"', rs_content))
    for flag in flags:
        if f"--{flag}" not in md_content:
            report.add(
                "warning", "cli-sync", "RUST_CLI.md", f"Rust flag --{flag} missing from docs"
            )


def check_cargo_features(report: Report):
    """Verify Cargo.toml features match RUST_CLI.md."""
    cargo_toml = REPO_ROOT / "cli/Cargo.toml"
    rust_cli_md = REPO_ROOT / ".agents/skills/do-web-doc-resolver/references/RUST_CLI.md"

    if not (cargo_toml.exists() and rust_cli_md.exists()):
        return

    toml_content = cargo_toml.read_text()
    md_content = rust_cli_md.read_text()

    if "[features]" in toml_content:
        features_section = toml_content.split("[features]")[1].split("[")[0]
        features = [
            f.split("=")[0].strip() for f in features_section.strip().splitlines() if "=" in f
        ]

        for feature in features:
            if feature not in md_content:
                report.add(
                    "warning",
                    "feature-sync",
                    "RUST_CLI.md",
                    f"Cargo feature '{feature}' missing from docs",
                )


def check_rust_architecture(report: Report):
    """Verify RUST_CLI.md architecture section against source tree."""
    rust_cli_md = REPO_ROOT / ".agents/skills/do-web-doc-resolver/references/RUST_CLI.md"
    if not rust_cli_md.exists():
        return

    content = rust_cli_md.read_text()
    for match in re.finditer(r"- `(\w+)`: (.+)", content):
        mod_name = match.group(1)
        if mod_name in ("providers", "resolver", "quality", "metrics", "synthesis"):
            mod_path = REPO_ROOT / "cli/src" / f"{mod_name}.rs"
            dir_path = REPO_ROOT / "cli/src" / mod_name
            if not (mod_path.exists() or dir_path.exists()):
                report.add(
                    "error", "arch-sync", "RUST_CLI.md", f"Source for module '{mod_name}' missing"
                )


def check_repo_tree(report: Report, doc_name: str, content: str):
    """Verify entries in ASCII tree diagrams exist in the filesystem."""
    for start_line, _lang, code in extract_code_blocks(content):
        if "├──" not in code and "└──" not in code:
            continue

        dir_stack: list[tuple[int, str]] = []

        for offset, tree_line in enumerate(code.splitlines()):
            line_no = start_line + offset

            indent_match = re.match(r"^([│ ]*)(?:├──|└──)", tree_line)
            if not indent_match:
                root_match = re.match(r"^(\S+/)$", tree_line.strip())
                if root_match:
                    root = root_match.group(1).rstrip("/")
                    dir_stack = [(-1, root)]
                continue

            indent = len(indent_match.group(1))
            entry_match = re.match(r"^[│ ]*(?:├──|└──)\s*(\S+)", tree_line)
            if not entry_match:
                continue

            entry = entry_match.group(1).rstrip("/")
            if entry in ("...", ""):
                continue

            while dir_stack and dir_stack[-1][0] >= indent:
                dir_stack.pop()

            parent = dir_stack[-1][1] if dir_stack else "."
            rel_path = f"{parent}/{entry}"
            if rel_path.startswith("./"):
                rel_path = rel_path[2:]

            full_path = REPO_ROOT / rel_path
            if not full_path.exists():
                report.add(
                    "warning",
                    "repo-tree",
                    doc_name,
                    f"Tree entry '{rel_path}' does not exist",
                    line_no,
                )

            is_dir = (
                entry_match.group(1).endswith("/")
                or full_path.is_dir()
                or entry.replace(".rs", "") in ("providers", "resolver")
            )
            if is_dir:
                dir_stack.append((indent, rel_path))


def check_npm_scripts(report: Report):
    """Verify package.json scripts match README.md instructions."""
    pkg_path = REPO_ROOT / "web/package.json"
    readme_path = REPO_ROOT / "README.md"

    if not (pkg_path.exists() and readme_path.exists()):
        return

    with open(pkg_path) as f:
        pkg = json.load(f)
        scripts = pkg.get("scripts", {})

    readme = readme_path.read_text()
    for match in re.finditer(r"pnpm run (\w+)", readme):
        cmd = match.group(1)
        if cmd not in scripts:
            report.add(
                "error",
                "npm-script",
                "README.md",
                f"Referenced npm script '{cmd}' missing from package.json",
            )


def check_runtime_versions(report: Report):
    """Verify README runtime/version claims match manifests and CI toolchains.

    Required documentation is never silently skipped: a missing README or a
    missing manifest is an error, not a skip.
    """
    readme_path = REPO_ROOT / "README.md"
    if not readme_path.exists():
        report.add("error", "runtime-versions", "README.md", "README.md is missing")
        return
    readme = readme_path.read_text()

    ci_path = REPO_ROOT / ".github/workflows/ci.yml"
    ci_env: dict[str, str] = {}
    if ci_path.exists():
        ci_text = ci_path.read_text()
        for var in ("PYTHON_VERSION", "RUST_TOOLCHAIN", "NODE_VERSION"):
            match = re.search(rf"{var}:\s*['\"]?([0-9.]+)", ci_text)
            if match:
                ci_env[var] = match.group(1)
    else:
        report.add(
            "error", "runtime-versions", ".github/workflows/ci.yml", "CI workflow is missing"
        )

    pkg_path = REPO_ROOT / "web/package.json"
    if pkg_path.exists():
        with open(pkg_path) as f:
            pkg = json.load(f)
        next_major = (
            re.sub(
                r"[^0-9]", "", str(pkg.get("dependencies", {}).get("next", ""))[:4].split(".")[0]
            )
            or "0"
        )
        next_version = str(pkg.get("dependencies", {}).get("next", ""))
        match = re.search(r"^[~^]?([0-9]+)", next_version)
        next_major = match.group(1) if match else "0"
        if f"Next.js-{next_major}" not in readme:
            report.add(
                "error",
                "runtime-versions",
                "README.md",
                f"README Next.js badge does not match web/package.json (next {next_version})",
            )
    else:
        report.add("error", "runtime-versions", "web/package.json", "package.json is missing")

    cargo_path = REPO_ROOT / "cli/Cargo.toml"
    if cargo_path.exists():
        cargo_text = cargo_path.read_text()
        match = re.search(r'rust-version\s*=\s*"(1\.[0-9]+)"', cargo_text)
        if match:
            rust_version = match.group(1)
            if f"Rust {rust_version}" not in readme:
                report.add(
                    "error",
                    "runtime-versions",
                    "README.md",
                    f"README Rust version claim does not match cli/Cargo.toml rust-version {rust_version}",
                )
            ci_rust = ci_env.get("RUST_TOOLCHAIN")
            if ci_rust and rust_version != ci_rust:
                report.add(
                    "error",
                    "runtime-versions",
                    "cli/Cargo.toml",
                    f"rust-version {rust_version} differs from CI RUST_TOOLCHAIN {ci_rust}",
                )
    else:
        report.add("error", "runtime-versions", "cli/Cargo.toml", "Cargo.toml is missing")

    ci_node = ci_env.get("NODE_VERSION")
    if ci_node and f"Node.js {ci_node}" not in readme:
        report.add(
            "error",
            "runtime-versions",
            "README.md",
            f"README Node.js version claim does not match CI NODE_VERSION {ci_node}",
        )

    pyproject_path = REPO_ROOT / "pyproject.toml"
    if pyproject_path.exists():
        py_text = pyproject_path.read_text()
        match = re.search(r'requires-python\s*=\s*">=([0-9.]+)"', py_text)
        if match:
            py_min = match.group(1)
            if f"Python {py_min}" not in readme:
                report.add(
                    "error",
                    "runtime-versions",
                    "README.md",
                    f"README Python version claim does not match pyproject requires-python >= {py_min}",
                )
            ci_python = ci_env.get("PYTHON_VERSION")
            if ci_python and version_tuple(ci_python) < version_tuple(py_min):
                report.add(
                    "error",
                    "runtime-versions",
                    ".github/workflows/ci.yml",
                    f"CI PYTHON_VERSION {ci_python} is below pyproject requires-python {py_min}",
                )
    else:
        report.add("error", "runtime-versions", "pyproject.toml", "pyproject.toml is missing")


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"[0-9]+", version))


# Cascade keys that are placeholders (no working provider behind them yet)
# and therefore carry no documentation requirement.
INTERNAL_ONLY_PROVIDERS = {"stealth"}

PROVIDER_CASCADE_FILES = [
    "scripts/_query_resolve.py",
    "scripts/_url_resolve.py",
]

# How each implementation cascade key may appear in README prose.
PROVIDER_README_ALIASES = {
    "exa_mcp": r"Exa MCP",
    "exa": r"Exa SDK|\bExa\b",
    "tavily": r"Tavily",
    "serper": r"Serper",
    "duckduckgo": r"DuckDuckGo",
    "mistral_websearch": r"Mistral WebSearch",
    "llms_txt": r"llms\.txt",
    "jina": r"Jina",
    "firecrawl": r"Firecrawl",
    "direct_fetch": r"direct HTTP fetch|direct_fetch",
    "mistral_browser": r"Mistral Browser",
    "visual_clip": r"CLIP|visual_clip",
}


def check_provider_inventory(report: Report):
    """Verify every shipped cascade provider is still described in README.

    The provider set is derived from the real cascade maps; a missing
    cascade definition file or an undocumented provider is an error.
    """
    known: set[str] = set()
    for rel in PROVIDER_CASCADE_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            report.add("error", "provider-inventory", rel, "cascade definition file is missing")
            continue
        for match in re.finditer(r'"([a-z_0-9]+)":\s*\(', path.read_text()):
            known.add(match.group(1))

    readme_path = REPO_ROOT / "README.md"
    if not readme_path.exists():
        report.add("error", "provider-inventory", "README.md", "README.md is missing")
        return
    readme = readme_path.read_text()

    for provider_key in sorted(known - INTERNAL_ONLY_PROVIDERS):
        alias = PROVIDER_README_ALIASES.get(provider_key, provider_key.replace("_", " "))
        if not re.search(alias, readme, re.IGNORECASE):
            report.add(
                "error",
                "provider-inventory",
                "README.md",
                f"Provider '{provider_key}' from the cascade is not documented in README",
            )


def check_cross_docs(report: Report):
    """Verify consistency across different documentation files."""
    readme_path = REPO_ROOT / "README.md"
    agents_path = REPO_ROOT / "AGENTS.md"

    if not (readme_path.exists() and agents_path.exists()):
        return

    readme = readme_path.read_text()
    seen: dict[tuple[str, str], int] = {}
    for line_no, text, target in extract_markdown_links(readme):
        key = (text, target)
        if key in seen:
            report.add(
                "warning",
                "duplicate-link",
                "README.md",
                f"Duplicate link: [{text}]({target}) (first at line {seen[key]})",
                line_no,
            )
        else:
            seen[key] = line_no


# --- Fixers ---


def fix_cargo_features(report: Report) -> int:
    """Auto-update RUST_CLI.md with missing Cargo features."""
    fixed = 0
    issues = [i for i in report.issues if i.category == "feature-sync"]
    if not issues:
        return 0

    cargo_toml = REPO_ROOT / "cli/Cargo.toml"
    rust_cli_md = REPO_ROOT / ".agents/skills/do-web-doc-resolver/references/RUST_CLI.md"

    toml_content = cargo_toml.read_text()
    features_section = toml_content.split("[features]")[1].split("[")[0]
    all_features = [
        f.split("=")[0].strip() for f in features_section.strip().splitlines() if "=" in f
    ]

    md_content = rust_cli_md.read_text()
    if "## Features" in md_content:
        lines = md_content.splitlines()
        feature_idx = -1
        for i, line in enumerate(lines):
            if "## Features" in line:
                feature_idx = i
                break

        if feature_idx != -1:
            for feature in all_features:
                if feature not in md_content:
                    lines.insert(feature_idx + 2, f"- `{feature}`: [Description needed]")
                    fixed += 1

            if fixed > 0:
                rust_cli_md.write_text("\n".join(lines))

    return fixed


def fix_duplicate_links(report: Report, doc: str = "README.md") -> int:
    """Remove duplicate markdown links from a doc, keeping the first occurrence.

    Only whole-line duplicate links are removed (a line whose trimmed content is
    exactly a single markdown link), so prose containing a link is never touched.
    """
    fixed = 0
    path = REPO_ROOT / doc
    if not path.exists():
        return fixed

    issues = [i for i in report.issues if i.category == "duplicate-link" and i.doc == doc]
    if not issues:
        return fixed

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    seen: set[tuple[str, str]] = set()
    # A line whose trimmed content is exactly one markdown link: [text](target)
    whole_line_link = re.compile(r"^\[([^\]]+)\]\(([^)]+)\)$")
    new_lines = []

    for line in lines:
        trimmed = line.strip()
        match = whole_line_link.match(trimmed)
        if match:
            key = (match.group(1), match.group(2))
            if key in seen:
                fixed += 1
                continue
            seen.add(key)
        new_lines.append(line)

    if fixed > 0:
        path.write_text("".join(new_lines), encoding="utf-8")
    return fixed


def fix_rust_architecture(report: Report) -> int:
    """Sync RUST_CLI.md architecture with actual file tree."""
    fixed = 0
    issues = [i for i in report.issues if i.category == "arch-sync"]
    if not issues:
        return 0

    return fixed
