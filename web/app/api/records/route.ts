import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { save, list, clear, search } from "@/lib/records";
import { BodyTooLargeError, readJsonWithLimit } from "@/lib/body-limit";
import { applySessionCookie, resolveSession } from "@/lib/session";

export async function GET(request: NextRequest) {
  const session = resolveSession(request);
  const { searchParams } = new URL(request.url);
  const rawLimit = parseInt(searchParams.get("limit") || "50", 10);
  const limit = Number.isFinite(rawLimit) ? Math.min(Math.max(rawLimit, 1), 200) : 50;
  const q = searchParams.get("q");

  const records = q ? search(session.sessionId, q, limit) : list(session.sessionId, limit);
  return applySessionCookie(NextResponse.json({ records }), session);
}

const RecordSchema = z.object({
  query: z.string().min(1).max(2000).optional(),
  url: z.string().max(2000).nullable().optional(),
  content: z.string().max(200_000).optional(),
  source: z.string().max(200).optional(),
  score: z.number().min(0).max(1).optional(),
});

export async function POST(request: NextRequest) {
  const session = resolveSession(request);

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

  const record = save(
    session.sessionId,
    {
      query: parsed.data.query || parsed.data.url || "",
      url: parsed.data.url ?? null,
      content: parsed.data.content || "",
      source: parsed.data.source || "manual",
      score: parsed.data.score ?? 0,
    }
  );
  return applySessionCookie(NextResponse.json(record, { status: 201 }), session);
}

export async function DELETE(request: NextRequest) {
  const session = resolveSession(request);

  const count = clear(session.sessionId);
  return applySessionCookie(NextResponse.json({ deleted: count }), session);
}
