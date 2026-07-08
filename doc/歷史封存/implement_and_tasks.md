# 政府智慧會議紀錄生成系統 實施計畫與任務清單

> **版本**：v2.0（審查後修訂版）  
> **建立日期**：2025-12-18  
> **狀態**：待批准  
> **關聯文件**：[系統改善計劃.md](./系統改善計劃.md)

---

## 📋 審查摘要

### 🔍 第一性原理深度審查發現的盲點

經過深度審查，我在原始計劃中發現以下**關鍵盲點**並已在本文件中修正：

| # | 盲點 | 風險等級 | 修正方案 |
|---|------|----------|----------|
| 1 | **多個啟動腳本衝突** | 🔴 Critical | 統一為單一啟動腳本 |
| 2 | **venv 指向錯誤 Python** | 🔴 Critical | 刪除 venv，統一用 conda |
| 3 | **scripts/start-mac-native.sh 使用 venv** | 🔴 Critical | 修改為使用 conda |
| 4 | **未考慮 frontend 靜態檔案服務** | 🟡 Medium | 確認 FastAPI 靜態掛載 |
| 5 | **未定義回滾策略** | 🟡 Medium | 新增回滾步驟 |
| 6 | **未定義測試音檔來源** | 🟡 Medium | 使用現有測試檔案 |

### 修正後的問題追蹤鏈

```
問題表徵：上傳音訊檔案後處理失敗
    ↓
直接原因：No module named 'av'
    ↓
根本原因 1：多個啟動腳本使用不同環境
    - start_service.sh 使用 conda meetingscribe ✅
    - scripts/start-mac-native.sh 使用 venv ❌
    - 用戶可能執行了錯誤的腳本
    ↓
根本原因 2：venv 環境配置錯誤
    - venv/bin/python3 -> /opt/anaconda3/bin/python3 (base 環境)
    - base 環境無 av、mlx-whisper
    - 導致 ImportError
    ↓
根本原因 3：依賴未統一管理
    - conda meetingscribe 有完整依賴 ✅
    - venv 缺少關鍵依賴 ❌
    - 兩套環境造成混淆
```

---

## 🎯 實施目標

### 成功標準（必須全部達成）

1. ✅ 上傳 50MB M4A 檔案成功轉錄
2. ✅ 無任何 `ImportError` 或 `ModuleNotFoundError`
3. ✅ 任務最終狀態為 `completed`
4. ✅ 日誌檔案正確生成於 `data/logs/` 目錄
5. ✅ 環境驗證腳本 100% 通過

### 技術邊界

| 項目 | 範圍內 | 範圍外 |
|------|--------|--------|
| 環境 | macOS + conda | Docker、Windows |
| Whisper | MLX-Whisper（主）、Faster-Whisper（備） | cloud whisper |
| LLM | Ollama、LM Studio（可選降級） | Gemini API |
| 測試 | 功能測試、整合測試 | 效能測試、壓力測試 |

---

## 📦 Phase 1：緊急環境修復

### 1.1 刪除混亂的 venv 環境

**任務描述**：移除造成混淆的 venv 目錄，統一使用 conda 環境

**技術棧**：Bash

**實施步驟**：
```bash
# 步驟 1：備份（以防萬一）
mv /Users/hsiaojohnny/dev/convert/venv /Users/hsiaojohnny/dev/convert/venv.backup.$(date +%Y%m%d)

# 步驟 2：確認刪除
ls -la /Users/hsiaojohnny/dev/convert/ | grep venv
```

**錯誤處理**：
- 若備份失敗：檢查磁碟空間
- 若需回滾：`mv venv.backup.* venv`

**驗收標準**：
| 檢查項目 | 預期結果 | 測試命令 |
|----------|----------|----------|
| venv 目錄不存在 | 無 venv 目錄 | `[ ! -d venv ] && echo "PASS"` |
| 備份存在 | 有 venv.backup.* | `ls -d venv.backup.* && echo "PASS"` |

