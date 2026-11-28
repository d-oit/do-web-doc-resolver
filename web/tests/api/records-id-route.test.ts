import { beforeEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { DELETE, GET } from "../../app/api/records/[id]/route";
import { clear, get, save } from "../../lib/records";
import { createSessionToken, SESSION_COOKIE } from "../../lib/session";

function requestWithCookie(token: string, method: "GET" | "DELETE"): NextRequest {
  return new NextRequest("http://localhost/api/records/record-id", {
    method,
    headers: { cookie: `${SESSION_COOKIE}=${token}` },
  });
}

function routeContext(id: string): { params: Promise<{ id: string }> } {
  return { params: Promise.resolve({ id }) };
}

describe("/api/records/[id] route", () => {
  const { token, sessionId: owner } = createSessionToken();

  beforeEach(() => {
    clear(owner);
  });

  it("returns a record to its owning session", async () => {
    const record = save(owner, { query: "q", url: null, content: "c", source: "test", score: 0 });

    const response = await GET(requestWithCookie(token, "GET"), routeContext(record.id));

    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({ id: record.id });
  });

  it("hides another session's record with 404", async () => {
    const record = save(owner, { query: "q", url: null, content: "secret", source: "test", score: 0 });

    const { token: attackerToken } = createSessionToken();
    const response = await GET(requestWithCookie(attackerToken, "GET"), routeContext(record.id));

    expect(response.status).toBe(404);
  });

  it("refuses to delete another session's record", async () => {
    const record = save(owner, { query: "q", url: null, content: "c", source: "test", score: 0 });

    const { token: attackerToken } = createSessionToken();
    const response = await DELETE(requestWithCookie(attackerToken, "DELETE"), routeContext(record.id));

    expect(response.status).toBe(404);
    expect(get(owner, record.id)).toBeDefined();
  });

  it("deletes the owner's record", async () => {
    const record = save(owner, { query: "q", url: null, content: "c", source: "test", score: 0 });

    const response = await DELETE(requestWithCookie(token, "DELETE"), routeContext(record.id));

    expect(response.status).toBe(200);
    expect(get(owner, record.id)).toBeUndefined();
  });
});
