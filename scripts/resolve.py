#!/usr/bin/env python3
"""Resolve query or URL inputs into compact, high-signal markdown for agents and RAG systems."""

import argparse
import hashlib
import json
import logging
import os
import sys
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

MAX_CHARS = 8000
MIN_CHARS = 200
EXA_RESULTS = 5
TAVILY_RESULTS = 3
CACHE_DIR = os.path.expanduser("~/.cache/web-doc-resolver")
CACHE_TTL = 3600 * 24
MISTRAL_AGENT_ID = "ag_019cd1597b9e760d9b0a71fd13b32f96"


def get_cache():
    try:
        import diskcache
        return diskcache.Cache(CACHE_DIR)
    except Exception:
        return None


_cache = None


def _get_cache():
    global _cache
    if _cache is None:
        _cache = get_cache()
    return _cache


def _cache_key(input_str: str, source: str) -> str:
    hash_input = f"{source}:{input_str}"
    return hashlib.sha256(hash_input.encode()).hexdigest()


def _get_from_cache(input_str: str, source: str) -> Optional[Dict[str, Any]]:
    cache = _get_cache()
    if not cache:
        return None
    try:
        key = _cache_key(input_str, source)
        result = cache.get(key)
        if result and isinstance(result, dict):
            logger.debug(f"Cache hit for {source}:{input_str[:30]}...")
            return result
    except Exception:
        pass
    return None


def _save_to_cache(input_str: str, source: str, result: Dict[str, Any]):
    cache = _get_cache()
    if not cache:
        return
    try:
        key = _cache_key(input_str, source)
        cache.set(key, result, expire=CACHE_TTL)
    except Exception:
        pass


def is_url(input_str: str) -> bool:
    try:
        result = urlparse(input_str)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def fetch_llms_txt(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        llms_url = f"{base_url}/llms.txt"

        logger.info(f"Checking {llms_url}")
        response = requests.get(llms_url, timeout=5)

        if response.status_code == 200:
            logger.info(f"Found llms.txt at {llms_url}")
            return response.text
    except Exception as e:
        logger.debug(f"No llms.txt found: {e}")
    return None


def resolve_with_exa(query: str, max_chars: int = MAX_CHARS) -> Optional[Dict[str, Any]]:
    cached = _get_from_cache(query, "exa")
    if cached:
        return cached

    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        logger.debug("EXA_API_KEY not set, skipping Exa")
        return None

    try:
        from exa_py import Exa

        client = Exa(api_key)
        results = client.search_and_contents(
            query,
            use_autoprompt=True,
            highlights=True,
            num_results=EXA_RESULTS
        )

        if not results or not results.results:
            return None

        content_parts = []
        for result in results.results:
            if hasattr(result, 'highlight') and result.highlight:
                content_parts.append(result.highlight)
            elif hasattr(result, 'text') and result.text:
                content_parts.append(result.text)

        content = "\n\n---\n\n".join(content_parts)[:max_chars]

        result_dict = {
            "source": "exa",
            "query": query,
            "content": content,
        }
        _save_to_cache(query, "exa", result_dict)
        return result_dict

    except ImportError:
        logger.warning("exa-py not installed. Install with: pip install exa-py")
        return None
    except Exception as e:
        logger.error(f"Exa search failed: {e}")
        return None


def resolve_with_tavily(query: str, max_chars: int = MAX_CHARS) -> Optional[Dict[str, Any]]:
    cached = _get_from_cache(query, "tavily")
    if cached:
        return cached

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.debug("TAVILY_API_KEY not set, skipping Tavily")
        return None

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=TAVILY_RESULTS)

        if not results or not results.get("results"):
            return None

        content_parts = [f"# Search Results for: {query}\n"]
        for r in results["results"]:
            title = r.get("title", "")
            content = r.get("content", "")
            url = r.get("url", "")
            if title:
                content_parts.append(f"## {title}\n\n{content}\n\nSource: {url}")

        content = "\n\n---\n\n".join(content_parts)[:max_chars]

        result_dict = {
            "source": "tavily",
            "query": query,
            "content": content,
        }
        _save_to_cache(query, "tavily", result_dict)
        return result_dict

    except ImportError:
        logger.warning("tavily-python not installed. Install with: pip install tavily-python")
        return None
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return None


def resolve_with_mistral_websearch(query: str, max_chars: int = MAX_CHARS) -> Optional[Dict[str, Any]]:
    cached = _get_from_cache(query, "mistral-websearch")
    if cached:
        return cached

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        logger.debug("MISTRAL_API_KEY not set, skipping Mistral websearch")
        return None

    agent_id = os.getenv("MISTRAL_AGENT_ID", MISTRAL_AGENT_ID)

    try:
        from mistralai import Mistral

        client = Mistral(api_key=api_key)

        logger.info(f"Using Mistral websearch to resolve: {query}")

        response = client.beta.conversations.start(
            agent_id=agent_id,
            inputs=query
        )

        content = ""
        for output in response.outputs:
            if hasattr(output, 'content') and isinstance(getattr(output, 'content', None), str):
                content = str(output.content)
                break

        if not content:
            return None

        result_dict = {
            "source": "mistral-websearch",
            "query": query,
            "content": content[:max_chars],
        }
        _save_to_cache(query, "mistral-websearch", result_dict)
        return result_dict

    except ImportError:
        logger.warning("mistralai not installed. Install with: pip install mistralai")
        return None
    except Exception as e:
        logger.error(f"Mistral websearch failed: {e}")
        return None


