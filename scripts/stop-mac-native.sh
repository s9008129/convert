#!/bin/bash
# ============================================================
# MeetingScribe - macOS 原生服務停止腳本
# v3.5.0 - 原生模式
# ============================================================

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 取得腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 進入專案目錄
cd "$PROJECT_ROOT"

echo ""
echo -e "${BLUE}[INFO]${NC} 正在停止 MeetingScribe 服務..."

# 停止服務
if [ -f ".server.pid" ]; then
    PID=$(cat .server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        sleep 2
        
        # 確認是否停止
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}[⚠️]${NC} 服務未完全停止，強制終止..."
            kill -9 $PID
        fi
        
        rm .server.pid
        echo -e "${GREEN}[✓]${NC} 服務已停止"
    else
        echo -e "${YELLOW}[⚠️]${NC} 服務 PID 不存在，可能已經停止"
        rm .server.pid
    fi
else
    echo -e "${YELLOW}[⚠️]${NC} 找不到 .server.pid 檔案"
    # 嘗試使用 pkill
    echo -e "${BLUE}[INFO]${NC} 嘗試使用進程名稱停止服務..."
    pkill -f "uvicorn backend.main:app"
    sleep 2
    echo -e "${GREEN}[✓]${NC} 服務已停止"
fi

echo ""
