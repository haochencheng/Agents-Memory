#!/bin/sh
# Backward-compatible wrapper for categorized web scripts.

set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec bash "$REPO_ROOT/scripts/web/manage.sh" "$@"
