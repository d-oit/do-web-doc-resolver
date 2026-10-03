/**
 * Bounded JSON request-body reading.
 *
 * `request.json()` buffers the entire body before any validation runs, so a
 * per-field schema cap bounds what gets *stored* but not what the server is
 * made to *allocate*. App Router route handlers have no `bodyParser.sizeLimit`
 * equivalent (that was a Pages Router API), so the limit has to be enforced
 * here rather than in configuration.
 */

/** Default cap. Must exceed the largest legitimate payload plus JSON overhead. */
export const MAX_BODY_BYTES = 512 * 1024;

export class BodyTooLargeError extends Error {
  constructor(readonly limit: number) {
    super(`Request body exceeds ${limit} bytes`);
    this.name = "BodyTooLargeError";
  }
}

/**
 * Read and parse a JSON body, rejecting anything over `limit` bytes.
 *
 * A declared `Content-Length` is refused up front so an oversized request is
 * never read at all. The stream is then counted as it is consumed, which covers
 * chunked requests that omit the header — without that second check the cap
 * would only hold for clients honest enough to send the header.
 */
export async function readJsonWithLimit(
  request: Request,
  limit: number = MAX_BODY_BYTES
): Promise<unknown> {
  const declared = request.headers.get("content-length");
  if (declared !== null) {
    const bytes = Number(declared);
    if (Number.isFinite(bytes) && bytes > limit) {
      throw new BodyTooLargeError(limit);
    }
  }

  if (!request.body) {
    return null;
  }

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value) continue;

      total += value.byteLength;
      if (total > limit) {
        await reader.cancel();
        throw new BodyTooLargeError(limit);
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  if (total === 0) {
    return null;
  }

  const raw = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    raw.set(chunk, offset);
    offset += chunk.byteLength;
  }

  return JSON.parse(new TextDecoder().decode(raw));
}
