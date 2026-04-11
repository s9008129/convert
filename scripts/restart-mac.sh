#!/bin/bash
# ============================================================
# MeetingScribe - macOS 安全重啟腳本
# v2.2 - 僅重啟本專案服務，不影響其他 Docker 服務
# ============================================================

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 取得腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_LOCAL_PATH="$PROJECT_ROOT/.env.local"
DEFAULT_OLLAMA_MODEL="gemma4:31b"
MAC_OLLAMA_MODEL="$DEFAULT_OLLAMA_MODEL"
MAC_MODEL_OVERRIDE_SOURCE=""

# 專案名稱（確保隔離）
export COMPOSE_PROJECT_NAME="meetingscribe"

# 進入專案目錄
cd "$PROJECT_ROOT"

# 顯示標題
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}║         🔄 MeetingScribe - 安全重啟工具                       ║${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 函數：顯示訊息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[⚠️]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 移除 .env 類設定中常見的包覆引號，避免模型名稱夾帶字面引號
strip_wrapping_quotes() {
    local value="$1"

    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
        value="${value#\"}"
        value="${value%\"}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
        value="${value#\'}"
        value="${value%\'}"
    fi

    printf '%s' "$value"
}

# 載入 macOS 本地覆蓋設定，確保 compose 重新啟動時沿用 LOCAL_LLM_MODEL_MAC
load_local_overrides() {
    if [ -n "${LOCAL_LLM_MODEL_MAC:-}" ]; then
        MAC_OLLAMA_MODEL="$LOCAL_LLM_MODEL_MAC"
        MAC_MODEL_OVERRIDE_SOURCE="環境變數 LOCAL_LLM_MODEL_MAC"
        return
    fi

    if [ -f "$ENV_LOCAL_PATH" ]; then
        info "載入 macOS 本地覆蓋設定 (.env.local)..."
        while IFS= read -r raw_line || [ -n "$raw_line" ]; do
            line="${raw_line%$'\r'}"
            case "$line" in
                ''|'#'*) continue ;;
            esac

            if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                key="${BASH_REMATCH[1]}"
                value="${BASH_REMATCH[2]}"
                value="$(strip_wrapping_quotes "$value")"
                export "$key=$value"
            fi
        done < "$ENV_LOCAL_PATH"
    fi

    if [ -n "${LOCAL_LLM_MODEL_MAC:-}" ]; then
        MAC_OLLAMA_MODEL="$LOCAL_LLM_MODEL_MAC"
        MAC_MODEL_OVERRIDE_SOURCE=".env.local"
    fi
}

# 顯示其他 Docker 服務狀態
show_other_services() {
    info "其他 Docker 服務狀態（不會受到影響）："
    echo ""
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -v "meetingscribe" | head -10
    echo ""
}

# 安全重啟
safe_restart() {
    echo -e "${YELLOW}⚠️  重要提示：此操作僅會重啟 MeetingScribe 服務${NC}"
    echo -e "${GREEN}✓  其他 Docker 服務不會受到任何影響${NC}"
    echo ""
    
    show_other_services
    if [ -n "$MAC_MODEL_OVERRIDE_SOURCE" ]; then
        info "使用 macOS 覆蓋模型: $MAC_OLLAMA_MODEL ($MAC_MODEL_OVERRIDE_SOURCE)"
    else
        info "使用預設 Gemma4 模型: $MAC_OLLAMA_MODEL"
    fi
    echo ""
    
    info "正在停止 MeetingScribe 服務..."
    docker compose -p meetingscribe -f docker/docker-compose-mac.yml down
    
    if [ $? -eq 0 ]; then
        success "服務已停止"
    else
        warn "停止服務時遇到問題，繼續執行..."
    fi
    
    echo ""
    info "正在啟動 MeetingScribe 服務..."
    docker compose -p meetingscribe -f docker/docker-compose-mac.yml up -d
    
    if [ $? -ne 0 ]; then
        error "服務啟動失敗"
        echo "請檢查錯誤訊息或執行以下命令查看日誌:"
        echo "docker compose -p meetingscribe -f docker/docker-compose-mac.yml logs"
        exit 1
    fi
    
    success "服務正在啟動..."
    
    # 等待服務就緒
    info "等待服務就緒..."
    max_attempts=24  # 24 * 5 = 120 秒
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:9527/api/health &> /dev/null; then
            success "服務已就緒！"
            break
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 5
    done
    
    echo ""
    
    if [ $attempt -ge $max_attempts ]; then
        warn "服務可能仍在初始化中"
    fi
    
    echo ""
    info "驗證其他服務狀態（應該沒有變化）："
    show_other_services
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}║         🎉 MeetingScribe 重啟完成！                           ║${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "   📍 ${CYAN}網址: http://localhost:9527${NC}"
    echo ""
}

# 主程式
main() {
    load_local_overrides
    safe_restart
}

# 執行
main "$@"