---

### 1.2 修復所有啟動腳本

**任務描述**：統一所有啟動腳本使用 conda meetingscribe 環境

**技術棧**：Bash、Shell Script

**修改檔案清單**：

#### 1.2.1 修改 `scripts/start-mac-native.sh`

**修改前**（第 140-152 行）：
```bash
setup_venv() {
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
}
```

**修改後**：
```bash
setup_conda_env() {
    info "啟用 conda meetingscribe 環境..."
    
    # 檢查 conda 環境是否存在
    if [ ! -d "/opt/anaconda3/envs/meetingscribe" ]; then
        error "conda meetingscribe 環境不存在"
        error "請執行: conda create -n meetingscribe python=3.10"
        exit 1
    fi
    
    # 啟用 conda 環境
    export PATH="/opt/anaconda3/envs/meetingscribe/bin:$PATH"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    export KMP_DUPLICATE_LIB_OK=TRUE
    
    success "conda meetingscribe 環境已啟用"
}
```

**修改前**（第 203 行）：
```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 9527 --reload &
```

**修改後**：
```bash
/opt/anaconda3/envs/meetingscribe/bin/python -m uvicorn backend.main:app \
    --host 0.0.0.0 --port 9527 --reload &
```

#### 1.2.2 修改 `scripts/service_manager.sh`

確保使用相同的 conda 環境路徑。

#### 1.2.3 確認 `start_service.sh`

已正確配置，無需修改。

**驗收標準**：
| 檢查項目 | 預期結果 | 測試命令 |
|----------|----------|----------|
| 無 venv 引用 | grep 無結果 | `grep -r "venv" scripts/*.sh \| wc -l` 應為 0 |
| 使用 conda 路徑 | 有 meetingscribe | `grep "meetingscribe" scripts/start-mac-native.sh` |

---

### 1.3 建立環境驗證腳本

**任務描述**：建立啟動前自動執行的環境檢查腳本

**技術棧**：Python 3.10+

**檔案路徑**：`scripts/verify_env.py`

