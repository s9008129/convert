#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
會議轉錄工具 - 主程式
Windows 版本（也支援 macOS/Linux）

整合 faster-whisper + Ollama 本地 LLM

使用方式：
    python main.py
    python main.py --config custom_config.yaml
    python main.py --verbose
    python main.py --help

白話說明：
1) 讀取設定檔，確認資料夾與輸入檔案。
2) 先把語音轉成文字，再請本地 LLM 做摘要。
3) 最後輸出成好閱讀的 Markdown 會議記錄。
"""
import sys
import os
import argparse
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 確保工作目錄正確
SCRIPT_DIR = Path(__file__).parent.resolve()
os.chdir(SCRIPT_DIR)
sys.path.insert(0, str(SCRIPT_DIR))

import yaml


def setup_logging(verbose: bool = False, log_dir: Optional[Path] = None) -> logging.Logger:
    """設定畫面與檔案日誌，方便查看目前進度與錯誤。"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    handlers = []
    
    # 控制台輸出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # 檔案輸出
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"transcription_{datetime.now():%Y%m%d_%H%M%S}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # 設定 root logger
    logging.basicConfig(level=level, handlers=handlers)
    
    return logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """讀取 YAML 設定檔，回傳程式執行所需參數。"""
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"找不到配置檔: {config_path}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def print_banner():
    """在終端機顯示工具標題，讓使用者確認程式已啟動。"""
    print()
    print("=" * 60)
    print("          會議轉錄工具 - 本地 AI 版")
    print("     faster-whisper + Ollama 本地 LLM")
    print("=" * 60)
    print()


def format_duration(seconds: float) -> str:
    """把秒數轉成較好讀的文字（秒/分/小時）。"""
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins} 分 {secs} 秒"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours} 小時 {mins} 分"


