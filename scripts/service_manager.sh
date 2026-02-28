#!/bin/bash

# ============================================
# MeetingScribe 服務管理快速指南
# v3.5.4 - macOS 原生模式
# ============================================
# 使用者導覽（給非技術同仁）：
# - 環境檢查：透過 /api/health 讀取版本與排隊資訊，確認服務是否在線。
# - 啟停流程：可從選單執行啟動/停止/重啟，並於每次操作後重新檢查狀態。
# - 清理步驟：停止與重啟都會先結束舊進程，避免同時存在多個服務實例。
# - 安全注意：SERVICE_NAME 請保持精準，避免匹配過廣導致誤關閉其他程序。

PROJECT_DIR="/Users/hsiaojohnny/dev/convert"
SERVICE_NAME="uvicorn backend.main:app"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  MeetingScribe 服務管理指南"
echo "========================================"

# 檢查服務狀態
check_status() {
    echo ""
    echo "📊 檢查服務狀態..."
    PID=$(ps aux | grep "$SERVICE_NAME" | grep -v grep | awk '{print $2}')
    
    if [ -n "$PID" ]; then
        echo -e "${GREEN}✅ 服務正在運行 (PID: $PID)${NC}"
        
        # 檢查版本
        VERSION=$(curl -s http://127.0.0.1:9527/api/health 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])" 2>/dev/null)
        if [ -n "$VERSION" ]; then
            echo -e "${GREEN}   版本: $VERSION${NC}"
        fi
        
        # 檢查排隊狀態
        QUEUE=$(curl -s http://127.0.0.1:9527/api/health 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['queue_status']['total_queued'])" 2>/dev/null)
        if [ -n "$QUEUE" ]; then
            echo -e "${GREEN}   排隊人數: $QUEUE${NC}"
        fi
    else
        echo -e "${RED}❌ 服務未運行${NC}"
    fi
}

# 顯示何時需要重啟
show_restart_guide() {
    echo ""
    echo "========================================"
    echo "  何時需要重啟服務？"
    echo "========================================"
    echo ""
    echo "✅ 必須手動重啟："
    echo "   • 環境變數變更（.env, config.yaml）"
    echo "   • 版本號變更（VERSION 檔案）"
    echo "   • 依賴套件更新（pip install）"
    echo "   • 靜態檔案變更（frontend/）"
    echo ""
    echo "⭐ 自動重載（不需重啟）："
    echo "   • Python 程式碼變更（backend/）"
    echo "   • 新增 .py 檔案"
    echo ""
}

# 主選單（提供常見維運操作，給非工程使用者快速選擇）
echo ""
echo "請選擇操作："
echo "1) 查看服務狀態"
echo "2) 啟動服務"
echo "3) 停止服務"
echo "4) 重啟服務"
echo "5) 查看服務日誌"
echo "6) 查看重啟指南"
echo "7) 退出"
echo ""
read -p "請輸入選項 (1-7): " choice

# 依照使用者輸入執行對應操作
case $choice in
    1)
        check_status
        ;;
    2)
        echo ""
        # 步驟：切到專案目錄後背景啟動服務
        echo "🚀 啟動服務..."
        cd "$PROJECT_DIR"
        ./start_service.sh &
        sleep 2
        check_status
        ;;
    3)
        echo ""
        # 步驟：先停止目前服務，再回報最新狀態
        echo "🛑 停止服務..."
        # 安全提醒：僅依 SERVICE_NAME 目標停用對應服務進程。
        pkill -f "$SERVICE_NAME"
        sleep 1
        check_status
        ;;
    4)
        echo ""
        # 步驟：先停再啟，確保服務用新設定啟動
        echo "🔄 重啟服務..."
        # 安全提醒：先關閉舊進程再啟動，避免埠號衝突與重複服務。
        pkill -f "$SERVICE_NAME"
        sleep 1
        cd "$PROJECT_DIR"
        ./start_service.sh &
        sleep 2
        check_status
        ;;
    5)
        echo ""
        echo "📋 查看服務日誌（Ctrl+C 退出）..."
        tail -f /tmp/uvicorn-service.log
        ;;
    6)
        show_restart_guide
        ;;
    7)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo -e "${RED}無效選項${NC}"
        exit 1
        ;;
esac
