import { NextRequest, NextResponse } from "next/server";
import { BodyTooLargeError, readJsonWithLimit } from "@/lib/body-limit";

// In-memory store for local development (will be replaced with Vercel KV in production)
const memoryHistory = new Map<string, HistoryEntry[]>();

interface HistoryEntry {
  id: string;
  query: string;
  url: string | null;
  result: string;
  provider: string;
  timestamp: number;
  charCount: number;
  resolveTime: number;
  profile?: string;
  flags?: {
    skipCache?: boolean;
    deepResearch?: boolean;
  };
  providers?: string[];
  normalizedUrlHashes?: string[];
}

const MAX_HISTORY = 100;
const TTL_MS = 90 * 24 * 60 * 60 * 1000; // 90 days

function getSessionId(request: NextRequest): string {
  const existing = request.cookies.get("ui-session")?.value;
  if (existing) return existing;
  return crypto.randomUUID();
}

// GET /api/history - List history entries
export async function GET(request: NextRequest) {
  const sessionId = getSessionId(request);
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get("limit") || "50");
  const query = searchParams.get("q");

  let entries = memoryHistory.get(sessionId) || [];

  // Filter out expired entries
  const now = Date.now();
  entries = entries.filter((e) => now - e.timestamp < TTL_MS);

  // Optional search filter
  if (query) {
    const q = query.toLowerCase();
    entries = entries.filter(
      (e) =>
        e.query.toLowerCase().includes(q) ||
        (e.result && e.result.toLowerCase().includes(q))
    );
  }

  const response = NextResponse.json({
    entries: entries.slice(0, limit),
  });

  // Set cookie if not already set
  if (!request.cookies.get("ui-session")?.value) {
    response.cookies.set("ui-session", sessionId, {
      httpOnly: true,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 365,
      path: "/",
    });
  }

  return response;
}

function normalizeHashes(input: unknown): string[] {
  if (!Array.isArray(input)) return [];
  const values = input
    .filter((value) => typeof value === "string")
    .map((value: string) => value.trim())
    .filter(Boolean);
  return Array.from(new Set(values));
}

function hasOverlap(a: string[] = [], b: string[] = []): boolean {
  if (a.length === 0 || b.length === 0) return false;
  const set = new Set(a);
  return b.some((hash) => set.has(hash));
}

// POST /api/history - Save new history entry
export async function POST(request: NextRequest) {
  const sessionId = getSessionId(request);

  let body: unknown;
  try {
    body = await readJsonWithLimit(request);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return NextResponse.json(
        { error: `Request body exceeds ${error.limit} bytes` },
        { status: 413 }
      );
    }
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  try {
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
    }
    const bodyRecord = body as Record<string, unknown>;
    const id = crypto.randomUUID();
    const normalizedUrlHashes = normalizeHashes(bodyRecord.normalizedUrlHashes);
    const flagsObj = (bodyRecord.flags && typeof bodyRecord.flags === "object")
      ? bodyRecord.flags as Record<string, unknown>
      : null;
    const flags: HistoryEntry["flags"] | undefined = flagsObj
      ? {
          ...(typeof flagsObj.skipCache === "boolean" ? { skipCache: flagsObj.skipCache } : {}),
          ...(typeof flagsObj.deepResearch === "boolean" ? { deepResearch: flagsObj.deepResearch } : {}),
        }
      : undefined;

    const entry: HistoryEntry = {
      id,
      query: typeof bodyRecord.query === "string" ? bodyRecord.query : "",
      url: typeof bodyRecord.url === "string" ? bodyRecord.url : null,
      result: typeof bodyRecord.result === "string" ? bodyRecord.result : "",
      provider: typeof bodyRecord.provider === "string" ? bodyRecord.provider : "unknown",
      timestamp: Date.now(),
      charCount: typeof bodyRecord.charCount === "number" ? bodyRecord.charCount : 0,
      resolveTime: typeof bodyRecord.resolveTime === "number" ? bodyRecord.resolveTime : 0,
      ...(typeof bodyRecord.profile === "string" ? { profile: bodyRecord.profile } : {}),
      ...(flags ? { flags } : {}),
      ...(Array.isArray(bodyRecord.providers) ? { providers: bodyRecord.providers.filter((p): p is string => typeof p === "string") } : {}),
      normalizedUrlHashes,
    };

    // Get or create history list
    let entries = memoryHistory.get(sessionId) || [];

    // Remove duplicates that target the same set of URLs
    if (normalizedUrlHashes.length > 0) {
      entries = entries.filter((existing) => !hasOverlap(existing.normalizedUrlHashes, normalizedUrlHashes));
    }

    // Add to front
    entries.unshift(entry);

    // Limit to MAX_HISTORY
    if (entries.length > MAX_HISTORY) {
      entries = entries.slice(0, MAX_HISTORY);
    }

    memoryHistory.set(sessionId, entries);

    const response = NextResponse.json({ ok: true, id });

    // Set cookie if not already set
    if (!request.cookies.get("ui-session")?.value) {
      response.cookies.set("ui-session", sessionId, {
        httpOnly: true,
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 365,
        path: "/",
      });
    }

    return response;
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

// DELETE /api/history?id=xxx - Delete specific entry
export async function DELETE(request: NextRequest) {
  const sessionId = getSessionId(request);
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return NextResponse.json({ error: "Missing id" }, { status: 400 });
  }

  const entries = memoryHistory.get(sessionId) || [];
  const filtered = entries.filter((e) => e.id !== id);
  memoryHistory.set(sessionId, filtered);

  return NextResponse.json({ ok: true });
}
