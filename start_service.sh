#!/bin/bash
cd /Users/hsiaojohnny/dev/convert
export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
export PYTHONPATH=/Users/hsiaojohnny/dev/convert:$PYTHONPATH

/opt/anaconda3/bin/python3 -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 9527 \
  --reload \
  2>&1 | tee /tmp/uvicorn-service.log
