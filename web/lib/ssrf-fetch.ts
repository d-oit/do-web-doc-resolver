import http from "node:http";
import https from "node:https";
import dnsPromises from "node:dns/promises";
import type { LookupAddress } from "node:dns";
import ipaddr from "ipaddr.js";
import { isPrivateIpAddress, validateUrl } from "./validation";

/**
 * The single audited outbound-fetch boundary for resolver-controlled URLs.
 *
 * Every hop of every request is revalidated (scheme, credentials, DNS) and
 * the connection itself is pinned to the vetted address, so a second DNS
 * resolution can never re-target an already-approved socket at a private
 * or reserved address.
 */

export type LookupFn = (
  hostname: string,
  options: { all: boolean }
) => Promise<LookupAddress[]>;

const defaultLookup: LookupFn = async (hostname, options) => {
  const result = await dnsPromises.lookup(hostname, { ...options, verbatim: true, all: true });
  return result as LookupAddress[];
};

function isRedirectStatus(status: number | undefined): boolean {
  return status === 301 || status === 302 || status === 303 || status === 307 || status === 308;
}

export interface SsrfFetchOptions extends Omit<RequestInit, "signal"> {
  timeoutMs?: number;
  maxRedirects?: number;
  maxBytes?: number;
  lookup?: LookupFn;
  signal?: AbortSignal;
  allowPrivateForTest?: boolean;
}

interface ResolvedTarget {
  url: URL;
  pinnedAddress: string;
}

export class SsrfBlockedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SsrfBlockedError";
  }
}

export function isPublicAddress(address: string): boolean {
  return !isPrivateIpAddress(address);
}

/**
 * Resolve a hostname and pin it to a single vetted public IP address.
 * Every resolved address must be public: one private answer among public
 * ones fails the whole hostname, so mixed DNS answers cannot be used to
 * race validation against connection.
 */
export async function resolvePinnedAddress(
  hostname: string,
  lookup: LookupFn = defaultLookup,
  allowPrivateAddresses = false
): Promise<string> {
  if (!allowPrivateAddresses && isPrivateIpAddress(hostname)) {
    throw new SsrfBlockedError(`Domain resolves to private/internal IP: ${hostname}`);
  }

  const addresses = await lookup(hostname, { all: true });
  if (!Array.isArray(addresses) || addresses.length === 0) {
    throw new SsrfBlockedError(`DNS resolution returned no addresses for ${hostname}`);
  }

  if (!allowPrivateAddresses) {
    for (const { address } of addresses) {
      if (!isPublicAddress(address)) {
        throw new SsrfBlockedError(`Domain resolves to private/internal IP: ${hostname}`);
      }
    }
  }

  const first = addresses[0];
  if (!first) {
    throw new SsrfBlockedError(`DNS resolution returned no addresses for ${hostname}`);
  }
  return first.address;
}

/**
 * Validate a URL for SSRF safety and pin it to a vetted IP address.
 */
export async function resolveAndValidateTarget(
  url: string,
  lookup: LookupFn = defaultLookup,
  allowPrivateAddresses = false
): Promise<ResolvedTarget> {
  const syncCheck = validateUrl(url);
  if (!syncCheck.valid) {
    throw new SsrfBlockedError(`SSRF blocked: ${syncCheck.error ?? "invalid URL"}`);
  }

  const target = new URL(url);
  if (target.username || target.password) {
    throw new SsrfBlockedError("SSRF blocked: credentials in URL are not allowed");
  }

  const pinnedAddress = await resolvePinnedAddress(
    target.hostname,
    lookup,
    allowPrivateAddresses
  );
  return { url: target, pinnedAddress };
}

/**
 * Fetch a resolver-controlled URL through the SSRF-safe boundary.
 *
 * Every redirect hop is revalidated from scratch (scheme, credentials,
 * DNS pinning), so a redirect chain can never reach an address that the
 * original target would have been rejected for.
 */
export async function ssrfFetch(url: string, options: SsrfFetchOptions = {}): Promise<Response> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    maxRedirects = DEFAULT_MAX_REDIRECTS,
    maxBytes = DEFAULT_MAX_RESPONSE_BYTES,
    lookup = defaultLookup,
    allowPrivateForTest = false,
    headers,
    method = "GET",
    body,
    signal,
  } = options;

  let currentUrl = url;
  let currentHeaders: Record<string, string> = normalizeHeaders(headers);
  let currentMethod = method;
  let currentBody: BodyInit | undefined = body === null ? undefined : body;

  for (let hop = 0; hop <= maxRedirects; hop++) {
    if (signal?.aborted) {
      throw new SsrfBlockedError("Request aborted before connection");
    }

    const { url: target, pinnedAddress } = await resolveAndValidateTargetWithPolicy(
      currentUrl,
      lookup,
      allowPrivateForTest
    );
    const response = await pinnedFetch(
      target,
      pinnedAddress,
      currentHeaders,
      currentMethod,
      currentBody,
      timeoutMs,
      maxBytes,
      signal
    );

    if (!isRedirectStatus(response.status)) {
      return response;
    }

    const location = response.headers.get("Location");
    if (!location) {
      return response;
    }

    const next = resolveRedirectTarget(target, location);
    // 303 always degrades to GET (and 301/302 follow historic browser
    // behavior); 307/308 keep the original method and body.
    if (response.status === 301 || response.status === 302 || response.status === 303) {
      if (currentMethod !== "GET" && currentMethod !== "HEAD") {
        currentMethod = "GET";
        currentBody = undefined;
      }
    }
    if (next.origin !== target.origin) {
      currentHeaders = stripSensitiveHeaders(currentHeaders);
    }
    currentUrl = next.toString();
  }

  throw new SsrfBlockedError(`Too many redirects (max ${maxRedirects})`);
}

