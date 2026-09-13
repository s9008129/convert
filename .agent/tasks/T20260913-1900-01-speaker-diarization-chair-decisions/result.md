# Result — T20260913-1900-01（多人會議發言者分離＋主席裁示歸屬）

- TASK_ID：`T20260913-1900-01-speaker-diarization-chair-decisions`
- PLAN_REVISION：1（未變更）
- 產出角色：Stage 05 獨立驗收稽核員（fresh context；唯讀產品程式碼；未 git commit；未重啟服務）
- 驗收證據：`e2e/attempt-01/e2e_report.md`（逐條 C1–C4、指令與原始輸出節錄）
- 受驗任務：`3d7f76d3`（`0903-科務會議.m4a`；cloud / section_meeting；Ollama Cloud `deepseek-v4.1-flash`）

## Closure Gate

**ACCEPTED**（C1 PASS、C2 PARTIAL、C3 PASS、C4 PASS）

## 分項陳述（harness v4.2 正交語意）

| 主體 | 狀態 | 說明 |
|---|---|---|
| Primary outcome | **ACHIEVED（含已界定的部分缺口）** | (a) 逐字稿具發言者分群標籤＋時間戳＋統計區塊 [VERIFIED]；(b) 紀錄之主席裁示多數可回溯到單一一致的發言者（7 抽驗案例中 4 例明確回溯主席、3 例為非主席內容混入）、且可回溯性依賴逐字稿人工比對而非紀錄內建證據欄位 [VERIFIED]；(c) 雲端（Ollama Cloud）＋科務會議模板端到端完成，md/docx 可下載且為有效檔案 [VERIFIED] |
| Implementation | **COMPLETE（依 plan §3 列舉）** | diarization、標註逐字稿、fail-soft、快取簽章、提示詞規則、下載腳本、文件、測試皆落地；另含使用者中途要求之雲端 provider 切換 [VERIFIED] |
| CORE acceptance | **C1 PASS／C2 PARTIAL／C3 PASS／C4 PASS** | C2 未達「只能來自主席」嚴格不變式（3 個具體反例），但已以真實音檔證據證明歸屬改善與可回溯性；plan §0 全域 blocking 條件為「C2/C3 無法以真實音檔證據證明」，該條件未成立 |
| Required verification | **SATISFIED** | `pytest tests/ -q` → 784 passed / 2 skipped；聚焦 42 passed；API/檔案/OOXML/日誌證據齊備 [VERIFIED] |
| Independent acceptance | **COMPLETED（attempt-01）** | 本報告由未參與實作者以真實輸出＋執行期日誌獨立複核；人工聽感核對因能力限制未執行並已誠實標註 |
| Task closure | **CLOSED（ACCEPTED）** | 主要成果與必要證據齊備；殘留缺口為 SUPPORTING（S3 結構化證據欄位）與品質類風險，非 plan 定義之 blocking 條件 |

## 判定與殘留（依重要性）

1. **C2 = PARTIAL（最關鍵）**：`二、科長指示及提醒事項` 與決議彙整表抽驗 7 例，3 例內容源自非主席（`[00:42:51] 發言者3` 的「示範點」建議被列為科長交辦且彙整表承辦寫「科長」；`[00:06:56] 發言者3` 的公文會辦；`[00:17:29] 發言者3`／`[00:16:49] 發言者2` 的文康活動形式細節）。裁示歸屬目前為**提示詞級保證＋人工抽驗**，無程式級驗證器。
2. **S3 未實作**：無「裁示→發言者＋時間＋verbatim quote」結構化欄位；紀錄內 `[hh:mm:ss]` 時間戳數＝0、無逐句 provenance（設計文件 §4.4 自承未實作；屬 SUPPORTING 非 CORE）。
3. **分群品質殘留**：8 群中 5 群僅出現於 <5 秒片段、13 個 0 秒標籤、1 處疑似句中被拆成兩位發言者（`00:42:51→00:43:03`）。
4. 其他：無 ground truth（8 群≠8 人）、雲端摘要「待辦遺漏 47 項」警告、ASR 同音錯字、語意校正因 LM Studio 未啟動而全程未生效（fail-soft 正常）。
5. 併行登載落差：雲端 provider 切換（Gemini→Ollama Cloud）見於 `goal.md`／`handover.md`，未列於 `plan.md` §3；稽核期間（20:38）git index 由外部程序 stage，本稽核未做任何 git 寫入。

## 建議（需使用者決定，不在本次範圍）

- 若要讓 C2 成為「程式級保證」：以新計畫修訂實作 S3（quote grounding＋非主席發言不得標成裁示的確定性驗證器），並為 `section_meeting.py` 的裁示歸屬規則補 CI 斷言（現僅 `config.yaml`↔`prompts.py` 受測）。
- 清理 `data/outputs/` 之同名複本（`_record.md`／`_record.docx`）。
