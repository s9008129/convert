# HANDOFF — T20260923-1810-01-local-record-fidelity-density（P7-B）

- 來源計畫：`plan.md`，**PLAN_REVISION 4**
- 修訂指紋：`sha256(plan.md)` = `dc11dd1167418ab9fbad8325b723566cd9e3df4d2db1cf8e1c3272c2994e08fc`
  （實作者／驗收者開工前必須重算並比對；不一致即**停止**，不得猜測。）
- 審查鏈：attempt-01 `PLAN_REVISION_REQUIRED`（I1–I8，已於 rev2 處置）→
  attempt-02 `PLAN_REVISION_REQUIRED`（I9／I10／I13，已於 rev4 處置）→
  attempt-03 **`PLAN_APPROVED`**（I14–I18 全為非阻斷，見下）。

## GOAL_ANCHOR（不得漂移）

讓**地端模型**（LM Studio／Ollama，任意開源模型；macOS／Windows 同一條程式路徑）產出的會議紀錄，
與雲端 Gemini 的落差縮小到使用者可接受的程度。本波鎖定兩個**已量測**的落差：

1. gemma 4 31B **漏掉會議後段整段事實**（R1：長逐字稿只跑一次萃取呼叫，尾段被稀釋）；
2. qwen 3.8 27B **把紀錄拆成一堆破碎短句、重複寫同一件事**（R2／R3）。

**非目標／不得宣稱**：不追求「地端＝雲端」；**不得**宣稱已達雲端水準。
本波「可接受」＝§5 的代理指標＋結構式尾段檢查達標。

## CRITICAL_PATH（照序；✅＝已完成並有證據）

1. ✅ 量測儀器擴充（`ac181be`）＝ `full_document_item_count`／`avg_item_chars`／`near_duplicate_items`（observation-only）。
2. ✅ 根因取證：尾段萃取探針（run-01／run-02）、區域覆蓋校準（否證偵測式）、跨 OS／Ollama 稽核。
3. ✅ CORE-1a 萃取筆記落檔（`LOCAL_LLM_DUMP_EXTRACTION_NOTES`，預設關；6 契約測試）。
4. ✅ CORE-1b 結構性分塊（`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS`，預設 6000、0＝停用＝回本波前；
   離線重播預註冊預測命中：恰 2 塊 5,960／5,918、chunk2 起 `[00:22:09]`、尾段事實 6/7——
   見 `evidence/p7b-chunk-replay/`）。
5. ✅ CORE-2a 生成紀律三開關（地端專屬區塊；雲端三支 prompt byte 不變＋補強 builder 覆蓋＋
   engine 參數化同碼路徑測試——見 `tests/test_t20260923_p7b_generation_discipline.py`）。
6. ✅ CORE-2b 觀測側（近似重複欄位，已於步驟 1）。
7. ✅ SUPPORTING-1 佔位符正規化（`LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT`，預設開；作用域釘死；
   既有交付重播 qwen 2→0、gemma 1→0——見 `evidence/p7b-placeholder-replay/`）。
8. ✅ §8 跨模型／跨 OS 三件套：skip-reason 觀測（分塊＋不回退守衛）、engine 參數化測試、
   `.env.example` 文件化。
9. ⏳ **E2E**：gemma 4 31B 1 場（必）＋ qwen 3.8 27B 1 場（必，驗不回退）；
   固定素材 `0903-科務會議.m4a`、`section_meeting`、`--quality-mode observe`。
10. ⏳ Stage 05 獨立複驗（結構式 7 條逐條＋DOCX 存在＋耗時對帳＋抽驗原文）。
11. ⏳ commit＋push（含意圖／做了什麼／下一步）。

## 語意不變式（動了就要 replan，不是 bounded fix）

- `LOCAL_LLM_RECORD_COVERAGE_MODE=off`：完全不跑、無 log、無 metrics（byte 級回本波前）。
- `LOCAL_LLM_REFINEMENT_NO_REGRESSION=false`：**無任何守衛 log**（P7-A 契約，P7-B 不動）。
- 共用常數 `LOCAL_EXTRACTION_PROMPT` 與 `CLOUD_EXTRACTION_PROMPT`：**一字不動**；
  地端紀律一律走地端專屬區塊。
- 既有閘門門檻、`off` 模式語意、雲端提示詞、`task_processor.py:259/262`：**不動**。
- 三開關全關＋`EXTRACTION_CHUNK_CEILING_TOKENS=0`＋`PLACEHOLDER_NORMALIZE_EXT=false`
  ⇒ 地端輸出 byte 級回本波前。
- 不得出現模型名或平台判斷（測試強制）。

## 停損（§7）

- 停損時鐘＝**runner 牆鐘**；對照場 gemma P7-A E7C `2,125.5 s`、qwen P6-A E6b `1,023.2 s`
  （pipeline total 1,570.2／769.6 s 只作交叉核對）。
- 牆鐘增加 ≥15% 且 §5 主驗收未達 ⇒ 停用 CORE-1b（`=0`）並改走 CORE-1c 備援。
- 備援①（尾段補萃取）成本 +150.5 s ⇒ qwen +14.7%／gemma +7.1%；與 CORE-1b 同時開啟
  使牆鐘增幅 ≥15% ⇒ **回 Planner**，執行者不得自行放行。

## 承接審查的非阻斷項（Stage 04 已處理／已登錄）

- **I18（實作）**：`_resolve_merge_targets` 的補強輪開銷估算已改傳 `mode="local"`（已實作）。
- **I16（文件）**：§5 量測表細節（儀器欄／清單路徑）——**未改 plan（已凍結於受審 sha）**，
  改由本 handoff 與 E2E README 指名欄位與完整路徑。
- **I14／I15／I17（文件一致性）**：同上，屬計畫行文；不影響任何 gate／驗收／停損語意。
- **SUPPORTING-1 已知界線**：彙整表**第 1 欄**（案由）的「（（待確認））」不在作用域
  （計畫明文「僅第 2 欄」）；如需涵蓋須回 Planner。

## 停止／升級條件

- 計畫指紋不符、或需動任一「語意不變式」⇒ 停止並回 Planner。
- E2E 出現既有 required 閘門 FAIL ⇒ 停止並回報（不得改門檻）。
- Windows／Ollama 實機一律 `[UNVERIFIED]`（本機 macOS），不得宣稱已驗。

## 證據索引

- 覆蓋率基線補算：`evidence/coverage-baseline-backfill/`（7 場早期場次，唯讀補算）
- 尾段萃取探針：`evidence/tail-extraction-probe/`（run-01 尾 25%、run-02 尾 50%＝150.5 s）
- 區域覆蓋校準（否證偵測式）：`evidence/region-coverage-calibration/`
- 量尺基線：`evidence/quality-instrument-p7b/`
- 分塊預註冊預測重播：`evidence/p7b-chunk-replay/`
- 佔位符正規化重播：`evidence/p7b-placeholder-replay/`
- 研究：`research/placeholder-audit.md`、`research/format-density-comparison.md`、
  `research/qwen-specific-gap.md`、`research/crossos-ollama-audit.md`
