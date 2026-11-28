import { NextRequest, NextResponse } from "next/server";
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

/**
 * Anonymous per-browser session identity.
 *
 * There is no identity provider: a session is a random id bound to an
 * HMAC-SHA256 signature computed over a server-side secret. The cookie value
 * is therefore unforgeable and unguessable, but it is still anonymous — it
 * proves "same browser", never "same person".
 *
 * All user-partitioned stores must key on the verified session id returned by
 * `resolveSession`; a raw `ui-session` cookie value is untrusted client input.
 */

export const SESSION_COOKIE = "ui-session";

/** Sliding lifetime: every response to a verified session extends the cookie. */
export const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7; // 7 days

const TOKEN_VERSION = "v1";
const SESSION_ID_BYTES = 16;

let processSecret: Buffer | null = null;

/**
 * Signing secret for session tokens.
 *
 * Set SESSION_SECRET (32+ bytes) in multi-instance production deployments so
 * every instance verifies tokens identically. Without it the secret is
 * generated per process, which means sessions do not survive instance
 * restarts and are not shared across instances — acceptable for the default
 * single-instance, in-memory deployment only.
 */
function getSecret(): Buffer {
  const fromEnv = process.env.SESSION_SECRET;
  if (fromEnv && fromEnv.length >= 32) {
    return Buffer.from(fromEnv, "utf8");
  }
  if (!processSecret) {
    processSecret = randomBytes(32);
  }
  return processSecret;
}

function sign(sessionId: string, expiresAt: number): string {
  const payload = `${sessionId}.${expiresAt}`;
  const signature = createHmac("sha256", getSecret())
    .update(payload)
    .digest("base64url");
  return `${TOKEN_VERSION}.${payload}.${signature}`;
}

function newSessionId(): string {
  return randomBytes(SESSION_ID_BYTES).toString("base64url");
}

export interface VerifiedToken {
  sessionId: string;
  expired: boolean;
}

/**
 * Verify a token's structure, signature and expiry.
 * Returns null for anything absent, malformed or forged.
 */
export function verifySessionToken(token: string | undefined): VerifiedToken | null {
  if (!token) return null;

  const parts = token.split(".");
  if (parts.length !== 4 || parts[0] !== TOKEN_VERSION) return null;

  const [, sessionId, expiresAtRaw, signature] = parts;
  if (!sessionId || !expiresAtRaw || !signature) return null;
  if (!/^\d+$/.test(expiresAtRaw)) return null;

  const expected = Buffer.from(
    createHmac("sha256", getSecret())
      .update(`${sessionId}.${expiresAtRaw}`)
      .digest("base64url")
  );
  const received = Buffer.from(signature);
  if (received.length !== expected.length || !timingSafeEqual(received, expected)) {
    return null;
  }

  return { sessionId, expired: Date.now() >= Number(expiresAtRaw) };
}

export interface SessionToken {
  sessionId: string;
  expiresAt: number;
  token: string;
}

export function createSessionToken(): SessionToken {
  const sessionId = newSessionId();
  const expiresAt = Date.now() + SESSION_TTL_SECONDS * 1000;
  return { sessionId, expiresAt, token: sign(sessionId, expiresAt) };
}

export interface SessionResolution {
  /** Verified partition key for all user-scoped stores. */
  sessionId: string;
  /** Signed token to hand back to the client. */
  token: string;
  /** True on every verified response: the refreshed cookie must be sent back. */
  rotated: boolean;
}

/**
 * Resolve the caller's session from the `ui-session` cookie.
 *
 * - Missing, forged or malformed cookies resolve to a brand-new session: the
 *   caller can only ever reach an empty partition, never another principal's.
 * - Correctly signed tokens slide on every request: same session id, fresh
 *   expiry. Data survives; replays cannot extend a token they cannot sign.
 *
 * Never fails, and never returns a client-chosen identifier.
 */
export function resolveSession(request: NextRequest): SessionResolution {
  const verified = verifySessionToken(request.cookies.get(SESSION_COOKIE)?.value);

  if (verified) {
    const expiresAt = Date.now() + SESSION_TTL_SECONDS * 1000;
    return {
      sessionId: verified.sessionId,
      token: sign(verified.sessionId, expiresAt),
      rotated: true,
    };
  }

  const fresh = createSessionToken();
  return { sessionId: fresh.sessionId, token: fresh.token, rotated: true };
}

export function sessionCookieOptions(): {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "lax";
  path: string;
  maxAge: number;
} {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  };
}

/** Attach the (refreshed) session cookie to a verified response. */
export function applySessionCookie(
  response: NextResponse,
  session: SessionResolution
): NextResponse {
  if (session.rotated) {
    response.cookies.set(SESSION_COOKIE, session.token, sessionCookieOptions());
  }
  return response;
}
