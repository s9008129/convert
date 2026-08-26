#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

if [ -x "$SCRIPT_DIR/stop-mac-native.sh" ]; then
    "$SCRIPT_DIR/stop-mac-native.sh"
fi

exec "$SCRIPT_DIR/start-mac-native.sh" "$@"
