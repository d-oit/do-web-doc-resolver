import { NextRequest, NextResponse } from "next/server";
import { stats, clear } from "@/lib/cache";

/**
 * The cache is process-local shared state, so clearing it affects every user
 * served by this instance.
 *
 * The session-cookie check below stops an anonymous `curl -X DELETE`, which is
 * the realistic abuse. It is not authorization: the cookie is client-supplied
 * and unverified, so anyone can obtain one by calling any endpoint. The same
 * caveat and the follow-up (sign the value server-side) are documented on
 * `hasSessionCookie` in app/api/records/route.ts.
 */
export async function GET() {
  return NextResponse.json(stats());
}

export async function DELETE(request: NextRequest) {
  if (!request.cookies.get("ui-session")?.value) {
    return NextResponse.json(
      { error: "Session required to clear cache" },
      { status: 401 }
    );
  }

  clear();
  return NextResponse.json({ ok: true });
}
