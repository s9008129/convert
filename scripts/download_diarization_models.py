#!/usr/bin/env python3
"""說話者分離模型預載腳本（T20260913-1900-01）。

下載並驗證「離線說話者分離」所需的兩個 ONNX 模型到
``settings.DIARIZATION_MODEL_DIR``（預設 ``models/diarization/``）：

1. ``sherpa-onnx-pyannote-segmentation-3-0``（語音區段偵測；int8 版優先）
2. ``3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx``（中文說話者 embedding）

設計原則：
- **冪等**：檔案已存在且大小合理時直接跳過（重跑不重下）。
- **可離線部署**：正式機可先在可連外環境跑本腳本，再把 ``models/diarization/``
  整個目錄複製到正式機（政府機敏環境不得連外）。
- **不阻斷**：下載失敗只回傳 False 並印出指引；系統在缺模型時照常運作
  （逐字稿無發言者標籤，fail-soft）。
"""

import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SEGMENTATION_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/"
    "sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
)
EMBEDDING_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
    "3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx"
)

SEGMENTATION_DIR_NAME = "sherpa-onnx-pyannote-segmentation-3-0"
EMBEDDING_NAME = "3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx"

#: 最小合理檔案大小（bytes）——避免半截檔案被當成「已下載」。
MIN_SEGMENTATION_BYTES = 500_000
MIN_EMBEDDING_BYTES = 5_000_000


def _download(url: str, target: Path) -> None:
    print(f"   下載 {url}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, open(target, "wb") as handle:
        shutil.copyfileobj(response, handle)


def ensure_segmentation_model(model_dir: Path) -> bool:
    target_dir = model_dir / SEGMENTATION_DIR_NAME
    for name in ("model.int8.onnx", "model.onnx"):
        candidate = target_dir / name
        if candidate.exists() and candidate.stat().st_size >= MIN_SEGMENTATION_BYTES:
            print(f"✅ 已存在語音區段模型：{candidate}")
            return True

    with tempfile.TemporaryDirectory() as temp_dir:
        archive = Path(temp_dir) / "segmentation.tar.bz2"
        try:
            _download(SEGMENTATION_URL, archive)
            with tarfile.open(archive, "r:bz2") as tar:
                tar.extractall(model_dir)
        except Exception as exc:  # noqa: BLE001 — 下載工具不得拋例外
            print(f"❌ 語音區段模型下載失敗：{exc}")
            return False

    for name in ("model.int8.onnx", "model.onnx"):
        candidate = target_dir / name
        if candidate.exists() and candidate.stat().st_size >= MIN_SEGMENTATION_BYTES:
            print(f"✅ 語音區段模型就緒：{candidate}")
            return True
    print(f"❌ 解壓後找不到模型檔案：{target_dir}")
    return False


def ensure_embedding_model(model_dir: Path) -> bool:
    target = model_dir / EMBEDDING_NAME
    if target.exists() and target.stat().st_size >= MIN_EMBEDDING_BYTES:
        print(f"✅ 已存在說話者 embedding 模型：{target}")
        return True
    try:
        _download(EMBEDDING_URL, target)
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 說話者 embedding 模型下載失敗：{exc}")
        return False
    if target.exists() and target.stat().st_size >= MIN_EMBEDDING_BYTES:
        print(f"✅ 說話者 embedding 模型就緒：{target}")
        return True
    print(f"❌ 下載後檔案大小異常：{target}")
    return False


def main() -> int:
    from backend.core.config import settings

    model_dir = Path(os.path.abspath(settings.DIARIZATION_MODEL_DIR))

    print("=" * 60)
    print("說話者分離模型預載工具（sherpa-onnx）")
    print("=" * 60)
    print(f"模型目錄：{model_dir}")
    print()

    ok_segmentation = ensure_segmentation_model(model_dir)
    ok_embedding = ensure_embedding_model(model_dir)

    print()
    if ok_segmentation and ok_embedding:
        print("✅ 說話者分離模型已就緒；系統會自動在轉錄後標註發言者。")
        print("   （缺少 sherpa-onnx 套件時請先安裝：uv sync 或 pip install -r requirements.txt）")
        return 0
    print("⚠️ 模型不完整：系統仍可運作，但逐字稿不會有發言者標籤。")
    print("   請確認網路可連線 GitHub releases，或手動把模型複製到上述目錄。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
