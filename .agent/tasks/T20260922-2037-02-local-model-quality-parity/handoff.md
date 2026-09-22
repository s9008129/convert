# Stage 03 HANDOFF — T20260922-2037-02-local-model-quality-parity（P4 波）

- 產出角色：Stage 03 HANDOFF 編譯員（fresh context；本檔為唯一寫入；**未改 `plan.md`、未改產品程式碼**）。
- 編譯來源：`plan.md` **PLAN_REVISION 15**（sha256 `a7ea4be6a06c30abd9bb68fd51c46c525e1da1ddec52cf6e45bdc0d3ac3a35fb`；編譯時重新量測一致）＋研究文件 `doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md` §12。
- 核准來源：`review/attempt-12/review.md`，gate＝**`PLAN_APPROVED`**；核准範圍＝rev 15＋同 sha256（`review.md`／`snapshot_plan.md`／`plan_sha256.txt` 三方一致）。**`plan.md` 若再變更，核准與本 handoff 均失效**（須遞增修訂、重審、重編）。
- 任務閘門（plan 標頭沿用）：`TASK_CLASS: STANDARD｜REVIEW_REQUIRED: YES｜INDEPENDENT_ACCEPTANCE_REQUIRED: YES｜E2E_REQUIRED: YES`（真音檔 `0903-科務會議.m4a`＋`section_meeting`＋`local`）。
- 編譯界限：只搬運 plan §0／§1／§9 全部子節與研究 §12 之已核准內容＋使用者於編譯期下達之強制更正與審查 N1–N3（§11）；**不新增需求**；**不把 SUPPORTING／§9.9「本波不做」升為必做**。
- 必含清單（依 Stage 03 指示）：GOAL_ANCHOR(§1)／CRITICAL_PATH(§2)／檔案所有權(§3)／凍結介面(§4)／SEMANTIC_INVARIANTS(§5)／BEST_EFFORT(§6)／VERIFICATION(§7)／STOP(§8)／ROLLBACK(§9)／如實邊界(§10)＋編譯期更正(§11)。
- 非持久來源宣告（plan rev15 §9 開頭 B-F2）：設計定稿細節檔（`/tmp/p4a_design.md`、`/tmp/p4b_design.md`、`/tmp/p4d_design.md`、`/tmp/p4_crossos_design.md`）與地面實證稽核／偵察檔（`/tmp/p4/*`）皆**非 repo、不持久**；本 handoff 已內化落地所需決策摘要，**實作不得依賴這些檔案存續**。
- 平行實作前提：§3 檔案所有權為**互斥寫入集**（同一時間僅該 owner 可寫該檔）；跨包耦合一律走 §4 凍結介面。

## 1. GOAL_ANCHOR（≤5 行）
1. **使用者要什麼**：Mac＋LM Studio 的地端會議紀錄（`section_meeting`）品質要接近／追上雲端 Gemini——「人工看過輸出，品質非常不夠理想、跟雲端差很多」是第一性目標；**未量測前不得宣稱達成**。
2. **為什麼是現在**：同一把尺五場對照顯示雲端不是天花板（27B dense 與雲端同級），痛點在量尺盲區（R28）與模型真漏寫 → 本波在模型無關的確定性層補召回與忠實度。
3. **不可縮小（一）**：品質槓桿必須**模型無關**——換模型不改機制；實作位於 LM Studio／Ollama 共用管線，不得模型名分支、不得依賴引擎專屬欄位。
4. **不可縮小（二）**：**macOS（LM Studio）＋ Windows 11＋RTX 4090（Ollama）雙平台一體適用**；Windows 實機未到前一律 `[UNVERIFIED]`。
5. **不可縮小（三）**：**雲端＝對照基準、byte 級不動**（提示詞不改、輸出與問題清單不變；P4-F 只登記）。

