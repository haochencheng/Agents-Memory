#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

bash "$SCRIPT_DIR/runtime.sh" restart
bash "$SCRIPT_DIR/web.sh" restart
