import { NextRequest, NextResponse } from "next/server";
import { stats, clear } from "@/lib/cache";
import { applySessionCookie, resolveSession } from "@/lib/session";

/**
 * The cache is process-local shared state, so clearing it affects every user
 * served by this instance. DELETE therefore requires a verified, server-signed
 * session (see lib/session) — not mere cookie presence.
 */
export async function GET() {
  return NextResponse.json(stats());
}

export async function DELETE(request: NextRequest) {
  const session = resolveSession(request);

  clear();
  return applySessionCookie(NextResponse.json({ ok: true }), session);
}
