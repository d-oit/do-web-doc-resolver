#!/usr/bin/env bash
# Canonical verification entry point (issue #730).
#
# The do-harness CLI is the authority; this wrapper only bootstraps the pinned
# release on a clean checkout and chooses between changed-only and full
# verification via scripts/harness_select.py.
#
# Usage: scripts/verify.sh [--full|--changed|--auto]   (default: --auto)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DO_HARNESS_VERSION="${DO_HARNESS_VERSION:-v0.4.7}"
MODE="auto"
for arg in "$@"; do
    case "$arg" in
        --full) MODE="full" ;;
        --changed) MODE="changed" ;;
        --auto) MODE="auto" ;;
        *)
            echo "usage: scripts/verify.sh [--full|--changed|--auto]" >&2
            exit 2
            ;;
    esac
done

if ! command -v do-harness >/dev/null 2>&1; then
    echo "do-harness not found; installing pinned ${DO_HARNESS_VERSION}..."
    curl -fsSL "https://raw.githubusercontent.com/d-o-hub/do-harness/${DO_HARNESS_VERSION}/scripts/install.sh" \
        | sh -s -- --version "${DO_HARNESS_VERSION}"
    export PATH="${HOME}/.local/bin:${PATH}"
fi
command -v do-harness >/dev/null 2>&1 || {
    echo "error: do-harness ${DO_HARNESS_VERSION} is not installed" >&2
    exit 1
}

do-harness init-db >/dev/null 2>&1 || true

MODE="$(python scripts/harness_select.py --mode "${MODE}" --format mode)"
CHANGED_ARGS=""
if [ "$MODE" = "changed" ]; then
    CHANGED_ARGS="--changed"
fi
echo "verify: mode=${MODE}"

mkdir -p .do-harness
set +e
do-harness verify --set verification ${CHANGED_ARGS} --strict --format json \
    --evidence .do-harness/evidence.json | tee .do-harness/verify-output.json
STATUS=${PIPESTATUS[0]}
set -e

if [ "$STATUS" -ne 0 ]; then
    echo "verify: failed checks and their fix commands:" >&2
    python scripts/harness_select.py fix-hints .do-harness/evidence.json >&2 || true
fi
exit "$STATUS"
