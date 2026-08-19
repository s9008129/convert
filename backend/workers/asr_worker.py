"""ASR 子程序 worker（v4.7.0）。

用法：python -m backend.workers.asr_worker <audio_path> <result_json_path>

- 進度以 JSON lines 寫到 stdout（{"progress": float, "message": str}），
  父程序逐行讀取轉發到前端進度條。
- 成功：轉錄結果寫入 result_json_path，exit 0。
- 失敗：錯誤訊息與 traceback 寫到 stderr，exit 1。
- CPU 降級重試沿用 TranscriptionService.transcribe_detailed 內建邏輯。

只 import 轉錄相關模組——不得觸發 routes/queue/websocket 等應用啟動副作用。
"""

import json
import sys
import traceback


def _emit_progress(progress: float, message: str) -> None:
    print(json.dumps({"progress": progress, "message": message}, ensure_ascii=False), flush=True)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("用法: python -m backend.workers.asr_worker <audio_path> <result_json_path>", file=sys.stderr)
        return 2

    audio_path, result_json_path = argv

    # 容器/Windows 環境下 stdout 預設編碼可能非 UTF-8，中文進度訊息會炸
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    try:
        # stdout 必須保持純 JSON lines（父程序逐行解析進度）——
        # 先觸發 logger 設定，再把所有 log sink 改導 stderr
        from loguru import logger as loguru_logger

        import backend.core.logger  # noqa: F401  觸發既有 sink 設定
        loguru_logger.remove()
        loguru_logger.add(
            sys.stderr,
            level="INFO",
            format="{time:HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        )

        from backend.services.transcription import transcription_service

        result = transcription_service.transcribe_detailed(
            audio_path,
            progress_callback=_emit_progress,
        )

        payload = {
            "text": result.text,
            "duration_seconds": result.duration_seconds,
            "language": result.language,
            "backend": result.backend,
            "chunks": [
                {"start": chunk.start, "end": chunk.end, "text": chunk.text}
                for chunk in (result.chunks or [])
            ],
        }
        with open(result_json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
