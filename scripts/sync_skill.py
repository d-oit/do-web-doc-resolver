#!/usr/bin/env python3
"""
Sync skill copies from main scripts/ to .agents/skills/do-web-doc-resolver/scripts/.

After ADR-014 refactoring, the main scripts/ were updated with:
- scripts/constants.py (centralized config)
- scripts/state.py (shared singletons)
- scripts/_query_resolve.py and scripts/_url_resolve.py (extracted submodules)
- New providers: docling, ocr, serper
- Updated type hints

This script propagates those changes to the skill copy so it stays in sync.
"""

import difflib
import filecmp
import shutil
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
MAIN_SCRIPTS = PROJECT_ROOT / "scripts"
SKILL_SCRIPTS = PROJECT_ROOT / ".agents/skills/do-web-doc-resolver/scripts"

# Files to sync (exclude __pycache__, __init__.py is special).
# `utils` is a package (scripts/utils/), so it is synced file-by-file below.
SYNC_FILES = [
    "cache_negative.py",
    "circuit_breaker.py",
    "constants.py",
    "models.py",
    "providers_impl.py",
    "quality.py",
    "resolve.py",
    "routing.py",
    "routing_memory.py",
    "state.py",
    "synthesis.py",
]

# Files inside the scripts/utils/ package mirror (kept in lock-step with the
# canonical package). Added after the flattening refactor (ADR-014), which
# turned the former utils.py module into a package.
UTILS_FILES = [
    "async_http.py",
    "cache.py",
    "content_clean.py",
    "fetch.py",
    "html.py",
    "http.py",
    "thread_pool.py",
    "urls.py",
]


def get_diff(file1: Path, file2: Path | None) -> str:
    """Get unified diff between two files."""
    with open(file1) as f1:
        lines1 = f1.readlines()
    if file2 and file2.exists():
        with open(file2) as f2:
            lines2 = f2.readlines()
    else:
        lines2 = []
    diff = difflib.unified_diff(
        lines2,
        lines1,
        fromfile=str(file2) if file2 else "/dev/null",
        tofile=str(file1),
        lineterm="",
    )
    return "\n".join(diff)


def sync_file(filename: str, dry_run: bool = False, subdir: str | None = None) -> bool:
    """Sync a single file. Returns True if file was synced."""
    src = (MAIN_SCRIPTS / subdir / filename) if subdir else (MAIN_SCRIPTS / filename)
    dst = (SKILL_SCRIPTS / subdir / filename) if subdir else (SKILL_SCRIPTS / filename)

    if not src.exists():
        print(f"  SKIP {filename} (source not found)")
        return False

    if dst.exists() and filecmp.cmp(src, dst):
        print(f"  OK   {filename} (already in sync)")
        return False

    if dry_run:
        if not dst.exists():
            print(f"  WOULD CREATE {filename}")
        else:
            print(f"  WOULD SYNC {filename}")
        diff = get_diff(src, dst if dst.exists() else None)
        if diff:
            print(diff[:500])
        return True

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  SYNC {filename}")
    return True


def sync_utils_package(dry_run: bool = False) -> int:
    """Sync scripts/utils/ package files and drop the obsolete flat utils.py."""
    synced = 0
    # ADR-014 turned utils.py into a package; the legacy flat file must not linger.
    legacy = SKILL_SCRIPTS / "utils.py"
    if legacy.exists():
        if dry_run:
            print("  WOULD DELETE utils.py (replaced by utils/ package)")
            synced += 1
        else:
            legacy.unlink()
            print("  DELETE utils.py (replaced by utils/ package)")
            synced += 1

    for filename in UTILS_FILES:
        if sync_file(filename, dry_run, subdir="utils"):
            synced += 1

    # __init__.py re-exports symbols and defines helpers (e.g. _detect_error_type)
    # that skill code imports from the package root — empty stubs break imports.
    if sync_file("__init__.py", dry_run, subdir="utils"):
        synced += 1
    return synced


def sync_init(dry_run: bool = False) -> None:
    """Ensure __init__.py exists in skill scripts."""
    dst = SKILL_SCRIPTS / "__init__.py"
    if not dst.exists():
        if not dry_run:
            dst.touch()
        print("  CREATE __init__.py")


def main():
    dry_run = "--dry-run" in sys.argv

    print("=== Skill Sync: scripts/ → .agents/skills/do-web-doc-resolver/scripts/ ===")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    if not SKILL_SCRIPTS.exists():
        print(f"ERROR: Skill scripts directory not found: {SKILL_SCRIPTS}")
        sys.exit(1)

    synced = 0
    for filename in SYNC_FILES:
        if sync_file(filename, dry_run):
            synced += 1
    synced += sync_utils_package(dry_run)

    sync_init(dry_run)

    print()
    if dry_run:
        print(f"Would sync {synced} file(s)")
    else:
        print(f"Synced {synced} file(s)")

    # Verify
    if not dry_run:
        print()
        print("=== Verification ===")
        all_ok = True
        for filename, subdir in [(f, None) for f in SYNC_FILES] + [
            (f, "utils") for f in UTILS_FILES
        ]:
            src = (MAIN_SCRIPTS / subdir / filename) if subdir else (MAIN_SCRIPTS / filename)
            dst = (SKILL_SCRIPTS / subdir / filename) if subdir else (SKILL_SCRIPTS / filename)
            if src.exists() and dst.exists():
                if filecmp.cmp(src, dst):
                    print(f"  OK   {filename}")
                else:
                    print(f"  FAIL {filename}")
                    all_ok = False
            elif src.exists() and not dst.exists():
                print(f"  MISS {filename}")
                all_ok = False

        if all_ok:
            print("\nAll files in sync!")
        else:
            print("\nSome files failed to sync!")
            sys.exit(1)


if __name__ == "__main__":
    main()
