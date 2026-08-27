#!/usr/bin/env bash
set -euo pipefail

# macOS native entry point. The environment is prepared separately with:
#   uv sync --frozen
# This script only validates the prepared environment and starts the service;
# it never installs packages, downloads models, or changes external runtimes.
#
# Provenance contract（plan CM-03）：
#   1. Git 可用時以 repo `git rev-parse HEAD` 為 authoritative build revision；
#      dirty worktree 以可區分的 "-dirty" 值標記，不冒充 clean SHA。
#   2. caller 明示要求的 revision（MEETINGSCRIBE_REQUESTED_REVISION /
#      MEETINGSCRIBE_EXPECTED_REVISION / MEETINGSCRIBE_BUILD_REVISION）與 clean
#      HEAD 不同時，啟動前 fail loudly。
#   3. 啟動前建立並實測 DATA_DIR 可寫；readiness 以 .venv Python 解析
#      /api/health JSON 的 build revision，精確相符才宣告 ready。
#   4. 啟動後任何失敗只終止本 script 啟動的 SERVER_PID 與其 service child，
#      並清除自己寫入的 PID file；不對不明 process 做廣域終止。

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

if ! mkdir -p "$DATA_DIR/uploads" "$DATA_DIR/outputs" "$DATA_DIR/cache" "$LOG_DIR"; then
    error "無法建立資料/日誌目錄：${DATA_DIR}、${LOG_DIR}"
    exit 1
fi

if [ ! -d "$DATA_DIR" ] || [ ! -w "$DATA_DIR" ]; then
    error "DATA_DIR 不存在或不可寫：${DATA_DIR}；不啟動 backend。"
    exit 1
fi
if ! DATA_WRITE_PROBE="$(mktemp "$DATA_DIR/.launcher-write-probe.XXXXXX" 2>/dev/null)"; then
    error "DATA_DIR 實際寫入測試失敗：${DATA_DIR}；不啟動 backend。"
    exit 1
fi
rm -f "$DATA_WRITE_PROBE"

# --- build revision provenance：Git clean HEAD 為 authoritative 來源 --------
GIT_TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null)" || GIT_TOPLEVEL=""
GIT_CLEAN_SHA=""
GIT_DIRTY_SUFFIX=""
if [ "$GIT_TOPLEVEL" = "$PROJECT_ROOT" ]; then
    GIT_CLEAN_SHA="$(git rev-parse HEAD 2>/dev/null)" || GIT_CLEAN_SHA=""
fi

if [ -n "$GIT_CLEAN_SHA" ]; then
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        GIT_DIRTY_SUFFIX="-dirty"
        info "偵測到未提交變更；build revision 將以可區分的 -dirty 值標記，不冒充 clean SHA。"
    fi
    DERIVED_REVISION="${GIT_CLEAN_SHA}${GIT_DIRTY_SUFFIX}"
else
    # No-Git packaged environment：僅此情況允許 explicit revision 或 unknown。
    DERIVED_REVISION="${MEETINGSCRIBE_BUILD_REVISION:-unknown}"
    info "Git 無法確認本專案 repo HEAD；build revision 採用：${DERIVED_REVISION}"
fi

REQUESTED_REVISION="${MEETINGSCRIBE_REQUESTED_REVISION:-${MEETINGSCRIBE_EXPECTED_REVISION:-${MEETINGSCRIBE_BUILD_REVISION:-}}}"
if [ -n "$REQUESTED_REVISION" ] && [ -n "$GIT_CLEAN_SHA" ] && [ "$REQUESTED_REVISION" != "$GIT_CLEAN_SHA" ]; then
    error "明確要求的 build revision（${REQUESTED_REVISION}）與 clean Git HEAD（${GIT_CLEAN_SHA}）不一致；不啟動 backend。"
    exit 1
fi

export MEETINGSCRIBE_BUILD_REVISION="$DERIVED_REVISION"

info "驗證已安裝的 native Python 環境..."
if ! uv run --no-sync python scripts/verify_env.py; then
    error "環境驗證失敗；未啟動服務。"
    exit 1
fi

export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONIOENCODING="utf-8"

info "啟動設定：project root=${PROJECT_ROOT} host=${HOST} port=${PORT} DATA_DIR=${DATA_DIR} build revision=${MEETINGSCRIBE_BUILD_REVISION}"

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

terminate_owned_service() {
    # 只終止本 script 啟動的 SERVER_PID 與其 pgrep -P 範圍內的 service child。
    local candidate
    for candidate in $(pgrep -P "$SERVER_PID" 2>/dev/null || true); do
        if [[ "$(ps -p "$candidate" -o command= 2>/dev/null || true)" == *"backend.main:app"* ]]; then
            kill "$candidate" 2>/dev/null || true
        fi
    done
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
}

cleanup_pid_file() {
    if [ -f "$PID_FILE" ] && [ "$(<"$PID_FILE")" = "$SERVER_PID" ]; then
        rm -f "$PID_FILE"
    fi
}

shutdown_owned_service() {
    if [ -n "${SERVER_PID:-}" ]; then
        terminate_owned_service
    fi
    cleanup_pid_file
}
trap shutdown_owned_service EXIT

for attempt in $(seq 1 30); do
    HEALTH_JSON="$(curl --fail --silent --show-error "http://127.0.0.1:$PORT/api/health" 2>/dev/null || true)"
    if [ -n "$HEALTH_JSON" ]; then
        HEALTH_REVISION="$(printf '%s' "$HEALTH_JSON" | "$PROJECT_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin).get("build_revision") or "")' 2>/dev/null)" || HEALTH_REVISION=""
        if [ -z "$HEALTH_REVISION" ]; then
            error "/api/health 回應缺少可解析的 build_revision；終止本 script 啟動的服務。"
            exit 1
        fi
        if [ "$HEALTH_REVISION" != "$MEETINGSCRIBE_BUILD_REVISION" ]; then
            error "health build_revision（${HEALTH_REVISION}）與啟動 revision（${MEETINGSCRIBE_BUILD_REVISION}）不一致；終止本 script 啟動的服務。"
            exit 1
        fi
        SERVICE_PID="$(find_service_pid)"
        echo "$SERVICE_PID" > "$PID_FILE"
        trap - EXIT
        success "服務已就緒：http://127.0.0.1:${PORT}（PID ${SERVICE_PID}，build revision ${MEETINGSCRIBE_BUILD_REVISION}）"
        exit 0
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        error "服務程序已提前結束；請查看 $LOG_FILE"
        exit 1
    fi
    sleep 1
done

error "服務未在 30 秒內通過 /api/health revision 驗證；請查看 $LOG_FILE。"
exit 1
