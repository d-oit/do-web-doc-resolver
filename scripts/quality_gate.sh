#!/bin/bash
# Compatibility wrapper (issue #730): the canonical gate is scripts/verify.sh,
# which drives the pinned do-harness CLI. This script always runs the full
# strict verification set; it is not a second authority.
#
# Usage: ./scripts/quality_gate.sh [--full|--changed|--auto]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$REPO_ROOT/scripts/verify.sh" --full "$@"
