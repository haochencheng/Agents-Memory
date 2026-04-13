#!/bin/sh
# Backward-compatible wrapper for categorized runtime scripts.

set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec bash "$REPO_ROOT/scripts/runtime/manage.sh" "$@"
