import { NextRequest, NextResponse } from "next/server";

// Allow up to 60 seconds for resolver operations
export const maxDuration = 60;

const MAX_CHARS = parseInt(process.env.WEB_RESOLVER_MAX_CHARS || "8000");

// Provider keys - can come from env vars or request body
interface ProviderKeys {
  SERPER_API_KEY?: string;
  TAVILY_API_KEY?: string;
  EXA_API_KEY?: string;
  FIRECRAWL_API_KEY?: string;
  MISTRAL_API_KEY?: string;
}

function isUrl(input: string): boolean {
  return /^https?:\/\/\S+$/i.test(input.trim());
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs = 15000
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function extractViaJina(url: string): Promise<string | null> {
  try {
    const res = await fetchWithTimeout(`https://r.jina.ai/${url}`, {
      headers: {
        Accept: "text/plain",
        "X-Return-Format": "text",
      },
    });
    if (!res.ok) return null;
    const text = await res.text();
    return text.length > 50 ? text.slice(0, MAX_CHARS) : null;
  } catch {
    return null;
  }
}

async function extractViaDirectFetch(url: string): Promise<string | null> {
  try {
    const res = await fetchWithTimeout(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (compatible; WebDocResolver/1.0; +https://web-eight-ivory-29.vercel.app)",
        Accept: "text/html",
      },
    });
    if (!res.ok) return null;
    const html = await res.text();
    // Basic HTML to text extraction
    const text = html
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    return text.length > 50 ? text.slice(0, MAX_CHARS) : null;
  } catch {
    return null;
  }
}

/**
 * Extract content via Firecrawl API (requires API key)
 * Deep extraction with JavaScript rendering
 */
async function extractViaFirecrawl(url: string, apiKey: string): Promise<string | null> {
  if (!apiKey) return null;
  try {
    const res = await fetchWithTimeout(
      "https://api.firecrawl.dev/v1/scrape",
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          formats: ["markdown"],
        }),
      },
      30000 // Longer timeout for JS rendering
    );
    if (!res.ok) return null;
    const data = await res.json();
    const markdown = data?.data?.markdown;
    return markdown && markdown.length > 50 ? markdown.slice(0, MAX_CHARS) : null;
  } catch {
    return null;
  }
}

async function searchViaSerper(query: string, apiKey: string): Promise<string | null> {
  if (!apiKey) return null;
  try {
    const res = await fetchWithTimeout(
      "https://google.serper.dev/search",
      {
        method: "POST",
        headers: {
          "X-API-KEY": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ q: query, num: 5 }),
      }
    );
    if (!res.ok) return null;
    const data = await res.json();
    const snippets = (data.organic || [])
      .map((r: { snippet?: string }) => r.snippet)
      .filter(Boolean)
      .join("\n\n");
    if (snippets.length < 100) return null;
    // Try to fetch the first result URL for full content
    const firstUrl = data.organic?.[0]?.link;
    if (firstUrl) {
      const content = await extractViaJina(firstUrl) || await extractViaDirectFetch(firstUrl);
      if (content && content.length > snippets.length) {
        return `Source: ${firstUrl}\n\n${content.slice(0, MAX_CHARS)}`;
      }
    }
    return `Search results for: ${query}\n\n${snippets.slice(0, MAX_CHARS)}`;
  } catch {
    return null;
  }
}

async function searchViaTavily(query: string, apiKey: string): Promise<string | null> {
  if (!apiKey) return null;
  try {
    const res = await fetchWithTimeout("https://api.tavily.com/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: apiKey,
        query,
        max_results: 5,
        include_raw_content: true,
      }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const results = (data.results || [])
      .map(
        (r: { title?: string; url?: string; raw_content?: string; content?: string }) =>
          `## ${r.title}\nSource: ${r.url}\n\n${r.raw_content || r.content || ""}`
      )
      .join("\n\n---\n\n");
    return results.length > 100
      ? results.slice(0, MAX_CHARS)
      : null;
  } catch {
    return null;
  }
}

