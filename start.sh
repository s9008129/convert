#!/bin/bash
# 會議轉錄工具 - macOS/Linux 啟動腳本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================"
echo "     會議轉錄工具 - macOS/Linux 版"
echo "     本地 AI 語音轉逐字稿轉會議紀錄"
echo "============================================"
echo ""

# 檢查 Ollama
echo "[1/4] 檢查 Ollama 服務..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "      [OK] Ollama 服務正常"
else
    echo "      [!] Ollama 未運行，嘗試啟動..."
    ollama serve > /dev/null 2>&1 &
    sleep 5
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "      [OK] Ollama 已啟動"
    else
        echo "      [錯誤] 無法啟動 Ollama"
        echo "      請手動執行: ollama serve"
        exit 1
    fi
fi

# 檢查 GPU (macOS Metal 或 NVIDIA CUDA)
echo "[2/4] 檢查運算裝置..."
if [[ "$(uname)" == "Darwin" ]]; then
    echo "      [OK] macOS - 使用 Metal 加速"
elif command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo "      [OK] 偵測到 GPU: $GPU_NAME"
else
    echo "      [!] 將使用 CPU 模式"
fi

# 檢查 Python
echo "[3/4] 檢查 Python 環境..."
if [[ -f "python/bin/python" ]]; then
    PYTHON="python/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "      [錯誤] 找不到 Python"
    exit 1
fi
echo "      [OK] 使用 $PYTHON"

# 檢查依賴
$PYTHON -c "import yaml" 2>/dev/null || $PYTHON -m pip install pyyaml -q
$PYTHON -c "import httpx" 2>/dev/null || $PYTHON -m pip install httpx -q

# 檢查輸入檔案
echo "[4/4] 掃描輸入檔案..."
mkdir -p input output temp logs

FILE_COUNT=$(find input -type f \( -name "*.mp3" -o -name "*.mp4" -o -name "*.wav" -o -name "*.m4a" -o -name "*.mkv" -o -name "*.webm" -o -name "*.flac" \) 2>/dev/null | wc -l | tr -d ' ')

if [[ "$FILE_COUNT" -eq 0 ]]; then
    echo ""
    echo "      [提示] input 資料夾沒有音訊/視訊檔案"
    echo "      請將檔案放入: $SCRIPT_DIR/input"
    exit 1
fi

echo "      [OK] 找到 $FILE_COUNT 個待處理檔案"
echo ""

# 列出檔案
echo "待處理檔案："
find input -type f \( -name "*.mp3" -o -name "*.mp4" -o -name "*.wav" -o -name "*.m4a" -o -name "*.mkv" -o -name "*.webm" -o -name "*.flac" \) -exec basename {} \; | while read f; do
    echo "  * $f"
done
echo ""

# 確認執行
read -p "按 Enter 開始處理，或按 Ctrl+C 取消... "

# 執行主程式
echo ""
echo "[開始] 執行轉錄與摘要..."
echo "============================================"
echo ""

$PYTHON main.py

echo ""
echo "============================================"
echo "[完成] 輸出檔案位於: $SCRIPT_DIR/output"
echo "============================================"
echo ""
