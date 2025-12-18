#!/bin/bash
cd /Users/hsiaojohnny/dev/convert
export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
export PYTHONPATH=/Users/hsiaojohnny/dev/convert:$PYTHONPATH
export KMP_DUPLICATE_LIB_OK=TRUE

# 使用 meetingscribe conda 環境（包含 PyAV）
/opt/anaconda3/envs/meetingscribe/bin/python -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 9527 \
  --reload \
  2>&1 | tee /tmp/uvicorn-service.log