## 2. CRITICAL_PATH（有序；本波真正要落地的順序）
1. **P4-A**（CORE，全域阻斷；W1）→ 2. **P4-B**（CORE；W2 模組＋W1 合併）→ 3. **P4-D**（CORE；先「產品標註去重複化」W4，後「runner 品質閘門」W3）→ 4. **P4-C**（SUPPORTING；W1；W-1／W-2 同源）。

- 全域阻斷＝僅 **P4-A／P4-B／P4-D**（plan §9.10）。P4-C 排在 CORE 之後；失敗時如實降級（觀測／config 級回退），**不阻斷** CORE。
- **P4-E／P4-G＝BEST_EFFORT（非阻斷）**；**P4-F＝只登記**（見 §6）。
- 排序註記：plan §9.11-6／研究 §12.10 另載「顧問性建議序 P4-D→A→B→C」；本 handoff 依使用者編譯指示採 **A→B→D→C**；兩者皆不改變各包驗收內容。

### 2.1 P4-A 落地摘要（漏寫召回：對帳 1 類→4+1 類）
- 意圖（plan §9.3）：模型真漏寫的事實要在**第二輪生成**被補回；對帳由「只查待辦」擴為議題／決議／數字／日期＋既有待辦；只回報、不改寫、不刪句。
- 機制：新增期望集合抽取器 ×4＋`_validate_record_source_coverage()`，**重用既有比對器**（對稱正規化、滑窗 LCS ≥0.6、否定詞／≥2 位數字守衛）；等價展開（`11月1日 ≡ 11/1`）；**數字比對前先剝來源標註**（`_SOURCE_TAG_PATTERN`，`summarization.py:164`）＋NFKC＋**去千分位逗號**；呼叫點僅地端（`:2367-2371`／`:2419-2423` 之後緊接併入）；空集合一律 `log.warning`＋`cov_*` metrics（不得靜默）。
- 設計／偵察期精確插入點（行號以 HEAD `f001e93` 量測；**實作前以現行 HEAD 再核**）：常數 `:165` 後、抽取器區 `:1152`、新方法 `:1257`、空集合 WARNING `:1222` 區、地端呼叫 `:2372`／`:2424`、pipeline metrics 行 `:2438` 區、`config.py` 新欄位 `:274` 後、`text_postprocess.py:849` 區。
- 驗收（plan §9.3，rev15 F1 版）：
  - **量尺釘版**＝`coverage-1.0.0`＋`quality/fact_checklist.json` sha256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`（實測一致；67 條／core 28）。P4-A 驗收一律用釘版；**P4-G 新尺不得回溯套用**。
  - **主要歸因閘門＝逐條事實**：E2E 逐筆命中 `600／800／17／13,600` 由 0/4→4/4、日期類逐筆命中（同清單 `facts[].covered` **＋ §11 N1 的原文片段可核**）、B2 不退步。
  - **聚合門檻＝觀察值**：`coverage_all 0.5075→≥0.65`、`coverage_core 0.6786→≥0.80`，須 **≥2 次取中位數**才可宣稱支持；單次結果一律註明「單次抽樣、不可歸因」。
  - **未達處理**：逐條達成但聚合未達 → 如實記錄＋根因分析；**不得**放寬量尺、擴類硬追、或改 denominator。
  - **共同歸因隔離**：P4-A 驗收場以 `LOCAL_FIDELITY_TRIPWIRES=false` 量測；若無法隔離，須明示共同歸因、召回功勞不得獨歸 P4-A。
  - **閘門不破**：現有 required 不得破（計數見 §11 C2）。
- 如實：每輪補強約 +350–400 s 為**預估**、待 E2E 實測；議題／決議解析良率 `[UNVERIFIED]`（`merged_notes` 未落盤）。

### 2.2 P4-B 落地摘要（忠實度絆索 A／B／C）
- 意圖（plan §9.4）：禁捏造／無依據歸屬／數字失真，從提示詞「希望」升級為**確定性絆索**→丟進補強問題清單（只回報、不改寫、不刪句）。
- 機制：新模組（§4.1 凍結介面）＋W1 薄方法掛地端兩呼叫點。A＝自創專名（三個高訊號位置＋registry＋fold 變體 `裏-裡-里-理／徵-征／菸-煙`，**上限 3 筆**）；B＝無依據歸屬（標註身分／開頭欄位／角色詞／承辦單位欄；歸屬內容一致性**僅觀察值**）；C＝數字／單位（先剝【發言者統計】與時間戳、單位綁類雙向比對；漏寫方向用材料視圖、捏造方向全量視圖）。硬約束：只引用紀錄與逐字稿原文、**永不生成新名稱**；輸出排序確定（不收斂保護不失靈）。
- 設計期校準（四場真實輸出）：A＝B2 0／B1 0／C1 1／D1 2（全為已知真實失真）；C 捏造＝0；漏寫四場一致＝`800／600／13,600／15%／17 人`；B 命中 B1 真缺陷「主持人：科長（發言者1）」。**registry-aware 修正**：`unsupported_entities` 舊 3 筆中 2–3 筆其實是正確官名（ASR 誤寫：稽查股／徵收股）→ 產品與量尺**共用同一份** registry-aware 函式。
- 驗收（plan §9.4）：地端捏造 ≤1（校準 0）；數字漏寫清單命中率上升（F024／F025 由 missing→covered）；不得報出 registry 官名；`local_fidelity_tripwires=false`＝產品輸出 **byte 級不變**；**雲端不動**（observe 預設／`enforce` 本波不得開啟）；**輪數不退步**：D1 現況 0 輪→預期 1 輪，但「輪數 >1 或 wall 退步 >25%＝未達」（baseline 記錄義務見 §11 N2）＋額外輪次下 B2／D1 coverage 不退步＋不收斂保護實證；E2E 27B＋Gemma 各一次、既有 required 全過不退步。成本接受（每模型預期輪數／牆鐘增量）＝**planner 決策**（「品質優先於時間」查無來源、不引用）。

### 2.3 P4-D 落地摘要（runner 閘門＋標註辨別力去重複化）
- 意圖（plan §9.6）：**不得再有 false PASS**（現行 required 無一來自品質儀器）＋修標註辨別力（可查核但不可檢索）。
- 產品側（W4）：吸附新增**規則 6：同標籤同時戳去重複化**——保留首筆，其餘改到同標籤 ±120 s 內**未使用**的真實段首（bigram 重疊優先）；cap=2、冪等、fail-soft、**不新增／不刪除標註**；由 `local_source_tag_diversify_enabled`（§4.2）控制。
- runner 側（W3）：契約見 §4.4；`--coverage-checklist` 永遠 observation；`distinct_tag_time_ratio` 維持觀察值。
- 驗收：B2 `distinct_tag_time_ratio` 0.288→**≥0.5**（離線模擬 0.654 `[INFERRED]`）；D1 ≥0.667 不退步（模擬 0.708）；`traceable／on_start／excluding_zero／body≥17／table=0` 均不退步；三模式語意（off／observe／required）逐條（§4.4）；**本機可執行**：provider 拆分（非 LM Studio 情境 required＝共通項，`model_inventory_unique`／`model_snapshot_consistent` 不因缺席 FAIL）、`mode_used` 事後斷言不符 ⇒ **FAIL**、登錄 `effective_local_llm_provider`。
- 升級判準（缺一不可；**本波不升級**）：連續 ≥3 場 observe、涵蓋 macOS＋Windows 兩引擎、每場個別過關、比值 max−min ≤0.02、儀器版本釘死、經 Plan＋獨立審查。
- Windows／Ollama full E2E 維持 `[UNVERIFIED]`。

### 2.4 P4-C 落地摘要（取樣與 context 同源）
- 意圖（plan §9.5）：先確認「參數與容量是否同一套」，讓 Mac 調出的參數在 Windows 生效。
- 內容（W1）：①Ollama `options` 改讀**同一份 config**（`top_p`／`top_k` 沿用 `LOCAL_LLM_SAMPLING_TOP_P/TOP_K`；`repeat_penalty` **另立 config 欄位**、不得寫死；保留 400 相容降級）；②補強路徑補「無法附逐字稿」WARNING；③context：**W-2 本波只登錄來源、不強改**（登錄 `context_window`＋`context_window_source`；報告另登錄 sampling 值與 Windows `LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`）；④A/B 0.7 vs 0.3（每組 2 次）中位數＋全距、表落檔。
- 現況（更正行號）：Ollama 寫死 `summarization.py:2779-2782`；`num_ctx` 讀取在 `:2783`（§11 C3）。
- 驗收（本機 payload 級 surrogate）：fake-engine options 斷言／WARNING 存在性／`context_window_source` 落檔欄位斷言／400 降級保留／A/B 中位數不退 ≥2 pp、字元數全距收斂。**Windows／Ollama 實機（gated `[UNVERIFIED]`）**：兩引擎同級（coverage／`on_start` 差異 ≤0.03）須 4090 實機量測；**不得以 Mac 上兩次 LM Studio 跑代替**；W-2 為「登錄欄位存在」明確斷言（不做數值強改）。

## 3. 檔案所有權（互斥寫入集；平行實作硬約束）
- **W1 擁有**：`backend/services/summarization.py`、`backend/core/config.py`
- **W2 擁有**：`backend/core/fidelity_checks.py`（新檔）、`data/glossary/` 或 `data/entities/` 下的 registry 資料檔、`scripts/e2e/measure_record_quality.py`
- **W3 擁有**：`scripts/e2e/run_owned_e2e.py`
- **W4 擁有**：`backend/core/text_postprocess.py`
- **任何人不得改**：`backend/services/task_processor.py:259/262`（逐字稿校正呼叫與其 temperature 傳參）、雲端提示詞（`CLOUD_SPEAKER_TRACEABILITY_RULE`）、**既有閘門門檻值**。
- 未配發所有權的本波檔案（例：`backend/core/glossary.py`、`scripts/e2e/measure_coverage.py`、`backend/core/templates.py` 等）——**動它之前先 STOP 回報**（§8），不得自行擴張寫入集。
- 跨包耦合只准走 §4 凍結介面（W1 讀 W2 的 `analyze_fidelity`；W4 讀 W1 提供的 config 開關），不得代寫他人檔案。

## 4. 凍結介面（W1／W2／W3／W4 一律照此實作；名稱凍結）
### 4.1 W2：`backend/core/fidelity_checks.py`（新檔）
```python
FIDELITY_METRIC_VERSION: str

