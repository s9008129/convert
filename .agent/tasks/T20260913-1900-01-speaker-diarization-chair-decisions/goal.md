# GOAL — 完成「多人會議發言者分離＋主席裁示歸屬」的落地與獨立驗收

## 任務目標（一句話）
在 `/Users/hsiaojohnny/dev/convert` 這套會議紀錄系統上，完成「多人會議發言者分群標註」與「主席（科長）裁示歸屬」功能的收尾、真實音檔 E2E 證據與**獨立驗收**，全程雲端 LLM 使用 **Ollama Cloud（`deepseek-v4.1-flash`）**、**不得使用 Gemini**，最後留下可稽核的證據與文件。

## 背景（上一輪已完成的部分）
- 實作已完成：diarization（sherpa-onnx，CPU、離線）、逐字稿發言者標註、fail-soft 契約、主席裁示提示詞規則、雲端 provider 切換到 Ollama Cloud、測試（784 passed / 2 skipped）、研究設計文件。
- 真實 45 分鐘音檔 E2E 已完成：任務 `3d7f76d3`（`completed`、`summary_failed=false`、709.1s、8 位發言者、逐字稿含 `[時間] 發言者N：` 標籤）。
- **接手者不要重做實作，也不要重跑整條 E2E 當成第一步**；先讀交接文件確認現況，再完成下列未竟事項。

## 必讀
1. `.agent/tasks/T20260913-1900-01-speaker-diarization-chair-decisions/handover.md`（交接文件：現況、指令、地雷、待辦）
2. `.agent/tasks/T20260913-1900-01-speaker-diarization-chair-decisions/plan.md`（權威需求：C1–C4、S1–S3、B1–B3、停止條件）

## 完成定義（Definition of Done）
1. **Stage 05 獨立驗收**：由**未參與實作**的 fresh-context 子代理，逐條稽核 C1–C4，產出 `.agent/tasks/<TASK_ID>/e2e/attempt-01/e2e_report.md` 與 `result.md`（gate ∈ `ACCEPTED` / `REJECTED` / `BLOCKED`，且每條判定附實際指令與輸出證據）。
2. **C1 證據**：逐字稿含 `[hh:mm:ss-hh:mm:ss] 發言者N：` 標籤與統計區塊；抽驗 ≥2 處時間軸換手點（無法聽音訊時要誠實標註「未抽聽」）。
3. **C2 證據**：紀錄中「科長指示及提醒事項／決議」抽驗 ≥3 案例，判斷是否可回溯到主席（科長）發言；明確指出目前**沒有**「裁示→發言者＋時間＋quote」結構化欄位（S3 未實作）以及混入非主席細節的情況。
4. **C3 證據**：真實音檔 E2E 的 md/docx/attachment 實際可下載且為有效檔案（docx 必須是有效 OOXML）。
5. **C4 證據**：diarization 失敗（模型缺失／逾時／解碼失敗／無時間軸）一律回退純文字且任務照常完成；失敗不得污染標註快取；有聚焦測試佐證。
6. **文件**：`doc/規格與設計/發言者分離與主席裁示-研究與設計.md` §9 有 E2E 實測證據；全文與程式碼現況一致（預設值、fp32、逾時/守門/快取、provider 中立）。
7. **回報**：先講 primary outcome（發言者標籤＋裁示歸屬的實證），再講任務閉環狀態，最後列殘留風險（無 ground truth、8 群≠真實人數、`發言者4–8` 可能是碎裂、摘要品質驗證仍回報遺漏、ASR 同音錯字、重疊語音未處理）。

## 硬性限制（違反即失敗）
- 雲端 LLM：**只用 Ollama Cloud `deepseek-v4.1-flash`**；不得呼叫 Gemini；不得把 provider 改回 gemini。
- 地端 LM Studio 沒開：**不要測地端模型**；`LOCAL_LLM_PROVIDER=auto` 解析失敗是預期現象，不得當 bug。
- 不得印出任何 API key；不得 `git reset`/`stash`/覆寫使用者未提交的工作；不得把 `data/` 產物或模型檔加入版控。
- 「發言者N」是自動分群編號、**不是姓名**；不得當人名寫入紀錄或文件。
- diarization 為 fail-soft 加值層：任何失敗都要退回純文字逐字稿，**不得**讓任務失敗。
- 未經使用者明確要求，不要自行 commit/push、不要擴張功能範圍（例如自行實作 S3、改調參）。
- **ASR 語意／錯字校正不在本 GOAL 範圍**：那是使用者另一個專案的獨立任務；本任務只做「發言者分離＋主席裁示歸屬」。若使用者要求移植，先開新任務與新計畫。

## 工作方式建議
- 平行處理：稽核、文件、證據抽取各派一個**唯讀**子代理；主線負責整合與最終判定。
- 每個結論標 `[VERIFIED]` / `[INFERRED]` / `[UNVERIFIED]`，附可重跑指令；**不得宣稱沒實際跑過的驗證**。
- 測試指令：`cd /Users/hsiaojohnny/dev/convert && DATA_DIR=./data .venv/bin/python -m pytest tests/ -q`（`DATA_DIR` 必須在 import backend 前設定）。
- 服務已在 `http://localhost:9527` 執行（PID 54026）；非必要不要重啟，若要重啟請用 detach helper（見交接文件 §7）。

## 停止／升級條件
- 若 Stage 05 判定 C2 或 C3 為 FAIL，或「主席裁示歸屬」無法用真實輸出證明改善 → 停止實作、回報 `PLANNER_REPLAN`，並說明需要修訂的語意或計畫。
- 若發現任何需要改動「語意契約」（required/optional、gating、fallback、錯誤語意）的修正 → 不得自行改，先回報使用者與計畫修訂。
