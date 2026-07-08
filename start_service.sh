#!/bin/bash
# ============================================================
# 政府智慧會議紀錄生成系統 服務啟動腳本 v4.0
# 使用 conda meetingscribe 環境，包含環境驗證
# ============================================================
# 使用者導覽（給非技術同仁）：
# - 環境檢查：啟動前會先跑 verify_env.py，失敗就停止啟動。
# - 啟停流程：確認環境後才啟動 uvicorn，並即時輸出到畫面。
# - 清理步驟：服務輸出同步寫入 /tmp/uvicorn-service.log，便於故障排查。
# - 安全注意：固定使用 meetingscribe conda Python，避免混用錯誤環境。

# 步驟 1：切換到專案資料夾，避免在錯誤路徑啟動
cd /Users/hsiaojohnny/dev/convert
# 步驟 2：設定執行時需要的環境變數
export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
export PYTHONPATH=/Users/hsiaojohnny/dev/convert:$PYTHONPATH
export KMP_DUPLICATE_LIB_OK=TRUE

PYTHON="/Users/hsiaojohnny/miniconda3/envs/meetingscribe/bin/python"

# 環境驗證（失敗則中止）
echo "🔍 執行環境驗證..."
if [ -f "scripts/verify_env.py" ]; then
    # 若環境不完整就不啟動，避免服務在錯誤狀態下運行。
    $PYTHON scripts/verify_env.py
    if [ $? -ne 0 ]; then
        echo "❌ 環境驗證失敗，中止啟動"
        exit 1
    fi
fi

# 步驟 3：啟動 API 服務，並把輸出同步寫入畫面與日誌
echo "🚀 啟動 政府智慧會議紀錄生成系統 服務..."
$PYTHON -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 9527 \
  --reload \
  2>&1 | tee /tmp/uvicorn-service.log
