#!/usr/bin/env bash
set -euo pipefail

# Build design tokens: primitives.json → semantic.css (CSS custom properties)
# Requires: style-dictionary (npm install -g style-dictionary)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="$SCRIPT_DIR/semantic.json"
OUTPUT="$SCRIPT_DIR/semantic.css"

if ! command -v npx &>/dev/null; then
  echo "Error: npx not found. Install Node.js." >&2
  exit 1
fi

echo "Building tokens from $INPUT → $OUTPUT"

# Generate CSS custom properties from semantic tokens
node -e "
const fs = require('fs');
const tokens = JSON.parse(fs.readFileSync('$INPUT', 'utf8'));

function flatten(obj, prefix = '--wdr') {
  const result = [];
  for (const [key, value] of Object.entries(obj)) {
    if (key.startsWith('\$')) continue;
    const name = prefix + '-' + key;
    if (value.\$value) {
      result.push(\`  \${name}: \${value.\$value};\`);
    } else if (typeof value === 'object') {
      result.push(...flatten(value, name));
    }
  }
  return result;
}

const lines = [
  '/* Auto-generated from semantic.json — do not edit manually */',
  '/* Run: ./build-tokens.sh */',
  '',
  ':root {',
  ...flatten(tokens),
  '}',
  '',
  '/* Dark mode overrides */',
  '@media (prefers-color-scheme: dark) {',
  '  :root:not([data-theme=\"light\"]) {',
  '    --wdr-surface-bg: oklch(0.14 0.00 0);',
  '    --wdr-surface-bg-elevated: oklch(0.20 0.00 0);',
  '    --wdr-surface-bg-sunken: oklch(0.10 0.00 0);',
  '    --wdr-text-primary: oklch(0.95 0.00 0);',
  '    --wdr-text-secondary: oklch(0.70 0.00 0);',
  '    --wdr-text-tertiary: oklch(0.55 0.00 0);',
  '    --wdr-border-default: oklch(0.27 0.00 0);',
  '    --wdr-border-subtle: oklch(0.20 0.00 0);',
  '    --wdr-border-strong: oklch(0.37 0.00 0);',
  '    --wdr-data-row-hover: oklch(0.20 0.00 0);',
  '    --wdr-data-row-selected: oklch(0.25 0.02 230);',
  '    --wdr-data-row-stripe: oklch(0.17 0.005 230);',
  '  }',
  '}',
  '',
  '[data-theme=\"dark\"] {',
  '    --wdr-surface-bg: oklch(0.14 0.00 0);',
  '    --wdr-surface-bg-elevated: oklch(0.20 0.00 0);',
  '    --wdr-surface-bg-sunken: oklch(0.10 0.00 0);',
  '    --wdr-text-primary: oklch(0.95 0.00 0);',
  '    --wdr-text-secondary: oklch(0.70 0.00 0);',
  '    --wdr-text-tertiary: oklch(0.55 0.00 0);',
  '    --wdr-border-default: oklch(0.27 0.00 0);',
  '    --wdr-border-subtle: oklch(0.20 0.00 0);',
  '    --wdr-border-strong: oklch(0.37 0.00 0);',
  '    --wdr-data-row-hover: oklch(0.20 0.00 0);',
  '    --wdr-data-row-selected: oklch(0.25 0.02 230);',
  '    --wdr-data-row-stripe: oklch(0.17 0.005 230);',
  '}',
];

fs.writeFileSync('$OUTPUT', lines.join('\n') + '\n');
console.log('Done: ' + '$OUTPUT');
"
