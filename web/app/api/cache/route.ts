import { NextRequest, NextResponse } from "next/server";
import { stats, clear } from "@/lib/cache";
import { SESSION_COOKIE, applySessionCookie, resolveSession, verifySessionToken } from "@/lib/session";

/**
 * The cache is process-local shared state, so clearing it affects every user
 * served by this instance. DELETE therefore requires a verified, server-signed
 * session (see lib/session) — not mere cookie presence.
 */
export async function GET() {
  return NextResponse.json(stats());
}

export async function DELETE(request: NextRequest) {
  const verified = verifySessionToken(request.cookies.get(SESSION_COOKIE)?.value);
  if (!verified) {
    return NextResponse.json(
      { error: "Verified session required to clear cache" },
      { status: 401 }
    );
  }

  const session = resolveSession(request);
  clear();
  return applySessionCookie(NextResponse.json({ ok: true }), session);
}
