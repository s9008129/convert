#!/usr/bin/env python3
"""
政府智慧會議紀錄生成系統 環境驗證腳本 v1.0
在服務啟動前執行，確保所有依賴可用

用途（給非技術使用者）：
    啟動服務前先做一輪「健康檢查」，快速確認環境是否可直接啟動，
    避免啟動後才發現缺套件、缺目錄或設定檔遺漏。

主要流程：
    1) 檢查 Python 版本與目前執行環境
    2) 檢查 FFmpeg、關鍵模組與可選加速模組
    2b) macOS（Apple Silicon）額外檢查 Apple 本機 ASR 前置（ffmpeg/ffprobe/swift/helper）；
        缺工具鏈或 helper 只提示不致命，非 macOS 完全跳過且不輸出 Apple 字樣
    3) 檢查並建立必要資料夾、確認設定檔存在
    4) 彙整結果，若有關鍵錯誤就回傳失敗退出碼

常見錯誤情境：
    - Python 版本太舊或不在預期環境
    - 關鍵套件未安裝（依 effective ASR backend 可能是 MLX-Whisper、Transformers 或 faster-whisper）
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
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WINDOWS_CUDA_REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.windows-cuda.txt"
APPLE_HELPER_DEFAULT_PATH = (
    PROJECT_ROOT / "apple_speech_cli" / ".build" / "release" / "apple-speech-cli"
)


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
║         🔍 政府智慧會議紀錄生成系統 環境驗證工具 v1.0                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")


def check_python_version() -> Tuple[bool, str]:
    """檢查 Python 版本"""
    version = sys.version_info
    if version < (3, 11):
        return False, f"Python {version.major}.{version.minor} 不支援，需要 3.11+"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"


def check_python_path() -> Tuple[bool, str]:
    """檢查 Python 執行路徑；uv/.venv 與其他隔離環境均可使用。"""
    path = Path(sys.executable)
    if sys.prefix != sys.base_prefix:
        return True, f"隔離環境: {path}"
    return True, f"Python: {path}（建議使用 uv sync --frozen 建立 .venv）"


def effective_asr_backend(
    system_name: str | None = None,
    machine_name: str | None = None,
    configured_backend: str | None = None,
    model_name: str | None = None,
) -> str:
    """依平台與設定推導 verify_env 應檢查的 ASR backend。"""
    configured = (configured_backend or os.getenv("ASR_BACKEND", "auto")).strip().lower()
    model = (model_name or os.getenv("WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")).strip().lower()
    if configured and configured != "auto":
        return configured
    if is_apple_silicon_mac(system_name=system_name, machine_name=machine_name):
        # Mac auto 預設是 Apple SpeechAnalyzer（本機、免 HF 模型）。
        return "apple"
    if "faster-whisper" in model or "/" not in model:
        return "faster_whisper"
    return "transformers"


def is_apple_silicon_mac(
    system_name: str | None = None,
    machine_name: str | None = None,
) -> bool:
    """只有 darwin + arm64/aarch64 才算 Apple 本機 ASR 平台（其餘一律不是）。"""
    system = (system_name or platform.system()).strip().lower()
    machine = (machine_name or platform.machine()).strip().lower()
    return system == "darwin" and machine in {"arm64", "aarch64"}


def check_ffprobe() -> Tuple[bool, str]:
    """檢查 ffprobe（Apple 路徑量測音長用；缺則退回逾時下限，不致命）。"""
    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, result.stdout.split("\n")[0][:60]
        return False, "ffprobe 執行失敗"
    except FileNotFoundError:
        return False, "ffprobe 未安裝（brew install ffmpeg 會一併提供）"
    except subprocess.TimeoutExpired:
        return False, "ffprobe 回應超時"


def check_swift_toolchain() -> Tuple[bool, str]:
    """檢查 Swift 工具鏈（僅建置 helper 需要；缺少只提示、不致命）。"""
    try:
        result = subprocess.run(
            ["swift", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return False, "缺少 swift 工具鏈；建置 helper 需 Xcode（Swift 6.0+）：xcode-select --install"
    except subprocess.TimeoutExpired:
        return False, "swift 回應超時"
    if result.returncode != 0:
        return False, "swift 執行失敗；建置 helper 需可用工具鏈：xcode-select --install"
    lines = (result.stdout or result.stderr or "").strip().splitlines()
    if not lines:
        return True, "Swift 工具鏈：可用"
    return True, f"Swift 工具鏈：{lines[0][:60]}"


def resolve_apple_helper_path() -> Path:
    """APPLE_SPEECH_CLI_PATH > repo release 產物 > PATH；找不到回預設路徑。"""
    configured = os.getenv("APPLE_SPEECH_CLI_PATH", "").strip()
    if configured:
        return Path(configured)
    if APPLE_HELPER_DEFAULT_PATH.is_file():
        return APPLE_HELPER_DEFAULT_PATH
    on_path = shutil.which("apple-speech-cli")
    if on_path:
        return Path(on_path)
    return APPLE_HELPER_DEFAULT_PATH


def check_apple_native_environment(
    system_name: str | None = None,
    machine_name: str | None = None,
) -> Optional[List[Tuple[bool, str]]]:
    """macOS（Apple Silicon）專屬的 Apple 本機 ASR 前置檢查。

    非 macOS 回 None＝完全跳過（不得輸出 Apple/Xcode 字樣）。
    缺 swift 工具鏈或 helper 只給提示與建置指令，永不視為致命。
    """
    if not is_apple_silicon_mac(system_name=system_name, machine_name=machine_name):
        return None

    helper_path = resolve_apple_helper_path()
    if helper_path.is_file():
        helper_result: Tuple[bool, str] = (True, f"Apple helper 執行檔存在：{helper_path}")
    else:
        helper_result = (
            False,
            "Apple helper 尚未建置（僅提示，不自動編譯；ASR_BACKEND=auto 會先嘗試 Apple、"
            "失敗回退 MLX-Whisper）。建置指令：cd apple_speech_cli && swift build -c release"
            "（產物：apple_speech_cli/.build/release/apple-speech-cli；"
            "詳見 doc/apple-speech-analyzer-operations.md）",
        )

    return [check_ffmpeg(), check_ffprobe(), check_swift_toolchain(), helper_result]


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
    """檢查 web/audio 與目前 effective ASR backend 的關鍵模組。"""
    modules = [
        ("av", "PyAV (音訊處理)", None),
        ("fastapi", "FastAPI (Web 框架)", None),
        ("uvicorn", "Uvicorn (ASGI 伺服器)", None),
        ("loguru", "Loguru (日誌系統)", None),
        ("pydantic", "Pydantic (資料驗證)", None),
        ("httpx", "HTTPX (HTTP 客戶端)", None),
        ("openai", "OpenAI-compatible client", None),
        ("huggingface_hub", "Hugging Face model cache", None),
        ("yaml", "PyYAML (配置解析)", None),
        ("aiofiles", "Aiofiles (非同步檔案)", None),
        ("docx", "python-docx (DOCX 文件生成)", "from docx import Document"),
    ]

    backend = effective_asr_backend()
    if backend == "apple":
        # Apple 路徑本身不需要 Python 模組（走 Swift helper）；mlx_whisper 是
        # auto 鏈的 fallback，仍須可匯入。
        modules.append(("mlx_whisper", "MLX-Whisper（Apple 路徑 fallback）", None))
    elif backend == "mlx_whisper":
        modules.append(("mlx_whisper", "MLX-Whisper (Metal ASR)", None))
    elif backend == "transformers":
        modules.extend([
            ("torch", "PyTorch (Transformers ASR)", None),
            ("transformers", "Transformers ASR", None),
        ])
    elif backend == "faster_whisper":
        modules.append(("faster_whisper", "Faster-Whisper", "from faster_whisper import WhisperModel"))
    else:
        modules.append((backend, f"ASR backend: {backend}", None))
    
    results = []
    for module, name, test in modules:
        results.append(check_module(module, name, test))
    
    return results


def check_optional_modules() -> List[Tuple[bool, str]]:
    """檢查未被目前 backend 使用的 supporting modules。"""
    modules = [
        ("mlx_whisper", "MLX-Whisper（未選用時為 supporting）", None),
        ("mlx", "MLX（未選用時為 supporting）", None),
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
    print(f"\n{Colors.BLUE}{Colors.BOLD}【Supporting 模組】{Colors.RESET}（不作 global gate）")
    
    optional_ok = True
    for ok, msg in check_optional_modules():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.YELLOW}⚠️{Colors.RESET}"
        print(f"  {status} {msg}")
        if not ok:
            optional_ok = False
    
    if not optional_ok:
        print(f"  {Colors.YELLOW}提示：未使用的 supporting backend 缺失不會阻擋目前 effective ASR 路徑{Colors.RESET}")

    # 4b. Apple SpeechAnalyzer（僅 macOS；缺工具鏈/helper 只提示，不阻擋啟動）
    apple_results = check_apple_native_environment()
    if apple_results is not None:
        print(f"\n{Colors.BLUE}{Colors.BOLD}【Apple SpeechAnalyzer（macOS 本機 ASR）】{Colors.RESET}（僅提示；不阻擋啟動）")
        for ok, msg in apple_results:
            status = f"{Colors.GREEN}✅{Colors.RESET}" if ok else f"{Colors.YELLOW}⚠️{Colors.RESET}"
            print(f"  {status} {msg}")

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
        print("  1. 在專案根目錄執行：uv sync --frozen")
        print("  2. 確認系統已安裝 ffmpeg")
        print("  3. 依上方 effective ASR backend 補齊對應依賴")
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