async function resolveAndValidateTargetWithPolicy(
  url: string,
  lookup: LookupFn,
  allowPrivateAddresses: boolean
): Promise<ResolvedTarget> {
  const syncCheck = validateUrl(url);
  if (!syncCheck.valid) {
    const isPrivateBlock = /private\/internal/i.test(syncCheck.error ?? "");
    if (!allowPrivateAddresses || !isPrivateBlock) {
      throw new SsrfBlockedError(`SSRF blocked: ${syncCheck.error ?? "invalid URL"}`);
    }
  }

  const target = new URL(url);
  if (target.username || target.password) {
    throw new SsrfBlockedError("SSRF blocked: credentials in URL are not allowed");
  }

  const pinnedAddress = await resolvePinnedAddress(target.hostname, lookup, allowPrivateAddresses);
  return { url: target, pinnedAddress };
}

/**
 * Issue an HTTP(S) request pinned to a single vetted IP address.
 * The socket's `lookup` is overridden to always return the pinned address,
 * so the connection can only ever reach the address that was validated.
 */
async function pinnedFetch(
  target: URL,
  pinnedAddress: string,
  headers: Record<string, string>,
  method: string,
  body: BodyInit | undefined,
  timeoutMs: number,
  maxBytes: number,
  signal?: AbortSignal
): Promise<Response> {
  return new Promise<Response>((resolve, reject) => {
    const transport = target.protocol === "https:" ? https : http;
    const req = transport.request(
      target,
      {
        method,
        headers,
        lookup: (_hostname, _options, callback) => {
          callback(null, pinnedAddress, addressFamily(pinnedAddress));
        },
        timeout: timeoutMs,
      },
      (res) => {
        void consumeResponse(res, maxBytes)
          .then((body) => {
            resolve(
              new Response(new Uint8Array(body), {
                status: res.statusCode ?? 0,
                statusText: res.statusMessage ?? "",
                headers: normalizeResponseHeaders(res.headers),
              })
            );
          })
          .catch(reject);
      }
    );

    if (signal) {
      signal.addEventListener(
        "abort",
        () => req.destroy(new SsrfBlockedError("Request aborted")),
        { once: true }
      );
    }

    if (typeof body === "string") {
      req.write(body);
    } else if (body && body instanceof Uint8Array) {
      req.write(Buffer.from(body));
    }
    req.end();
  });
}

async function consumeResponse(res: http.IncomingMessage, maxBytes: number): Promise<Buffer> {
  return new Promise<Buffer>((resolve, reject) => {
    const chunks: Buffer[] = [];
    let total = 0;
    res.on("data", (chunk: Buffer) => {
      total += chunk.length;
      if (total > maxBytes) {
        res.destroy();
        reject(new SsrfBlockedError(`Response exceeds size limit (${maxBytes} bytes)`));
        return;
      }
      chunks.push(chunk);
    });
    res.on("end", () => resolve(Buffer.concat(chunks)));
    res.on("error", reject);
  });
}

function normalizeResponseHeaders(headers: http.IncomingHttpHeaders): Record<string, string> {
  const normalized: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    if (typeof value === "string") {
      normalized[key] = value;
    } else if (Array.isArray(value)) {
      normalized[key] = value.join(", ");
    }
  }
  return normalized;
}

function resolveRedirectTarget(target: URL, location: string): URL {
  const next = new URL(location, target);
  if (next.protocol !== "http:" && next.protocol !== "https:") {
    throw new SsrfBlockedError(`SSRF blocked: unsupported redirect scheme ${next.protocol}`);
  }
  if (next.username || next.password) {
    throw new SsrfBlockedError("SSRF blocked: credentials in redirect target");
  }
  return next;
}

function stripSensitiveHeaders(headers: Record<string, string>): Record<string, string> {
  const stripped: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    if (!SENSITIVE_HEADERS.has(key.toLowerCase())) {
      stripped[key] = value;
    }
  }
  return stripped;
}

function normalizeHeaders(headers: HeadersInit | undefined): Record<string, string> {
  const normalized: Record<string, string> = {};
  if (!headers) return normalized;
  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      normalized[key] = value;
    });
  } else if (Array.isArray(headers)) {
    for (const [key, value] of headers) {
      normalized[key] = value;
    }
  } else {
    for (const [key, value] of Object.entries(headers)) {
      normalized[key] = value;
    }
  }
  return normalized;
}

function addressFamily(address: string): 4 | 6 {
  return ipaddr.parse(address).kind() === "ipv6" ? 6 : 4;
}

const SENSITIVE_HEADERS = new Set([
  "authorization",
  "cookie",
  "x-api-key",
  "proxy-authorization",
]);

export const DEFAULT_TIMEOUT_MS = 15000;
export const DEFAULT_MAX_REDIRECTS = 5;
export const DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024;
