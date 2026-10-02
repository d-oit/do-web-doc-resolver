import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { save, list, clear, search } from "@/lib/records";

/**
 * Destructive record operations are scoped to the caller's own session.
 *
 * The store is process-local, so without this check any client could DELETE the
 * entire record set (and POST unbounded `content` strings into it). The
 * identifier matches the one used by /api/history.
 */
function isOwnedSession(request: NextRequest): boolean {
  return Boolean(request.cookies.get("ui-session")?.value);
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const rawLimit = parseInt(searchParams.get("limit") || "50", 10);
  const limit = Number.isFinite(rawLimit) ? Math.min(Math.max(rawLimit, 1), 200) : 50;
  const q = searchParams.get("q");

  const records = q ? search(q, limit) : list(limit);
  return NextResponse.json({ records });
}

const RecordSchema = z.object({
  query: z.string().min(1).max(2000).optional(),
  url: z.string().max(2000).nullable().optional(),
  content: z.string().max(200_000).optional(),
  source: z.string().max(200).optional(),
  score: z.number().min(0).max(1).optional(),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = RecordSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: "Invalid record payload", details: parsed.error.issues },
        { status: 400 }
      );
    }

    if (!parsed.data.query && !parsed.data.url) {
      return NextResponse.json(
        { error: "query or url required" },
        { status: 400 }
      );
    }

    const record = save({
      query: parsed.data.query || parsed.data.url || "",
      url: parsed.data.url ?? null,
      content: parsed.data.content || "",
      source: parsed.data.source || "manual",
      score: parsed.data.score ?? 0,
    });
    return NextResponse.json(record, { status: 201 });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

export async function DELETE(request: NextRequest) {
  if (!isOwnedSession(request)) {
    return NextResponse.json(
      { error: "Session required to clear records" },
      { status: 401 }
    );
  }

  const count = clear();
  return NextResponse.json({ deleted: count });
}