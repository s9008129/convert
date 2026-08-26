#!/usr/bin/env bash
set -euo pipefail

# macOS native entry point. The environment is prepared separately with:
#   uv sync --frozen
# This script only validates the prepared environment and starts the service;
# it never installs packages, downloads models, or changes external runtimes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$PROJECT_ROOT/.server.pid"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/app.log"
HOST="${MEETINGSCRIBE_HOST:-0.0.0.0}"
PORT="${MEETINGSCRIBE_PORT:-9527}"
export DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/data}"

cd "$PROJECT_ROOT"

info() { printf '[INFO] %s\n' "$*"; }
success() { printf '[OK] %s\n' "$*"; }
error() { printf '[ERROR] %s\n' "$*" >&2; }

if ! command -v uv >/dev/null 2>&1; then
    error "找不到 uv；請先依專案文件完成 uv 安裝。"
    exit 1
fi

if [ ! -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    error "找不到已準備好的 .venv。請先在專案根目錄執行：uv sync --frozen"
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    error "找不到 ffmpeg；請先由系統管理者安裝後再啟動。"
    exit 1
fi

if [ -f "$PID_FILE" ]; then
    existing_pid="$(<"$PID_FILE")"
    if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
        error "服務似乎已在執行中（PID $existing_pid）。"
        exit 1
    fi
    rm -f "$PID_FILE"
fi

mkdir -p "$PROJECT_ROOT/data/uploads" "$PROJECT_ROOT/data/outputs" "$PROJECT_ROOT/data/cache" "$LOG_DIR"

info "驗證已安裝的 native Python 環境..."
if ! uv run --no-sync python scripts/verify_env.py; then
    error "環境驗證失敗；未啟動服務。"
    exit 1
fi

export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONIOENCODING="utf-8"

info "啟動 FastAPI（repo root: ${PROJECT_ROOT}）..."
nohup uv run --no-sync uvicorn backend.main:app --host "$HOST" --port "$PORT" \
    </dev/null >"$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

find_service_pid() {
    local candidate command
    for candidate in $(pgrep -P "$SERVER_PID" 2>/dev/null || true); do
        command="$(ps -p "$candidate" -o command= 2>/dev/null || true)"
        if [[ "$command" == *"backend.main:app"* ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    printf '%s\n' "$SERVER_PID"
}

cleanup_pid_file() {
    if [ -f "$PID_FILE" ] && [ "$(<"$PID_FILE")" = "$SERVER_PID" ]; then
        rm -f "$PID_FILE"
    fi
}
trap cleanup_pid_file EXIT

for attempt in $(seq 1 30); do
    if curl --fail --silent --show-error "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
        SERVICE_PID="$(find_service_pid)"
        echo "$SERVICE_PID" > "$PID_FILE"
        trap - EXIT
        success "服務已就緒：http://127.0.0.1:${PORT}（PID ${SERVICE_PID}）"
        exit 0
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        error "服務程序已提前結束；請查看 $LOG_FILE"
        exit 1
    fi
    sleep 1
done

error "服務尚未在 30 秒內回應；請查看 $LOG_FILE。"
exit 1
