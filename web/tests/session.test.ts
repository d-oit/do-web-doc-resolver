import { describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";
import {
  SESSION_COOKIE,
  SESSION_TTL_SECONDS,
  applySessionCookie,
  createSessionToken,
  resolveSession,
  sessionCookieOptions,
  verifySessionToken,
} from "../lib/session";

function requestWithCookie(cookie: string | undefined): NextRequest {
  const headers: Record<string, string> = {};
  if (cookie !== undefined) headers.cookie = cookie;
  return new NextRequest("http://localhost/api/records", { headers });
}

describe("session tokens", () => {
  it("creates a signed token that verifies to its session id", () => {
    const { token, sessionId, expiresAt } = createSessionToken();

    const verified = verifySessionToken(token);
    expect(verified).toEqual({ sessionId, expired: false });
    expect(expiresAt).toBeGreaterThan(Date.now());
    expect(token).toMatch(/^v1\./);
  });

  it("rejects forged signatures", () => {
    const { token } = createSessionToken();
    const forged = token.slice(0, -4) + "AAAA";

    expect(verifySessionToken(forged)).toBeNull();
  });

  it("rejects a signature minted for a different session id", () => {
    const { token } = createSessionToken();
    const [, , expiresAt, signature] = token.split(".");
    const stolen = `v1.attacker-session.${expiresAt}.${signature}`;

    expect(verifySessionToken(stolen)).toBeNull();
  });

  it("rejects malformed tokens", () => {
    const { token } = createSessionToken();

    expect(verifySessionToken(undefined)).toBeNull();
    expect(verifySessionToken("")).toBeNull();
    expect(verifySessionToken("not-a-token")).toBeNull();
    expect(verifySessionToken(`v2.${token.slice(3)}`)).toBeNull();
    expect(verifySessionToken(`v1.abc.${token.split(".")[2]}`)).toBeNull();
    expect(verifySessionToken("v1.abc.notanumber.c2ln")).toBeNull();
  });

  it("detects expired tokens", () => {
    const { token, sessionId } = createSessionToken();

    vi.useFakeTimers();
    try {
      vi.setSystemTime(Date.now() + SESSION_TTL_SECONDS * 1000 + 1000);
      expect(verifySessionToken(token)).toEqual({
        sessionId,
        expired: true,
      });
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("resolveSession", () => {
  it("mints a new session when no cookie is present", () => {
    const session = resolveSession(requestWithCookie(undefined));

    expect(session.rotated).toBe(true);
    expect(verifySessionToken(session.token)?.sessionId).toBe(session.sessionId);
  });

  it("keeps the session id for a valid cookie without rotating", () => {
    const { token, sessionId } = createSessionToken();
    const session = resolveSession(requestWithCookie(`${SESSION_COOKIE}=${token}`));

    expect(session).toEqual({ sessionId, token, rotated: false });
  });

  it("rotates the token but keeps the id for an expired cookie", () => {
    const { token, sessionId } = createSessionToken();

    vi.useFakeTimers();
    try {
      vi.setSystemTime(Date.now() + SESSION_TTL_SECONDS * 1000 + 1000);

      const session = resolveSession(requestWithCookie(`${SESSION_COOKIE}=${token}`));

      expect(session.rotated).toBe(true);
      expect(session.sessionId).toBe(sessionId);
      expect(verifySessionToken(session.token)).toEqual({ sessionId, expired: false });
    } finally {
      vi.useRealTimers();
    }
  });

  it("gives a forged cookie a fresh unrelated session", () => {
    const { sessionId: legitId } = createSessionToken();
    const session = resolveSession(requestWithCookie(`${SESSION_COOKIE}=${legitId}.tampered`));

    expect(session.sessionId).not.toBe(legitId);
    expect(session.rotated).toBe(true);
    expect(verifySessionToken(session.token)?.sessionId).toBe(session.sessionId);
  });

  it("never echoes a client-chosen identifier", () => {
    const session = resolveSession(requestWithCookie(`${SESSION_COOKIE}=totally-controlled`));

    expect(session.sessionId).not.toBe("totally-controlled");
  });
});

describe("session cookie attributes", () => {
  it("sets HttpOnly, SameSite=Lax, path and bounded max-age", () => {
    expect(sessionCookieOptions()).toMatchObject({
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: SESSION_TTL_SECONDS,
    });
  });

  it("marks the cookie Secure in production", () => {
    vi.stubEnv("NODE_ENV", "production");
    try {
      expect(sessionCookieOptions().secure).toBe(true);
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("omits Secure outside production", () => {
    vi.stubEnv("NODE_ENV", "development");
    try {
      expect(sessionCookieOptions().secure).toBe(false);
    } finally {
      vi.unstubAllEnvs();
    }
  });
});

describe("applySessionCookie", () => {
  it("sets the cookie on the response when rotated", () => {
    const session = resolveSession(requestWithCookie(undefined));
    const response = applySessionCookie(NextResponse.json({}), session);

    const setCookie = response.cookies.get(SESSION_COOKIE);
    expect(setCookie).toBeDefined();
    expect(setCookie?.value).toBe(session.token);
    expect(setCookie?.httpOnly).toBe(true);
  });

  it("leaves the response untouched for an unrotated session", () => {
    const { token, sessionId } = createSessionToken();
    const session = resolveSession(requestWithCookie(`${SESSION_COOKIE}=${token}`));
    const response = applySessionCookie(NextResponse.json({}), session);

    expect(response.cookies.get(SESSION_COOKIE)).toBeUndefined();
    expect(session.sessionId).toBe(sessionId);
  });
});