**完整程式碼**：
```python
#!/usr/bin/env python3
"""
政府智慧會議紀錄生成系統 環境驗證腳本 v1.0
在服務啟動前執行，確保所有依賴可用
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Tuple, List

# 顏色輸出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header():
    print(f"""
{Colors.BLUE}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║         🔍 政府智慧會議紀錄生成系統 環境驗證工具 v1.0                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")

def check_python_version() -> Tuple[bool, str]:
    """檢查 Python 版本"""
    version = sys.version_info
    if version < (3, 10):
        return False, f"Python {version.major}.{version.minor} 不支援，需要 3.10+"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"

def check_python_path() -> Tuple[bool, str]:
    """檢查 Python 執行路徑"""
    path = sys.executable
    if "meetingscribe" in path:
        return True, f"使用 conda meetingscribe 環境"
    elif "venv" in path:
        return False, f"使用 venv 環境（應使用 conda meetingscribe）"
    else:
        return False, f"未知環境: {path}"

def check_ffmpeg() -> Tuple[bool, str]:
    """檢查 FFmpeg"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        version = result.stdout.split('\n')[0] if result.returncode == 0 else "版本未知"
        return True, version[:50]
    except FileNotFoundError:
        return False, "FFmpeg 未安裝"
    except subprocess.TimeoutExpired:
        return False, "FFmpeg 回應超時"

def check_module(module_name: str, display_name: str) -> Tuple[bool, str]:
    """檢查 Python 模組"""
    try:
        mod = __import__(module_name)
        version = getattr(mod, '__version__', '版本未知')
        return True, f"{display_name} v{version}"
    except ImportError as e:
        return False, f"{display_name}: {e}"

def check_critical_modules() -> List[Tuple[bool, str]]:
    """檢查所有關鍵模組"""
    modules = [
        ("av", "PyAV (音訊處理)"),
        ("faster_whisper", "Faster-Whisper (語音轉錄)"),
        ("fastapi", "FastAPI (Web 框架)"),
        ("uvicorn", "Uvicorn (ASGI 伺服器)"),
        ("loguru", "Loguru (日誌系統)"),
        ("pydantic", "Pydantic (資料驗證)"),
        ("httpx", "HTTPX (HTTP 客戶端)"),
    ]
    
    results = []
    for module, name in modules:
        results.append(check_module(module, name))
    
    return results

def check_optional_modules() -> List[Tuple[bool, str]]:
    """檢查可選模組"""
    modules = [
        ("mlx_whisper", "MLX-Whisper (MPS 加速)"),
        ("mlx", "MLX (Apple ML 框架)"),
    ]
    
    results = []
    for module, name in modules:
        results.append(check_module(module, name))
    
    return results

def check_directories() -> List[Tuple[bool, str]]:
    """檢查必要目錄"""
    base_path = Path(__file__).parent.parent
    
    required_dirs = [
        base_path / "data" / "uploads",
        base_path / "data" / "outputs",
        base_path / "data" / "logs",
        base_path / "data" / "cache",
    ]
    
    results = []
    for dir_path in required_dirs:
        if dir_path.exists():
            results.append((True, f"目錄存在: {dir_path.name}"))
        else:
            # 嘗試建立
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                results.append((True, f"目錄已建立: {dir_path.name}"))
            except Exception as e:
                results.append((False, f"無法建立目錄 {dir_path.name}: {e}"))
    
    return results

def run_all_checks() -> bool:
    """執行所有檢查"""
    print_header()
    
    all_passed = True
    critical_failed = False
    
    # 1. Python 環境
    print(f"{Colors.BLUE}【Python 環境】{Colors.RESET}")
    
    ok, msg = check_python_version()
    status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
    print(f"  {status} Python 版本: {msg}")
    if not ok:
        critical_failed = True
    
    ok, msg = check_python_path()
    status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
    print(f"  {status} 執行環境: {msg}")
    if not ok:
        critical_failed = True
    
    # 2. 系統依賴
    print(f"\n{Colors.BLUE}【系統依賴】{Colors.RESET}")
    
    ok, msg = check_ffmpeg()
    status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
    print(f"  {status} FFmpeg: {msg}")
    if not ok:
        critical_failed = True
    
    # 3. 關鍵模組
    print(f"\n{Colors.BLUE}【關鍵模組】（必須全部通過）{Colors.RESET}")
    
    for ok, msg in check_critical_modules():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
        print(f"  {status} {msg}")
        if not ok:
            critical_failed = True
    
    # 4. 可選模組
    print(f"\n{Colors.BLUE}【可選模組】（建議安裝）{Colors.RESET}")
    
    for ok, msg in check_optional_modules():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.YELLOW}⚠️{Colors.RESET}"
        print(f"  {status} {msg}")
    
    # 5. 目錄結構
    print(f"\n{Colors.BLUE}【目錄結構】{Colors.RESET}")
    
    for ok, msg in check_directories():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
        print(f"  {status} {msg}")
        if not ok:
            all_passed = False
    
    # 最終結果
    print("\n" + "=" * 60)
    
    if critical_failed:
        print(f"{Colors.RED}❌ 環境驗證失敗 - 存在關鍵問題，無法啟動服務{Colors.RESET}")
        print(f"\n{Colors.YELLOW}建議修復步驟：{Colors.RESET}")
        print("  1. 確認使用 conda meetingscribe 環境")
        print("  2. 執行: conda activate meetingscribe")
        print("  3. 執行: conda install -c conda-forge av ffmpeg")
        print("  4. 執行: pip install faster-whisper mlx-whisper")
        return False
    else:
        print(f"{Colors.GREEN}✅ 環境驗證通過 - 可以啟動服務{Colors.RESET}")
        return True

if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
```

