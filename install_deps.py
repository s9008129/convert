#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
會議轉錄工具 - 安裝依賴腳本

給第一次接觸這個專案的人：
- 這支程式會自動安裝「必要套件」。
- 安裝完成後，主程式才能正常讀取設定與呼叫 API。
- 執行方式：python install_deps.py

資料流向：
1) 讀取 REQUIRED_PACKAGES 清單
2) 呼叫 pip 逐一安裝
3) 印出完成摘要供使用者核對

使用方式：
- python install_deps.py           安裝依賴（預設）
- python install_deps.py --check   只檢查/顯示平台提示，不安裝任何套件

例外情境說明：
- 安裝失敗會立即中止，避免留下看似成功、實際不完整的環境。

平台守衛（Windows 零 Apple）：
- Apple SpeechAnalyzer helper 的提示只在 macOS 出現，且只提示、不自動編譯、不下載模型；
  Windows/Linux 一律不輸出任何 Apple/Xcode/Swift 字樣。
"""
import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = REPO_ROOT / "requirements.txt"
WINDOWS_CUDA_REQUIREMENTS_FILE = REPO_ROOT / "requirements.windows-cuda.txt"
CUDA_TORCH_INDEX_URL = "https://download.pytorch.org/whl/cu126"
APPLE_HELPER_HINT_HEADER = "提示（僅 macOS）："
APPLE_HELPER_BUILD_COMMAND = "  cd apple_speech_cli && swift build -c release"
APPLE_HELPER_BINARY_PATH = "  apple_speech_cli/.build/release/apple-speech-cli"


def apple_helper_hint(system_name: str | None = None) -> str | None:
    """回傳 macOS 專屬的 Apple helper 建置提示；非 macOS 一律 None（Windows 零 Apple）。

    只提示，不安裝、不編譯、不下載模型。
    """
    if (system_name or platform.system()).strip().lower() != "darwin":
        return None
    return "\n".join(
        [
            APPLE_HELPER_HINT_HEADER,
            "  macOS 的 ASR_BACKEND=auto 預設使用 Apple SpeechAnalyzer（本機引擎），",
            "  需要本機建置的 Swift helper；本安裝腳本不會自動編譯，也不會下載模型。",
            "  建置指令（需 Xcode 工具鏈）：",
            APPLE_HELPER_BUILD_COMMAND,
            "  建置後產物應存在：",
            APPLE_HELPER_BINARY_PATH,
            "  未建置時 auto 會自動回退 MLX-Whisper，服務仍可運作；",
            "  詳見 doc/apple-speech-analyzer-operations.md。",
        ]
    )


def print_environment_notes(system_name: str | None = None) -> None:
    """印出平台專屬的環境提示；非 macOS 不會有任何 Apple 相關輸出。"""
    hint = apple_helper_hint(system_name=system_name)
    if hint:
        print(f"\n{hint}")


def _run_pip_install(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", *args],
        check=True,
    )


def _has_nvidia_gpu() -> bool:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def _is_windows_nvidia_host(system_name: str | None = None, has_nvidia_gpu: bool | None = None) -> bool:
    detected_system = system_name or platform.system()
    detected_gpu = _has_nvidia_gpu() if has_nvidia_gpu is None else has_nvidia_gpu
    return detected_system == "Windows" and detected_gpu


def _should_install_windows_cuda_torch(system_name: str | None = None, has_nvidia_gpu: bool | None = None) -> bool:
    return _is_windows_nvidia_host(system_name=system_name, has_nvidia_gpu=has_nvidia_gpu)


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


def _validate_windows_cuda_runtime(
    status: dict[str, object] | None = None,
    system_name: str | None = None,
    has_nvidia_gpu: bool | None = None,
) -> tuple[bool, str]:
    if not _is_windows_nvidia_host(system_name=system_name, has_nvidia_gpu=has_nvidia_gpu):
        return True, ""

    runtime = status or _read_torch_runtime_status()
    if runtime["cuda_available"]:
        return True, (
            "已確認 torch CUDA 可用："
            f" version={runtime['version']}, cuda={runtime['cuda_version']}"
        )

    repair_command = (
        f'"{sys.executable}" -m pip install --upgrade --force-reinstall '
        f'-r "{WINDOWS_CUDA_REQUIREMENTS_FILE}" --prefer-binary'
    )
    return False, (
        "偵測到 Windows + NVIDIA GPU，但目前 torch 尚未啟用 CUDA："
        f" version={runtime['version'] or '未安裝'},"
        f" torch.version.cuda={runtime['cuda_version']},"
        f" torch.cuda.is_available()={runtime['cuda_available']}。\n"
        f"請在專案根目錄執行：{repair_command}"
    )


def main(argv: list[str] | None = None, system_name: str | None = None) -> int:
    """依序安裝必要套件，並在最後顯示安裝摘要；`--check` 只檢查、不安裝。"""
    args = list(sys.argv[1:] if argv is None else argv)
    check_only = "--check" in args
    detected_system = system_name or platform.system()

    if check_only:
        print("檢查模式（--check）：只檢查環境與平台提示，不安裝任何套件。")
    else:
        print("安裝必要的 Python 套件...")

    has_nvidia_gpu = _has_nvidia_gpu()
    should_install_windows_cuda_torch = _should_install_windows_cuda_torch(
        system_name=detected_system,
        has_nvidia_gpu=has_nvidia_gpu,
    )

    if not check_only:
        _run_pip_install("--upgrade", "pip")

        print(f"  安裝 {REQUIREMENTS_FILE.name}...")
        _run_pip_install("-r", str(REQUIREMENTS_FILE), "--prefer-binary")

        if should_install_windows_cuda_torch:
            print(f"\n偵測到 Windows + NVIDIA GPU，正在覆寫安裝 CUDA 版 torch...")
            _run_pip_install(
                "--upgrade",
                "--force-reinstall",
                "-r",
                str(WINDOWS_CUDA_REQUIREMENTS_FILE),
                "--prefer-binary",
            )

    cuda_ok, cuda_message = _validate_windows_cuda_runtime(
        system_name=detected_system,
        has_nvidia_gpu=has_nvidia_gpu,
    )
    if cuda_message:
        print(f"\n{cuda_message}")
    if not cuda_ok:
        raise SystemExit(1)

    print_environment_notes(system_name=detected_system)

    if check_only:
        print("\n檢查完成（未安裝任何套件）。")
        print(f"  必要套件清單：{REQUIREMENTS_FILE.name}")
        if should_install_windows_cuda_torch:
            print(f"  Windows CUDA 覆寫清單：{WINDOWS_CUDA_REQUIREMENTS_FILE.name}")
        return 0

    print("\n安裝完成！")
    print("\n已安裝的套件：")
    print(f"  ✓ {REQUIREMENTS_FILE.name}")
    if should_install_windows_cuda_torch:
        print(f"  ✓ {WINDOWS_CUDA_REQUIREMENTS_FILE.name}")
        print(f"  ✓ CUDA torch ({CUDA_TORCH_INDEX_URL})")
    return 0


if __name__ == "__main__":
    main()
