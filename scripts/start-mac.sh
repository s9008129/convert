#!/bin/bash
# ============================================================
# MeetingScribe - macOS 啟動腳本
# v2.2 - 完全隔離設計，不影響其他 Docker 服務
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
echo -e "${CYAN}║         🎙️  MeetingScribe - macOS 啟動工具                    ║${NC}"
echo -e "${CYAN}║                     v2.2 完全隔離版                           ║${NC}"
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

# 載入 macOS 本地覆蓋設定，讓 docker compose 也能讀到 LOCAL_LLM_MODEL_MAC
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

# 檢查 Docker
check_docker() {
    info "檢查 Docker Desktop..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker 未安裝，請先安裝 Docker Desktop"
        echo "下載地址: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker 未運行，請先啟動 Docker Desktop"
        echo "請點擊 Dock 中的 Docker 圖示啟動"
        exit 1
    fi
    
    success "Docker Desktop 運行中"
}

# 檢查 Ollama
check_ollama() {
    info "檢查 Ollama 服務..."
    
    if ! command -v ollama &> /dev/null; then
        warn "Ollama 未安裝"
        echo "下載地址: https://ollama.ai"
        echo "本地模式將無法使用，但雲端模式仍可正常運作"
        return 1
    fi
    
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        warn "Ollama 未運行，嘗試啟動..."
        open -a Ollama
        sleep 5
        
        if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
            warn "Ollama 啟動失敗，本地模式可能無法使用"
            return 1
        fi
    fi
    
    success "Ollama 服務運行中"
    
    # 檢查模型
    info "檢查 Ollama 模型..."
    if [ -n "$MAC_MODEL_OVERRIDE_SOURCE" ]; then
        info "使用 macOS 覆蓋模型: $MAC_OLLAMA_MODEL ($MAC_MODEL_OVERRIDE_SOURCE)"
    else
        info "使用預設 Gemma4 模型: $MAC_OLLAMA_MODEL"
    fi

    installed_models="$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}')"
    gemma4_models="$(printf '%s\n' "$installed_models" | grep '^gemma4:' || true)"

    if printf '%s\n' "$installed_models" | grep -qx "$MAC_OLLAMA_MODEL"; then
        success "目標模型已安裝: $MAC_OLLAMA_MODEL"
    elif [[ "$MAC_OLLAMA_MODEL" == gemma4:* ]] && [ -n "$gemma4_models" ]; then
        success "已找到可相容的 Gemma4 模型: $(echo "$gemma4_models" | paste -sd ', ' -)"
        echo "      應用程式會自動優先使用已安裝的 Gemma4 標籤"
    elif [ -n "$MAC_MODEL_OVERRIDE_SOURCE" ]; then
        warn "尚未安裝覆蓋模型: $MAC_OLLAMA_MODEL"
        echo "正在下載模型，請耐心等待..."
        if ollama pull "$MAC_OLLAMA_MODEL"; then
            success "模型下載完成"
        else
            error "模型下載失敗"
            echo "您可以手動執行: ollama pull $MAC_OLLAMA_MODEL"
        fi
    else
        warn "尚未安裝預設模型: $DEFAULT_OLLAMA_MODEL"
        echo "      若您的 Mac 記憶體較小，請先在 .env.local 設定 LOCAL_LLM_MODEL_MAC 為較小的 gemma4 標籤"
        echo "      若要使用預設模型，請手動執行: ollama pull $DEFAULT_OLLAMA_MODEL"
    fi
}

# 建立資料目錄
create_dirs() {
    info "建立資料目錄..."
    mkdir -p "$PROJECT_ROOT/data/uploads"
    mkdir -p "$PROJECT_ROOT/data/outputs"
    mkdir -p "$PROJECT_ROOT/data/cache"
    success "資料目錄已建立"
}

# 啟動服務
start_service() {
    info "啟動 MeetingScribe 服務..."
    info "🔒 使用獨立專案名稱: meetingscribe"
    info "🔒 使用獨立網路: meetingscribe-network"
    
    # 先清理舊的資源（僅限本專案）
    info "清理舊的容器和網路（僅 meetingscribe 專案）..."
    docker compose -p meetingscribe -f docker/docker-compose-mac.yml down --remove-orphans 2>/dev/null || true
    
    # 清理舊的隔離網路（如果存在）
    docker network rm meetingscribe-isolated-net 2>/dev/null || true
    
    # 使用 macOS 專用的 docker-compose 配置（帶專案名稱）
    docker compose -p meetingscribe -f docker/docker-compose-mac.yml up -d --build
    
    if [ $? -ne 0 ]; then
        error "服務啟動失敗"
        echo "請檢查錯誤訊息或執行以下命令查看日誌:"
        echo "docker compose -p meetingscribe -f docker/docker-compose-mac.yml logs"
        exit 1
    fi
    
    success "服務啟動中..."
    
    # 等待服務就緒
    info "等待服務就緒（最多 3 分鐘）..."
    
    max_attempts=36  # 36 * 5 = 180 秒
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
        warn "服務啟動時間較長，可能仍在初始化中"
        echo "您可以執行以下命令查看日誌:"
        echo "docker compose -p meetingscribe -f docker/docker-compose-mac.yml logs -f"
    fi
}

# 顯示完成訊息
show_success() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}║         🎉 MeetingScribe 啟動成功！                           ║${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "   📍 ${CYAN}網址: http://localhost:9527${NC}"
    echo ""
    echo "   ────────────────────────────────────────────────────────"
    echo ""
    echo -e "   🔒 ${GREEN}隔離狀態：完全隔離，不影響其他 Docker 服務${NC}"
    echo "   • 專案名稱: meetingscribe"
    echo "   • 獨立網路: meetingscribe-network (172.30.0.0/16)"
    echo ""
    echo "   ────────────────────────────────────────────────────────"
    echo ""
    echo "   常用指令:"
    echo "   • 查看狀態: docker compose -p meetingscribe ps"
    echo "   • 查看日誌: docker compose -p meetingscribe -f docker/docker-compose-mac.yml logs -f"
    echo "   • 停止服務: docker compose -p meetingscribe -f docker/docker-compose-mac.yml down"
    echo "   • 重啟服務: ./scripts/restart-mac.sh"
    echo ""
    
    # 自動開啟瀏覽器
    info "正在開啟瀏覽器..."
    sleep 2
    open "http://localhost:9527"
}

# 主程式
main() {
    load_local_overrides
    check_docker
    check_ollama
    create_dirs
    start_service
    show_success
}

# 執行
main "$@"