/**
 * Free search via DuckDuckGo using Jina Reader to parse search results
 * This works without any API key by scraping DDG search results
 */
async function searchViaDuckDuckGoFree(query: string): Promise<string | null> {
  try {
    // Use DuckDuckGo HTML search and parse via Jina Reader
    const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
    const res = await fetchWithTimeout(`https://r.jina.ai/${searchUrl}`, {
      headers: {
        Accept: "text/plain",
        "X-Return-Format": "text",
      },
    });
    if (!res.ok) return null;
    const text = await res.text();

    // Clean up the search results text
    // Jina returns the page content, we need to extract meaningful parts
    const lines = text.split('\n').filter(line => {
      const trimmed = line.trim();
      // Filter out navigation and noise
      if (trimmed.length < 20) return false;
      if (trimmed.includes('Your browser is out of date')) return false;
      if (trimmed.includes('DuckDuckGo')) return false;
      if (trimmed.match(/^[\s\-\*\|]+$/)) return false;
      return true;
    });

    const cleaned = lines.join('\n\n').trim();
    return cleaned.length > 100 ? cleaned.slice(0, MAX_CHARS) : null;
  } catch {
    return null;
  }
}

/**
 * Alternative: Use DuckDuckGo Lite search via Jina
 */
async function searchViaDuckDuckGoLite(query: string): Promise<string | null> {
  try {
    const searchUrl = `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`;
    const res = await fetchWithTimeout(`https://r.jina.ai/${searchUrl}`, {
      headers: {
        Accept: "text/plain",
        "X-Return-Format": "text",
      },
    });
    if (!res.ok) return null;
    const text = await res.text();

    // DDG Lite is cleaner, parse results
    const lines = text.split('\n').filter(line => {
      const trimmed = line.trim();
      if (trimmed.length < 20) return false;
      // Remove noise
      if (trimmed.includes('DuckDuckGo')) return false;
      if (trimmed.includes('web images news')) return false;
      if (trimmed.match(/^[\d\.\s]+$/)) return false;
      return true;
    });

    const cleaned = lines.join('\n\n').trim();
    return cleaned.length > 100 ? cleaned.slice(0, MAX_CHARS) : null;
  } catch {
    return null;
  }
}

/**
 * Free search via Exa MCP (Model Context Protocol)
 * No API key required, rate limited.
 */
async function searchViaExaMcp(query: string): Promise<string | null> {
  try {
    const mcpRequest = {
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "web_search_exa",
        arguments: {
          query,
          numResults: 8,
        },
      },
    };
    const res = await fetchWithTimeout("https://mcp.exa.ai/mcp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(mcpRequest),
    });
    if (!res.ok) return null;
    const text = await res.text();
    // Response is streamed with "data: " lines
    const lines = text.split("\n");
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.result && data.result.content) {
            const content = data.result.content[0]?.text;
            if (content && content.length > 100) {
              return content.slice(0, MAX_CHARS);
            }
          }
        } catch {
          // ignore parse errors
        }
      }
    }
    return null;
  } catch {
    return null;
  }
}

// Provider mapping for custom selection
type ProviderFn = (query: string, keys: ProviderKeys) => Promise<string | null>;

const providerMap: Record<string, ProviderFn> = {
  exa_mcp: async (query, keys) => searchViaExaMcp(query),
  serper: async (query, keys) => {
    const key = keys.SERPER_API_KEY || process.env.SERPER_API_KEY;
    return key ? searchViaSerper(query, key) : null;
  },
  tavily: async (query, keys) => {
    const key = keys.TAVILY_API_KEY || process.env.TAVILY_API_KEY;
    return key ? searchViaTavily(query, key) : null;
  },
  duckduckgo: async (query, keys) => searchViaDuckDuckGoLite(query) || searchViaDuckDuckGoFree(query),
};

