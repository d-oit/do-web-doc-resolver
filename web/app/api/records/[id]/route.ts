import { NextRequest, NextResponse } from "next/server";
import { get, remove } from "@/lib/records";
import { applySessionCookie, resolveSession } from "@/lib/session";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = resolveSession(request);
  const { id } = await params;
  const record = get(session.sessionId, id);
  if (!record) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  return applySessionCookie(NextResponse.json(record), session);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = resolveSession(request);
  const { id } = await params;
  const existed = remove(session.sessionId, id);
  if (!existed) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  return applySessionCookie(NextResponse.json({ deleted: true }), session);
}
