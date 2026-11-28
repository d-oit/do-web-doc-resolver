import { describe, expect, it, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("../../lib/records", () => ({
  save: vi.fn().mockReturnValue({ id: "rec-1" }),
  list: vi.fn().mockReturnValue([]),
  search: vi.fn().mockReturnValue([]),
  clear: vi.fn().mockReturnValue(3),
}));

import { DELETE, GET, POST } from "../../app/api/records/route";
import { MAX_BODY_BYTES } from "../../lib/body-limit";
import * as records from "../../lib/records";
import { createSessionToken, SESSION_COOKIE, verifySessionToken } from "../../lib/session";

/** Build a POST request with a JSON body. */
function postRequest(body: unknown, headers: Record<string, string> = {}): NextRequest {
  return new NextRequest("http://localhost/api/records", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

/** Build a request carrying a valid signed session cookie. */
function withSession(method = "DELETE"): { request: NextRequest; sessionId: string } {
  const { token, sessionId } = createSessionToken();
  const request = new NextRequest("http://localhost/api/records", {
    method,
    headers: { cookie: `${SESSION_COOKIE}=${token}` },
  });
  return { request, sessionId };
}

describe("/api/records route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(records.clear).mockReturnValue(3);
  });

  it("partitions GET by the verified session and issues a cookie when absent", async () => {
    const response = await GET(new NextRequest("http://localhost/api/records"));

    expect(response.status).toBe(200);
    expect(records.list).toHaveBeenCalledTimes(1);
    const call = vi.mocked(records.list).mock.calls[0];
    expect(call).toBeDefined();
    const sessionId = call?.[0];

    const setCookie = response.cookies.get(SESSION_COOKIE);
    expect(setCookie).toBeDefined();
    expect(setCookie?.httpOnly).toBe(true);
    expect(verifySessionToken(setCookie?.value)?.sessionId).toBe(sessionId);
  });

  it("searches inside the caller's session only", async () => {
    const { request, sessionId } = withSession("GET");

    await GET(new NextRequest(new URL("http://localhost/api/records?q=secret").toString(), {
      headers: { cookie: request.headers.get("cookie") || "" },
    }));

    expect(records.search).toHaveBeenCalledWith(sessionId, "secret", 50);
    expect(records.list).not.toHaveBeenCalled();
  });

  it("gives a forged cookie a fresh empty session, not the original partition", async () => {
    const { sessionId: legitId } = createSessionToken();
    const response = await GET(
      new NextRequest("http://localhost/api/records", {
        headers: { cookie: `${SESSION_COOKIE}=${legitId}.tampered` },
      })
    );

    expect(response.status).toBe(200);
    const call = vi.mocked(records.list).mock.calls[0];
    expect(call).toBeDefined();
    expect(call?.[0]).not.toBe(legitId);
    expect(response.cookies.get(SESSION_COOKIE)).toBeDefined();
  });

  it("rejects a payload with no query or url", async () => {
    const response = await POST(postRequest({ content: "orphan" }));

    expect(response.status).toBe(400);
    expect(records.save).not.toHaveBeenCalled();
  });

  it("rejects an oversized content field", async () => {
    const response = await POST(
      postRequest({
        query: "example",
        content: "x".repeat(200_001),
      })
    );

    expect(response.status).toBe(400);
    expect(records.save).not.toHaveBeenCalled();
  });

  it("rejects an out-of-range score", async () => {
    const response = await POST(postRequest({ query: "example", score: 42 }));

    expect(response.status).toBe(400);
    expect(records.save).not.toHaveBeenCalled();
  });

  it("accepts a valid record into the caller's session", async () => {
    const { request, sessionId } = withSession("POST");
    const response = await POST(
      new NextRequest("http://localhost/api/records", {
        method: "POST",
        headers: { "content-type": "application/json", cookie: request.headers.get("cookie") || "" },
        body: JSON.stringify({ query: "example", content: "ok", score: 0.8 }),
      })
    );

    expect(response.status).toBe(201);
    expect(records.save).toHaveBeenCalledWith(sessionId, {
      query: "example",
      url: null,
      content: "ok",
      source: "manual",
      score: 0.8,
    });
  });

  it("clamps the GET limit parameter", async () => {
    await GET(new NextRequest("http://localhost/api/records?limit=99999"));

    expect(records.list).toHaveBeenCalledWith(expect.any(String), 200);
  });

  it("clears only the caller's session partition", async () => {
    const { request, sessionId } = withSession();

    const response = await DELETE(request);

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ deleted: 3 });
    expect(records.clear).toHaveBeenCalledWith(sessionId);
  });

  it("rejects an oversized body via Content-Length before reading it", async () => {
    const response = await POST(
      postRequest(
        { query: "example", content: "ok" },
        { "content-length": String(MAX_BODY_BYTES + 1) }
      )
    );

    expect(response.status).toBe(413);
    expect(records.save).not.toHaveBeenCalled();
  });

  it("rejects an oversized body sent without Content-Length", async () => {
    // A chunked request omits the header, so the stream has to be counted as it
    // is consumed. Without that, the cap would only bind honest clients.
    const response = await POST(postRequest({ query: "example", content: "x".repeat(MAX_BODY_BYTES + 64) }));

    expect(response.status).toBe(413);
    expect(records.save).not.toHaveBeenCalled();
  });

  it("accepts a body just under the cap", async () => {
    const response = await POST(
      postRequest({ query: "example", content: "x".repeat(200_000) })
    );

    expect(response.status).toBe(201);
  });
});
