export interface ProviderResult {
  id: string;
  title: string;
  url?: string;
  normalizedUrl?: string;
  author?: string;
  published?: string;
  snippet: string;
  raw: string;
}

const SPLIT_REGEX = /\n-{3,}\n+/g;
const PLACEHOLDER_VALUES = new Set(["n/a", "na", "unknown", "none", "-", "–", ""]);

const sanitizeMeta = (value: string | undefined): string | undefined => {
  if (!value) return undefined;
  const trimmed = value.trim();
  return PLACEHOLDER_VALUES.has(trimmed.toLowerCase()) ? undefined : trimmed || undefined;
};

const extractFirstUrlCandidate = (input: string): string | undefined => {
  const urlMatch = input.match(/https?:\/\/[^)\s]+/u);
  if (urlMatch) return urlMatch[0];
  const trimmed = input.trim();
  return trimmed.startsWith("http") ? trimmed : undefined;
};

const canonicalizeUrl = (raw?: string): string | undefined => {
  if (!raw) return undefined;
  const candidate = extractFirstUrlCandidate(raw)?.trim();
  if (!candidate) return undefined;
  const normalizedCandidate = candidate.replace(/https?:\/([^/])/g, (match) => match.replace(/:\//, "://"));
  try {
    const url = new URL(normalizedCandidate);
    if (url.hostname === "nextjs.org") {
      url.pathname = url.pathname.replace("/docs/llm-digest", "/docs");
    }
    url.hash = "";
    return url.toString();
  } catch {
    return normalizedCandidate;
  }
};

const normalizeSnippet = (lines: string[]): string => {
  return lines
    .map((line) => line.trim())
    .filter(Boolean)
    .join("\n")
    .trim();
};

interface ParsedBlockMeta {
  title?: string;
  url?: string;
  author?: string;
  published?: string;
  snippetLines: string[];
  hasHighlights: boolean;
}

const parseFieldLine = (line: string, lower: string): Record<string, string | undefined> | null => {
  if (lower.startsWith("title:")) return { title: line.split(/title:/iu)[1]?.trim() };
  if (lower.startsWith("url:")) return { url: line.split(/url:/iu)[1]?.trim() };
  if (lower.startsWith("author:")) return { author: sanitizeMeta(line.split(/author:/iu)[1]) };
  if (lower.startsWith("published:")) return { published: sanitizeMeta(line.split(/published:/iu)[1]) };
  return null;
};

const processHighlightsLine = (line: string, meta: ParsedBlockMeta): boolean => {
  const lower = line.toLowerCase();
  if (!lower.startsWith("highlights:")) return false;

  meta.hasHighlights = true;
  const content = line.split(/highlights:/iu)[1]?.trim();
  if (content) meta.snippetLines.push(content);
  return true;
};

const parseBlockMetadata = (lines: string[]): ParsedBlockMeta => {
  const meta: ParsedBlockMeta = { snippetLines: [], hasHighlights: false };
  let inHighlights = false;

  for (const line of lines) {
    const lower = line.toLowerCase();

    if (!inHighlights && processHighlightsLine(line, meta)) {
      inHighlights = true;
    } else if (inHighlights) {
      meta.snippetLines.push(line);
    } else {
      const field = parseFieldLine(line, lower);
      if (field) Object.assign(meta, field);
    }
  }

  return meta;
};

const buildResultId = (index: number, title?: string, url?: string): string => {
  const base = title || url || Math.random().toString(36).slice(2);
  return `${index}-${base}`;
};

const withOptionalProps = (
  result: ProviderResult,
  meta: ParsedBlockMeta,
  normalizedUrl: string | undefined,
): ProviderResult => {
  const { url, author, published } = meta;
  if (url !== undefined) result.url = url;
  if (normalizedUrl !== undefined) result.normalizedUrl = normalizedUrl;
  if (author !== undefined) result.author = author;
  if (published !== undefined) result.published = published;
  return result;
};

const buildProviderResult = (
  meta: ParsedBlockMeta,
  index: number,
  block: string,
  snippetSource: string[],
): ProviderResult | null => {
  const snippet = normalizeSnippet(snippetSource);
  if (!meta.title && !snippet) return null;

  const normalizedUrl = canonicalizeUrl(meta.url);
  const result: ProviderResult = {
    id: buildResultId(index, meta.title, meta.url),
    title: meta.title || "Untitled Result",
    snippet: snippet || block.trim(),
    raw: block.trim(),
  };

  return withOptionalProps(result, meta, normalizedUrl);
};

const parseBlock = (block: string, index: number): ProviderResult | null => {
  const lines = block.trim().split(/\n+/);
  if (lines.length === 0) return null;
  const meta = parseBlockMetadata(lines);
  const snippetSource = meta.hasHighlights ? meta.snippetLines : lines.slice(1);
  return buildProviderResult(meta, index, block, snippetSource);
};

export const dedupeResults = (results: ProviderResult[]): ProviderResult[] => {
  const seen = new Map<string, ProviderResult>();
  for (const result of results) {
    const key = (result.normalizedUrl || result.title || result.raw).toLowerCase();
    if (!seen.has(key)) {
      seen.set(key, result);
    }
  }
  return Array.from(seen.values());
};

export const parseProviderResults = (markdown: string): ProviderResult[] => {
  if (!markdown) return [];
  const blocks = markdown.split(SPLIT_REGEX).map((block) => block.trim()).filter(Boolean);
  const parsed: ProviderResult[] = [];
  blocks.forEach((block, index) => {
    const result = parseBlock(block, index);
    if (result) parsed.push(result);
  });
  return dedupeResults(parsed);
};

export const extractNormalizedUrls = (results: ProviderResult[]): string[] => {
  return Array.from(new Set(results.map((r) => r.normalizedUrl).filter(Boolean))) as string[];
};
