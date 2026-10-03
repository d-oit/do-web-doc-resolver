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

/** Build a POST request with a JSON body. */
function postRequest(body: unknown, headers: Record<string, string> = {}): NextRequest {
  return new NextRequest("http://localhost/api/records", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

describe("/api/records route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(records.clear).mockReturnValue(3);
  });

  it("rejects DELETE without a session cookie", async () => {
    const response = await DELETE(
      new NextRequest("http://localhost/api/records", { method: "DELETE" })
    );

    expect(response.status).toBe(401);
    expect(records.clear).not.toHaveBeenCalled();
  });

  it("allows DELETE with a session cookie", async () => {
    const response = await DELETE(withCookie());

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ deleted: 3 });
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

  it("accepts a valid record", async () => {
    const response = await POST(
      postRequest({ query: "example", content: "ok", score: 0.8 })
    );

    expect(response.status).toBe(201);
    expect(records.save).toHaveBeenCalledWith({
      query: "example",
      url: null,
      content: "ok",
      source: "manual",
      score: 0.8,
    });
  });

  it("clamps the GET limit parameter", async () => {
    await GET(new NextRequest("http://localhost/api/records?limit=99999"));

    expect(records.list).toHaveBeenCalledWith(200);
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

/** Build a DELETE request carrying a session cookie. */
function withCookie(): NextRequest {
  return new NextRequest("http://localhost/api/records", {
    method: "DELETE",
    headers: { cookie: "ui-session=sess-1" },
  });
}
