#!/usr/bin/env python3
"""Validate that skill symlinks in .blackbox/skills/, .claude/skills/, .opencode/skills/ point to .agents/skills/web-doc-resolver."""

import sys
from pathlib import Path


def validate_single_symlink(skill_dir: Path, canonical_dir: Path, name: str) -> bool:
    """Validate a single skill directory symlink."""
    errors = []

    # Check if symlink exists
    if not skill_dir.exists():
        errors.append(f"❌ {name}: Symlink does not exist: {skill_dir}")

    # Check if it's a symlink
    elif not skill_dir.is_symlink():
        errors.append(f"❌ {name}: Not a symlink (it's a regular file or directory): {skill_dir}")

    else:
        # Resolve both to absolute paths for comparison
        resolved_target = skill_dir.resolve()
        resolved_expected = canonical_dir.resolve()

        if resolved_target != resolved_expected:
            errors.append(f"❌ {name}: Points to wrong target")
            errors.append(f"   Expected: {resolved_expected}")
            errors.append(f"   Got:      {resolved_target}")

    # Check if canonical directory exists with SKILL.md
    skill_md = canonical_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append(f"❌ {name}: SKILL.md does not exist in canonical: {skill_md}")

    if errors:
        for error in errors:
            print(error)
        return False

    print(f"✅ {name}: Valid")
    print(f"   Link: {skill_dir}")
    print(f"   Target: {skill_dir.resolve()}")
    return True


def validate_skill_symlinks():
    """Ensure all skill symlinks point to the correct location."""
    root_dir = Path(__file__).parent.parent
    canonical_skill = root_dir / ".agents" / "skills" / "web-doc-resolver"

    # Define all skill locations (symlinks point to .agents/skills/web-doc-resolver)
    skill_locations = [
        (root_dir / ".blackbox" / "skills" / "web-doc-resolver", ".blackbox/skills"),
        (root_dir / ".claude" / "skills" / "web-doc-resolver", ".claude/skills"),
        (root_dir / ".opencode" / "skills" / "web-doc-resolver", ".opencode/skills"),
    ]

    all_valid = True
    results = []

    for skill_dir, name in skill_locations:
        if skill_dir.exists() or skill_dir.is_symlink():
            is_valid = validate_single_symlink(skill_dir, canonical_skill, name)
            all_valid = all_valid and is_valid
            results.append((name, is_valid, skill_dir.resolve() if is_valid else None))
        else:
            print(f"⚠️  {name}: Symlink not found at {skill_dir}")
            # Don't fail if a skill location doesn't exist (optional)
            # But warn about it

    print()
    if all_valid:
        print("✅ PASS: All skill symlinks are valid")
        print(f"   Canonical: {canonical_skill}")
        print(f"   SKILL.md size: {(canonical_skill / 'SKILL.md').stat().st_size} bytes")
        return True
    else:
        print("❌ FAIL: Some skill symlinks are invalid")
        sys.exit(1)


if __name__ == "__main__":
    validate_skill_symlinks()
