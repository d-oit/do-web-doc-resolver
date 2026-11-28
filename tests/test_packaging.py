"""Packaging metadata consistency tests."""

import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEV_ONLY_TOOLS = {
    "pytest",
    "pytest-cov",
    "pytest-asyncio",
    "respx",
    "black",
    "ruff",
    "flake8",
    "mypy",
    "types-requests",
    "pip-audit",
}


def load_pyproject() -> dict:
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


class TestDependencyGroups(unittest.TestCase):
    def setUp(self):
        self.pyproject = load_pyproject()

    def test_runtime_dependencies_exclude_dev_tooling(self):
        deps = {
            d.split(">")[0].split("<")[0].split("[")[0].strip().lower()
            for d in self.pyproject["project"]["dependencies"]
        }
        overlap = deps & DEV_ONLY_TOOLS
        self.assertEqual(overlap, set(), f"runtime deps contain dev tooling: {overlap}")

    def test_dev_group_matches_dev_extra(self):
        group = {d.strip().lower() for d in self.pyproject["dependency-groups"]["dev"]}
        extra = {
            d.strip().lower() for d in self.pyproject["project"]["optional-dependencies"]["dev"]
        }
        self.assertEqual(
            group, extra, "[dependency-groups].dev and [project.optional-dependencies].dev drifted"
        )

    def test_requirements_file_delegates_to_package(self):
        text = (REPO_ROOT / "requirements.txt").read_text()
        self.assertIn("-e .[dev]", text)
        self.assertNotIn("pytest", text)


class TestVersionMetadata(unittest.TestCase):
    def setUp(self):
        self.pyproject = load_pyproject()

    def test_requires_python_consistent_with_classifiers(self):
        requires = self.pyproject["project"]["requires-python"]
        min_minor = int(requires.split(".")[1].lstrip(">="))
        classifiers = " ".join(self.pyproject["project"]["classifiers"])
        self.assertIn(f"Python :: 3.{min_minor}", classifiers)

    def test_console_scripts_point_to_existing_modules(self):
        from importlib import import_module

        for entry in self.pyproject["project"]["scripts"].values():
            module_path, attr = entry.split(":")
            module = import_module(module_path)
            self.assertTrue(hasattr(module, attr), f"{entry} is not importable")

    def test_version_matches_ci_toolchain_pins(self):
        ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
        cargo = (REPO_ROOT / "cli" / "Cargo.toml").read_text()
        self.assertIn('rust-version = "1.85"', cargo)
        self.assertIn("RUST_TOOLCHAIN: '1.85'", ci)


if __name__ == "__main__":
    unittest.main()
