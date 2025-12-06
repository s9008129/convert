# macOS 部署指南

版本：v3.5.0  
更新日期：2025-12-06  
平台：macOS (Apple Silicon)

## 🚀 快速開始

### 1. 系統需求
- macOS 12.0+
- Python 3.8-3.12
- 16GB+ RAM
- Apple Silicon (推薦)

### 2. 安裝步驟
```bash
# 克隆專案
git clone https://github.com/s9008129/convert.git
cd convert

# 安裝依賴
pip install -r requirements.txt

# 配置環境
export DATA_DIR=/Users/你的使用者名稱/dev/convert/data
export PYTHONPATH=$(pwd):$PYTHONPATH

# 啟動服務
uvicorn backend.main:app --host 0.0.0.0 --port 9527
```

### 3. 訪問服務
http://localhost:9527

## 📝 詳細說明請參閱 README.md
