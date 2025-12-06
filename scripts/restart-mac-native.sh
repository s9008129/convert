#!/bin/bash
# ============================================================
# MeetingScribe - macOS 原生服務重啟腳本
# v3.5.0 - 原生模式安全重啟
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

# 進入專案目錄
cd "$PROJECT_ROOT"

# 顯示標題
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}║         🔄 MeetingScribe - 原生服務重啟工具                    ║${NC}"
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

# 停止服務
stop_service() {
    info "正在停止 MeetingScribe 服務..."
    
    if [ -f ".server.pid" ]; then
        PID=$(cat .server.pid)
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            sleep 2
            
            # 確認是否停止
            if ps -p $PID > /dev/null 2>&1; then
                warn "服務未完全停止，強制終止..."
                kill -9 $PID
            fi
            
            rm .server.pid
            success "服務已停止"
        else
            warn "服務 PID 不存在，可能已經停止"
            rm .server.pid
        fi
    else
        warn "找不到 .server.pid 檔案"
        # 嘗試使用 pkill
        info "嘗試使用進程名稱停止服務..."
        pkill -f "uvicorn backend.main:app"
        sleep 2
        success "服務已停止"
    fi
}

# 啟動服務
start_service() {
    info "正在啟動 MeetingScribe 服務..."
    
    # 啟動虛擬環境
    source venv/bin/activate
    
    # 設定環境變數
    export WHISPER_DEVICE=mps
    export OLLAMA_BASE_URL=http://localhost:11434
    
    # 啟動服務
    python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 9527 --reload &
    
    SERVER_PID=$!
    echo $SERVER_PID > .server.pid
    
    success "服務已啟動 (PID: $SERVER_PID)"
    
    # 等待服務就緒
    info "等待服務就緒..."
    max_attempts=6
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
}

# 顯示完成訊息
show_success() {
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
    stop_service
    echo ""
    start_service
    show_success
}

# 執行
main "$@"
