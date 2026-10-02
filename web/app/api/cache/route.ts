import { NextRequest, NextResponse } from "next/server";
import { stats, clear } from "@/lib/cache";

/**
 * The cache is process-local shared state, so clearing it affects every user
 * served by this instance. Require the caller's own session so a random
 * client cannot wipe it.
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