**驗收標準**：
| 檢查項目 | 預期結果 | 測試命令 |
|----------|----------|----------|
| 腳本可執行 | 退出碼 0 | `python scripts/verify_env.py && echo "PASS"` |
| 偵測錯誤環境 | 退出碼 1 | `venv/bin/python scripts/verify_env.py; [ $? -eq 1 ] && echo "PASS"` |
| 所有模組通過 | 無 ❌ 輸出 | `python scripts/verify_env.py 2>&1 \| grep -c "❌"` 應為 0 |

---

### 1.4 整合驗證到啟動流程

**任務描述**：在服務啟動前自動執行環境驗證

**修改 `start_service.sh`**：

```bash
#!/bin/bash
cd /Users/hsiaojohnny/dev/convert
export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
export PYTHONPATH=/Users/hsiaojohnny/dev/convert:$PYTHONPATH
export KMP_DUPLICATE_LIB_OK=TRUE

# 環境驗證（失敗則中止）
echo "🔍 執行環境驗證..."
/opt/anaconda3/envs/meetingscribe/bin/python scripts/verify_env.py
if [ $? -ne 0 ]; then
    echo "❌ 環境驗證失敗，中止啟動"
    exit 1
fi

# 啟動服務
echo "🚀 啟動 政府智慧會議紀錄生成系統 服務..."
/opt/anaconda3/envs/meetingscribe/bin/python -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 9527 \
  --reload \
  2>&1 | tee /tmp/uvicorn-service.log
```

**驗收標準**：
| 檢查項目 | 預期結果 | 測試命令 |
|----------|----------|----------|
| 驗證失敗時中止 | 不啟動服務 | 模擬環境錯誤後執行 |
| 驗證通過後啟動 | 服務運行 | `curl http://localhost:9527/api/health` |

---

## 📦 Phase 2：日誌系統實作

### 2.1 升級日誌系統

**任務描述**：實作完整的結構化日誌系統

**技術棧**：Loguru 0.7.2

**修改檔案**：`backend/core/logger.py`

**完整程式碼**：
```python
"""
政府智慧會議紀錄生成系統 結構化日誌系統 v2.0

特性：
- 控制台彩色輸出（開發模式）
- 檔案日誌（每日輪轉，保留 30 天）
- 錯誤日誌（獨立檔案，保留 90 天）
- JSON 結構化日誌（用於分析）
- 任務追蹤 ID 綁定
"""

import sys
import os
from pathlib import Path
from loguru import logger

# 從環境變數或預設值取得設定
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATA_DIR = os.getenv("DATA_DIR", str(Path(__file__).parent.parent.parent / "data"))


def setup_logger():
    """設定日誌系統"""
    # 移除預設處理器
    logger.remove()
    
    # 確保日誌目錄存在
    log_dir = Path(DATA_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 控制台輸出（彩色，人類可讀）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # 2. 檔案日誌 - 所有級別
    logger.add(
        str(log_dir / "app_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} | {extra} | {message}",
        level="DEBUG",
        rotation="00:00",      # 每天午夜輪轉
        retention="30 days",   # 保留 30 天
        compression="zip",     # 壓縮舊日誌
        encoding="utf-8",
        enqueue=True,          # 非同步寫入
    )
    
    # 3. 錯誤日誌（僅 ERROR 和 CRITICAL）
    logger.add(
        str(log_dir / "error_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} | {message}\n{exception}",
        level="ERROR",
        rotation="100 MB",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
    
    # 4. JSON 結構化日誌（用於日誌聚合系統）
    logger.add(
        str(log_dir / "structured_{time:YYYY-MM-DD}.jsonl"),
        serialize=True,
        level="INFO",
        rotation="100 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
    )
    
    logger.info("日誌系統初始化完成", log_dir=str(log_dir))
    
    return logger


def get_task_logger(task_id: str):
    """取得帶有任務 ID 的日誌器"""
    return logger.bind(task_id=task_id)


# 初始化日誌
log = setup_logger()
```

