# Design: Visual CLIP Resolver

The `VisualResolver` implements a cross-modal retrieval approach to URL resolution.

## Pipeline

1. **Screenshot Generation**: Uses Playwright to render the full page. This ensures that JS-heavy SPAs and complex layouts are fully captured as they would appear to a user.
2. **CLIP Encoding**:
   - **Image**: The screenshot is preprocessed and passed through the CLIP vision encoder.
   - **Text**: The user's query is passed through the CLIP text encoder.
3. **Similarity Scoring**: Calculates the cosine similarity between the image embedding and the text embedding.
4. **Gating**:
   - If `similarity >= threshold`: The resolver "accepts" the page as relevant. It then performs downstream extraction (e.g., OCR via Tesseract or a summary of the visual layout).
   - If `similarity < threshold`: Returns `None`, signaling the cascade to continue to the next provider.

## Technical Stack

- **Playwright**: For high-fidelity web rendering.
- **OpenAI CLIP**: For zero-shot visual-textual alignment.
- **PyTorch**: Backend for CLIP.

## Performance Considerations

- **Latency**: Screenshotting and CLIP encoding can take 2-5 seconds.
- **Memory**: Running CLIP (even ViT-B/32) requires significant RAM/VRAM.
- **Caching**: Visual embeddings should be cached to avoid re-encoding the same page for similar queries.
