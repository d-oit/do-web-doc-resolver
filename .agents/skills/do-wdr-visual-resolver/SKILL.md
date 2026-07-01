---
name: do-wdr-visual-resolver
description: Visual URL resolution skill using CLIP screenshot embeddings to handle scanned PDFs, image-heavy layouts, and JS-heavy SPAs.
license: MIT
compatibility: Python 3.11+, CLIP, Playwright
allowed-tools: Bash(python:*|do-wdr:*) Read
metadata:
  author: d-oit
  version: "0.1.0"
  source: https://github.com/d-oit/do-web-doc-resolver
---

# Visual Resolver Skill

Extends the Web Doc Resolver cascade with a visual provider based on CLIP screenshot embeddings.

## When to use this skill

Activate this skill when text-based extractors (Jina, Firecrawl, etc.) fail to resolve a URL, particularly for:

- Scanned PDFs (raster text)
- Single Page Applications (SPAs) returning skeleton HTML
- Infographic-heavy or chart/table-only documents
- Complex multi-column academic layouts

## Prerequisites

Install visual resolution dependencies:

```bash
pip install torch torchvision torchaudio
pip install git+https://github.com/openai/CLIP.git
pip install playwright
playwright install chromium
```

## Integration

This skill is designed to be integrated into the `scripts/_url_resolve.py` cascade.

## Usage

```python
from .visual_resolver import VisualResolver

resolver = VisualResolver()
if resolver.is_available():
    result = resolver.resolve("https://example.com/scanned-pdf", "technical architecture diagram")
```
