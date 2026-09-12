# Apple SpeechAnalyzer vs Whisper(MLX) — 同一檔案實測對照

- 音檔：`0903-科務會議.m4a`（44.9 分鐘，sha256 `b42f83d2c405d3f7…`）
- 兩者都走同一服務層 `transcription_service.transcribe_detailed`，只換 `ASR_BACKEND`。
- 逐字稿原文（未節錄）：`/Users/hsiaojohnny/dev/convert/data/cache/apple-vs-whisper-0903`（gitignored）。

## 速度

| 引擎 | 後端 | 耗時(s) | RTF（越小越快） | 音訊分鐘/耗時分鐘 |
|---|---|---|---|---|
| apple | apple | 15.4 | 0.0057 | 174.7× |
| whisper_breeze_mlx | mlx_whisper（doggy8088/Breeze-ASR-26-MLX） | 442.0 | 0.1640 | 6.1× |
| whisper_turbo | mlx_whisper（mlx-community/whisper-large-v3-turbo） | 145.6 | 0.0540 | 18.5× |

## 逐字稿統計

- **apple**：10315 字（CJK 10001）、標點 138（每百 CJK 1.38）、數字 80、拉丁 47、重複 8-gram 比例 0.0010
- **whisper_breeze_mlx**：12685 字（CJK 10746）、標點 0（每百 CJK 0.0）、數字 8、拉丁 39、重複 8-gram 比例 0.0460
- **whisper_turbo**：10070 字（CJK 9713）、標點 240（每百 CJK 2.47）、數字 31、拉丁 48、重複 8-gram 比例 0.0034

## 共同片段對照（同一時間點誰寫得對）

