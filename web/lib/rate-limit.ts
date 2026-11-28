import { createHash } from "node:crypto";

/**
 * Rate limiting for the paid-provider resolve path.
 *
 * The enforcement store is selected at startup:
 * - Upstash Redis REST (distributed, atomic) when UPSTASH_REDIS_REST_URL and
 *   UPSTASH_REDIS_REST_TOKEN are set — production.
 * - In-memory Map otherwise — a clearly identified development/test adapter
 *   whose counters are per process and never shared across instances.
 *
 * Client identity never trusts arbitrary user-supplied forwarding headers:
 * platform-set headers are honored only when running on the platform
 * (VERCEL) or when the operator opts in via RATE_LIMIT_TRUST_PROXY=1 for a
 * known reverse proxy in front. Identifiers are hashed before use as keys.
 */

export interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
}

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetAt: number;
}

export type RateLimitScope = "resolve" | "resolve_deep" | "resolve_route" | "global_provider";

export interface RateLimitStore {
  hit(key: string, config: RateLimitConfig): Promise<RateLimitResult>;
}

export const DEFAULT_RATE_LIMIT_CONFIG: RateLimitConfig = {
  windowMs: 60 * 1000,
  maxRequests: 30,
};

/**
 * Scope budgets: per-client limits for the resolve path (the edge proxy gate
 * and the route-handler enforcement each use their own counter), a stricter
 * per-client budget for deep-research runs (expensive provider fan-out), and
 * a shared global ceiling that bounds total provider spend per minute.
 */
export const RATE_LIMIT_SCOPES: Record<RateLimitScope, RateLimitConfig> = {
  resolve: { windowMs: 60_000, maxRequests: 30 },
  resolve_route: { windowMs: 60_000, maxRequests: 30 },
  resolve_deep: { windowMs: 60_000, maxRequests: 10 },
  global_provider: {
    windowMs: 60_000,
    maxRequests: parseInt(process.env.RATE_LIMIT_GLOBAL_MAX || "600"),
  },
};

/**
 * Store failure policy for the paid-provider path. Fail-closed (default)
 * blocks requests when the counter backend is unavailable so cost limits
 * are never bypassed; set RATE_LIMIT_FAILURE_MODE=fail-open to prefer
 * availability over cost protection.
 */
export type FailureMode = "fail-open" | "fail-closed";

export function getFailureMode(): FailureMode {
  return process.env.RATE_LIMIT_FAILURE_MODE === "fail-open" ? "fail-open" : "fail-closed";
}

// ---------------------------------------------------------------------------
// Development/test adapter: process-local, bounded, TTL-cleaned
// ---------------------------------------------------------------------------

export const MAX_TRACKED_CLIENTS = 10_000;

interface RateLimitEntry {
  count: number;
  resetAt: number;
}

const requests = new Map<string, RateLimitEntry>();

export class MemoryRateLimitStore implements RateLimitStore {
  async hit(key: string, config: RateLimitConfig): Promise<RateLimitResult> {
    return checkRateLimit(key, config);
  }
}

/**
 * Check if a request is allowed under rate limiting (in-memory adapter).
 * The map is bounded: when it grows past MAX_TRACKED_CLIENTS, expired
 * entries are reclaimed first and the oldest entries are evicted.
 */
export function checkRateLimit(
  identifier: string,
  config: RateLimitConfig = DEFAULT_RATE_LIMIT_CONFIG
): { allowed: boolean; remaining: number; resetAt: number } {
  const now = Date.now();
  evictIfNeeded();
  const entry = requests.get(identifier);

  if (!entry || now > entry.resetAt) {
    const resetAt = now + config.windowMs;
    requests.set(identifier, { count: 1, resetAt });
    return { allowed: true, remaining: config.maxRequests - 1, resetAt };
  }

  if (entry.count >= config.maxRequests) {
    return { allowed: false, remaining: 0, resetAt: entry.resetAt };
  }

  entry.count++;
  return { allowed: true, remaining: config.maxRequests - entry.count, resetAt: entry.resetAt };
}

function evictIfNeeded(): void {
  if (requests.size < MAX_TRACKED_CLIENTS) return;
  cleanupExpiredEntries();
  while (requests.size >= MAX_TRACKED_CLIENTS) {
    const oldest = requests.keys().next();
    if (oldest.done) break;
    requests.delete(oldest.value);
  }
}

/**
 * Get client identifier from the request.
 *
 * Trust boundary: platform-set headers (x-real-ip, then x-forwarded-for as
 * set by the platform edge) are honored only when running on Vercel or when
 * RATE_LIMIT_TRUST_PROXY=1 declares a trusted reverse proxy. Otherwise the
 * caller is untrusted and shares a single dev identifier. The identifier is
 * hashed so raw IPs never become keys and cardinality stays bounded.
 */
