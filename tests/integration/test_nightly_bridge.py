import os
import subprocess

import pytest

CLI_PATH = "./cli/target/release/do-wdr"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.path.exists(CLI_PATH),
        reason=f"CLI binary not found at {CLI_PATH}. Run 'cd cli && cargo build --release' first.",
    ),
]


@pytest.mark.integration
def test_nightly_direct_fetch_indentation():
    """Verify that direct_fetch preserves indentation in code blocks."""
    # Use a real site known to have indented code blocks in its documentation
    url = "https://docs.rs/tokio/latest/tokio/"

    result = subprocess.run(
        [CLI_PATH, "resolve", url, "--provider", "direct_fetch"],
        capture_output=True,
        text=True,
        check=True,
    )

    content = result.stdout
    # Check for indented code inside a code block
    lines = content.splitlines()
    in_code_block = False
    found_indentation = False
    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        # Check for 4 spaces indentation inside code block
        if in_code_block and line.startswith("    "):
            found_indentation = True
            break

    assert found_indentation, "Indentation not preserved in direct_fetch code blocks"


@pytest.mark.integration
def test_nightly_direct_fetch_latex_extraction():
    """Verify that direct_fetch correctly extracts LaTeX."""
    url = "https://en.wikipedia.org/wiki/Quadratic_formula"

    result = subprocess.run(
        [CLI_PATH, "resolve", url, "--provider", "direct_fetch"],
        capture_output=True,
        text=True,
        check=True,
    )

    content = result.stdout
    # Wikipedia uses {\displaystyle ...} in alt text.
    assert "{\\displaystyle" in content
    # Check for standard quadratic formula part
    assert "b^{2}-4ac" in content


@pytest.mark.integration
def test_nightly_llm_ready_standards():
    """Verify that synthesized output follows 2026 LLM-ready standards."""
    url = "https://docs.rs/tokio/latest/tokio/"

    result = subprocess.run(
        [CLI_PATH, "resolve", url, "--provider", "direct_fetch", "--synthesize"],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "MISTRAL_API_KEY": "test_key"},
    )

    content = result.stdout

    # YAML Frontmatter
    assert content.startswith("---")
    assert "relevance_score:" in content
    assert "intent_category:" in content
    assert "token_estimate:" in content
    assert "last_updated:" in content

    # Structural Anchors
    assert "[ANCHOR: SUMMARY]" in content
    assert "[ANCHOR: TECHNICAL_DETAILS]" in content
    assert "[ANCHOR: COMPARISON]" in content
    assert "[ANCHOR: CITATIONS]" in content
