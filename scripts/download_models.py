#!/usr/bin/env python3
"""
政府智慧會議紀錄生成系統 模型預載腳本。
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.asr_model_resolver import (
    infer_asr_backend,
    resolve_asr_model,
    resolve_engine_chain,
    resolve_mlx_model_source,
    resolve_model_revision,
    resolve_transformers_model_source,
)


def download_breeze_asr() -> bool:
    from backend.core.config import settings

    print("=" * 60)
    print("政府智慧會議紀錄生成系統 - 模型預載工具")
    print("=" * 60)
    print()

    backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
    model_name = resolve_asr_model(settings.WHISPER_MODEL, settings.ASR_BACKEND)
    resolved_revision = resolve_model_revision(
        model_name,
        settings.WHISPER_MODEL_REVISION,
    )

    # T20260912-2242-01：Mac auto 的 backend 現在解析為 apple。Apple
    # SpeechAnalyzer 使用 macOS 系統內建模型，不需 Hugging Face 下載；
    # 但 auto fallback 鏈仍以 mlx_whisper 收尾——維持 Mac 使用者既有行為，
    # 預載 MLX 模型（絕不改成 faster-whisper 模型）。
    if backend == "apple":
        print("ℹ️ Apple SpeechAnalyzer 使用 macOS 系統內建模型，不需要下載 Hugging Face 模型。")
        fallback_engine = next(
            (
                engine
                for engine in resolve_engine_chain(settings.ASR_BACKEND, settings.WHISPER_MODEL)
                if engine != "apple"
            ),
            None,
        )
        if fallback_engine != "mlx_whisper":
            print("ℹ️ 顯式 apple 為 fail-closed（無 fallback 引擎），略過模型預載。")
            return True
        print("📦 依 auto fallback 鏈預載 MLX 模型（Apple 引擎失敗時的備援）...")
        backend = "mlx_whisper"

    print(f"📦 準備預載模型: {model_name}")
    print(f"   後端: {backend}")
    print(f"   Revision: {resolved_revision or '未固定'}")
    print(f"   快取目錄: {os.environ.get('HF_HOME', '~/.cache/huggingface')}")
    print()

    try:
        if backend == "transformers":
            local_path = resolve_transformers_model_source(
                model_name,
                revision=resolved_revision,
                local_files_only=False,
                allow_patterns=settings.asr_safe_allow_patterns_list,
                deny_patterns=settings.asr_safe_deny_patterns_list,
            )
            print(f"✅ 官方 Transformers 模型已下載到: {local_path}")
            return True

        if backend == "mlx_whisper":
            local_path = resolve_mlx_model_source(
                model_name,
                revision=resolved_revision,
                local_files_only=False,
            )
            print(f"✅ MLX 模型已下載／命中 shared Hugging Face cache: {local_path}")
            return True

        from faster_whisper import WhisperModel

        WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )
        print("✅ faster-whisper 模型下載成功")
        return True

    except Exception as exc:  # noqa: BLE001
        print(f"❌ 模型下載失敗: {exc}")
        print("💡 建議：")
        print("   1. 確認網路連線正常")
        print("   2. 確認 Hugging Face 可存取")
        print("   3. 檢查磁碟空間是否足夠")
        print("   4. 若使用官方 ASR-26，請確認 revision 與 safetensors allowlist 正確")
        return False


def main() -> None:
    success = download_breeze_asr()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
