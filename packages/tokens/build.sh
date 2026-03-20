#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="$(dirname "$0")/src"
OUT_DIR="$(dirname "$0")/dist"

mkdir -p "$OUT_DIR"

cat > "$OUT_DIR/tokens.css" << 'CSSEOF'
:root {
  --color-primary: #0ea5e9;
  --color-secondary: #64748b;
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-bg: #ffffff;
  --color-fg: #0f172a;
  --font-sans: system-ui, -apple-system, sans-serif;
  --font-mono: ui-monospace, monospace;
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 1rem;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
}
CSSEOF

cat > "$OUT_DIR/index.js" << 'JSEOF'
export const colors = {
  primary: "#0ea5e9",
  secondary: "#64748b",
  success: "#22c55e",
  warning: "#f59e0b",
  error: "#ef4444",
  bg: "#ffffff",
  fg: "#0f172a",
};
export const fonts = {
  sans: "system-ui, -apple-system, sans-serif",
  mono: "ui-monospace, monospace",
};
export const radii = { sm: "0.25rem", md: "0.5rem", lg: "1rem" };
export const space = {
  1: "0.25rem", 2: "0.5rem", 3: "0.75rem",
  4: "1rem", 6: "1.5rem", 8: "2rem",
};
JSEOF

cat > "$OUT_DIR/index.d.ts" << 'DTSEOF'
export declare const colors: Record<string, string>;
export declare const fonts: Record<string, string>;
export declare const radii: Record<string, string>;
export declare const space: Record<number, string>;
DTSEOF

echo "Tokens built to $OUT_DIR"