def format_size(bytes_size: int) -> str:
    """把位元組大小轉成 B/KB/MB 等常見單位。"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def scan_input_files(input_dir: Path) -> List[Path]:
    """掃描輸入資料夾，找出支援的音訊與影片檔案。"""
    extensions = {'.mp3', '.mp4', '.wav', '.m4a', '.mkv', '.webm', 
                  '.flac', '.ogg', '.wma', '.aac', '.avi', '.mov', '.opus'}
    
    files = []
    for f in input_dir.iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            files.append(f)
    
    return sorted(files)


def main():
    """
    主流程控制：
    - 解析參數、讀設定、初始化模型
    - 逐檔執行轉錄與摘要
    - 將結果輸出為 Markdown 並回報統計

    主要分支與例外：
    - --dry-run：只預覽不執行，適合上線前確認檔案清單。
    - --file：只處理單一檔案，方便臨時補跑。
    - 任何初始化失敗（設定/Ollama/Whisper）都會提早結束，避免產生半成品。
    - 單檔處理失敗時，是否繼續由 continue_on_error 決定。
    """
    # 解析命令列參數
    parser = argparse.ArgumentParser(
        description="會議轉錄工具 - 本地 AI 版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
    python main.py                    # 使用預設配置
    python main.py --config my.yaml   # 使用自訂配置
    python main.py --verbose          # 詳細輸出模式
    python main.py --dry-run          # 預覽模式（不實際執行）
        """
    )
    parser.add_argument("--config", "-c", default="config.yaml", 
                        help="配置檔路徑 (預設: config.yaml)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="詳細輸出模式")
    parser.add_argument("--dry-run", action="store_true",
                        help="預覽模式，只顯示會處理的檔案")
    parser.add_argument("--file", "-f", type=str,
                        help="只處理指定檔案")
    
    args = parser.parse_args()
    
    print_banner()
    
    # 載入配置：若這裡失敗，代表流程所需路徑與模型參數都不可靠，直接停止。
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print("[錯誤] %s" % e)
        return 1
    except yaml.YAMLError as e:
        print("[錯誤] 配置檔格式錯誤: %s" % e)
        return 1
    
    # 設定日誌
    log_dir = Path(config.get("paths", {}).get("logs", "logs"))
    verbose = args.verbose or config.get("advanced", {}).get("verbose", False)
    logger = setup_logging(verbose, log_dir)
    
    logger.info("配置檔: %s", args.config)
    
    # 準備必要資料夾，避免後續讀寫失敗
    input_dir = Path(config["paths"]["input"]).resolve()
    output_dir = Path(config["paths"]["output"]).resolve()
    temp_dir = Path(config["paths"]["temp"]).resolve()
    
    for d in [input_dir, output_dir, temp_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 決定要處理哪一些檔案（單檔或整批）
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error("找不到指定檔案: %s", args.file)
            return 1
        files = [file_path.resolve()]
    else:
        files = scan_input_files(input_dir)
    
    if not files:
        logger.warning("沒有找到可處理的檔案")
        logger.info("請將音訊/視訊檔案放入: %s", input_dir)
        logger.info("支援格式: mp3, mp4, wav, m4a, mkv, webm, flac...")
        return 0
    
    logger.info("找到 %d 個待處理檔案", len(files))
    
    # 預覽模式：只顯示「會處理什麼」，不真的呼叫轉錄與摘要。
    if args.dry_run:
        print("\n[預覽模式] 將處理以下檔案:")
        for f in files:
            size = format_size(f.stat().st_size)
            print("  • %s (%s)" % (f.name, size))
        return 0
    
    # 延後載入核心模組：可先完成參數與設定檢查，再啟動較重元件
    try:
        from src.ollama_client import OllamaClient
        from src.whisper_transcriber import WhisperTranscriber
        from src.summarizer import MeetingSummarizer, MarkdownFormatter
    except ImportError as e:
        logger.error("載入模組失敗: %s", e)
        logger.error("請確認 src 目錄中有必要的 Python 檔案")
        return 1
    
    # 初始化本地 LLM 連線
    ollama_config = config["llm"]["ollama"]
    
    logger.info("初始化 Ollama 客戶端...")
    ollama = OllamaClient(
        base_url=ollama_config.get("base_url", "http://localhost:11434"),
        model=ollama_config.get("model", "llama3.1:8b"),
        num_ctx=ollama_config.get("num_ctx", 32768),
        timeout=ollama_config.get("timeout", 600)
    )
    
    # 先確認 Ollama 服務有啟動，避免後續摘要步驟失敗
    if not ollama.is_running():
        logger.error("Ollama 服務未運行！")
        logger.error("請啟動 Ollama：")
        logger.error("  Windows: 執行 Ollama 應用程式")
        logger.error("  macOS/Linux: ollama serve")
        return 1
    
    # 檢查指定模型是否可用
    models = ollama.list_models()
    logger.info("Ollama 可用模型: %s", ', '.join(models) if models else '(無)')
    
    if not ollama.has_model():
        logger.warning("模型 %s 可能未下載", ollama.model)
        logger.warning("請執行: ollama pull %s", ollama.model)
    
    # 初始化語音轉文字模組
    whisper_config = config["whisper"]
    
    logger.info("初始化 Whisper 轉錄器...")
    try:
        transcriber = WhisperTranscriber(
            exe_path=whisper_config.get("exe_path"),
            model=whisper_config.get("model", "large-v3"),
            language=whisper_config.get("language", "zh"),
            device=whisper_config.get("device", "auto"),
            compute_type=whisper_config.get("compute_type", "float16"),
            cache_dir=str(temp_dir)
        )
    except Exception as e:
        logger.error("初始化 Whisper 失敗: %s", e)
        return 1
    
    # 初始化摘要器（負責把逐字稿轉成會議摘要）
    system_prompt = config.get("system_prompt", "")
    summarizer = MeetingSummarizer(
        ollama_client=ollama,
        system_prompt=system_prompt,
        temperature=ollama_config.get("temperature", 0.7)
    )
    
    # 語言品質檢查提示
    if system_prompt:
        logger.info("[設定] 系統提示詞已啟用（%d 字元）", len(system_prompt))
        if "100% 使用正體中文" in system_prompt or "禁止英文" in system_prompt:
            logger.info("[品質] 已啟用中文強制約束機制 ✓")
        else:
            logger.warning("[警告] 系統提示詞未包含英文禁止約束")
            logger.warning("[建議] 更新 config.yaml 的 system_prompt 以啟用語言檢查")
    else:
        logger.error("[錯誤] 未設定系統提示詞，可能導致輸出語言混亂")
    
    # 讀取進階選項
    use_cache = config.get("advanced", {}).get("use_cache", True)
    continue_on_error = config.get("advanced", {}).get("continue_on_error", True)
    include_transcript = config.get("advanced", {}).get("include_transcript", True)
    
    # 用於最後摘要報告的統計數字
    success_count = 0
    fail_count = 0
    total_start = time.time()
    
    # 主迴圈：逐一處理每個檔案
    for i, file_path in enumerate(files, 1):
        print()
        logger.info("=" * 50)
        logger.info("[%d/%d] %s", i, len(files), file_path.name)
        logger.info("檔案大小: %s", format_size(file_path.stat().st_size))
        logger.info("=" * 50)
        
        file_start = time.time()
        
        try:
            # === 步驟 1：語音轉錄（音訊 -> 文字）===
            logger.info("[步驟 1/3] 語音轉錄...")
            
            result = transcriber.transcribe(
                str(file_path),
                use_cache=use_cache
            )
            
            transcript = result.text
            
            if result.from_cache:
                logger.info("[快取] 使用已存在的逐字稿")
            else:
                logger.info("轉錄完成: %d 字", result.word_count)
                if result.speed_ratio > 0:
                    logger.info("速度: %.1fx 即時", result.speed_ratio)
            
            if not transcript.strip():
                logger.warning("轉錄結果為空，跳過此檔案")
                fail_count += 1
                continue
            
            # === 步驟 2：LLM 摘要（文字 -> 重點）===
            logger.info("[步驟 2/3] LLM 摘要生成...")
            
            summary_result = summarizer.summarize(transcript)
            summary = summary_result.summary
            
            logger.info("摘要完成: %d 字", summary_result.summary_length)
            logger.info("壓縮比: %.1fx", summary_result.compression_ratio)
            
            # === 步驟 3：生成輸出（重點 -> Markdown）===
            logger.info("[步驟 3/3] 生成 Markdown...")
            
            file_elapsed = time.time() - file_start
            
            metadata = {
                'whisper_model': whisper_config['model'],
                'llm_model': ollama_config['model'],
                'total_time': format_duration(file_elapsed)
            }
            
            output_content = MarkdownFormatter.format_meeting_record(
                summary=summary,
                source_file=str(file_path),
                transcript=transcript if include_transcript else "(略)",
                metadata=metadata
            )
            
            # 寫入檔案
            output_file = output_dir / f"{file_path.stem}_摘要.md"
            output_file.write_text(output_content, encoding='utf-8')
            
            logger.info("[完成] 輸出: %s", output_file.name)
            logger.info("[耗時] %s", format_duration(file_elapsed))
            
            success_count += 1
            
        except KeyboardInterrupt:
            # 人為中斷：保留已完成成果並安全離開。
            logger.warning("使用者中斷")
            break
            
        except Exception as e:
            # 單檔案錯誤保護：記錄失敗後可選擇繼續處理下一檔。
            logger.error("[錯誤] %s", e)
            fail_count += 1
            
            if verbose:
                import traceback
                traceback.print_exc()
            
            if not continue_on_error:
                logger.error("設定為錯誤時停止，終止處理")
                break
    
    # 顯示統計
    total_elapsed = time.time() - total_start
    
    print()
    logger.info("=" * 50)
    logger.info("處理完成！")
    logger.info("=" * 50)
    logger.info("成功: %d 個檔案", success_count)
    if fail_count > 0:
        logger.info("失敗: %d 個檔案", fail_count)
    logger.info("總耗時: %s", format_duration(total_elapsed))
    logger.info("輸出目錄: %s", output_dir)
    print()
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[中斷] 使用者取消")
        sys.exit(130)
    except Exception as e:
        print("\n[錯誤] 未預期的錯誤: %s" % e)
        sys.exit(1)
