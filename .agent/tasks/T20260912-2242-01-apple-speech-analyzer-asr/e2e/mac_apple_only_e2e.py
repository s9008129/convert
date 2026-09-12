#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mac-only Apple SpeechAnalyzer E2E（Owner 2026-09-13 語意收斂後實測）。

驗證四件事（全部以真實產品路徑執行，不 mock 產品程式碼）：

A. `ASR_BACKEND=auto` 在 macOS 上→ 真實轉錄 `tests/0903-科務會議.m4a`，
   metadata 必須是 `requested_engine=auto`、`resolved_engine=apple`、
   `engine_chain=apple`（單一引擎）。
B. `ASR_BACKEND=apple` 在 macOS 上→ 同一條鏈、同樣 `engine_chain=apple`。
C. 路由紅線（純函式／resolver 層）：Mac 上顯式 `transformers` /
   `faster_whisper` / `mlx_whisper` 一律 `ValueError`，且 `should_fallback`
   已不存在；非 Mac（mock win32）行為與改動前一致。
D. 反向證明「沒有 fallback」：把 helper 換成一個「存在、可執行、但立刻以
   非零碼失敗」的 shim（舊語意下此錯誤碼是允許 fallback 的），跑 `auto`
   必須拿到 `AppleSpeechError` 且訊息含「未 fallback」，且子程序
   `sys.modules` 內**沒有** `mlx_whisper`／`faster_whisper`／`torch`／`mlx`
   ——也就是沒有任何 Whisper 備援被觸發。

用法：
    uv run python .agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/e2e/mac_apple_only_e2e.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
AUDIO = REPO_ROOT / "tests" / "0903-科務會議.m4a"
REPORT_DIR = Path(__file__).resolve().parent / "mac-apple-only"


