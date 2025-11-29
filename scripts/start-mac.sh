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
    info "檢查 Gemma3:12B 模型..."
    if ollama list 2>/dev/null | grep -q "gemma3:12b"; then
        success "Gemma3:12B 模型已安裝"
    else
        warn "Gemma3:12B 模型未安裝"
        echo "正在下載模型（約 8GB，請耐心等待）..."
        ollama pull gemma3:12b
        if [ $? -eq 0 ]; then
            success "模型下載完成"
        else
            error "模型下載失敗"
            echo "您可以手動執行: ollama pull gemma3:12b"
        fi
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
    check_docker
    check_ollama
    create_dirs
    start_service
    show_success
}

# 執行
main "$@"
