"""
ASR model resolution helpers.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable, Optional

from huggingface_hub import snapshot_download


DEFAULT_BREEZE_ASR_26_MODEL = "MediaTek-Research/Breeze-ASR-26"
DEFAULT_BREEZE_ASR_26_REVISION = "949c87bca9dbe90e160cf739460cc765e80805f3"

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
    normalized_preference = (backend_preference or "auto").strip().lower()
    if normalized_preference in {"transformers", "faster_whisper"}:
        return normalized_preference
    if is_faster_whisper_model(model_name):
        return "faster_whisper"
    if "/" not in model_name and not is_local_model_path(model_name):
        return "faster_whisper"
    return "transformers"


def build_asr_cache_signature(
    model_name: str,
    backend: str,
    revision: Optional[str] = None,
) -> str:
    raw_signature = f"{backend}::{model_name}::{revision or 'unpinned'}"
    return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:16]


def resolve_model_revision(model_name: str, revision: Optional[str] = None) -> Optional[str]:
    if revision:
        return revision
    if model_name.strip().lower() == DEFAULT_BREEZE_ASR_26_MODEL.lower():
        return DEFAULT_BREEZE_ASR_26_REVISION
    return None


def resolve_transformers_model_source(
    model_name: str,
    revision: Optional[str] = None,
    *,
    local_files_only: bool = False,
    cache_dir: Optional[str] = None,
    allow_patterns: Optional[Iterable[str] | str] = None,
    deny_patterns: Optional[Iterable[str] | str] = None,
) -> str:
    if is_local_model_path(model_name):
        return str(Path(model_name).resolve())

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    resolved_revision = resolve_model_revision(model_name, revision)
    return snapshot_download(
        repo_id=model_name,
        revision=resolved_revision,
        allow_patterns=_split_patterns(allow_patterns, DEFAULT_TRANSFORMERS_ALLOW_PATTERNS),
        ignore_patterns=_split_patterns(deny_patterns, DEFAULT_TRANSFORMERS_DENY_PATTERNS),
        local_files_only=local_files_only,
        cache_dir=cache_dir,
    )
