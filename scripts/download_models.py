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

from backend.core.asr_model_resolver import infer_asr_backend, resolve_model_revision, resolve_transformers_model_source


if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = os.path.join(os.path.dirname(__file__), "..", "models")


def download_breeze_asr() -> bool:
    from backend.core.config import settings

    print("=" * 60)
    print("政府智慧會議紀錄生成系統 - 模型預載工具")
    print("=" * 60)
    print()

    backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
    resolved_revision = resolve_model_revision(
        settings.WHISPER_MODEL,
        settings.WHISPER_MODEL_REVISION,
    )
    print(f"📦 準備預載模型: {settings.WHISPER_MODEL}")
    print(f"   後端: {backend}")
    print(f"   Revision: {resolved_revision or '未固定'}")
    print(f"   快取目錄: {os.environ.get('HF_HOME', '~/.cache/huggingface')}")
    print()

    try:
        if backend == "transformers":
            local_path = resolve_transformers_model_source(
                settings.WHISPER_MODEL,
                revision=resolved_revision,
                local_files_only=False,
                allow_patterns=settings.asr_safe_allow_patterns_list,
                deny_patterns=settings.asr_safe_deny_patterns_list,
            )
            print(f"✅ 官方 Transformers 模型已下載到: {local_path}")
            return True

        from faster_whisper import WhisperModel

        WhisperModel(
            settings.WHISPER_MODEL,
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
