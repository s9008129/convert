#!/usr/bin/env python3
"""
MeetingScribe 環境驗證腳本 v1.0
在服務啟動前執行，確保所有依賴可用

用途（給非技術使用者）：
    啟動服務前先做一輪「健康檢查」，快速確認環境是否可直接啟動，
    避免啟動後才發現缺套件、缺目錄或設定檔遺漏。

主要流程：
    1) 檢查 Python 版本與目前執行環境
    2) 檢查 FFmpeg、關鍵模組與可選加速模組
    3) 檢查並建立必要資料夾、確認設定檔存在
    4) 彙整結果，若有關鍵錯誤就回傳失敗退出碼

常見錯誤情境：
    - Python 版本太舊或不在預期環境
    - 關鍵套件未安裝（例如 faster-whisper、aiofiles）
    - 系統缺少 FFmpeg
    - 必要目錄建立失敗或設定檔缺失

使用方式：
    python scripts/verify_env.py

退出碼：
    0 - 所有驗證通過
    1 - 存在關鍵問題
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from typing import Tuple, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WINDOWS_CUDA_REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.windows-cuda.txt"


class Colors:
    """終端顏色代碼"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """顯示標題"""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║         🔍 MeetingScribe 環境驗證工具 v1.0                   ║
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
        return True, "conda meetingscribe 環境 ✓"
    elif "venv" in path:
        return False, f"使用 venv 環境（應使用 conda meetingscribe）"
    else:
        # 允許其他正確配置的環境
        return True, f"環境: {os.path.basename(os.path.dirname(os.path.dirname(path)))}"


def check_ffmpeg() -> Tuple[bool, str]:
    """檢查 FFmpeg"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            return True, version[:60]
        return False, "FFmpeg 執行失敗"
    except FileNotFoundError:
        return False, "FFmpeg 未安裝（brew install ffmpeg）"
    except subprocess.TimeoutExpired:
        return False, "FFmpeg 回應超時"


