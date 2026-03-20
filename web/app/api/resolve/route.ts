import { NextRequest, NextResponse } from "next/server";

const PROVIDERS = {
  EXA_API_KEY: process.env.EXA_API_KEY,
  TAVILY_API_KEY: process.env.TAVILY_API_KEY,
  SERPER_API_KEY: process.env.SERPER_API_KEY,
  FIRECRAWL_API_KEY: process.env.FIRECRAWL_API_KEY,
  MISTRAL_API_KEY: process.env.MISTRAL_API_KEY,
};

const MAX_CHARS = parseInt(process.env.WEB_RESOLVER_MAX_CHARS || "8000");

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
    return text.length > 200 ? text.slice(0, MAX_CHARS) : null;
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
    return text.length > 200 ? text.slice(0, MAX_CHARS) : null;
  } catch {
    return null;
  }
}

async function searchViaSerper(query: string): Promise<string | null> {
  if (!PROVIDERS.SERPER_API_KEY) return null;
  try {
    const res = await fetchWithTimeout(
      "https://google.serper.dev/search",
      {
        method: "POST",
        headers: {
          "X-API-KEY": PROVIDERS.SERPER_API_KEY,
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

async function searchViaTavily(query: string): Promise<string | null> {
  if (!PROVIDERS.TAVILY_API_KEY) return null;
  try {
    const res = await fetchWithTimeout("https://api.tavily.com/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: PROVIDERS.TAVILY_API_KEY,
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

async function searchViaDuckDuckGo(query: string): Promise<string | null> {
  try {
    const res = await fetchWithTimeout(
      `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_html=1&skip_disambig=1`,
      {}
    );
    if (!res.ok) return null;
    const data = await res.json();
    const parts = [
      data.AbstractText,
      ...(data.RelatedTopics || [])
        .slice(0, 5)
        .map((t: { Text?: string }) => t.Text)
        .filter(Boolean),
    ].filter(Boolean);
    const text = parts.join("\n\n");
    return text.length > 100 ? text.slice(0, MAX_CHARS) : null;
  } catch {
    return null;
  }
}

async function resolveUrl(url: string): Promise<string> {
  // URL cascade: Jina (free) → Direct fetch (free)
  let result = await extractViaJina(url);
  if (result) return result;

  result = await extractViaDirectFetch(url);
  if (result) return result;

  throw new Error("Failed to extract content from URL");
}

async function resolveQuery(query: string): Promise<string> {
  // Query cascade: Serper → Tavily → DuckDuckGo
  let result = await searchViaSerper(query);
  if (result) return result;

  result = await searchViaTavily(query);
  if (result) return result;

  result = await searchViaDuckDuckGo(query);
  if (result) return result;

  throw new Error("No search results found for query");
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

    const urlMode = isUrl(input);
    const markdown = urlMode
      ? await resolveUrl(input)
      : await resolveQuery(input);

    return NextResponse.json({ markdown });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Internal error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
