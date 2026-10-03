import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { save, list, clear, search } from "@/lib/records";
import { BodyTooLargeError, readJsonWithLimit } from "@/lib/body-limit";

/**
 * Whether the caller presented a session cookie.
 *
 * This is a speed bump against anonymous `curl`, not authorization: the cookie
 * value is client-supplied and unverified, so anyone can mint one by calling any
 * endpoint. Making it a real access check means signing the value server-side —
 * see agents-docs/ISSUES.md.
 *
 * Note the asymmetry it leaves behind: the store in `lib/records.ts` is a single
 * process-global map with no per-session partitioning, so `GET` still returns
 * every user's records and `GET ?q=` searches across them. Partitioning the
 * store is a schema change and is deliberately out of scope here.
 */
function hasSessionCookie(request: NextRequest): boolean {
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
  let body: unknown;

  try {
    // Bounded before parsing: the per-field caps below only bound what is
    // stored, not what the client can make this handler allocate.
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
}

export async function DELETE(request: NextRequest) {
  if (!hasSessionCookie(request)) {
    return NextResponse.json(
      { error: "Session required to clear records" },
      { status: 401 }
    );
  }

  const count = clear();
  return NextResponse.json({ deleted: count });
}
