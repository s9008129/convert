"""
ASR model resolution helpers.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable, Optional

from huggingface_hub import snapshot_download

from backend.core.errors import (
    ASR_MODEL_UNAVAILABLE,
    StableServiceError,
    describe_exception,
)
from backend.core.platform_config import is_darwin_arm64, resolve_platform_asr_backend


DEFAULT_BREEZE_ASR_26_MODEL = "MediaTek-Research/Breeze-ASR-26"
DEFAULT_BREEZE_ASR_26_REVISION = "949c87bca9dbe90e160cf739460cc765e80805f3"
DEFAULT_BREEZE_ASR_26_MLX_MODEL = "doggy8088/Breeze-ASR-26-MLX"
DEFAULT_BREEZE_ASR_26_MLX_REVISION = "619860a64925c0f0dfecdbb5f8d9a2da2df1bc12"

DEFAULT_TRANSFORMERS_ALLOW_PATTERNS = (
    "config.json",
    "generation_config.json",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "normalizer.json",
    "merges.txt",
    "vocab.json",
    "added_tokens.json",
    "model.safetensors.index.json",
    "model-*.safetensors",
)

DEFAULT_TRANSFORMERS_DENY_PATTERNS = (
    "*.bin",
    "*.pt",
    "*.pth",
    "*.ckpt",
    "training_args.bin",
)


def _split_patterns(patterns: Optional[Iterable[str] | str], defaults: tuple[str, ...]) -> list[str]:
    if patterns is None:
        return list(defaults)
    if isinstance(patterns, str):
        return [item.strip() for item in patterns.split(",") if item.strip()]
    return [item.strip() for item in patterns if item and item.strip()]


def is_local_model_path(model_name: str) -> bool:
    return Path(model_name).exists()


def is_ct2_model_path(model_name: str) -> bool:
    model_path = Path(model_name)
    return model_path.exists() and (model_path / "model.bin").exists()


def is_faster_whisper_model(model_name: str) -> bool:
    normalized = model_name.lower()
    return "faster-whisper" in normalized or is_ct2_model_path(model_name)


def infer_asr_backend(model_name: str, backend_preference: str = "auto") -> str:
    model_name = (model_name or "").strip()
    normalized_preference = (backend_preference or "auto").strip().lower().replace("-", "_")
    if normalized_preference == "apple":
        # 顯式 apple：非 Mac 直接 ValueError（僅 macOS），Mac 原樣尊重；
        # 不在這裡做任何 fallback（fail-closed，SI-02）。
        return resolve_platform_asr_backend("apple")
    if normalized_preference in {"transformers", "faster_whisper", "mlx_whisper"}:
        # 顯式 legacy：非 Mac 原樣尊重；Mac 由平台守衛硬性拒絕
        # （Mac 僅提供 Apple SpeechAnalyzer，Owner 2026-09-13）。
        return resolve_platform_asr_backend(normalized_preference)
    if normalized_preference not in {"", "auto"}:
        # 與 platform_config 共用同一份可接受值檢查，避免未知值靜默改走其他 backend。
        resolve_platform_asr_backend(normalized_preference)

    # Apple Silicon 的 auto 預設是 Apple SpeechAnalyzer（本機、需 macOS 26+）；
    # 只有明確 backend 才能保留 MLX / transformers / faster_whisper 路徑。
    if normalized_preference in {"", "auto"} and is_darwin_arm64():
        return "apple"
    if is_faster_whisper_model(model_name):
        return "faster_whisper"
    if "/" not in model_name and not is_local_model_path(model_name):
        return "faster_whisper"
    return "transformers"


def resolve_engine_chain(
    backend_preference: str = "auto",
    model_name: str = "",
) -> tuple[str, ...]:
    """解析本次請求的 ASR 引擎嘗試鏈（SI-01 / SI-02 / SI-03）。

    - 顯式 ``apple``：非 Apple 平台直接 ``ValueError``（僅 macOS）；Apple 平台回
      ``("apple",)``，fail-closed 不 fallback。
    - ``auto``：Apple 平台 ``("apple",)``——單一引擎、永不 fallback；非 Apple 平台
      維持既有單點解析（不碰 Windows/Linux 行為）。
    - Apple 平台上的顯式 ``transformers`` / ``faster_whisper`` / ``mlx_whisper``：
      ``ValueError`` 硬性拒絕（Mac 已無 Whisper 選項）。
    - 非 Apple 平台的其他顯式值：單點、原樣尊重（未知值 fail-fast，語意不變）。
    """

    normalized = (backend_preference or "auto").strip().lower().replace("-", "_")
    if normalized == "apple":
        return (resolve_platform_asr_backend("apple"),)
    if normalized not in {"", "auto"}:
        # 未知值與 platform_config 共用同一份檢查（維持既有 fail-fast 語意）。
        resolve_platform_asr_backend(normalized)
    effective = normalized or "auto"
    # 延後 import：backend.services.__init__ 會拉起 device_detector（再回頭 import
    # 本模組），模組頂層 import 會形成循環。
    from backend.services.asr_apple.dispatcher import resolve_engine_chain as apple_chain

    return apple_chain(
        effective,
        is_apple_platform=is_darwin_arm64(),
        default_backend=infer_asr_backend(model_name, effective),
    )


def resolve_asr_model(model_name: str, backend_preference: str = "auto") -> str:
    """解析平台預設模型；明確 model/backend 設定永遠優先。

    macOS（Apple Silicon）已無 Whisper 路徑（Owner 2026-09-13）：``auto`` 且仍是
    預設 Breeze 模型時回空字串，代表「本機沒有 Whisper 模型，由 Apple
    SpeechAnalyzer 的系統內建模型推論」，不再映射到任何 MLX/Whisper 模型 id。
    非 Apple 平台的既有解析完全不變（原樣回傳設定值）。
    """
    normalized_model = (model_name or "").strip()
    normalized_preference = (backend_preference or "auto").strip().lower().replace("-", "_")
    if (
        normalized_preference in {"", "auto"}
        and is_darwin_arm64()
        and normalized_model.lower() == DEFAULT_BREEZE_ASR_26_MODEL.lower()
    ):
        return ""
    return normalized_model


def build_asr_cache_signature(
    model_name: str,
    backend: str,
    revision: Optional[str] = None,
    *,
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    beam_size: Optional[int] = None,
    vad_enabled: Optional[bool] = None,
) -> str:
    # 除 backend/model/revision 外，納入會改變文字輸出的主要 ASR 選項，
    # 避免切換語言提示或解碼參數時誤用舊逐字稿。
    raw_signature = "::".join(
        str(value) if value is not None else "unset"
        for value in (
            backend,
            model_name,
            revision or "unpinned",
            language or "auto",
            initial_prompt or "",
            beam_size if beam_size is not None else "default",
            vad_enabled if vad_enabled is not None else "default",
        )
    )
    return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:16]


def resolve_model_revision(model_name: str, revision: Optional[str] = None) -> Optional[str]:
    if revision:
        return revision
    if model_name.strip().lower() == DEFAULT_BREEZE_ASR_26_MLX_MODEL.lower():
        return DEFAULT_BREEZE_ASR_26_MLX_REVISION
    if model_name.strip().lower() == DEFAULT_BREEZE_ASR_26_MODEL.lower():
        return DEFAULT_BREEZE_ASR_26_REVISION
    return None


def resolve_mlx_model_source(
    model_name: str,
    revision: Optional[str] = None,
    *,
    local_files_only: bool = False,
    cache_dir: Optional[str] = None,
) -> str:
    """從本機路徑或 shared Hugging Face cache 解析 MLX 模型。"""
    normalized_model = (model_name or "").strip()
    if not normalized_model:
        raise StableServiceError(ASR_MODEL_UNAVAILABLE, "MLX ASR 模型名稱不可為空")
    if is_local_model_path(normalized_model):
        return str(Path(normalized_model).resolve())

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    resolved_revision = resolve_model_revision(normalized_model, revision)
    try:
        return snapshot_download(
            repo_id=normalized_model,
            revision=resolved_revision,
            local_files_only=local_files_only,
            cache_dir=cache_dir,
        )
    except Exception as exc:  # noqa: BLE001 — 統一成穩定的 ASR model boundary 錯誤
        revision_label = resolved_revision or "unpinned"
        raise StableServiceError(
            ASR_MODEL_UNAVAILABLE,
            f"無法解析 MLX ASR 模型 {normalized_model}@{revision_label}：{describe_exception(exc)}",
        ) from exc


def resolve_transformers_model_source(
    model_name: str,
    revision: Optional[str] = None,
    *,
    local_files_only: bool = False,
    cache_dir: Optional[str] = None,
    allow_patterns: Optional[Iterable[str] | str] = None,
    deny_patterns: Optional[Iterable[str] | str] = None,
) -> str:
    normalized_model = (model_name or "").strip()
    if not normalized_model:
        raise StableServiceError(ASR_MODEL_UNAVAILABLE, "Transformers ASR 模型名稱不可為空")
    if is_local_model_path(normalized_model):
        return str(Path(normalized_model).resolve())

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    resolved_revision = resolve_model_revision(normalized_model, revision)
    try:
        return snapshot_download(
            repo_id=normalized_model,
            revision=resolved_revision,
            allow_patterns=_split_patterns(allow_patterns, DEFAULT_TRANSFORMERS_ALLOW_PATTERNS),
            ignore_patterns=_split_patterns(deny_patterns, DEFAULT_TRANSFORMERS_DENY_PATTERNS),
            local_files_only=local_files_only,
            cache_dir=cache_dir,
        )
    except Exception as exc:  # noqa: BLE001 — 統一成穩定的 ASR model boundary 錯誤
        revision_label = resolved_revision or "unpinned"
        raise StableServiceError(
            ASR_MODEL_UNAVAILABLE,
            f"無法解析 Transformers ASR 模型 {normalized_model}@{revision_label}：{describe_exception(exc)}",
        ) from exc