export function getClientIdentifier(request: Request): string {
  const trusted =
    process.env.VERCEL === "1" || process.env.RATE_LIMIT_TRUST_PROXY === "1";

  let clientIp: string | null = null;
  if (trusted) {
    const realIp = request.headers.get("x-real-ip");
    if (realIp) {
      clientIp = realIp.trim();
    } else {
      const forwarded = request.headers.get("x-forwarded-for");
      if (forwarded) {
        clientIp = forwarded.split(",")[0]?.trim() || null;
      }
    }
  }

  if (!clientIp) {
    clientIp = "untrusted";
  }
  return hashIdentifier(clientIp);
}

export function hashIdentifier(identifier: string): string {
  return createHash("sha256").update(identifier).digest("hex").slice(0, 32);
}

/**
 * Clean up expired entries (call periodically)
 */
export function cleanupExpiredEntries(): number {
  const now = Date.now();
  let cleaned = 0;
  for (const [key, entry] of requests) {
    if (now > entry.resetAt) {
      requests.delete(key);
      cleaned++;
    }
  }
  return cleaned;
}

export function clearRateLimits(): void {
  requests.clear();
}

export function getRateLimitStats(): { totalEntries: number; activeEntries: number } {
  const now = Date.now();
  let active = 0;
  for (const entry of requests.values()) {
    if (now <= entry.resetAt) active++;
  }
  return { totalEntries: requests.size, activeEntries: active };
}

// ---------------------------------------------------------------------------
// Distributed adapter: Upstash Redis REST, atomic fixed-window counter
// ---------------------------------------------------------------------------

const RATE_LIMIT_LUA = `
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('PTTL', KEYS[1])
return {count, ttl}
`;

export class UpstashRestRateLimitStore implements RateLimitStore {
  constructor(
    private readonly baseUrl: string,
    private readonly token: string
  ) {}

  async hit(key: string, config: RateLimitConfig): Promise<RateLimitResult> {
    const response = await fetch(`${this.baseUrl}/eval`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify([RATE_LIMIT_LUA, `ratelimit:${key}`, String(config.windowMs)]),
    });
    if (!response.ok) {
      throw new Error(`Rate limit store returned ${response.status}`);
    }
    const payload = (await response.json()) as { result?: unknown; error?: string };
    if (payload.error) {
      throw new Error(`Rate limit store error: ${payload.error}`);
    }
    const [count, ttlMs] = parseEvalResult(payload.result);
    const resetAt = Date.now() + Math.max(0, ttlMs);
    return {
      allowed: count <= config.maxRequests,
      remaining: Math.max(0, config.maxRequests - count),
      resetAt,
    };
  }
}

function parseEvalResult(result: unknown): [number, number] {
  let raw = result;
  if (typeof raw === "string") {
    try {
      raw = JSON.parse(raw);
    } catch {
      throw new Error("Rate limit store returned an unreadable result");
    }
  }
  if (!Array.isArray(raw) || raw.length < 2) {
    throw new Error("Rate limit store returned an unreadable result");
  }
  const count = Number(raw[0]);
  const ttlMs = Number(raw[1]);
  if (!Number.isFinite(count) || !Number.isFinite(ttlMs)) {
    throw new Error("Rate limit store returned an unreadable result");
  }
  return [count, ttlMs];
}

let configuredStore: RateLimitStore | undefined;

export function getRateLimitStore(): RateLimitStore {
  if (configuredStore) return configuredStore;
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (url && token) {
    configuredStore = new UpstashRestRateLimitStore(url, token);
  } else {
    configuredStore = new MemoryRateLimitStore();
  }
  return configuredStore;
}

export function setRateLimitStoreForTesting(store: RateLimitStore | undefined): void {
  configuredStore = store;
}

/**
 * Enforce a scope's budget through the configured store. Keys are prefixed
 * per scope so the edge gate and route enforcement never share counters;
 * every key carries the window TTL so expired counters are reclaimed
 * automatically by the store.
 */
export async function enforceRateLimit(
  identifier: string,
  scope: RateLimitScope,
  config?: RateLimitConfig
): Promise<RateLimitResult> {
  const effectiveConfig = config ?? RATE_LIMIT_SCOPES[scope];
  const key = scope === "global_provider" ? scope : `${scope}:${identifier}`;
  try {
    return await getRateLimitStore().hit(key, effectiveConfig);
  } catch {
    if (getFailureMode() === "fail-open") {
      return {
        allowed: true,
        remaining: effectiveConfig.maxRequests,
        resetAt: Date.now() + effectiveConfig.windowMs,
      };
    }
    return { allowed: false, remaining: 0, resetAt: Date.now() + effectiveConfig.windowMs };
  }
}
