#!/bin/bash
# ============================================================
# MeetingScribe 服務啟動腳本 v3.5.5
# 使用 conda meetingscribe 環境，包含環境驗證
# ============================================================

cd /Users/hsiaojohnny/dev/convert
export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
export PYTHONPATH=/Users/hsiaojohnny/dev/convert:$PYTHONPATH
export KMP_DUPLICATE_LIB_OK=TRUE

PYTHON="/opt/anaconda3/envs/meetingscribe/bin/python"

# 環境驗證（失敗則中止）
echo "🔍 執行環境驗證..."
if [ -f "scripts/verify_env.py" ]; then
    $PYTHON scripts/verify_env.py
    if [ $? -ne 0 ]; then
        echo "❌ 環境驗證失敗，中止啟動"
        exit 1
    fi
fi

# 啟動服務
echo "🚀 啟動 MeetingScribe 服務..."
$PYTHON -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 9527 \
  --reload \
  2>&1 | tee /tmp/uvicorn-service.log
