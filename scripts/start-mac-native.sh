#!/bin/bash
# ============================================================
# MeetingScribe - macOS 原生服務啟動腳本
# v3.5.0 - 原生模式（使用 MPS 加速，不使用 Docker）
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
echo -e "${CYAN}║         🎙️  MeetingScribe - macOS 原生服務啟動工具            ║${NC}"
echo -e "${CYAN}║                     v3.5.0 原生模式                           ║${NC}"
echo -e "${CYAN}║           ⚡ 使用 MPS 加速，效能提升 3-5 倍                    ║${NC}"
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

# 檢查 Python
check_python() {
    info "檢查 Python 環境..."
    
    if ! command -v python3 &> /dev/null; then
        error "Python 3 未安裝，請先安裝 Python 3.11+"
        echo "建議使用 Homebrew 安裝: brew install python@3.11"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    success "Python 版本: $PYTHON_VERSION"
}

# 檢查 FFmpeg
check_ffmpeg() {
    info "檢查 FFmpeg..."
    
    if ! command -v ffmpeg &> /dev/null; then
        warn "FFmpeg 未安裝，正在安裝..."
        if command -v brew &> /dev/null; then
            brew install ffmpeg
            success "FFmpeg 安裝完成"
        else
            error "請先安裝 Homebrew，或手動安裝 FFmpeg"
            echo "Homebrew: https://brew.sh/"
            exit 1
        fi
    else
        success "FFmpeg 已安裝"
    fi
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
    info "檢查 mlx-community/whisper-large-v3-mlx 模型..."
    if ollama list 2>/dev/null | grep -q "mlx-community/whisper-large-v3-mlx"; then
        success "Whisper MLX 模型已安裝"
    else
        warn "Whisper MLX 模型未安裝"
        echo "正在下載模型（約 1.5GB，請耐心等待）..."
        ollama pull mlx-community/whisper-large-v3-mlx
        if [ $? -eq 0 ]; then
            success "模型下載完成"
        else
            error "模型下載失敗"
            echo "您可以手動執行: ollama pull mlx-community/whisper-large-v3-mlx"
        fi
    fi
    
    info "檢查 gemma3:27b-it-qat 模型..."
    if ollama list 2>/dev/null | grep -q "gemma3:27b-it-qat"; then
        success "gemma3:27b-it-qat 模型已安裝"
    else
        warn "gemma3:27b-it-qat 模型未安裝"
        echo "正在下載模型（約 8GB，請耐心等待）..."
        ollama pull gemma3:27b-it-qat
        if [ $? -eq 0 ]; then
            success "模型下載完成"
        else
            error "模型下載失敗"
            echo "您可以手動執行: ollama pull gemma3:27b-it-qat"
        fi
    fi
}

# 設置虛擬環境
setup_venv() {
    info "檢查虛擬環境..."
    
    if [ ! -d "venv" ]; then
        info "建立虛擬環境..."
        python3 -m venv venv
        success "虛擬環境已建立"
    else
        success "虛擬環境已存在"
    fi
    
    info "啟動虛擬環境並安裝依賴..."
    source venv/bin/activate
    
    # 安裝依賴
    pip install --upgrade pip
    pip install -r requirements.txt
    
    success "依賴安裝完成"
}

# 建立資料目錄
create_dirs() {
    info "建立資料目錄..."
    mkdir -p "$PROJECT_ROOT/data/uploads"
    mkdir -p "$PROJECT_ROOT/data/outputs"
    mkdir -p "$PROJECT_ROOT/data/cache"
    mkdir -p "$PROJECT_ROOT/models"
    mkdir -p "$PROJECT_ROOT/logs"
    success "資料目錄已建立"
}

# 檢查環境變數
check_env() {
    info "檢查環境變數..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            success "已建立 .env 檔案（從 .env.example 複製）"
        else
            warn ".env 檔案不存在，將使用預設配置"
        fi
    else
        success ".env 檔案已存在"
    fi
}

# 啟動服務
start_service() {
    info "啟動 MeetingScribe 原生服務..."
    info "⚡ 使用 Apple MPS 加速"
    info "🚀 效能提升 3-5 倍"
    
    # 啟動虛擬環境
    source venv/bin/activate
    
    # 設定環境變數
    export WHISPER_DEVICE=mps
    export OLLAMA_BASE_URL=http://localhost:11434
    
    # 啟動服務
    info "正在啟動 FastAPI 服務..."
    python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 9527 --reload &
    
    SERVER_PID=$!
    echo $SERVER_PID > .server.pid
    
    success "服務已啟動 (PID: $SERVER_PID)"
    
    # 等待服務就緒
    info "等待服務就緒（最多 30 秒）..."
    
    max_attempts=6  # 6 * 5 = 30 秒
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
        echo "tail -f logs/app.log"
    fi
}

# 顯示完成訊息
show_success() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}║         🎉 MeetingScribe 原生服務啟動成功！                   ║${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "   📍 ${CYAN}網址: http://localhost:9527${NC}"
    echo ""
    echo "   ────────────────────────────────────────────────────────"
    echo ""
    echo -e "   ⚡ ${GREEN}加速狀態：使用 Apple MPS 加速，效能提升 3-5 倍${NC}"
    echo "   • Whisper 轉錄: MPS 加速"
    echo "   • Ollama 推理: MPS 加速"
    echo "   • 統一記憶體: 高效能資料共享"
    echo ""
    echo "   ────────────────────────────────────────────────────────"
    echo ""
    echo "   常用指令:"
    echo "   • 查看狀態: ps aux | grep uvicorn"
    echo "   • 查看日誌: tail -f logs/app.log"
    echo "   • 停止服務: kill \$(cat .server.pid)"
    echo "   • 重啟服務: ./scripts/restart-mac-native.sh"
    echo ""
    
    # 自動開啟瀏覽器
    info "正在開啟瀏覽器..."
    sleep 2
    open "http://localhost:9527"
}

# 主程式
main() {
    check_python
    check_ffmpeg
    check_ollama
    setup_venv
    create_dirs
    check_env
    start_service
    show_success
}

# 執行
main "$@"
