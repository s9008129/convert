#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CHECK-12：Apple ASR 的包裝/平台守衛（Windows 零 Apple、無 tracked binary）。

驗證三件事：
1. repo 沒有被追蹤的 helper binary／SwiftPM 建置產物；
2. Apple 模組在非 macOS 匯入零副作用（不啟動子程序、不寫檔）且不拉重型 ML 依賴；
3. `pyproject.toml` 沒有因本功能新增 Apple 專屬 Python 依賴（Apple 路徑零 Python 依賴）。
"""

import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())

APPLE_MODULES = (
    "backend.services.asr_apple.contract",
    "backend.services.asr_apple.dispatcher",
    "backend.services.asr_apple.apple_cli",
    "backend.services.asr_apple.apple",
)


def test_repo_has_no_tracked_apple_binary():
    tracked = subprocess.run(
        ["git", "ls-files", "--", "apple_speech_cli"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    tracked += subprocess.run(
        ["git", "ls-files"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    offenders = [
        path
        for path in tracked
        if path.endswith("apple-speech-cli")
        or "/.build/" in path
        or path.startswith("apple_speech_cli/.build")
    ]
    assert offenders == []


def test_local_helper_build_directory_is_gitignored():
    build_dir = REPO_ROOT / "apple_speech_cli" / ".build"
    if not build_dir.exists():
        return

    ignored = subprocess.run(
        ["git", "check-ignore", "apple_speech_cli/.build"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0, "SwiftPM .build 目錄必須被 .gitignore 排除"


def test_apple_modules_import_is_side_effect_free_on_windows():
    """非 macOS 匯入 Apple 模組：不 spawn、不寫檔、不拉重型依賴。"""

    program = """
import json, os, sys, tempfile
import platform

platform.system = lambda: "Windows"
platform.machine = lambda: "AMD64"

spawned = []
import subprocess as _subprocess
real_popen = _subprocess.Popen

def _blocked_popen(*args, **kwargs):
    spawned.append(args)
    raise AssertionError("非 macOS 路徑不得啟動子程序")

_subprocess.Popen = _blocked_popen

probe_dir = tempfile.mkdtemp()
os.environ["DATA_DIR"] = probe_dir

modules = %r
import importlib

# 先匯入既有非 Apple 服務套件當基準線：`backend.services.__init__` 會初始化
# transcription/queue 等既有服務並建立 Data 目錄，屬全平台既有行為；
# 這裡要證明的是 Apple 模組本身沒有「額外」副作用。
importlib.import_module("backend.services")
before = set(os.listdir(probe_dir))

for name in modules:
    importlib.import_module(name)

after = set(os.listdir(probe_dir))
new_entries = sorted(after - before)
heavy = [n for n in ("torch", "mlx_whisper", "mlx", "silero", "faster_whisper") if n in sys.modules]
print(json.dumps({
    "spawned": len(spawned),
    "new_entries": new_entries,
    "heavy": heavy,
}))
""" % (list(APPLE_MODULES),)

    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])

    assert payload["spawned"] == 0
    # 基準線（既有 backend 服務）之外不得出現任何新增檔案，尤其不得有 .apple. 暫存檔。
    assert payload["new_entries"] == []
    assert payload["heavy"] == []


def test_pyproject_adds_no_apple_python_dependency():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = data["project"]["dependencies"]

    offenders = [
        dep
        for dep in dependencies
        if "apple" in dep.lower() or "speech" in dep.lower() or "swift" in dep.lower()
    ]
    assert offenders == []

    # T20260912-2242-01（Owner 2026-09-13）：macOS 只提供 Apple SpeechAnalyzer，
    # 沒有 Whisper 選項也沒有 fallback，因此 mlx-whisper／mlx 不得再是本專案的
    # 相依（原本要求「mlx-whisper 必須維持 Darwin/arm64 marker」的契約已失效）。
    mlx_deps = [
        dep
        for dep in dependencies
        if dep.lower().startswith(("mlx-whisper", "mlx==", "mlx "))
    ]
    assert mlx_deps == [], f"macOS 已無 Whisper 路徑，不應再有 MLX 相依：{mlx_deps}"
