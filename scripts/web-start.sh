#!/usr/bin/env bash
# Backward-compatible wrapper for categorized web scripts.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$REPO_ROOT/scripts/web/manage.sh" "$@"
