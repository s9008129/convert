# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02，attempt-03，聚焦複審）

- 受審對象：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md`，自稱 `PLAN_REVISION 4`；
  本審查快照 sha256 `86c9744f9cbe4d5ca2d423850c90cb0d383410801c3a13cfc1de1f025a15bf63`（155 行；mtime 22:14:25；
  開審與完稿前後各量一次，同值）。
- 審查者：獨立 Stage 02（fresh context；read-only）。未修改產品程式碼、`plan.md`、`review/attempt-01/`、
  `review/attempt-02/`、既有 E2E 證據或研究文件；只新增本檔（`review/attempt-03/`，append-only）。
- 範圍（依指派）：①驗證 N1（修訂身分）是否真修好、修訂紀錄是否如實（不得美化）；②抽查 N2–N5 是否收斂；
  ③明確指出任何「為讓驗收過關而放寬標準」或「契約文字仍與實作相反」之處。F1–F3 之內容面已由 attempt-02
  獨立判定收斂，本輪不重做；僅在「被宣稱已收斂」時逐項核對。
- 本輪實際動作（皆實跑）：
  1. 讀 `plan.md`（rev 4）、`review/attempt-01/review.md`、`review/attempt-02/review.md`、研究文件 §10 全文。
  2. `DATA_DIR="$PWD/data" PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest tests/test_t20260922_record_quality.py -q -p no:randomly -p no:cacheprovider`
     → **`22 passed in 0.48s`**。
  3. 程式碼核對：`measure_tag_traceability`（`ex0=None` 分支、`metric_version`）、`template_supports_source_tags`、
     `TAG_SNAP_MAX_SHIFT_SECONDS=120` 與 `kept_far` 分支（`backend/core/text_postprocess.py`）。
  4. 純函式退化案例實測（無模型）：17 筆「（科長，00:00:00）」＋兩段逐字稿。
  5. 產物核對：B2 `record_quality.json`、`instrument_recheck_20260922.json`（A1／B2／P1／B1／P1BASE）、
     `attempt-B1-moe-fix/attempt.json`；時間線（mtime）核對。

## 0. Goal Baseline（重建自使用者需求＋既有獨立驗收報告）

1. 主目標：Mac＋LM Studio 以 `section_meeting` 產出的地端會議紀錄品質「接近雲端 Gemini」；
   且優化機制**與模型無關**（日後 Win11＋RTX 4090＋Ollama／Gemma 一體適用）。
2. 本波（P2）CORE＝可查核性：CORE-1 出處標註（時間戳真實＋吸附後盡量落段首）、CORE-2 修復位於共用確定性層、
   無模型名分支。
3. 三輪審查的處置鏈：attempt-01（F1 契約文字漂移／F2 輔助閘門定義驗收期間變更／F3 研究文件數字不可重現）→
   attempt-02（F1–F3 內容面全收斂、判「降級 `exact_tag_ratio` 是量尺修正非放水」；唯一阻斷 N1＝修訂身分）→
   rev 4（本輪受審）。

## 1. N1 驗證（修訂身分）→ **已修正** [VERIFIED]

1. **版號單調**：`PLAN_REVISION: 4`（`plan.md:4`）；rev 1–4 條目列於 :5–12，遞增且與事實相符。
2. **修訂紀錄如實（關鍵）**：rev-4 條目（:9–12）明載「rev 3 被 `review/attempt-01` 判 `PLAN_REVISION_REQUIRED`
   （F1／F2／F3）後，修訂內容被就地寫回同一份 `plan.md` 而仍自稱 rev 3（違反修訂單調與 approval 綁定規則，
   `review/attempt-02` 的 N1）」；§6.4 亦記「修訂動作（內容；**完成後才遞增版號**）」（:148）。
   即「就地寫回在前、版號遞增在後」兩個容易美化的點都被主動寫出，未見粉飾。
3. **§6.4 與兩份審查紀錄一致、無矛盾（除下述 N2–N5 一句）**：
   - attempt-01 條目（:146–147）的 F1／F2／F3 與嚴重度（高／中高／中）與 `attempt-01` §5 完全一致。
   - attempt-02 條目（:152–154）的「唯一阻斷項 N1＝修訂身分」「內容面 F1／F2／F3 全部判定已收斂」
     「降級 `exact_tag_ratio` 是量尺修正、不是放水」與 `attempt-02` §4／§6 完全一致。
4. **小點（不阻斷）**：rev 3 存在兩顆受審快照（attempt-01 的 `bf6158d0…`、attempt-02 的 `4cf6ac0a…`）；
   plan 僅引用前者（:12「受審快照見 `review/attempt-01` 引用的 hash」）。建議兩顆並列引用，便於下游追溯。

## 2. N2–N5 抽查（逐項）

### 2.1 N2（`kept_far` 語氣）→ **未收斂（與 rev 4 自稱不符）**

attempt-02 要求把 `kept_far`（位移 > 120 s 者刻意保留原時間戳）的例外反映在 CORE-1／§2／§5 的絕對語氣。
現行三處與 attempt-02 所引 rev 3 文字**相同**、均未帶例外：

- `plan.md:39–40`（§1 CORE-1 定義句）：「…其時間戳必須落在逐字稿的真實段落上，且吸附後必須落在**真實段落起點**（speaker-agnostic）。」
- `plan.md:82`（§2 R21 影響欄）：「證明可用『吸附』確定性修復，不需重生成。」（未帶 MoE 單靠吸附僅 74.1% 的限定）
- `plan.md:104`（§5 首條）：「改寫目標是『時間戳所在的真實段落起點』；」（對規則 2 nearest 仍不精確）

全檔 grep 佐證：`kept_far` 僅出現於 :13（rev-4 自稱句）；`120`／「保留原時間戳」僅出現於 §6.3（:140–141）。
即 CORE 條文本身仍無例外 → header（:13）與 §6.4（:154）「非阻斷建議 N2–N5 亦已收斂」對 N2 **不成立**（見 R1）。

### 2.2 N3（append-only 明文／`metric_version`）→ **部分收斂**

- ① append-only 明文：**已收斂**。新增原則列（:15–17）：「`plan.md` 只由 Planner 遞增修訂；`review/attempt-NN/*`
  與 `e2e/attempt-*/*` 一律新增、不得就地覆寫」，並註記 B2 `record_quality.json` 覆寫事件與 `metric_version` 收斂。
- ② `instrument_recheck_20260922.json` 無 `metric_version`：**未收斂**（對整個 `e2e/attempt-B2-27b-fix/` grep，
  該字串僅出現於 `record_quality.json`／`attempt.json`／`verify_independent.md`／`run_notes.md`）。
- ③ W3 未列 `metric_version` 交付物：**未收斂**（`plan.md:91–92` 仍未列）。
- 補充觀察（低）：B2 `record_quality.json` mtime `22:05:12`＝attempt-01（22:03:18）之後又有一次就地重寫
  （補 `metric_version`；第一次覆寫 21:50:52 已見 `verify_independent.md` §4.3 與 plan §6.2-3，第二次僅能由
  「儀器輸出加 `metric_version`」的處置推知）。rev 4 既立 append-only 原則，後續重測建議以新檔名（如 `.recheck-2`）
  產出；本次僅記錄，不阻斷。

### 2.3 N4（研究文件）→ **部分收斂**

- ① §10.4 測試數：**已收斂**。現為「`tests/test_t20260922_record_quality.py` 22 passed；含 4 條本波契約與
  v4.9.0 的儀器契約」（研究 :797）；我實跑同檔得 `22 passed in 0.48s`，一致。
  （小註：§8.1 歷史區塊仍寫「21 passed…本文件撰寫時實跑」——屬當時的歷史敘述、非閘門文字；可順手標註。）
- ② §10.5 SOP 門檻 `on_start_tag_ratio ≥ 0.9`（研究 :813）與計畫 §4-3 閘門 `≥ 0.95`（plan :99）仍是
  同一指標兩個門檻、未說明關係：**未收斂**（低）。

### 2.4 N5①（`on_start_tag_ratio_excluding_zero = None` 語意）→ **已收斂（明示語意）＋殘餘風險**

- plan :45–49 明示：全場標註皆為 `00:00:00` 時該指標為 `None`＝**不判定**，改用 `on_start_tag_ratio` 與
  `zero_time_tag_ratio` 人工判讀。與實作一致：分母為 0 時回 `None`（`backend/core/text_postprocess.py:969–971`）。
- 我以純函式重現退化案例（17 筆全 `00:00:00`、`section_meeting`）：`on_start=1.0`、`ex0=None`、
  `zero_time_tag_ratio=1.0`、`traceable=1.0` → **全部機械閘門可過、只剩人工判讀**。此為明示的降級語意，
  且 B2 實際值 `ex0=1.000` 不受影響（非「為本波驗收而放寬」）；惟較 attempt-01 F4 建議（`None ⇒ FAIL`）寬，
  列殘餘風險（低）：建議下一波為 `zero_time_tag_ratio` 訂上限，Stage 05 遇 `None` 時須明示人工判讀結論。

### 2.5 N5②（`body_source_tag_count ≥ 17` 適用範圍）→ **已收斂（改以模板族界定）**

- plan :57–59：適用於「與 `section_meeting` 同族的來源標註模板」；換到不要求標註的模板時改為觀察值，
  並指名由 `template_supports_source_tags()` 判定。程式實證：函式存在（`text_postprocess.py:806–808`），
  `section_meeting→True`、`general→False`（實測）。
- 註（低）：依此規則，MoE 在 `section_meeting` 的 B1 場（`body_source_tag_count=14`；`attempt-B1-moe-fix/attempt.json`）
  仍落於 ≥17 閘門內。若團隊對 MoE 的預期是「觀察值」，需另立條文；否則此為設計上的 gate 訊號，非歧義。

## 3. 「為讓驗收過關而放寬標準」？／「契約文字與實作相反」？

1. **`exact_tag_ratio` 降級＝量尺修正，非放水（維持 attempt-02 判定，我複核成立）**：提示詞明文允許角色名
   （B2 為 52 筆中 51 筆「科長」→ 上限 1/52）；替代主指標 `on_start_tag_ratio` 在釘住版 `3fec08f` 即存在；
   新增 `ex0`（排除 `00:00:00`）反而更嚴；`exact`／`inside_same` 仍列觀察值。
2. **B2 閘門值全部複核**：`on_start=52/52=1.000`、`ex0=45/45=1.000`、`traceable=1.0`、`body=52`、`table=0`、
   字元 4,062、條目 25（`record_quality.json`，`metric_version=tag_traceability-1.1.0`）→ 與 §6.1 一致。
   §1 基線（MoE `10/27`、`exact 4/27`；27B `58/61`、`exact 46/61`）與 §6.3（`74.1%`／`100%`、
   `70.4%`／`95.1%`）與 `instrument_recheck_20260922.json`、研究 §10.3 一致。
3. **契約與實作相反的殘留**：CORE-1 定義句（:39–40）的絕對語氣 vs 實作 `kept_far`（位移 > 120 s 保留原時間戳；
   `text_postprocess.py:883–886`）＝即 N2 所指，仍在（閘門為比例制 ≥0.95，屬敘述層矛盾、非閘門層 false 判定）。
   rev 4 卻自稱該建議已收斂（見 R1）。
4. 未發現其他新放寬；`mode="cloud"` 不變性、CORE-2 無模型名分支等由既有測試／程式碼維持（本輪未重驗全測）。

## 4. 發現清單

| # | 發現 | 嚴重度 | 要求 |
|---|---|---|---|
| R1 | **修訂紀錄不準確**：header `:13` 與 §6.4 `:154` 稱 N2–N5「已收斂」，但 N2（`kept_far` 語氣）三處目標文字未動（`:39–40`／`:82`／`:104`）；另 N3②③、N4② 亦未處理。與 N1 同屬「紀錄如實性」軸。 | 中（記錄正確性；不影響閘門與產品碼） | **必做（bounded、純文字）**：二選一——(a) 套用 N2 三處 `kept_far` 限定（建議；可同時消解 §3-3 敘述層矛盾）；(b) 如實改寫收斂聲明（列出已處理：N3①／N4①／N5①②；未處理：N2、N3②③、N4②，或改列後續波）。 |
| R2 | N4②：研究 §10.5 `on_start ≥ 0.9` 與計畫 §4-3 `≥ 0.95` 關係未說明 | 低 | 建議一句話界定（SOP＝上線前哨下限 vs 波驗收閘門）或對齊。 |
| R3 | N3②③：recheck 檔無 `metric_version`；W3 未列交付物 | 低 | 建議註記或補列（勿再就地覆寫既有證據檔）。 |
| R4 | N5① 殘餘：全零標註退化紀錄可過全部機械閘門（`ex0=None` 不判定） | 低 | 後續波為 `zero_time_tag_ratio` 訂上限；Stage 05 遇 `None` 須明示人工判讀結論。 |
| R5 | 小點：§6 標題仍為「rev 3 追加」但含 rev 4 內容（:112）；rev 3 兩顆受審 hash 建議並列 | 極低 | 順手修正。 |

## 5. 閘門結論

**PLAN_REVISION_REQUIRED**（bounded、純文字；唯一阻斷項 R1）

- 依據：rev 4 **正確修正 N1**（版號 4＋如實記載「就地寫回在前、版號遞增在後」；§6.4 與兩份審查紀錄一致），
  F1–F3 之實質內容維持有審查證據；本輪覆核 rev 4 新增語意（`ex0=None`、`body ≥ 17` 適用範圍）與實作一致。
  但 rev 4 自稱「N2–N5 已收斂」與事實不符——N2 三處目標文字未動，N3②③ 與 N4② 未處理。核准必須綁定
  唯一且如實的修訂；此為記錄正確性缺陷，須以最小文字修訂收斂（R1），R2–R5 建議一併處理。
- 狀態語意：產品程式碼、吸附行為、量尺語意、B2 產物與測試證據本輪**未發現新缺陷**；本結論**不阻斷產品碼**，
  僅要求 `plan.md` 修訂紀錄如實後再複審（attempt-04）。
- 未重驗（不在本次範圍）：全測 881 passed／2 skipped baseline、MoE 實測重跑、E2E 重跑。