def resolve_with_firecrawl(url: str, max_chars: int = MAX_CHARS) -> Optional[Dict[str, Any]]:
    cached = _get_from_cache(url, "firecrawl")
    if cached:
        return cached

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.debug("FIRECRAWL_API_KEY not set, skipping Firecrawl")
        return None

    try:
        from firecrawl import Firecrawl

        app = Firecrawl(api_key=api_key)
        logger.info(f"Using Firecrawl to extract: {url}")

        result = app.scrape(url, formats=["markdown"])
        markdown = ""
        if result and hasattr(result, 'markdown'):
            markdown = result.markdown or ""

        result_dict = {"source": "firecrawl", "url": url, "content": markdown[:max_chars]}
        _save_to_cache(url, "firecrawl", result_dict)
        return result_dict

    except ImportError:
        logger.warning("firecrawl not installed. Install with: pip install firecrawl-py")
        return None

    except Exception as e:
        error_msg = str(e).lower()

        if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
            logger.warning("Firecrawl rate limit exceeded. Trying Mistral fallback...")
            return resolve_with_mistral_websearch(url, max_chars)

        if "credit" in error_msg or "quota" in error_msg or "insufficient" in error_msg:
            logger.warning("Firecrawl credits exhausted. Trying Mistral fallback...")
            return resolve_with_mistral_websearch(url, max_chars)

        if "unauthorized" in error_msg or "401" in error_msg or "invalid" in error_msg:
            logger.error(f"Firecrawl authentication failed: {e}")
            return None

        logger.error(f"Firecrawl extraction failed: {e}. Trying Mistral fallback...")
        return resolve_with_mistral_websearch(url, max_chars)


def resolve_with_mistral_browser(url: str, max_chars: int = MAX_CHARS) -> Optional[Dict[str, Any]]:
    """Backward-compatible alias - uses Mistral websearch for queries."""
    return resolve_with_mistral_websearch(url, max_chars)


def resolve(input_str: str, max_chars: int = MAX_CHARS) -> Dict[str, Any]:
    logger.info(f"Resolving: {input_str}")

    if is_url(input_str):
        llms_content = fetch_llms_txt(input_str)
        if llms_content:
            return {
                "source": "llms.txt",
                "url": input_str,
                "content": llms_content[:max_chars],
            }

        firecrawl_result = resolve_with_firecrawl(input_str, max_chars)
        if firecrawl_result:
            return firecrawl_result

        return {
            "source": "none",
            "url": input_str,
            "content": f"# Unable to resolve URL: {input_str}\n\nNo llms.txt found and Firecrawl not available.\n",
            "error": "No resolution method available",
        }

    else:
        exa_result = resolve_with_exa(input_str, max_chars)
        if exa_result:
            return exa_result

        tavily_result = resolve_with_tavily(input_str, max_chars)
        if tavily_result:
            return tavily_result

        mistral_result = resolve_with_mistral_websearch(input_str, max_chars)
        if mistral_result:
            return mistral_result

        return {
            "source": "none",
            "query": input_str,
            "content": f"# Unable to resolve query: {input_str}\n\nNo API keys configured. Set EXA_API_KEY, TAVILY_API_KEY, or MISTRAL_API_KEY.\n",
            "error": "No resolution method available",
        }


def main():
    parser = argparse.ArgumentParser(
        description="Resolve queries or URLs into LLM-ready markdown"
    )
    parser.add_argument("input", nargs="?", help="URL or search query to resolve")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=MAX_CHARS,
        help=f"Maximum characters in output (default: {MAX_CHARS})",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not args.input:
        parser.error("Provide input argument or use - for stdin")

    if args.input == "-":
        inputs = [line.strip() for line in sys.stdin if line.strip()]
        for i, inp in enumerate(inputs):
            result = resolve(inp, args.max_chars)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(result.get("content", ""))
                if "note" in result:
                    print(f"\n---\nNote: {result['note']}", file=sys.stderr)
                if "error" in result:
                    print(f"\n---\nError: {result['error']}", file=sys.stderr)
            if i < len(inputs) - 1:
                print("\n" + "=" * 40 + "\n")
    else:
        result = resolve(args.input, args.max_chars)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result.get("content", ""))
            if "note" in result:
                print(f"\n---\nNote: {result['note']}", file=sys.stderr)
            if "error" in result:
                print(f"\n---\nError: {result['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