// Run providers sequentially until one succeeds
async function runProvidersSequential(
  query: string,
  keys: ProviderKeys,
  providerNames: string[]
): Promise<string> {
  for (const name of providerNames) {
    const fn = providerMap[name];
    if (!fn) continue;
    const result = await fn(query, keys);
    if (result) return result;
  }
  throw new Error("No search results found for query. Try adding API keys for better results.");
}

// Run multiple providers in parallel and concatenate results
async function runProvidersParallel(
  query: string,
  keys: ProviderKeys,
  providerNames: string[]
): Promise<string> {
  const results = await Promise.all(
    providerNames.map(async (name) => {
      const fn = providerMap[name];
      if (!fn) return null;
      try {
        return await fn(query, keys);
      } catch {
        return null;
      }
    })
  );
  const successful = results.filter((r): r is string => r !== null);
  if (successful.length === 0) {
    throw new Error("No search results found for query. Try adding API keys for better results.");
  }
  // Combine results with provider headers
  return successful
    .map((content, idx) => `## Results from ${providerNames[idx]}\n\n${content}`)
    .join("\n\n---\n\n");
}

async function resolveUrl(url: string, keys: ProviderKeys): Promise<string> {
  // URL cascade: Jina (free) → Firecrawl (paid) → Direct fetch (free)
  let result = await extractViaJina(url);
  if (result) return result;

  // Try Firecrawl if API key is available
  const firecrawlKey = keys.FIRECRAWL_API_KEY || process.env.FIRECRAWL_API_KEY;
  if (firecrawlKey) {
    result = await extractViaFirecrawl(url, firecrawlKey);
    if (result) return result;
  }

  result = await extractViaDirectFetch(url);
  if (result) return result;

  throw new Error("Failed to extract content from URL");
}

async function resolveQuery(query: string, keys: ProviderKeys): Promise<string> {
  // Query cascade: Exa MCP (free) → Serper → Tavily → DuckDuckGo (free)
  let result: string | null = null;

  // 1. Exa MCP (free, no API key required)
  result = await searchViaExaMcp(query);
  if (result) return result;

  // 2. Paid providers if keys are available
  const serperKey = keys.SERPER_API_KEY || process.env.SERPER_API_KEY;
  const tavilyKey = keys.TAVILY_API_KEY || process.env.TAVILY_API_KEY;

  if (serperKey) {
    result = await searchViaSerper(query, serperKey);
    if (result) return result;
  }

  if (tavilyKey) {
    result = await searchViaTavily(query, tavilyKey);
    if (result) return result;
  }

  // 3. Free fallback: DuckDuckGo via Jina Reader
  result = await searchViaDuckDuckGoLite(query);
  if (result) return result;

  result = await searchViaDuckDuckGoFree(query);
  if (result) return result;

  throw new Error("No search results found for query. Try adding API keys for better results.");
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const input = body.query?.trim() || body.url?.trim();

    if (!input) {
      return NextResponse.json(
        { error: "No query or URL provided" },
        { status: 400 }
      );
    }

    // Extract optional user-provided API keys from request body
    const userKeys: ProviderKeys = {
      SERPER_API_KEY: body.serper_api_key,
      TAVILY_API_KEY: body.tavily_api_key,
      EXA_API_KEY: body.exa_api_key,
      FIRECRAWL_API_KEY: body.firecrawl_api_key,
      MISTRAL_API_KEY: body.mistral_api_key,
    };

    const urlMode = isUrl(input);
    let markdown: string;
    if (urlMode) {
      markdown = await resolveUrl(input, userKeys);
    } else {
      // Query mode: check for provider selection and deep research
      const providers: string[] = body.providers || [];
      const deepResearch: boolean = body.deepResearch || false;
      
      if (providers.length === 0) {
        // Default cascade
        markdown = await resolveQuery(input, userKeys);
      } else if (deepResearch) {
        // Run selected providers in parallel
        markdown = await runProvidersParallel(input, userKeys, providers);
      } else {
        // Run selected providers sequentially in given order
        markdown = await runProvidersSequential(input, userKeys, providers);
      }
    }

    return NextResponse.json({ markdown });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Internal error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}