def analyze_fidelity(
    record_text: str,
    transcript_text: str | None,
    template_id: str | None = None,
) -> dict
# 純函式、fail-soft：內部錯誤回傳空結果，不得拋出。

def load_entity_registry() -> set[str]
```
- `analyze_fidelity` 回傳 dict **至少**含：
  `{"metric_version": str, "problems": list[str], "fabricated_entities": list[str], "attribution_violations": list[str], "missing_numbers": list[str], "registry_aware_unsupported_entities": list[str], "raw_unsupported_entities": list[str]}`
- `problems`＝可直接併入既有補強問題清單的**人類可讀字串**（只回報、不改寫、不刪句、不提議替代名稱）。
- registry 資料檔置於 `data/glossary/` 或 `data/entities/`（W2 決定；內容＝官名／股別等已知實體白名單，供產品與量尺共用）。
- 設計草稿曾用暫名（`run_fidelity_checks`／`FidelityReport` 等）——**一律以本節凍結名稱為準**。

### 4.2 W1：`backend/core/config.py` 新增（名稱凍結）
- `local_llm_record_coverage_mode: str = "enforce"`（可為 `enforce`／`observe`／`off`）
- `local_fidelity_tripwires: bool = True`
- `local_source_tag_diversify_enabled: bool = True`
- Ollama 取樣參數與 context 預算的**同源設定**（依 plan §9.5）：`top_p`／`top_k` 沿用既有 `LOCAL_LLM_SAMPLING_TOP_P/TOP_K`；`repeat_penalty` **另立新 config 欄位**（名稱依 `config.py:224-270` 既有 `LOCAL_LLM_*` 慣例，實際名稱登錄於 `execution.md`）；context 沿用 `LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS` 並登錄 `context_window`／`context_window_source`——**不得寫死**。

### 4.3 W1：呼叫契約（地端忠實度合併）
- 在既有兩個地端呼叫點（`summarization.py:2371`／`:2423` 附近）把 `analyze_fidelity(...)["problems"]` **併入既有補強問題清單**（不改寫、不刪句、不新增提示詞）。
- `local_fidelity_tripwires=False` 時**完全不得呼叫**（byte 級不變；驗證方式見 §11 N3）。
- 雲端路徑不動（見 §5 不變式、§8 STOP）。

### 4.4 W3：runner 契約（`scripts/e2e/run_owned_e2e.py`）
- `--quality-mode {off,observe,required}`（**預設 `off`**）＋`--coverage-checklist`。
- `off`＝`run_summary.json` **不得出現新鍵**且 verdict 與現行相同；`observe`＝quality 有值、verdict 不因品質值改變；`required`＝低品質 fixture 必 FAIL 且 `failure_reasons` 逐條指名（且 `required` 無 `--template`＝`parser.error`）。
- 門檻**一律沿用既有值**（`table=0`／`body≥17`／`traceable≥0.95`／`on_start≥0.95`／`excluding_zero≥0.9`；`excluding_zero=None`＝不判定）；**不得新增未經審查的門檻**；`distinct_tag_time_ratio` 維持觀察值。
- `mode_used` 事後斷言：後端實際生效模式與請求不符 ⇒ FAIL；required 清單拆「共通必要／provider 相依」，登錄 `effective_local_llm_provider`。

### 4.5 W4：文字後處理契約（`backend/core/text_postprocess.py`）
- 吸附函式尾端新增**規則 6**（plan §9.6）：同標籤同時戳去重複化——保留首筆，其餘改到同標籤 ±120 s 內**未使用**的真實段首（bigram 重疊優先）；cap=2、冪等、fail-soft、不新增／不刪除標註；規則 0（段首保護）與精度保護（`kept_far`；`TAG_SNAP_MAX_SHIFT_SECONDS=120`）行為不變。
- 開關＝W1 提供的 `local_source_tag_diversify_enabled`（預設 True；False＝P3 byte 級回退）；stats／log 擴充依 plan §9.6 設計（不得改既有指標定義）。

## 5. SEMANTIC_INVARIANTS（不得破壞者）
- 雲端輸出 **byte 級不變**（提示詞與雲端問題清單不動；`CLOUD_FIDELITY_TRIPWIRES_MODE=observe` 為 plan 預設、`enforce` 本波不得開啟；I-2）。
- **既有閘門門檻值不改**（含 `on_start≥0.95`、`excluding_zero≥0.9`、`traceable≥0.95`、`body_source_tag_count≥17`、`table_source_tag_count=0`）；不得新增未經審查的門檻。
- **回退開關一行可關**（每包見 §9）。
- 吸附**規則 0（段首保護）**與**精度保護行為不變**（`kept_far` 刻意保留原時間戳；位移上限 120 s 語意不動）。
- **純 Python**：不得引入平台分支、不得模型名分支、不得 POSIX-only API（`start_new_session`／`killpg`／`SIGKILL` 等；樣板＝`run_owned_e2e.py:212-241` 既有 `os.name=="posix"` 分支）。

## 6. BEST_EFFORT／非阻斷（不得阻斷 CORE）
- **P4-E**（詞彙表治理＋長會議跨塊去重）：BEST_EFFORT；資料級回退；跨塊去重**尚無 config 開關**（設計缺口）→ 落地時須補「一行關閉」方可上線；其檔案多不在 §3 所有權集內（見 §3 註）。
- **P4-G**（量尺修訂＋文體維度，0 模型成本）：BEST_EFFORT；修訂以**新 `metric_version`／新清單 sha256** 落地，**不得就地改寫 `coverage-1.0.0` 語意**；**P4-A 驗收不受其回溯**。
- **P4-F**（雲端出處標註退化）：**只登記**，不修（動它＝動對照基準＋共用提示詞）。
- **本波不做（plan §9.9 原樣；不得升為必做）**：P4-F 修復；規則 2 不收緊；國字數字折疊；逐字稿關鍵詞抽議題／決議；`*討論重點*` 列入對帳；`check_record_output.py` 結構檢查整併（P1-11）；「保留最佳版本」；雲端 fidelity enforce／雲端標註去重複化；**P4-D `required` 升級決策**（本波只交付 off／observe／required 機制與 observe 證據）；跨標籤時間碰撞處理。

## 7. VERIFICATION
### 7.1 單元測試
```bash
DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py
```
- 新增測試檔（設計期定名，內化自設計定稿）：
  - `tests/test_t20260923_p4a_record_coverage.py`（P4-A；正反例與開關，15 項）
  - `tests/test_t20260922_2037_p4b_fidelity_tripwires.py`（P4-B；A／B／C／合併／開關／雲端不變）
  - P4-D（加入既有檔）：`tests/test_t20260922_2037_p3_parity.py`（規則 6／冪等／cap／精度）、`tests/test_owned_e2e_acceptance.py`（runner 三模式／fixture）、`tests/test_record_quality_metrics.py`（證據投影 schema）。
- 必含「不變量測試」：`local_fidelity_tripwires=false` 與 `--quality-mode off` 的 byte 級不變（§11 N3 函式級 golden）、雲端 byte 不變、規則 0／精度行為不變。

### 7.2 E2E（**必須前景執行**；run to completion）
```bash
uv run python scripts/e2e/run_owned_e2e.py \
  --audio "/Users/hsiaojohnny/Downloads/0903-科務會議.m4a" \
  --template section_meeting \
  --processing-mode local \
  --artifacts-dir .agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-<新目錄> \
  --runtime-dir data/cache/e2e/<隔離目錄>
