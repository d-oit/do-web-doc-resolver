# do-wdr-visual-resolver

Visual URL resolution skill for the Web Doc Resolver (do-wdr).

## Overview

This skill adds a `VisualResolver` that uses CLIP (Contrastive Language-Image Pre-training) to "see" web pages. It handles scenarios where text-based extractors fail by:

1. Taking a screenshot of the target URL.
2. Generating an embedding of the screenshot using CLIP.
3. Comparing the screenshot embedding with the query embedding.
4. Returning content only if the visual similarity meets a specified threshold.

## Installation

```bash
# Core dependencies
pip install torch torchvision torchaudio
pip install git+https://github.com/openai/CLIP.git
pip install playwright

# Install browser for screenshots
playwright install chromium
```

## Structure

- `visual_resolver.py`: Core implementation.
- `SKILL.md`: Skill definition and metadata.
- `evals/`: Evaluation suite.
- `references/`: Detailed design, integration, and configuration docs.

## Usage

When integrated into the `do-wdr` cascade, it serves as a high-fidelity fallback for non-textual or JS-heavy content.

```python
from .visual_resolver import VisualResolver

resolver = VisualResolver(threshold=0.25)
if resolver.is_available():
    result = resolver.resolve(
        url="https://example.com/infographic.png",
        query="Explain the data pipeline shown in the infographic"
    )
```

## Testing

Run the evaluation suite:

```bash
python -m pytest .agents/skills/do-wdr-visual-resolver/evals/ -v
```
