/**
 * Single source of truth for URL detection in the web runtime.
 *
 * The page's mode label ("Resolving as URL" vs "Searching") and the API
 * route's execution path must agree, otherwise the UI can promise one mode
 * while the server runs the other. Client components importing the full
 * resolver map just for this predicate would pull every provider SDK into
 * the browser bundle, so it lives in its own module.
 */
export function isUrl(input: string): boolean {
  return /^https?:\/\/\S+$/i.test((input ?? "").trim());
}
