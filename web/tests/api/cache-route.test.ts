import { describe, expect, it, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("../../lib/cache", () => ({
  stats: vi.fn().mockReturnValue({ entries: 0 }),
  clear: vi.fn(),
}));

import { DELETE, GET } from "../../app/api/cache/route";
import * as cache from "../../lib/cache";
import { createSessionToken, SESSION_COOKIE, verifySessionToken } from "../../lib/session";

describe("/api/cache route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exposes cache stats without a session", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    expect(cache.stats).toHaveBeenCalledTimes(1);
  });

  it("clears the cache for a verified session", async () => {
    const { token } = createSessionToken();
    const request = new NextRequest("http://localhost/api/cache", {
      method: "DELETE",
      headers: { cookie: `${SESSION_COOKIE}=${token}` },
    });

    const response = await DELETE(request);

    expect(response.status).toBe(200);
    expect(cache.clear).toHaveBeenCalledTimes(1);

    const setCookie = response.cookies.get(SESSION_COOKIE);
    expect(setCookie).toBeDefined();
    expect(verifySessionToken(setCookie?.value)).not.toBeNull();
  });

  it("rejects an anonymous DELETE with 401", async () => {
    const request = new NextRequest("http://localhost/api/cache", {
      method: "DELETE",
    });

    const response = await DELETE(request);

    expect(response.status).toBe(401);
    expect(cache.clear).not.toHaveBeenCalled();
  });

  it("rejects a forged-cookie DELETE with 401", async () => {
    const { sessionId } = createSessionToken();
    const request = new NextRequest("http://localhost/api/cache", {
      method: "DELETE",
      headers: { cookie: `${SESSION_COOKIE}=${sessionId}.tampered` },
    });

    const response = await DELETE(request);

    expect(response.status).toBe(401);
    expect(cache.clear).not.toHaveBeenCalled();
    expect(response.cookies.get(SESSION_COOKIE)).toBeUndefined();
  });
});