# ---------------------------------------------------------------------------
# child：在乾淨子程序中跑單一情境
# ---------------------------------------------------------------------------
def _child(scenario: str) -> int:
    out_path = os.environ["E2E_OUT"]
    audio = os.environ["E2E_AUDIO"]
    sys.path.insert(0, str(REPO_ROOT))

    payload: dict = {"scenario": scenario}
    try:
        from backend.core.config import settings
        from backend.services.transcription import transcription_service

        started = time.time()
        result = transcription_service.transcribe_detailed(audio)
        elapsed = time.time() - started

        text = result.text or ""
        payload.update(
            {
                "ok": True,
                "backend": result.backend,
                "language": result.language,
                "duration_seconds": float(result.duration_seconds or 0.0),
                "elapsed_seconds": elapsed,
                "real_time_factor": elapsed / (float(result.duration_seconds or 0.0) or 1.0),
                "chunk_count": len(result.chunks),
                "char_count": len(text),
                "text_sha256": __import__("hashlib").sha256(text.encode("utf-8")).hexdigest(),
                "text_head": text[:120],
                "metadata": dict(result.metadata or {}),
                "settings_asr_backend": settings.ASR_BACKEND,
                "loaded_asr_modules": sorted(
                    m
                    for m in sys.modules
                    if m in {"mlx_whisper", "faster_whisper", "torch", "transformers", "mlx"}
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001 - 失敗本身就是要觀測的證據
        payload.update(
            {
                "ok": False,
                "error_type": type(exc).__name__,
                "error_code": getattr(exc, "code", None),
                "error_message": str(exc),
                "error_context": dict(getattr(exc, "context", {}) or {}),
                "loaded_asr_modules": sorted(
                    m
                    for m in sys.modules
                    if m in {"mlx_whisper", "faster_whisper", "torch", "transformers", "mlx"}
                ),
            }
        )

    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if payload.get("ok") else 3


def _failing_helper_shim(data_dir: str) -> str:
    """建立一個存在、可執行、但一定失敗的 helper shim（證明無 fallback）。"""

    shim = Path(data_dir) / "failing-apple-speech-cli"
    shim.write_text("#!/bin/sh\nprintf 'shim: simulated helper failure\\n' >&2\nexit 7\n", encoding="utf-8")
    shim.chmod(0o755)
    return str(shim)


def run_scenario(name: str, *, asr_backend: str, cli_path: str = "", data_dir: str) -> dict:
    out_path = Path(data_dir) / f"scenario-{name}.json"
    env = dict(os.environ)
    env.update(
        {
            "DATA_DIR": data_dir,
            "ASR_BACKEND": asr_backend,
            "E2E_OUT": str(out_path),
            "E2E_AUDIO": str(Path(data_dir) / "uploads" / AUDIO.name),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    if cli_path:
        env["APPLE_SPEECH_CLI_PATH"] = cli_path
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child", name],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if out_path.exists():
        data = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        data = {"scenario": name, "ok": False, "error_message": "child 未產生報告"}
    data["exit_code"] = proc.returncode
    data["stderr_tail"] = (proc.stderr or "")[-800:]
    return data


# ---------------------------------------------------------------------------
# 靜態路由紅線（不需要音檔，直接驗已凍結語意）
# ---------------------------------------------------------------------------
def router_redlines() -> dict:
    sys.path.insert(0, str(REPO_ROOT))
    import backend.services.asr_apple.dispatcher as dispatcher
    from backend.core.platform_config import (
        APPLE_PLATFORM_ASR_BACKENDS,
        resolve_platform_asr_backend,
    )
    from backend.services.asr_apple.contract import APPLE_AUTO_FALLBACK

    cases: dict = {
        "APPLE_AUTO_FALLBACK": list(APPLE_AUTO_FALLBACK),
        "APPLE_PLATFORM_ASR_BACKENDS": sorted(APPLE_PLATFORM_ASR_BACKENDS),
        "should_fallback_removed": not hasattr(dispatcher, "should_fallback"),
    }
    for requested in ("auto", "apple", "transformers", "faster_whisper", "mlx_whisper"):
        try:
            chain = dispatcher.resolve_engine_chain(requested, is_apple_platform=True)
            cases[f"mac:{requested}"] = {"chain": list(chain)}
        except ValueError as exc:
            cases[f"mac:{requested}"] = {"ValueError": str(exc)}
    # 非 Mac：必須與改動前完全一致
    for requested in ("auto", "apple", "transformers", "faster_whisper", "mlx_whisper"):
        try:
            chain = dispatcher.resolve_engine_chain(
                requested, is_apple_platform=False, default_backend="mlx_whisper"
            )
            cases[f"nonmac:{requested}"] = {"chain": list(chain)}
        except ValueError as exc:
            cases[f"nonmac:{requested}"] = {"ValueError": str(exc)}
    # 平台解析器（真實平台 = macOS）
    for requested in ("auto", "apple", "mlx_whisper"):
        try:
            cases[f"resolver:{requested}"] = {"resolved": resolve_platform_asr_backend(requested)}
        except ValueError as exc:
            cases[f"resolver:{requested}"] = {"ValueError": str(exc)}
    return cases


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--child", default="")
    args = parser.parse_args()
    if args.child:
        return _child(args.child)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    data_dir = tempfile.mkdtemp(prefix="mac-apple-only-e2e-")
    # loguru 在 import time 就會 mkdir(DATA_DIR/logs)：必須在任何 backend import 前設定。
    os.environ["DATA_DIR"] = data_dir
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    uploads = Path(data_dir) / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    shutil.copy2(AUDIO, uploads / AUDIO.name)

    report: dict = {
        "task_id": "T20260912-2242-01",
        "semantics": "macOS: Apple SpeechAnalyzer only, single engine, no fallback",
        "audio": str(AUDIO.relative_to(REPO_ROOT)),
        "audio_sha256": __import__("hashlib").sha256(AUDIO.read_bytes()).hexdigest(),
        "router_redlines": router_redlines(),
        "scenarios": {},
    }

    report["scenarios"]["auto_real"] = run_scenario(
        "auto_real", asr_backend="auto", data_dir=data_dir
    )
    report["scenarios"]["apple_real"] = run_scenario(
        "apple_real", asr_backend="apple", data_dir=data_dir
    )
    report["scenarios"]["auto_failing_helper_no_fallback"] = run_scenario(
        "auto_failing_helper_no_fallback",
        asr_backend="auto",
        cli_path=_failing_helper_shim(data_dir),
        data_dir=data_dir,
    )

    # ---------------------------- 判定 ----------------------------
    checks: dict = {}
    auto = report["scenarios"]["auto_real"]
    apple = report["scenarios"]["apple_real"]
    missing = report["scenarios"]["auto_failing_helper_no_fallback"]
    rl = report["router_redlines"]

    checks["A_auto_real_transcribed"] = bool(auto.get("ok"))
    checks["A_auto_chain_is_single_apple"] = auto.get("metadata", {}).get("engine_chain") == "apple"
    checks["A_auto_resolved_engine_apple"] = auto.get("metadata", {}).get("resolved_engine") == "apple"
    checks["A_auto_requested_engine_auto"] = auto.get("metadata", {}).get("requested_engine") == "auto"
    checks["A_auto_backend_apple"] = auto.get("backend") == "apple"
    checks["A_no_whisper_module_loaded"] = auto.get("loaded_asr_modules") == []
    checks["B_apple_explicit_chain_is_single_apple"] = (
        apple.get("metadata", {}).get("engine_chain") == "apple"
    )
    checks["B_apple_explicit_matches_auto_text"] = (
        apple.get("text_sha256") is not None and apple.get("text_sha256") == auto.get("text_sha256")
    )
    checks["C_apple_auto_fallback_len1"] = rl["APPLE_AUTO_FALLBACK"] == ["apple"]
    checks["C_apple_platform_backends"] = rl["APPLE_PLATFORM_ASR_BACKENDS"] == ["apple", "auto"]
    checks["C_should_fallback_removed"] = rl["should_fallback_removed"] is True
    for requested in ("transformers", "faster_whisper", "mlx_whisper"):
        checks[f"C_mac_{requested}_rejected"] = "ValueError" in rl[f"mac:{requested}"]
        checks[f"C_nonmac_{requested}_passes_through"] = rl[f"nonmac:{requested}"] == {
            "chain": [requested]
        }
    checks["C_nonmac_auto_uses_default_backend"] = rl["nonmac:auto"] == {"chain": ["mlx_whisper"]}
    checks["C_resolver_mac_auto_is_apple"] = rl["resolver:auto"] == {"resolved": "apple"}
    checks["C_resolver_mac_mlx_rejected"] = "ValueError" in rl["resolver:mlx_whisper"]
    checks["D_failing_helper_raises"] = missing.get("ok") is False
    checks["D_failing_helper_error_type"] = missing.get("error_type") == "AppleSpeechError"
    checks["D_failing_helper_no_fallback"] = missing.get("loaded_asr_modules") == []
    checks["D_failing_helper_message_says_no_fallback"] = "未 fallback" in (
        missing.get("error_message") or ""
    )
    checks["D_failing_helper_has_stable_code"] = bool(missing.get("error_code"))

    report["checks"] = checks
    report["failed_checks"] = sorted(k for k, v in checks.items() if not v)
    report["verdict"] = "PASS" if not report["failed_checks"] else "FAIL"

    out = REPORT_DIR / "report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"verdict: {report['verdict']}")
    for key in ("auto_real", "apple_real", "auto_failing_helper_no_fallback"):
        s = report["scenarios"][key]
        print(f"  {key}: ok={s.get('ok')} backend={s.get('backend')} "
              f"chain={(s.get('metadata') or {}).get('engine_chain')} "
              f"elapsed={round(s.get('elapsed_seconds') or 0, 1)}s "
              f"modules={s.get('loaded_asr_modules')}")
    print(f"  failed_checks: {report['failed_checks']}")
    print(f"  report: {out}")

    shutil.rmtree(data_dir, ignore_errors=True)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
