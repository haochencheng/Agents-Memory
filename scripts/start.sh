#!/usr/bin/env bash
# Backward-compatible wrapper for categorized runtime scripts.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$REPO_ROOT/scripts/runtime/manage.sh" "$@"