def has_nvidia_gpu() -> bool:
    """檢查目前主機是否可見 NVIDIA GPU。"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def get_windows_cuda_fix_command(python_executable: str | None = None) -> str:
    """提供 Windows + NVIDIA GPU 的 torch 修復指令。"""
    python_cmd = python_executable or sys.executable
    return (
        f'"{python_cmd}" -m pip install --upgrade --force-reinstall '
        f'-r "{WINDOWS_CUDA_REQUIREMENTS_FILE}" --prefer-binary'
    )


def _read_torch_runtime_status() -> dict[str, object]:
    try:
        import torch
    except ImportError:
        return {
            "installed": False,
            "version": None,
            "cuda_version": None,
            "cuda_available": False,
        }

    return {
        "installed": True,
        "version": getattr(torch, "__version__", None),
        "cuda_version": getattr(torch.version, "cuda", None),
        "cuda_available": bool(torch.cuda.is_available()),
    }


def evaluate_windows_cuda_torch_status(
    runtime_status: dict[str, object],
    system_name: str,
    nvidia_gpu_available: bool,
) -> Tuple[bool, str]:
    """評估 Windows + NVIDIA 環境是否真的具備 CUDA 版 torch。"""
    if system_name != "Windows" or not nvidia_gpu_available:
        return True, "未偵測到 Windows + NVIDIA GPU，略過 CUDA torch 檢查"

    if runtime_status["cuda_available"]:
        return True, (
            f"torch {runtime_status['version']} 已啟用 CUDA "
            f"(torch.version.cuda={runtime_status['cuda_version']})"
        )

    return False, (
        "偵測到 Windows + NVIDIA GPU，但目前 torch 為 CPU-only 或 CUDA 未啟用："
        f" torch={runtime_status['version'] or '未安裝'},"
        f" torch.version.cuda={runtime_status['cuda_version']},"
        f" torch.cuda.is_available()={runtime_status['cuda_available']}。\n"
        f"    修復指令：{get_windows_cuda_fix_command()}\n"
        "    或改用：python install_deps.py"
    )


def check_windows_cuda_torch() -> Tuple[bool, str]:
    """檢查 Windows + NVIDIA 主機上的 torch 是否真為 CUDA 版。"""
    return evaluate_windows_cuda_torch_status(
        runtime_status=_read_torch_runtime_status(),
        system_name=platform.system(),
        nvidia_gpu_available=has_nvidia_gpu(),
    )


def check_module(module_name: str, display_name: str, import_test: str = None) -> Tuple[bool, str]:
    """檢查 Python 模組"""
    try:
        if import_test:
            exec(import_test)
        else:
            mod = __import__(module_name)
            version = getattr(mod, '__version__', '已安裝')
            return True, f"{display_name} v{version}"
        return True, f"{display_name} ✓"
    except ImportError as e:
        return False, f"{display_name}: {str(e)[:50]}"
    except Exception as e:
        return False, f"{display_name}: {str(e)[:50]}"


def check_critical_modules() -> List[Tuple[bool, str]]:
    """檢查所有關鍵模組"""
    modules = [
        ("av", "PyAV (音訊處理)", None),
        ("faster_whisper", "Faster-Whisper", "from faster_whisper import WhisperModel"),
        ("fastapi", "FastAPI (Web 框架)", None),
        ("uvicorn", "Uvicorn (ASGI 伺服器)", None),
        ("loguru", "Loguru (日誌系統)", None),
        ("pydantic", "Pydantic (資料驗證)", None),
        ("httpx", "HTTPX (HTTP 客戶端)", None),
        ("yaml", "PyYAML (配置解析)", None),
        ("aiofiles", "Aiofiles (非同步檔案)", None),
        ("docx", "python-docx (DOCX 文件生成)", "from docx import Document"),
    ]
    
    results = []
    for module, name, test in modules:
        results.append(check_module(module, name, test))
    
    return results


def check_optional_modules() -> List[Tuple[bool, str]]:
    """檢查可選模組（macOS MPS 加速）"""
    modules = [
        ("mlx_whisper", "MLX-Whisper (MPS 加速)", None),
        ("mlx", "MLX (Apple ML 框架)", None),
    ]
    
    results = []
    for module, name, test in modules:
        results.append(check_module(module, name, test))
    
    return results


def check_directories() -> List[Tuple[bool, str]]:
    """檢查並建立必要目錄"""
    # 取得專案根目錄
    script_dir = Path(__file__).parent
    base_path = script_dir.parent
    
    required_dirs = [
        base_path / "data" / "uploads",
        base_path / "data" / "outputs",
        base_path / "data" / "logs",
        base_path / "data" / "cache",
    ]
    
    results = []
    for dir_path in required_dirs:
        if dir_path.exists():
            results.append((True, f"{dir_path.name}/ 已存在"))
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                results.append((True, f"{dir_path.name}/ 已建立"))
            except Exception as e:
                results.append((False, f"無法建立 {dir_path.name}/: {e}"))
    
    return results


def check_config_files() -> List[Tuple[bool, str]]:
    """檢查配置檔案"""
    script_dir = Path(__file__).parent
    base_path = script_dir.parent
    
    configs = [
        (base_path / "config.yaml", "config.yaml (通用配置)"),
        (base_path / "config.macos.yaml", "config.macos.yaml (macOS 配置)"),
    ]
    
    results = []
    for config_path, name in configs:
        if config_path.exists():
            results.append((True, f"{name} 存在"))
        else:
            results.append((False, f"{name} 不存在"))
    
    return results


def run_all_checks() -> bool:
    """
    執行完整環境檢查並回傳是否可啟動服務。

    回傳 True 代表關鍵檢查都通過；回傳 False 代表有關鍵錯誤，
    例如核心依賴缺失或目錄建立失敗，應先修復後再啟動。
    """
    print_header()
    
    # 只要關鍵項目有任一失敗，就標記為不可啟動。
    critical_failed = False
    
    # 1. Python 環境
    print(f"{Colors.BLUE}{Colors.BOLD}【Python 環境】{Colors.RESET}")
    
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
    print(f"\n{Colors.BLUE}{Colors.BOLD}【系統依賴】{Colors.RESET}")
    
    ok, msg = check_ffmpeg()
    status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
    print(f"  {status} FFmpeg: {msg}")
    if not ok:
        critical_failed = True
    
    # 3. 關鍵模組
    print(f"\n{Colors.BLUE}{Colors.BOLD}【關鍵模組】{Colors.RESET}（必須全部通過）")
    
    for ok, msg in check_critical_modules():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
        print(f"  {status} {msg}")
        if not ok:
            critical_failed = True
    
    # 4. 可選模組
    print(f"\n{Colors.BLUE}{Colors.BOLD}【可選模組】{Colors.RESET}（macOS MPS 加速）")
    
    optional_ok = True
    for ok, msg in check_optional_modules():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.YELLOW}⚠️{Colors.RESET}"
        print(f"  {status} {msg}")
        if not ok:
            optional_ok = False
    
    if not optional_ok:
        print(f"  {Colors.YELLOW}提示：安裝 mlx-whisper 可獲得 3-5 倍加速{Colors.RESET}")

    # 5. Windows CUDA / Torch
    print(f"\n{Colors.BLUE}{Colors.BOLD}【Windows CUDA / Torch】{Colors.RESET}")
    ok, msg = check_windows_cuda_torch()
    status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
    print(f"  {status} {msg}")
    if not ok:
        critical_failed = True
    
    # 6. 目錄結構
    print(f"\n{Colors.BLUE}{Colors.BOLD}【目錄結構】{Colors.RESET}")
    
    for ok, msg in check_directories():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.RED}❌{Colors.RESET}"
        print(f"  {status} {msg}")
        if not ok:
            critical_failed = True
    
    # 7. 配置檔案
    print(f"\n{Colors.BLUE}{Colors.BOLD}【配置檔案】{Colors.RESET}")
    
    for ok, msg in check_config_files():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.YELLOW}⚠️{Colors.RESET}"
        print(f"  {status} {msg}")
    
    # 最終結果
    print("\n" + "=" * 60)
    
    if critical_failed:
        print(f"{Colors.RED}{Colors.BOLD}❌ 環境驗證失敗 - 存在關鍵問題，無法啟動服務{Colors.RESET}")
        print(f"\n{Colors.YELLOW}建議修復步驟：{Colors.RESET}")
        print("  1. 確認使用 conda meetingscribe 環境")
        print("  2. conda activate meetingscribe")
        print("  3. conda install -c conda-forge av ffmpeg -y")
        print("  4. pip install faster-whisper mlx-whisper")
        if platform.system() == "Windows" and has_nvidia_gpu():
            print(f"  5. {get_windows_cuda_fix_command()}")
        return False
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ 環境驗證通過 - 可以啟動服務{Colors.RESET}")
        return True


if __name__ == "__main__":
    try:
        success = run_all_checks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}驗證過程發生錯誤: {e}{Colors.RESET}")
        sys.exit(1)
