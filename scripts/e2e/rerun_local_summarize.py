#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地摘要快速重跑工具 v1.0（rerun local summarize smoke harness）

用途（給非技術使用者）：
    只重跑「地端（LM Studio）摘要」這一段，輸入既有逐字稿檔案；
    不重新做 ASR＋語者分離（可省下約 3 分鐘），適合快速驗證摘要修正是否生效。

主要流程：
    1) 讀取逐字稿 txt 整份內容原樣送入（含開頭【發言者標註說明】【發言者統計】
       標頭區塊，與正式管線收到的內容一致）
    2) 比照 scripts/macos/start-mac-native.sh 準備 DATA_DIR（預設 <repo>/data），
       必須在 import backend 模組之前寫入 os.environ，否則 settings 會採用
       Docker 預設值 /app/data
    3) 走正式生產路徑：backend.services.summarization.SummarizationService.summarize
       （mode=local、指定模板、掛進度回呼）
    4) 將完整會議紀錄寫入 --out，並在主控台摘要耗時、字元數、token 估計與前 40 行

使用方式：
    uv run python scripts/e2e/rerun_local_summarize.py
    uv run python scripts/e2e/rerun_local_summarize.py --transcript /path/to/逐字稿.txt
    uv run python scripts/e2e/rerun_local_summarize.py --transcript /path/to/逐字稿.txt \
        --template general --out data/outputs/test.md

    預設逐字稿：/Users/hsiaojohnny/Downloads/20260922134904_逐字稿.txt
    主控台預設只留 CRITICAL 等級日誌，避免失敗時 log.exception 的長 traceback 洗版；
    完整日誌／traceback 一律保留在 <DATA_DIR>/logs/。需要主控台完整日誌時：
        LOG_LEVEL=INFO uv run python scripts/e2e/rerun_local_summarize.py ...

退出碼：
    0 - 摘要成功且輸出已寫入 --out
    1 - 失敗（逐字稿不存在、模板無效、摘要例外等），主控台只印精簡錯誤訊息
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Callable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSCRIPT_PATH = Path("/Users/hsiaojohnny/Downloads/20260922134904_逐字稿.txt")
DEFAULT_TEMPLATE_ID = "general"
DEFAULT_MODE = "local"
DEFAULT_OUTPUT_FILENAME = "rerun_local_summarize.md"
OUTPUT_HEAD_LINE_COUNT = 40

