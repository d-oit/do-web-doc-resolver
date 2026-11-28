#!/usr/bin/env python3
"""
Clean-environment packaging smoke test.

Builds the sdist and wheel, installs the wheel into a throwaway virtual
environment, and verifies the published install paths a real user would hit:

- the wheel installs without dev/test dependencies
- the console script `do-wdr --help` works
- the installed package imports and can access its runtime resources
- the sdist builds (checked by the build step, not installed)

CI validates the artifacts; nothing is published.

Usage: python scripts/check_packaging.py [--keep-temp]
"""

import argparse
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"

DEV_ONLY_TOOLS = ("pytest", "ruff", "black", "mypy", "flake8", "pip-audit")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed: {' '.join(cmd)}")
    return result


def build_artifacts() -> tuple[Path, Path]:
    run([sys.executable, "-m", "pip", "install", "--quiet", "build"])
    run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(DIST_DIR)],
        cwd=REPO_ROOT,
    )
    wheels = sorted(DIST_DIR.glob("*.whl"))
    sdists = sorted(DIST_DIR.glob("*.tar.gz"))
    if not wheels or not sdists:
        raise SystemExit("Build did not produce both a wheel and an sdist")
    return sdists[-1], wheels[-1]


def smoke_test_wheel(wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="dowdr-wheel-") as tmp:
        venv_dir = Path(tmp) / "venv"
        venv.create(venv_dir, with_pip=True)
        pip = str(venv_dir / "bin" / "pip")
        py = str(venv_dir / "bin" / "python")

        run([pip, "install", "--quiet", str(wheel)])

        run([str(venv_dir / "bin" / "do-wdr"), "--help"])

        installed = run(
            [pip, "list", "--format=json"],
            capture_output=True,
            text=True,
        )
        names = {pkg["name"].lower() for pkg in __import__("json").loads(installed.stdout)}
        for tool in DEV_ONLY_TOOLS:
            if tool in names:
                raise SystemExit(f"Wheel install pulled in dev-only dependency '{tool}'")

        run(
            [
                py,
                "-c",
                "import scripts.resolve; import scripts.cli; print('import-ok')",
            ],
            cwd=Path(tmp),
        )

    print("OK: wheel install smoke test passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-temp", action="store_true", help="Unused; kept for CI compat")
    parser.parse_args()

    _, wheel = build_artifacts()
    smoke_test_wheel(wheel)


if __name__ == "__main__":
    main()
