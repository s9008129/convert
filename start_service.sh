#!/usr/bin/env bash
set -euo pipefail

# Compatibility entry point. The canonical native startup implementation lives
# in scripts/macos/start-mac-native.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(uname -s)" != "Darwin" ]; then
    printf '[ERROR] start_service.sh is the macOS native entry point.\n' >&2
    exit 1
fi

exec "$SCRIPT_DIR/scripts/macos/start-mac-native.sh" "$@"
