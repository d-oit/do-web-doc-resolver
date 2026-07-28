import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class MockSentenceTransformer:
    def __init__(self, model_name=None):
        self.model_name = model_name

    def get_embedding_dimension(self):
        return 384

    def encode(self, sentences, convert_to_numpy=True, normalize_embeddings=True, **kwargs):
        if isinstance(sentences, str):
            single = True
            sentences_list = [sentences]
        elif isinstance(sentences, (list, tuple)):
            single = False
            sentences_list = list(sentences)
        else:
            single = True
            sentences_list = [str(sentences)]

        embeddings = []
        for text in sentences_list:
            vec = np.zeros(384, dtype=np.float32)
            words = text.lower().split()
            stop = {"how", "to", "do", "i", "a", "in", "the", "an", "and", "of", "for", "is", "are"}
            words = [w for w in words if w not in stop]
            for word in words:
                stem = word[:4]
                h1 = hash(stem) % 384
                h2 = hash(word) % 384
                vec[h1] += 1.0
                vec[(h1 + 1) % 384] += 0.5
                vec[(h1 - 1) % 384] += 0.5
                vec[h2] += 0.5
                vec[(h2 + 1) % 384] += 0.25
                vec[(h2 - 1) % 384] += 0.25
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            embeddings.append(vec)

        if single:
            return embeddings[0]
        return np.array(embeddings)


# Mock sentence_transformers module to avoid HuggingFace model downloads during tests
mock_st_module = MagicMock()
mock_st_module.SentenceTransformer = MockSentenceTransformer
sys.modules["sentence_transformers"] = mock_st_module

import scripts.providers_impl  # noqa: E402
import scripts.quality  # noqa: E402
import scripts.resolve  # noqa: E402
import scripts.routing  # noqa: E402
import scripts.routing_memory  # noqa: E402
import scripts.state  # noqa: E402
import scripts.synthesis  # noqa: E402
import scripts.utils  # noqa: E402
import scripts.utils.cache  # noqa: E402


class MemoryCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, expire=None):
        self.data[key] = value

    def clear(self):
        self.data.clear()


@pytest.fixture(autouse=True)
def setup_test_env():
    # Fresh cache for every test to avoid cross-test contamination
    cache = MemoryCache()

    # Apply to all possible locations
    scripts.utils._cache = cache
    scripts.utils.cache._cache = cache
    scripts.utils.cache._l1_clear()
    if hasattr(scripts.resolve, "_cache"):
        scripts.resolve._cache = cache
    # Also reset the module-level _cache in cache.py
    scripts.utils.cache._cache = cache

    # Mock get_cache to return our memory cache
    with patch("scripts.utils.cache.get_cache", return_value=cache):
        # Reset shared state via state.py singletons
        scripts.state.routing_memory.clear()
        scripts.state.circuit_breakers.clear()
        scripts.providers_impl._clear_rate_limits()

        # Mock synthesis to avoid LLM calls
        original_should_synth = scripts.synthesis.should_call_llm_synthesis
        original_merge = scripts.synthesis.deterministic_merge
        scripts.synthesis.should_call_llm_synthesis = lambda x: False
        scripts.synthesis.deterministic_merge = lambda x: "Merged content"

        # Force deterministic order for tests
        original_plan = scripts.routing.plan_provider_order

        def mock_plan(target, is_url, custom_order=None, skip_providers=None, **kwargs):
            if custom_order:
                base = list(custom_order)
            elif is_url:
                base = [
                    "llms_txt",
                    "jina",
                    "firecrawl",
                    "direct_fetch",
                    "mistral_browser",
                    "duckduckgo",
                ]
            else:
                base = ["exa_mcp", "exa", "tavily", "duckduckgo", "mistral_websearch"]

            skip = skip_providers or set()
            return [p for p in base if p not in skip]

        scripts.routing.plan_provider_order = mock_plan

        yield

        # Restore
        scripts.synthesis.should_call_llm_synthesis = original_should_synth
        scripts.synthesis.deterministic_merge = original_merge
        scripts.routing.plan_provider_order = original_plan
