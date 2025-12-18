#!/usr/bin/env python3
"""
MeetingScribe 完整管線測試 v1.0
測試從上傳到結果生成的完整流程

使用方式：
    python scripts/test_full_pipeline.py

退出碼：
    0 - 所有測試通過
    1 - 存在失敗的測試
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional


# 設定
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:9527")
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TEST_FILE = PROJECT_ROOT / "input" / "test_meeting_1.wav"
TIMEOUT = 300  # 5 分鐘超時


class Colors:
    """終端顏色代碼"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class TestResult:
    """測試結果收集器"""
    
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.start_time = datetime.now()
        
    def add(self, name: str, passed: bool, message: str = "", details: str = ""):
        """添加測試結果"""
        self.tests.append({
            "name": name,
            "passed": passed,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        
        # 即時顯示結果
        status = f"{Colors.GREEN}✅{Colors.RESET}" if passed else f"{Colors.RED}❌{Colors.RESET}"
        print(f"  {status} {name}: {message}")
        if details and not passed:
            print(f"      {Colors.YELLOW}詳情: {details}{Colors.RESET}")
            
    def summary(self) -> str:
        total = self.passed + self.failed
        duration = (datetime.now() - self.start_time).total_seconds()
        return f"測試結果: {self.passed}/{total} 通過 (耗時 {duration:.1f}秒)"
    
    def all_passed(self) -> bool:
        return self.failed == 0
    
    def generate_report(self) -> dict:
        """生成測試報告"""
        return {
            "summary": {
                "total": self.passed + self.failed,
                "passed": self.passed,
                "failed": self.failed,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": (datetime.now() - self.start_time).total_seconds()
            },
            "tests": self.tests
        }


def test_health_check(result: TestResult):
    """測試健康檢查 API"""
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            version = data.get('version', 'unknown')
            result.add("健康檢查", True, f"API 正常 (版本: {version})")
            return True
        else:
            result.add("健康檢查", False, f"狀態碼: {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        result.add("健康檢查", False, "無法連線到服務", f"請確認服務已啟動於 {API_BASE}")
        return False
    except Exception as e:
        result.add("健康檢查", False, f"發生錯誤: {e}")
        return False


def test_config_api(result: TestResult):
    """測試配置 API"""
    try:
        resp = requests.get(f"{API_BASE}/api/config", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result.add("配置 API", True, f"取得配置成功")
            return True
        else:
            result.add("配置 API", False, f"狀態碼: {resp.status_code}")
            return False
    except Exception as e:
        result.add("配置 API", False, f"發生錯誤: {e}")
        return False


def test_upload_file(result: TestResult) -> Optional[str]:
    """測試檔案上傳"""
    if not TEST_FILE.exists():
        result.add("檔案上傳", False, f"測試檔案不存在", str(TEST_FILE))
        return None
    
    try:
        file_size = TEST_FILE.stat().st_size
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
            response_data = resp.json()
            task_id = response_data.get('task_id')
            result.add("檔案上傳", True, f"任務 ID: {task_id} (大小: {file_size/1024:.1f}KB)")
            return task_id
        else:
            result.add("檔案上傳", False, f"狀態碼: {resp.status_code}", resp.text[:100])
            return None
    except Exception as e:
        result.add("檔案上傳", False, f"上傳失敗", str(e))
        return None


def test_task_status(result: TestResult, task_id: str) -> bool:
    """測試任務狀態查詢"""
    if not task_id:
        result.add("任務狀態", False, "無任務 ID")
        return False
    
    try:
        resp = requests.get(f"{API_BASE}/api/tasks/{task_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status', 'unknown')
            result.add("任務狀態查詢", True, f"狀態: {status}")
            return True
        else:
            result.add("任務狀態查詢", False, f"狀態碼: {resp.status_code}")
            return False
    except Exception as e:
        result.add("任務狀態查詢", False, f"發生錯誤", str(e))
        return False


def test_task_completion(result: TestResult, task_id: str) -> bool:
    """測試任務完成"""
    if not task_id:
        result.add("任務完成", False, "無任務 ID")
        return False
    
    print(f"  ⏳ 等待任務完成 (最長 {TIMEOUT} 秒)...")
    
    start_time = time.time()
    last_status = ""
    
    while time.time() - start_time < TIMEOUT:
        try:
            resp = requests.get(f"{API_BASE}/api/tasks/{task_id}", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get('status', 'unknown')
                progress = data.get('progress', 0)
                
                # 顯示進度更新
                if status != last_status:
                    elapsed = time.time() - start_time
                    print(f"      [{elapsed:.0f}s] 狀態: {status}, 進度: {progress}%")
                    last_status = status
                
                if status == 'completed':
                    elapsed = time.time() - start_time
                    result.add("任務完成", True, f"耗時 {elapsed:.1f} 秒")
                    return True
                elif status == 'failed':
                    error = data.get('error_message', '未知錯誤')
                    result.add("任務完成", False, f"任務失敗", error)
                    return False
                    
        except Exception as e:
            pass  # 忽略暫時性錯誤
        
        time.sleep(2)
    
    result.add("任務完成", False, f"超時 ({TIMEOUT}秒)")
    return False


def test_log_files(result: TestResult):
    """測試日誌檔案"""
    log_dir = PROJECT_ROOT / "data" / "logs"
    today = datetime.now().strftime("%Y-%m-%d")
    
    all_ok = True
    
    # 檢查 app 日誌
    app_logs = list(log_dir.glob("app_*.log"))
    if app_logs:
        latest = max(app_logs, key=lambda p: p.stat().st_mtime)
        size = latest.stat().st_size
        result.add("App 日誌", True, f"{latest.name} ({size} bytes)")
    else:
        result.add("App 日誌", False, "日誌不存在")
        all_ok = False
    
    # 檢查 JSON 日誌
    json_logs = list(log_dir.glob("structured_*.jsonl"))
    if json_logs:
        latest = max(json_logs, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest) as f:
                first_line = f.readline()
                json.loads(first_line)
            result.add("JSON 日誌", True, f"{latest.name} (格式有效)")
        except json.JSONDecodeError:
            result.add("JSON 日誌", False, "JSON 格式無效")
            all_ok = False
        except Exception as e:
            result.add("JSON 日誌", False, f"讀取失敗: {e}")
            all_ok = False
    else:
        result.add("JSON 日誌", False, "日誌不存在")
        all_ok = False
    
    return all_ok


def run_all_tests() -> int:
    """執行所有測試"""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║         🧪 MeetingScribe 完整管線測試 v1.0                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")
    
    print(f"{Colors.BLUE}測試目標: {API_BASE}{Colors.RESET}")
    print(f"{Colors.BLUE}測試檔案: {TEST_FILE}{Colors.RESET}")
    print()
    
    result = TestResult()
    
    # 測試 1: 健康檢查
    print(f"{Colors.BOLD}【測試 1】服務健康檢查{Colors.RESET}")
    if not test_health_check(result):
        print(f"\n{Colors.RED}⚠️ 服務未啟動，請先執行: ./start_service.sh{Colors.RESET}")
        return 1
    
    # 測試 2: 配置 API
    print(f"\n{Colors.BOLD}【測試 2】配置 API{Colors.RESET}")
    test_config_api(result)
    
    # 測試 3: 檔案上傳
    print(f"\n{Colors.BOLD}【測試 3】檔案上傳{Colors.RESET}")
    task_id = test_upload_file(result)
    
    # 測試 4: 任務狀態
    if task_id:
        print(f"\n{Colors.BOLD}【測試 4】任務狀態查詢{Colors.RESET}")
        test_task_status(result, task_id)
        
        # 測試 5: 任務完成
        print(f"\n{Colors.BOLD}【測試 5】任務完成{Colors.RESET}")
        test_task_completion(result, task_id)
    
    # 測試 6: 日誌檔案
    print(f"\n{Colors.BOLD}【測試 6】日誌系統{Colors.RESET}")
    test_log_files(result)
    
    # 輸出報告
    print(f"""
{'=' * 60}
{Colors.BOLD}📊 測試報告{Colors.RESET}
{'=' * 60}
""")
    
    for test in result.tests:
        status = f"{Colors.GREEN}✅{Colors.RESET}" if test['passed'] else f"{Colors.RED}❌{Colors.RESET}"
        print(f"  {status} {test['name']}: {test['message']}")
    
    print(f"""
{'-' * 60}
  {result.summary()}
{'-' * 60}
""")
    
    if result.all_passed():
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 所有測試通過！{Colors.RESET}")
        
        # 保存測試報告
        report = result.generate_report()
        report_path = PROJECT_ROOT / "data" / "logs" / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  報告已保存至: {report_path}")
        
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ 存在失敗的測試{Colors.RESET}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}測試過程發生錯誤: {e}{Colors.RESET}")
        sys.exit(1)