**驗收標準**：
| 檢查項目 | 預期結果 | 測試命令 |
|----------|----------|----------|
| app 日誌存在 | 檔案存在 | `ls data/logs/app_*.log` |
| error 日誌存在 | 檔案存在 | `ls data/logs/error_*.log` |
| JSON 日誌有效 | 可解析 | `head -1 data/logs/structured_*.jsonl \| python -m json.tool` |
| 任務 ID 綁定 | 日誌含 task_id | `grep "task_id" data/logs/app_*.log` |

---

## 📦 Phase 3：完整功能測試

### 3.1 建立測試腳本

**任務描述**：建立自動化測試腳本驗證所有功能

**檔案路徑**：`scripts/test_full_pipeline.py`

**完整程式碼**：
```python
#!/usr/bin/env python3
"""
政府智慧會議紀錄生成系統 完整管線測試 v1.0
測試從上傳到結果生成的完整流程
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime

# 設定
API_BASE = "http://127.0.0.1:9527"
TEST_FILE = Path(__file__).parent.parent / "input" / "test_meeting_1.wav"
TIMEOUT = 300  # 5 分鐘超時

class TestResult:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        
    def add(self, name: str, passed: bool, message: str = ""):
        self.tests.append({
            "name": name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            
    def summary(self) -> str:
        total = self.passed + self.failed
        return f"測試結果: {self.passed}/{total} 通過"
    
    def all_passed(self) -> bool:
        return self.failed == 0

def test_health_check(result: TestResult):
    """測試健康檢查 API"""
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=10)
        if resp.status_code == 200:
            result.add("健康檢查", True, "API 回應正常")
        else:
            result.add("健康檢查", False, f"狀態碼: {resp.status_code}")
    except Exception as e:
        result.add("健康檢查", False, f"連線失敗: {e}")

def test_upload_file(result: TestResult) -> str:
    """測試檔案上傳"""
    if not TEST_FILE.exists():
        result.add("檔案上傳", False, f"測試檔案不存在: {TEST_FILE}")
        return None
    
    try:
        with open(TEST_FILE, 'rb') as f:
            files = {'file': (TEST_FILE.name, f, 'audio/wav')}
            data = {'processing_mode': 'local'}
            resp = requests.post(
                f"{API_BASE}/api/upload",
                files=files,
                data=data,
                timeout=60
            )
        
        if resp.status_code == 200:
            task_id = resp.json().get('task_id')
            result.add("檔案上傳", True, f"任務 ID: {task_id}")
            return task_id
        else:
            result.add("檔案上傳", False, f"狀態碼: {resp.status_code}")
            return None
    except Exception as e:
        result.add("檔案上傳", False, f"上傳失敗: {e}")
        return None

def test_task_completion(result: TestResult, task_id: str):
    """測試任務完成"""
    if not task_id:
        result.add("任務完成", False, "無任務 ID")
        return
    
    start_time = time.time()
    
    while time.time() - start_time < TIMEOUT:
        try:
            resp = requests.get(f"{API_BASE}/api/tasks/{task_id}", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get('status')
                
                if status == 'completed':
                    result.add("任務完成", True, f"耗時: {time.time() - start_time:.1f}秒")
                    return
                elif status == 'failed':
                    error = data.get('error_message', '未知錯誤')
                    result.add("任務完成", False, f"任務失敗: {error}")
                    return
        except Exception as e:
            pass
        
        time.sleep(2)
    
    result.add("任務完成", False, f"超時 ({TIMEOUT}秒)")

def test_log_files(result: TestResult):
    """測試日誌檔案"""
    log_dir = Path(__file__).parent.parent / "data" / "logs"
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 檢查 app 日誌
    app_log = log_dir / f"app_{today}.log"
    if app_log.exists() and app_log.stat().st_size > 0:
        result.add("App 日誌", True, f"大小: {app_log.stat().st_size} bytes")
    else:
        result.add("App 日誌", False, "日誌不存在或為空")
    
    # 檢查 JSON 日誌
    json_log = log_dir / f"structured_{today}.jsonl"
    if json_log.exists():
        try:
            with open(json_log) as f:
                first_line = f.readline()
                json.loads(first_line)
            result.add("JSON 日誌", True, "格式有效")
        except:
            result.add("JSON 日誌", False, "JSON 格式無效")
    else:
        result.add("JSON 日誌", False, "日誌不存在")

def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("🧪 政府智慧會議紀錄生成系統 完整管線測試")
    print("=" * 60)
    print()
    
    result = TestResult()
    
    # 測試 1: 健康檢查
    print("📋 測試 1: 健康檢查...")
    test_health_check(result)
    
    # 測試 2: 檔案上傳
    print("📋 測試 2: 檔案上傳...")
    task_id = test_upload_file(result)
    
    # 測試 3: 任務完成
    if task_id:
        print("📋 測試 3: 等待任務完成...")
        test_task_completion(result, task_id)
    
    # 測試 4: 日誌檔案
    print("📋 測試 4: 日誌檔案...")
    test_log_files(result)
    
    # 輸出結果
    print()
    print("=" * 60)
    print("📊 測試報告")
    print("=" * 60)
    
    for test in result.tests:
        status = "✅" if test['passed'] else "❌"
        print(f"  {status} {test['name']}: {test['message']}")
    
    print()
    print("-" * 60)
    print(f"  {result.summary()}")
    print("-" * 60)
    
    if result.all_passed():
        print("🎉 所有測試通過！")
        return 0
    else:
        print("❌ 存在失敗的測試")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
```

