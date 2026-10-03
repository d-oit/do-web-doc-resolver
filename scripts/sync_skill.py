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

# The mirror is a byte-for-byte copy of the source tree, so the file set is
# discovered from disk rather than listed by hand. A hand-maintained list is
# exactly what let the mirror drift: `_query_resolve`, `_url_resolve`,
# `semantic_cache`, `cli` and the whole `providers/` package were added to
# scripts/ and never reached the skill, leaving the standalone skill
# unimportable.
#
# Discovery is allow-by-default, so a new resolver module is picked up without
# anyone remembering to add it. `MAINTENANCE_ONLY` is the correction: tooling
# that lives in scripts/ but is not part of the resolver runtime, and which
# would only bloat or confuse the standalone skill if copied in.
NOT_SYNCED = {"__init__.py"}

# Repo maintenance / CI tooling, not resolver runtime. Copying these is actively
# wrong: sync_skill.py would ship a copy of itself, and the validators resolve
# paths that do not exist outside this repository.
MAINTENANCE_ONLY = {
    "diagnose_providers.py",
    "doc_models.py",
    "doc_validator.py",
    "generate_changelog.py",
    "monitor_providers.py",
    "sync_skill.py",
    "sync_versions.py",
    "validate_docs.py",
    "validate_skill_symlink.py",
}


def discover(subdir: str | None = None) -> list[str]:
    """List the syncable runtime modules of `scripts/<subdir>/`, sorted."""
    base = MAIN_SCRIPTS / subdir if subdir else MAIN_SCRIPTS
    if not base.is_dir():
        return []
    return sorted(
        p.name
        for p in base.glob("*.py")
        if p.name not in NOT_SYNCED and p.name not in MAINTENANCE_ONLY
    )


def sync_targets() -> list[tuple[str, str | None]]:
    """Every (filename, subdir) pair the mirror must contain."""
    targets: list[tuple[str, str | None]] = [(name, None) for name in discover()]
    # These two packages export symbols from their roots, so __init__.py is
    # part of the mirror rather than an empty shim.
    for subdir in ("providers", "utils"):
        targets += [(name, subdir) for name in discover(subdir)]
        if (MAIN_SCRIPTS / subdir / "__init__.py").exists():
            targets.append(("__init__.py", subdir))
    return targets


def stale_mirror_files() -> list[Path]:
    """Mirror files with no counterpart in the source tree.

    Catches the opposite direction of drift: a module renamed, merged or deleted
    upstream that is still sitting in the skill, shadowing nothing and rotting.
    """
    if not SKILL_SCRIPTS.is_dir():
        return []
    expected = {SKILL_SCRIPTS / (sub or "") / name for name, sub in sync_targets()}
    # sync_init() creates an empty shim at the mirror root; it is not a copy of
    # scripts/__init__.py and must not be reported as stale.
    expected.add(SKILL_SCRIPTS / "__init__.py")
    actual = {p for p in SKILL_SCRIPTS.rglob("*.py") if "__pycache__" not in p.parts}
    return sorted(actual - expected)


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
    return synced


def sync_init(dry_run: bool = False) -> None:
    """Ensure __init__.py exists in skill scripts."""
    dst = SKILL_SCRIPTS / "__init__.py"
    if not dst.exists():
        if not dry_run:
            dst.touch()
        print("  CREATE __init__.py")


def main():
    # --check is the CI gate: report drift and exit non-zero without writing.
    # --dry-run previews writes. Both are non-destructive.
    check_only = "--check" in sys.argv
    dry_run = check_only or "--dry-run" in sys.argv

    print("=== Skill Sync: scripts/ → .agents/skills/do-web-doc-resolver/scripts/ ===")
    if check_only:
        print("Mode: CHECK (no writes)")
    elif dry_run:
        print("Mode: DRY RUN")
    else:
        print("Mode: LIVE")
    print()

    if not SKILL_SCRIPTS.exists():
        print(f"ERROR: Skill scripts directory not found: {SKILL_SCRIPTS}")
        sys.exit(1)

    targets = sync_targets()
    print(f"Discovered {len(targets)} module(s) to mirror\n")

    synced = 0
    for filename, subdir in targets:
        if sync_file(filename, dry_run, subdir=subdir):
            synced += 1
    synced += sync_utils_package(dry_run)
    sync_init(dry_run)

    # Remove mirror files with no source counterpart.
    for stale in stale_mirror_files():
        rel = stale.relative_to(SKILL_SCRIPTS)
        if check_only or dry_run:
            print(f"  STALE {rel}")
            synced += 1
        else:
            stale.unlink()
            print(f"  DELETE {rel} (no source counterpart)")
            synced += 1

    print()
    if check_only:
        if synced:
            print(f"FAIL: {synced} mirrored file(s) out of sync.")
            print("Run: python scripts/sync_skill.py")
            sys.exit(1)
        print("OK: skill mirror is in sync.")
        return
    if dry_run:
        print(f"Would sync {synced} file(s)")
    else:
        print(f"Synced {synced} file(s)")

    # Verify
    if not dry_run:
        print()
        print("=== Verification ===")
        all_ok = True
        for filename, subdir in targets:
            src = MAIN_SCRIPTS / subdir / filename if subdir else MAIN_SCRIPTS / filename
            dst = SKILL_SCRIPTS / subdir / filename if subdir else SKILL_SCRIPTS / filename
            label = f"{subdir}/{filename}" if subdir else filename
            if src.exists() and dst.exists():
                if filecmp.cmp(src, dst):
                    print(f"  OK   {label}")
                else:
                    print(f"  FAIL {label}")
                    all_ok = False
            elif src.exists() and not dst.exists():
                print(f"  MISS {label}")
                all_ok = False

        if all_ok:
            print("\nAll files in sync!")
        else:
            print("\nSome files failed to sync!")
            sys.exit(1)


if __name__ == "__main__":
    main()
