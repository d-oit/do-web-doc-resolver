#!/usr/bin/env python3
"""Resolve query or URL inputs into compact, high-signal markdown for agents and RAG systems."""

import argparse
import json
import logging
import os
import sys
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Defaults from SKILL.md
MAX_CHARS = 8000
MIN_CHARS = 200
EXA_RESULTS = 5
TAVILY_RESULTS = 3
OUTPUT_LIMIT = 10


def resolve_url(url: str, max_chars: int = MAX_CHARS) -> dict:
    """Resolve a URL following the cascade: llms.txt first, then Firecrawl fallback."""
    logger.info(f"Resolving URL: {url}")
    
    # Step 1: Try llms.txt
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    llms_txt_url = f"{origin}/llms.txt"
    
    logger.debug(f"Probing {llms_txt_url}")
    # TODO: Implement llms.txt fetching and parsing
    
    # Step 2: Fallback to direct fetch or Firecrawl
    logger.debug("Using direct fetch as fallback")
    # TODO: Implement Firecrawl fallback if EXA_API_KEY present
    
    return {
        "url": url,
        "content_markdown": "# Sample content\n\nThis is a placeholder implementation.",
        "source": "placeholder",
        "score": 0.5
    }


def resolve_query(query: str, exa_results: int = EXA_RESULTS, 
                 tavily_results: int = TAVILY_RESULTS, 
                 max_chars: int = MAX_CHARS) -> list:
    """Resolve a query following the cascade: Exa highlights first, Tavily fallback."""
    logger.info(f"Resolving query: {query}")
    results = []
    
    # Step 1: Try Exa with highlights if key available
    exa_key = os.getenv("EXA_API_KEY")
    if exa_key:
        logger.debug(f"Using Exa search with {exa_results} results")
        # TODO: Implement Exa search with highlights
    else:
        logger.warning("EXA_API_KEY not set, skipping Exa search")
    
    # Step 2: Fallback to Tavily if needed
    if len(results) < 3:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            logger.debug(f"Using Tavily fallback with {tavily_results} results")
            # TODO: Implement Tavily search
        else:
            logger.warning("TAVILY_API_KEY not set, skipping Tavily search")
    
    # Placeholder result
    results.append({
        "url": "https://example.com",
        "content_markdown": "# Sample query result\n\nPlaceholder for query: " + query,
        "source": "placeholder",
        "score": 0.7
    })
    
    return results


def is_url(text: str) -> bool:
    """Check if text is a URL."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Resolve query or URL into compact, LLM-ready markdown"
    )
    parser.add_argument("input", help="Query string or URL to resolve")
    parser.add_argument("--min-chars", type=int, default=MIN_CHARS,
                       help=f"Minimum content length (default: {MIN_CHARS})")
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS,
                       help=f"Maximum content length (default: {MAX_CHARS})")
    parser.add_argument("--exa-results", type=int, default=EXA_RESULTS,
                       help=f"Number of Exa results (default: {EXA_RESULTS})")
    parser.add_argument("--tavily-results", type=int, default=TAVILY_RESULTS,
                       help=f"Number of Tavily results (default: {TAVILY_RESULTS})")
    parser.add_argument("--output-limit", type=int, default=OUTPUT_LIMIT,
                       help=f"Maximum results to return (default: {OUTPUT_LIMIT})")
    parser.add_argument("--log-level", default="WARNING",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level (default: WARNING)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
        stream=sys.stderr
    )
    
    try:
        # Determine if input is URL or query
        if is_url(args.input):
            result = resolve_url(args.input, max_chars=args.max_chars)
            results = [result]
        else:
            results = resolve_query(
                args.input,
                exa_results=args.exa_results,
                tavily_results=args.tavily_results,
                max_chars=args.max_chars
            )
        
        # Limit output
        results = results[:args.output_limit]
        
        # Output JSON to stdout
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        logger.error(f"Error during resolution: {e}")
        error_output = [{"error": str(e), "input": args.input}]
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