**驗收標準**：
| 檢查項目 | 預期結果 | 測試命令 |
|----------|----------|----------|
| 測試全部通過 | 退出碼 0 | `python scripts/test_full_pipeline.py` |
| 無 ❌ 輸出 | 全 ✅ | 檢視輸出 |

---

## 📦 Phase 4：文件更新與提交

### 4.1 更新 CHANGELOG.md

**任務描述**：記錄本次修復內容

### 4.2 Git 提交

**任務描述**：提交所有修改並附詳細 zh-TW 說明

---

## 📋 任務檢查清單

### Phase 1 檢查清單（緊急修復）
- [x] 1.1 刪除 venv 目錄
- [x] 1.2 修復 scripts/start-mac-native.sh
- [x] 1.3 建立 scripts/verify_env.py
- [x] 1.4 整合驗證到啟動流程
- [x] 1.5 執行環境驗證通過

### Phase 2 檢查清單（日誌系統）
- [x] 2.1 升級 backend/core/logger.py
- [x] 2.2 確認日誌檔案生成
- [x] 2.3 確認 JSON 格式有效

### Phase 3 檢查清單（測試驗證）
- [x] 3.1 建立 scripts/test_full_pipeline.py
- [x] 3.2 執行完整管線測試
- [x] 3.3 所有測試通過

### Phase 4 檢查清單（文件提交）
- [x] 4.1 更新 CHANGELOG.md
- [x] 4.2 Git add, commit

---

## 🔙 回滾策略

若實施失敗，執行以下回滾步驟：

```bash
# 1. 還原 venv
mv venv.backup.* venv

# 2. 還原啟動腳本
git checkout scripts/start-mac-native.sh
git checkout start_service.sh

# 3. 還原日誌系統
git checkout backend/core/logger.py
```

---

## 📝 批准紀錄

| 項目 | 狀態 | 批准人 | 日期 |
|------|------|--------|------|
| 整體計劃 | ✅ 已完成 | | |
| Phase 1 緊急修復 | ✅ 已完成 | | |
| Phase 2 日誌系統 | ✅ 已完成 | | |
| Phase 3 測試驗證 | ✅ 已完成 | | |
| Phase 4 文件提交 | ✅ 已完成 | | |

---

**請確認是否批准此實施計畫？批准後將開始執行。**