```
- **必須前景執行**（不得背景化、不得中途抽離 session）；27B 與 Gemma 各一次（plan §9.4）。
- Preflight（hard gate、fail-closed）：**乾淨工作樹**（dirty → verdict FAIL、backend 不啟動）＋音檔存在＋`DATA_DIR` 可寫；attempt 目錄 **append-only**（已存在即拒）。勿動 port 9527（使用者 App）。
- E2E 前先記下 baseline（§11 N2）：`e2e/attempt-D1-gemma31b-p3/attempt.json` → `duration_seconds=1227.2`（`timing_breakdown.runner_total_seconds=1227.2`）、`pipeline_total_seconds=738.8`、補強輪數＝0（該場；輪數現僅在 log／人工記錄）。
- Windows 直跑補充：`uv run --with tzdata ...`（W-10）；本機 Mac 不需。

### 7.3 量尺指令（兩支 script）
```bash
uv run python scripts/e2e/measure_record_quality.py \
  --record "<runtime>/backend_data/outputs/0903-科務會議_<task>.md" \
  --transcript "<同上>_逐字稿.txt" --template section_meeting --out "<q.json>"
uv run python scripts/e2e/measure_coverage.py \
  --record "<同上 md>" \
  --checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json \
  --label <label> --transcript "<同上 逐字稿>" --json-out "<cov.json>"
