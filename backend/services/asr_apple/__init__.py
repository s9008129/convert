"""Apple SpeechAnalyzer ASR provider（僅 macOS）。

套件層級保持 import 純潔（NFR-03 / SI-11）：頂層不得拉入
``mlx_whisper`` / ``torch`` / ``silero`` / ``faster_whisper``，且非 macOS
匯入不得產生任何副作用（不偵測平台、不啟動子程序、不寫檔）。

子模組分工（皆為純新增，匯入本套件不會自動載入它們）：

- ``contract``：helper schema 1.0 的凍結契約（錯誤碼、離場碼、segment 型別）。
- ``dispatcher``：凍結的引擎鏈路由（顯式 fail-closed、auto 才 fallback）。
- ``apple_cli``：helper 執行邊界（執行檔探索、子行程 runner、嚴格驗證、CJK 正規化）。
"""