# 服務的進度回呼介面：progress_callback(progress: float, message: str)
ProgressCallback = Callable[[float, str], None]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令列參數。"""
    parser = argparse.ArgumentParser(
        prog="rerun_local_summarize.py",
        description=(
            "只重跑地端（LM Studio）摘要階段：讀取既有逐字稿，跳過 ASR＋語者分離，"
            "快速驗證摘要修正是否生效。"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=DEFAULT_TRANSCRIPT_PATH,
        help="既有逐字稿 txt 路徑（整份內容原樣送入，含開頭標註說明區塊）",
    )
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE_ID,
        help="會議模板 id（general／procurement_evaluation／section_meeting／isms_monthly）",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="輸出 Markdown 路徑（預設 <DATA_DIR>/outputs/rerun_local_summarize.md）",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default=DEFAULT_MODE,
        help="摘要模式；本工具主要用於 local（LM Studio）",
    )
    return parser.parse_args(argv)


def prepare_environment() -> Path:
    """在 import backend 模組之前準備執行環境，回傳實際使用的 DATA_DIR。

    與 scripts/macos/start-mac-native.sh 一致：DATA_DIR 未設定時預設
    <repo>/data；必須在 backend.core.config 被 import 之前寫入 os.environ，
    否則 settings（及 backend.core.logger 的日誌目錄）會落到 Docker 預設 /app/data。
    """
    data_dir = Path(os.environ.get("DATA_DIR") or (PROJECT_ROOT / "data"))
    os.environ["DATA_DIR"] = str(data_dir)
    # 主控台預設只留 CRITICAL：摘要失敗時 backend 內部的 log.exception 不會把完整
    # traceback 洗滿畫面（完整內容仍寫入 <DATA_DIR>/logs/ 的日誌檔）。
    # 需要主控台完整日誌時以環境變數覆寫即可（例如 LOG_LEVEL=INFO）。
    os.environ.setdefault("LOG_LEVEL", "CRITICAL")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    return data_dir


def build_progress_printer() -> ProgressCallback:
    """建立精簡的進度列印回呼（單行、附相對累計秒數）。"""
    started_at = time.perf_counter()

    def _print_progress(progress: float, message: str) -> None:
        elapsed = time.perf_counter() - started_at
        print(f"[進度 {progress:5.1f}%（{elapsed:.1f}s）] {message}", flush=True)

    return _print_progress


def print_result_summary(
    record: str,
    transcript_char_count: int,
    elapsed_seconds: float,
    output_tokens: int,
    output_path: Path,
) -> None:
    """印出最終摘要：耗時、字元數、token 估計與紀錄前 40 行。"""
    lines = record.splitlines()
    print("")
    print("========== 重跑摘要結果 ==========")
    print(f"總計耗時       ：{elapsed_seconds:.1f} 秒")
    print(f"逐字稿字元數   ：{transcript_char_count}")
    print(f"輸出字元數     ：{len(record)}")
    print(f"輸出 token 估計：{output_tokens}")
    print(f"輸出檔案       ：{output_path}")
    print(f"---------- 紀錄前 {OUTPUT_HEAD_LINE_COUNT} 行 ----------")
    for line in lines[:OUTPUT_HEAD_LINE_COUNT]:
        print(line)
    if len(lines) > OUTPUT_HEAD_LINE_COUNT:
        print(f"...（其餘 {len(lines) - OUTPUT_HEAD_LINE_COUNT} 行省略，完整內容見輸出檔案）")


async def main() -> int:
    """主流程：參數 → 環境 → 讀稿 → 呼叫正式摘要服務 → 寫檔與列印摘要。"""
    args = parse_args()

    transcript_path = args.transcript.expanduser()
    if not transcript_path.is_file():
        print(f"[ERROR] 找不到逐字稿檔案：{transcript_path}", file=sys.stderr)
        return 1

    data_dir = prepare_environment()
    output_path = args.out.expanduser() if args.out else data_dir / "outputs" / DEFAULT_OUTPUT_FILENAME

    # 延遲載入 backend 模組：--help 不需環境準備，且確保 DATA_DIR 已先寫入 os.environ。
    from backend.core.templates import get_template
    from backend.models.schemas import ProcessingMode
    from backend.services.summarization import SummarizationService

    try:
        template = get_template(args.template)
    except ValueError as exc:
        print(f"[ERROR] 模板參數無效：{exc}", file=sys.stderr)
        return 1

    transcript = transcript_path.read_text(encoding="utf-8")
    print(f"[INFO] 逐字稿：{transcript_path}（{len(transcript)} 字元）", flush=True)
    print(f"[INFO] 模式：{args.mode}；模板：{template.id}（{template.display_name}）", flush=True)
    print(f"[INFO] DATA_DIR：{data_dir}", flush=True)

    service = SummarizationService()
    started_at = time.perf_counter()
    try:
        record = await service.summarize(
            transcript,
            mode=ProcessingMode(args.mode),
            template_id=template.id,
            progress_callback=build_progress_printer(),
        )
    except Exception as exc:  # noqa: BLE001 - 刻意只印類別＋訊息，完整 traceback 留在日誌檔
        elapsed = time.perf_counter() - started_at
        print(f"[ERROR] 摘要失敗（{elapsed:.1f} 秒）：{type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"[ERROR] 完整 traceback 保留於日誌：{data_dir / 'logs'}", file=sys.stderr)
        print(
            "[ERROR] 需要主控台完整日誌可改用：LOG_LEVEL=INFO uv run python "
            "scripts/e2e/rerun_local_summarize.py ...",
            file=sys.stderr,
        )
        return 1
    elapsed = time.perf_counter() - started_at
    output_tokens = service._estimate_tokens(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(record, encoding="utf-8")

    print_result_summary(record, len(transcript), elapsed, output_tokens, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