```
- 行號（更正後）：`measure_record_quality.py --out`＝`:391-392`；`METRIC_VERSION`＝`scripts/e2e/measure_coverage.py:72`（版本鎖 `:73`；`measure_record_quality.py` 本身無 `METRIC_VERSION`）。

### 7.4 驗收必載產出（`execution.md`／驗收紀錄）
- P4-A **實際離線判缺表**（四份逐字稿×四份紀錄；§11 C1）。
- 逐條事實命中的**新紀錄原文片段**（grep 可核）＋「離線判缺」來源標註（§11 N1）。
- 補強輪數的計數方式與 log 證據（若未進 `pipeline_metrics`；§11 N2）。
- `off`／未開啟與現行的**函式級 golden byte 對照**（§11 N3）。
- A/B 中位數表（P4-C）、三模式證據（P4-D）、registry-aware 前後對照（P4-B）。

## 8. STOP／ESCALATION
- 任何需要**改既有閘門門檻**、**改雲端路徑**、**改 `task_processor.py:259/262`**、或**讓 `off` 模式行為改變**者 → **停止並回報**，不得自行決定。
- **若實作後發現「需要改既有閘門門檻、改雲端路徑、或改 `off` 模式行為」才能讓驗收過關 → 立即停止並回報（不得自行放寬）。**
- 任何語意變更（requiredness／gating／error／fallback／priority／validity）→ escalation＋planner replan（plan §9 開頭；AGENTS.md §10）。
- 需要動「未配發所有權」的檔案（§3 註）→ 先停止回報。
- `plan.md` 於核准後再變更 ⇒ 核准失效、本 handoff 失效（重審＋重編）；handoff↔plan 修訂／hash 不一致＝stop condition。

## 9. ROLLBACK（每工作包一行開關）
- **P4-A**：`LOCAL_LLM_RECORD_COVERAGE_MODE=off`（一行回本波前；`observe`＝只記 log／metrics；可縮 `CATEGORIES`）。
- **P4-B**：`LOCAL_FIDELITY_TRIPWIRES=false`（一行；產品輸出 byte 級不變）。
- **P4-D 產品**：`LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED=false`（一行回 P3 byte 級）。
- **P4-D runner**：`--quality-mode observe|off`（預設 off）。
- **P4-C**：保留舊常數路徑（一行 rollback 回寫死值）；A/B 前後對照存證。
- **P4-E**：詞表與紀錄級修正皆資料級逐行回退；跨塊去重上線前須先補「一行關閉」開關（設計缺口）。
- **P4-G**：量尺為工具、不改產品行為；清單與儀器 tracked，以 git 版本回退（新舊並存可比）。

## 10. 如實邊界（不得超譯）
- **Windows／Ollama 全 `[UNVERIFIED]`**（本機 macOS；研究 §12.9 七步最小驗證清單待 4090 實機）。
- 五場對照皆**單次抽樣**（temperature ≠ 0）；跨模型／引擎差異需 ≥2 次取中位數才可定論。
- C5 雲端基線 runner 未完成收尾（無 verdict／無 stored-bytes SHA；DOCX 事後補）→ 只當「真實雲端產物＋儀器量測」。
- 67 條清單為**相對比較工具**（18% 假陰性＋多筆假陽性），非絕對分數。
- 設計期數字：P4-D 0.654／0.708 為離線模擬 `[INFERRED]`；P4-A 議題／決議解析良率 `[UNVERIFIED]`；P4 補強 +350–400 s／輪為預估、待 E2E 實測。
- 本 P4 波**全部未實作**；未量測前不得宣稱「追上雲端」或任何未實作之事。

## 11. 編譯期強制更正（grounding audit＋review；不得略過）
### C1〔FALSIFIED 阻斷級〕P4-A 離線判缺表不得當已驗證前提
- 事實（獨立地面實證稽核 `/tmp/p4/review_grounding.md`＋編譯期重跑）：設計附原型 `/tmp/p4a_probe.py` 重跑只得到候選 `100／15／17／25／40／600／800`（**不含 13600**），且 **B2 只判缺 `600,800`**——`17` 被來源標註 `00:17:52` 洗白；`15` 四份皆未判缺。
- 實作**必須**：①數字比對前先剝來源標註（`_SOURCE_TAG_PATTERN`）＋NFKC＋**去千分位逗號**；②候選樣式要能涵蓋 `13,600`／`13600`；③**實作者要重跑四份逐字稿×四份紀錄，並把實際判缺表寫進 `execution.md`**（如實記錄；**不得沿用**未驗證的「5 數字、零誤判」措辭）。
- **E2E 的逐條事實命中仍是主要歸因閘門（不變）。**

### C2〔計數更正〕閘門 required 計數
- `required` 實為 **smoke 4／full 14／full+template 15**（`required_smoke`＝`backend_started`／`health_ok`／`build_revision_match`／`child_terminated`；full 再加 10 項；`--template` 再加 `template_applied`）。
- `run_summary.checks` **16 鍵＝15 required＋`model_snapshot_captured`（非 required）**。
- **任何文件不得再寫「16 個 required」**（歷史文件之舊口徑不追改；新文件一律用本節數字）。

### C3〔行號更正〕引用時用更正值
- Ollama `num_ctx`＝`backend/services/summarization.py:2783`（`:2773` 是 `"stream": True`）。
- 雲端日期接地 `_validate_cloud_date_grounding`＝`:1334-1356`（`:1295-1332` 為年份抽取器）。
- `METRIC_VERSION`＝`scripts/e2e/measure_coverage.py:72`（版本鎖 `:73`）。〔更正：稽核轉述之檔名「measure_record_quality.py」為誤；該檔無 `METRIC_VERSION`。〕
- `--out`（`measure_record_quality.py`）＝`:391-392`。
- 其他高頻引用校正（自地面稽核；行號基準 HEAD `f001e93`）：`_build_record_generation_message :1512-1553`、`_build_record_refinement_message :1563-1605`、`CLOUD_SPEAKER_TRACEABILITY_RULE :115-123`、`LOCAL_SOURCE_TAG_PLACEMENT_RULE :131-136`、pipeline metrics 行 `:2430-2442`、Ollama options 寫死 `:2779-2782`、LM Studio 取樣讀取 `:3242-3245`、`file_manager.save_result` 檔名 `:226`／log `:232`、`asr_worker :46-49`、`pypinyin`＝`pyproject.toml:56`。**實作前一律以現行 HEAD 再核行號**。

### N1〔review §C；中〕逐條事實閘門要可核
- 「逐筆命中」除 flags 外，**必須附新紀錄原文片段（grep 得到）**並留存於驗收紀錄；並標明「離線判缺」的來源（**人工複核 vs 原型探針**）。
- 已知量尺假陽性縫隙：`F061`（`10月底`）在 B2 量尺標 ✅ 但 B2 產物 grep＝0 → **不得只用 flags 判定**；若僅 flag 轉正而片段缺失 → **判未達**並登錄量尺假陽性案例。

### N2〔review §C；低〕輪數／wall baseline 先記再跑
- E2E 前先記下 baseline 欄位：**補強輪數＋wall 時間**（D1：`duration_seconds=1227.2`／`pipeline_total_seconds=738.8`／輪數 0），以判定「輪數 >1 或 wall 退步 >25%＝未達」。
- 補強輪數目前**不在** runner `pipeline_metrics`（僅 `merge_rounds`）——若未結構化，實作者要在 `execution.md` **如實說明你是怎麼數的（log 證據）**。

### N3〔review §C；低〕byte 不變＝函式級 golden
- `off` 模式（與 `local_fidelity_tripwires=false`、雲端 observe）之 byte 級不變（I-2）驗證要寫成**函式級 golden 測試**（同一輸入在 `off`／未開啟與現行的輸出**相同**），**不得只靠兩次 live 跑對照**。

### N4〔review §C；低；登記〕研究文件殘留舊口徑
- 研究文件 §12 仍有一處歷史「16 個 required」口徑（`:1170`；`:881` 引歷史）未修；本波**不得再寫**該口徑（見 C2），研究文件留待下次修訂一行校正。
