#!/usr/bin/env python3
"""Validate that skill symlinks in .blackbox/skills/, .claude/skills/, .opencode/skills/ point to root SKILL.md."""

import sys
from pathlib import Path


def validate_single_symlink(skill_link: Path, root_skill: Path, name: str) -> bool:
    """Validate a single skill symlink."""
    errors = []

    # Check if symlink exists
    if not skill_link.exists():
        errors.append(f"❌ {name}: Symlink does not exist: {skill_link}")

    # Check if it's a symlink
    elif not skill_link.is_symlink():
        errors.append(f"❌ {name}: Not a symlink (it's a regular file or directory): {skill_link}")

    else:
        # Resolve both to absolute paths for comparison
        resolved_target = skill_link.resolve()
        resolved_expected = root_skill.resolve()

        if resolved_target != resolved_expected:
            errors.append(f"❌ {name}: Points to wrong target")
            errors.append(f"   Expected: {resolved_expected}")
            errors.append(f"   Got:      {resolved_target}")

    # Check if target file exists
    if not root_skill.exists():
        errors.append(f"❌ {name}: Target file does not exist: {root_skill}")

    if errors:
        for error in errors:
            print(error)
        return False

    print(f"✅ {name}: Valid")
    print(f"   Link: {skill_link}")
    print(f"   Target: {skill_link.resolve()}")
    return True


def validate_skill_symlinks():
    """Ensure all skill symlinks point to the correct location."""
    root_dir = Path(__file__).parent.parent
    root_skill = root_dir / "SKILL.md"

    # Define all skill locations (symlinks point to .agents/skills/web-doc-resolver)
    skill_locations = [
        (root_dir / ".blackbox" / "skills" / "web-doc-resolver" / "SKILL.md", ".blackbox/skills"),
        (root_dir / ".claude" / "skills" / "web-doc-resolver" / "SKILL.md", ".claude/skills"),
        (root_dir / ".opencode" / "skills" / "web-doc-resolver" / "SKILL.md", ".opencode/skills"),
    ]

    all_valid = True
    results = []

    for skill_link, name in skill_locations:
        if skill_link.exists():
            is_valid = validate_single_symlink(skill_link, root_skill, name)
            all_valid = all_valid and is_valid
            results.append((name, is_valid, skill_link.resolve() if is_valid else None))
        else:
            print(f"⚠️  {name}: Symlink not found at {skill_link}")
            # Don't fail if a skill location doesn't exist (optional)
            # But warn about it

    print()
    if all_valid:
        print("✅ PASS: All skill symlinks are valid")
        print(f"   Root SKILL.md: {root_skill}")
        print(f"   File size: {root_skill.stat().st_size} bytes")
        return True
    else:
        print("❌ FAIL: Some skill symlinks are invalid")
        sys.exit(1)


if __name__ == "__main__":
    validate_skill_symlinks()
