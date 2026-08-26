#!/usr/bin/env bash
set -euo pipefail

# Interactive compatibility menu for the canonical macOS native scripts.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
START_SCRIPT="$PROJECT_ROOT/scripts/macos/start-mac-native.sh"
STOP_SCRIPT="$PROJECT_ROOT/scripts/macos/stop-mac-native.sh"
RESTART_SCRIPT="$PROJECT_ROOT/scripts/macos/restart-mac-native.sh"
PID_FILE="$PROJECT_ROOT/.server.pid"
PORT="${MEETINGSCRIBE_PORT:-9527}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_status() {
    printf '\n📊 檢查服務狀態...\n'

    if [ ! -f "$PID_FILE" ]; then
        printf '%b❌ 服務未運行%b\n' "$RED" "$NC"
        return 0
    fi

    local pid command version queue
    pid="$(<"$PID_FILE")"
    if ! [[ "$pid" =~ ^[0-9]+$ ]] || ! kill -0 "$pid" 2>/dev/null; then
        printf '%b❌ 服務未運行（PID 檔案已過期）%b\n' "$RED" "$NC"
        return 0
    fi

    command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$command" != *"backend.main:app"* ]]; then
        printf '%b⚠️ PID %s 不是本專案服務程序%b\n' "$YELLOW" "$pid" "$NC"
        return 0
    fi

    printf '%b✅ 服務正在運行 (PID: %s)%b\n' "$GREEN" "$pid" "$NC"
    version="$(curl --silent --fail "http://127.0.0.1:$PORT/api/health" 2>/dev/null \
        | python3 -c 'import json, sys; print(json.load(sys.stdin).get("version", ""))' 2>/dev/null || true)"
    if [ -n "$version" ]; then
        printf '%b   版本: %s%b\n' "$GREEN" "$version" "$NC"
    fi
    queue="$(curl --silent --fail "http://127.0.0.1:$PORT/api/health" 2>/dev/null \
        | python3 -c 'import json, sys; print(json.load(sys.stdin).get("queue_status", {}).get("total_queued", ""))' 2>/dev/null || true)"
    if [ -n "$queue" ]; then
        printf '%b   排隊人數: %s%b\n' "$GREEN" "$queue" "$NC"
    fi
}

show_restart_guide() {
    printf '\n%b何時需要重啟服務？%b\n' "$YELLOW" "$NC"
    printf '  • 環境變數、設定檔、依賴或靜態檔案變更後。\n'
    printf '  • 依賴更新後，先在專案根目錄執行 uv sync --frozen。\n'
    printf '  • Python 程式碼變更後，重新啟動以載入新版本。\n'
}

printf '========================================\n'
printf '  政府智慧會議紀錄生成系統 服務管理指南\n'
printf '========================================\n'
printf '\n請選擇操作：\n'
printf '1) 查看服務狀態\n'
printf '2) 啟動服務\n'
printf '3) 停止服務\n'
printf '4) 重啟服務\n'
printf '5) 查看服務日誌\n'
printf '6) 查看重啟指南\n'
printf '7) 退出\n\n'
read -r -p '請輸入選項 (1-7): ' choice

case "$choice" in
    1)
        check_status
        ;;
    2)
        "$START_SCRIPT"
        ;;
    3)
        "$STOP_SCRIPT"
        ;;
    4)
        "$RESTART_SCRIPT"
        ;;
    5)
        tail -f "$PROJECT_ROOT/logs/app.log"
        ;;
    6)
        show_restart_guide
        ;;
    7)
        exit 0
        ;;
    *)
        printf '%b無效選項%b\n' "$RED" "$NC" >&2
        exit 1
        ;;
esac
