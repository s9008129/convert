# attempt-E5-qwen27b-p5：qwen3.8-27b-splash 真實音檔 E2E（**產品層 PASS；runner 層無 verdict**）

- 場次代號：E5-qwen27b-p5｜音檔：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（43.02 MB／2695.1 s）
- 模板：`section_meeting`｜模式：`local`｜品質模式：`observe`
- 受測 build revision：`ce995023dcbc1943beb9142b53cef6851c994262`（`health_snapshot.json` 的
  `expected_build_revision` 與 `actual_build_revision` 相符，時間 2026-09-23T12:14:34）
- 執行時刻（Asia/Taipei）：**12:14:29 啟動 backend → 12:35:48 任務完成**

## 一、執行方式與事故（為什麼沒有 `run_summary.json`）

- `scripts/e2e/run_owned_e2e.py` 以 **背景程序**（`nohup … &`）啟動。preflight 全數通過並留下本目錄
  四個 snapshot，且 runner 的「唯一 loaded LLM」gate 通過（`model_snapshot.json`：
  `unique_loaded_llm_count=1`、`loaded_instance_ids=["qwen3.8-27b-splash"]`，時間 12:14:34）。
- 上傳成功（`upload_response.json`：`task_id=323b1e60`，12:14:34）。
- **12:14:55 之後 runner 程序消失**（`backend.log` 只剩 3 次 `GET /api/tasks/323b1e60`），
  沒有寫出 `run_summary.json`、沒有 render verdict。
  根因＝**執行環境的背景程序收割政策**：啟動它的 shell 指令結束時，該程序群被回收；
  但 backend child 因 `start_new_session=True` 自成 process group 而存活，
  於是「runner 死亡、backend 繼續把任務跑完」。
- 因此本場**沒有 runner verdict（`verdict`／16 項 checks）**；下方數字全部是
  **產品層實測**（backend log＋交付檔案＋專案既有量尺），標記為 `[VERIFIED]` 者皆可重跑。

## 二、產品層結果 `[VERIFIED]`

| 項目 | 值 | 來源 |
| --- | --- | --- |
| 任務終態 | `TaskStatus.COMPLETED`（`summary_failed=false`） | `backend.log` 12:35:48 |
| 處理耗時 | **1273.7 s**（21 分 14 秒） | `backend.log:369` |
| 逐字稿 | `0903-科務會議_323b1e60_逐字稿.txt`（38,146 B） | outputs |
| 會議紀錄 Markdown | `0903-科務會議_323b1e60.md`（7,748 B） | outputs |
| **會議紀錄 DOCX** | `0903-科務會議_323b1e60.docx`（**40,961 B**，HTTP 200） | `GET /api/tasks/323b1e60/result?format=docx`（12:38，runner 死後由驗收者以**產品自身端點**補抓） |
| 詞彙表載入 | 121 詞、43 條已知誤辨修正 | `backend.log` 12:17:23 |
| 確定性清理 | 公務用字修正 **43 項** | `backend.log` 12:17:23 |
| 語意校正 | 45 段中 **2 段有修正、1 段放棄、採納 3 處替換**；確定性誤辨修正 0 處（清理層已先修掉） | `backend.log` 12:19:06 |
| 品質補強 | 2 輪（第 1 輪：待辦/數字/日期遺漏＋表格歸屬；第 2 輪：日期＋疑似捏造「1000元」） | `backend.log` 12:26:56、12:31:21 |

### 階段耗時拆解（1273.7 s）

| 階段 | 起訖 | 秒數 | 佔比 |
| --- | --- | ---: | ---: |
| ASR（Apple SpeechAnalyzer） | 12:14:36→12:14:51 | 15.7 | 1.2% |
| 講者分群（diarization） | 12:14:51→12:17:23 | 151.9 | 11.9% |
| 確定性清理（詞彙表 43 項） | 12:17:23 | ~0 | 0% |
| 語意校正（12 段 LLM 小呼叫） | 12:17:23→12:19:06 | 103 | 8.1% |
| 摘要主生成＋P4-A 對帳 | 12:19:06→12:26:56 | 470 | 36.9% |
| 品質補強第 1 輪 | 12:26:56→12:31:21 | 265 | 20.8% |
| 品質補強第 2 輪 | 12:31:21→12:35:48 | 267 | 21.0% |

**LLM 生成合計 ≈ 1005 s（79%）**：dense 27B（17.38 GB, 4bit）在 M4 Pro 48 GB 上的
prefill ≈ 1.2–2.0 萬 token／次，主生成單次呼叫即 248 s（`prompt_tokens=12582`）。

## 三、品質量測 `[VERIFIED]`（同一支音檔、同一份 ASR 快取、同一模板）

| 量尺 | E4（P5 前，`985.2 s`） | **E5（P5 後，`1273.7 s`）** | 雲端 C5（Gemini） |
| --- | --- | --- | --- |
| 逐字稿亂碼（19 型清單） | 46 型／109 次 | **13 型／15 次** | 1 型／1 次（僅 `煙酒文神股`） |
| 紀錄亂碼（同清單） | 7 型／10 次 | **4 型／5 次** | — |
| `coverage_all` | 0.7015（47/67） | 0.6866（46/67） | **0.8060（54/67）** |
| `coverage_core` | 0.8214（23/28） | 0.7857（22/28） | **0.8929（25/28）** |
| 逐字稿對清單涵蓋 | — | 1.0000（67/67） | 0.9851 |

- E5 紀錄殘留 5 處：`西龍股`×2、`省員`×1、`平上`×1、`煙酒文神股`×1 → **全部屬於「無 ground truth 不登錄」類**；
  其中 `煙酒文神股` 在雲端 C5 也同樣出現 1 次（非地端獨有）。
- 逐字稿亂碼 109→15 次（**-86.2%**）、46→13 型；紀錄亂碼 10→5 次（**-50.0%**）、7→4 型。
- `F021`（下週一內稽）**涵蓋**：紀錄含「內稽前整理歸位相關物品」「下個禮拜一內稽前…」。
- **未達項（如實登錄）**：本場自訂驗收門檻「紀錄亂碼 ≤3 處」**未達**（實測 5 處）；
  `coverage_all/core` 與 E4 同級（差異落在 temperature 0.7 單次抽樣噪音內），並未因此波而提升。

## 四、`[UNVERIFIED]` / 限制

- 無 runner `run_summary.json` → **無 16 項 checks 與 `verdict`**；本場不得對外宣稱「runner PASS」。
- 修正後重跑：見 `../attempt-E5-qwen27b-p5b/`（正式 runner verdict）。
- 雲端 C5 數字引自 `../attempt-C5-cloud-baseline/coverage.json`（同一 checklist `cf012d1f…`）。
