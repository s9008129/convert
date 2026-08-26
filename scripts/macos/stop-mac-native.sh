#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$PROJECT_ROOT/.server.pid"

cd "$PROJECT_ROOT"

if [ ! -f "$PID_FILE" ]; then
    printf '[INFO] 找不到服務 PID 檔案，沒有可停止的服務。\n'
    exit 0
fi

PID="$(<"$PID_FILE")"
if ! [[ "$PID" =~ ^[0-9]+$ ]]; then
    printf '[ERROR] PID 檔案格式無效，未執行終止操作。\n' >&2
    exit 1
fi

if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    printf '[INFO] 服務程序已不存在，已清理 PID 檔案。\n'
    exit 0
fi

COMMAND="$(ps -p "$PID" -o command= 2>/dev/null || true)"
if [[ "$COMMAND" != *"backend.main:app"* ]]; then
    printf '[ERROR] PID %s 不是本專案服務程序，未執行終止操作。\n' "$PID" >&2
    exit 1
fi

kill "$PID"
for _ in $(seq 1 10); do
    if ! kill -0 "$PID" 2>/dev/null; then
        rm -f "$PID_FILE"
        printf '[OK] 服務已停止。\n'
        exit 0
    fi
    sleep 1
done

printf '[WARN] 服務未在 10 秒內停止，執行最後的精確 PID 終止。\n'
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
printf '[OK] 服務已停止。\n'
