# Stage 02 獨立計劃審查（attempt-12）

- 受審對象：`T20260922-2037-02-local-model-quality-parity` / `plan.md` 的 **`PLAN_REVISION: 15`**（§9 P4 波，`plan.md:672-884`）＋配套研究文件 `doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md` §12。
- 受審 sha256：**`a7ea4be6a06c30abd9bb68fd51c46c525e1da1ddec52cf6e45bdc0d3ac3a35fb`**（2026-09-23 04:10–04:16 CST 量測；`review/attempt-12/snapshot_plan.md` 為同刻副本、`plan_sha256.txt` 同值）。使用者先前轉述的 `d40cc16a…` 為 Planner 寫入途中的中間狀態（使用者已更正），**最終值以上述量測為準**；本審查前後兩次量測與 snapshot 三方一致。
- 上一輪（attempt-11）審的是 rev 14（sha256 `a3acc7d7…`），gate＝`PLAN_REVISION_REQUIRED`（阻斷 F1，及 F2／F3／F4／B-F1）。本判定只綁 **rev 15＋上述 sha256**；`plan.md` 若再變更即失效。
- 審查者：fresh context、read-only（未修改產品碼與 `plan.md`；只落檔 `review/attempt-12/`；`attempt-11/` 未動）。

## A. Goal Baseline（自行重建；來源＝使用者原話見 plan §0／§7／§9.1＋`quality/fact_checklist.json`）

1. **主要成果（N-6／沿用 N-4）**：Mac＋LM Studio（Qwen3.8-27B dense、Gemma 4 31B）`section_meeting` 會議紀錄品質**接近／追上雲端 Gemini**；未量測前不得宣稱達成。使用者指定**只測 Qwen3.8-27B**，不以 `qwen3.6-35b-a3b-splash` 為受測目標。
2. **機制要求（N-7／N-8）**：品質槓桿必須**模型無關**；**macOS（LM Studio）＋ Windows 11＋RTX 4090（Ollama）**一體適用；Windows 實機未到前一律 `[UNVERIFIED]`。
3. **邊界（N-9）**：雲端＝**對照基準、byte 級不動**（P4-F 只登記）。
4. **量尺事實**：清單 67 條＝core 28（`quality/fact_checklist.json`，sha256 實測 `cf012d1f…` 與 plan 所載一致）；D1 Gemma `coverage_all 0.5075／core 0.6786`；B2 27B `0.8209／0.8929`；C5 雲端 `0.8060／0.8929`；量尺自身 18.2% 假陰性＋假陽性（R28）→ 它是**相對比較工具**（§9.11-4）。
5. **本波合理核心**：P4-A（漏寫事實第二輪補回）／P4-B（忠實度絆索）／P4-D（runner 防 false PASS＋標註辨別力）＝CORE 全域阻斷；P4-C／E／G＝SUPPORTING。

## B. attempt-11 六條 finding 的逐條收斂核對（引用 rev 15 實文，不信自述）

### F1〔原阻斷〕P4-A 歸因治理 — **已實質收斂（5/5 要件到位）**
1. **量尺釘版**：`plan.md:717-719`「一切判定一律以 `coverage-1.0.0`＋`quality/fact_checklist.json` sha256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001` 量測；**P4-G 的修訂不得回溯套用到 P4-A 的驗收數字**」。我重驗：該 sha256 與現行檔案**完全相同**；`coverage_gemma31b_d1.json` 之 `metric_version`＝`coverage-1.0.0`。✓
2. **逐條事實升主要歸因閘門**：`:720-722`「主要歸因閘門＝逐條事實…E2E 逐筆命中：`600／800／17／13,600` 由 0/4→4/4、日期類逐筆命中（以同清單 `facts[].covered` 判讀）；B2 不退步」。我重驗：F024＝600元禮券（supporting）、F025＝800元/17人/13600元（core）、F021＝`週一`（core）、F061＝`10月底`（core）**皆實際存在於清單**→ 閘門有可執行落點。✓（但有假陽性縫隙 → 見 N1）
3. **聚合降觀察值＋≥2 次中位數**：`:723-724`「`coverage_all 0.5075→≥0.65`、`coverage_core 0.6786→≥0.80` 列**觀察目標**，須 **≥2 次取中位數**才可宣稱支持；單次結果一律註明『單次抽樣、不可歸因』」。✓（全 plan §9 內 `0.65／0.80` 僅此一處，無殘留硬閘門）
4. **未達如實處置**：`:725-726`「逐條達成但聚合未達 → **如實記錄＋根因分析**；**不得**放寬量尺、擴類硬追、或改 denominator」。✓
5. **P4-B 隔離**：`:727-728`「P4-A 驗收場以 `LOCAL_FIDELITY_TRIPWIRES=false` 量測；若無法隔離，須明示共同歸因、召回功勞不得獨歸 P4-A」。✓ 且 P4-G 側對稱條款在 `:846-847`「**P4-A 驗收不受本修訂回溯**（一律用釘版…，新尺僅並列觀察）」。✓
- 判定：**收斂**（原阻斷解除）。殘餘以 N1（中，非阻斷）承接。

### F2〔原中〕P4-B 雲端 byte 不變＋補強輪增量 — **實質收斂（殘留細節 → N2／N3）**
- 雲端：`:756-757`「`CLOUD_FIDELITY_TRIPWIRES_MODE=observe`（預設）下，雲端輸出與問題清單 **byte 級不變（I-2）**；`enforce` **本波不得開啟**」。✓
- 輪數：`:758-759`「D1 現況 **0 輪 → 落地後預期 1 輪**，但**輪數 >1（需第 2 輪）或 wall 時間退步 >25%＝未達**；額外輪次下 B2／D1 coverage 不退步＋不收斂保護實證（問題集合不變即停）」。我重驗：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 預設＝**2**（`backend/core/config.py:270`）→ 此條非空洞；收斂保護在 `summarization.py:2377-2387`。✓
- 無來源陳述：`:759-760` 改記「成本接受＝**planner 決策**（設計檔『使用者品質優先於時間』於 §0／§9.1 **查無來源**，不引用）」。✓
- 判定：**收斂**；「>25% 對哪個 baseline」「輪數無結構化欄位」為執行細節，列 N2（低）。

### F3〔原中〕W-3／W-5 provider 拆分＋`mode_used` — **實質收斂**
- `:807-813`「本機可執行驗收（不需真的 Ollama）：provider 拆分（非 LM-Studio provider 下 required＝共通項，inventory 檢查不因缺席 FAIL，monkeypatch 單元測試）／`mode_used` 與請求不符 ⇒ FAIL／Ollama 模式登錄 `effective_local_llm_provider`＋定義該分支（runner 現 **0 Ollama 分支**…落地時須定義）」。✓ 三項全數落地，且與現況證據（`:792`）互相對齊。
- 判定：**收斂**。

### F4〔原中〕P4-C 兩引擎同級驗收不可本機執行 — **實質收斂**
- `:777-782` 拆兩層：①本機 payload 級 surrogate（fake-engine options 斷言／WARNING 存在性／`context_window_source` 落檔斷言／400 降級保留／A/B 2×2 中位數＋全距）；②Windows 實機 gated `[UNVERIFIED]`，「**不得以 Mac 上兩次 LM Studio 跑代替**」；W-2 寫成「登錄欄位存在」明確斷言。✓
- 判定：**收斂**。

### B-F1〔原中〕「16」計數 — **收斂（我逐處重驗）**
- 四處已改：`:729-730`（另附對帳：`run_summary.checks` 另含 1 個非 required 鍵，故歷史「16/16」不衝突）、`:761`、`:790-791`、`:792`。
- 我重驗計數：`scripts/e2e/run_owned_e2e.py` required＝`required_smoke`(4)＋10 項＝**14**，`--template` 時 **15**；歷史檔 `e2e/attempt-B2-27b-fix/run_summary.json` 之 `checks`＝**16 鍵**（15 required＋1 非 required `model_snapshot_captured`）→ plan 的對帳**正確**。✓
- 判定：**收斂**。

### B-F2〔原建議〕設計檔僅存 `/tmp`＋W 編號 — **部分收斂（可接受，非阻斷）**
- `:680-682` 加註「四份設計細節僅存 `/tmp`（非 repo 產物、不持久）→ **落地時須把決策摘要內化至 plan/handoff、不得依賴 `/tmp`**；W 編號雙軌（衝突者帶來源前綴）」。rev15 修訂紀錄（`:99-100`）明示本輪僅准改 `plan.md` 故不收入 repo。設計決策在 §9.3-9.11 已有足夠摘要（本輪審查即以 §9 實文判讀），風險已由「內化義務」覆蓋。殘留：handoff 須落實內化（N4 附帶）。
- 判定：**有理由之延後，可接受**。

### B-F3〔原「可不修」〕研究 §12.9「8192／16384」精確化 — **不修可接受**；惟研究文件 §12 仍殘留舊口徑「16」（見 N4）。

## C. Top-down／新問題掃描（rev 15 是否引入新缺陷）

- **閘門可達成性**：聚合門檻已降為觀察值（`:723`），主要閘門＝逐條事實且各條在清單中真實存在 → 非不可達成。**無** SUPPORTING→CORE 升格（`:736` CORE／`:765` CORE／`:786` SUPPORTING／`:819` CORE／`:837` SUPPORTING／`:851` SUPPORTING，與 §9.10 一致）。**無** 未標 `[UNVERIFIED]` 的 Windows 宣稱（§9.3 `:734-735`、§9.5 `:785`、§9.6 `:813`／`:817-818`、§9.11-3）。P4-D 升級判準與「不在本波自動發生」齊備（`:679`、`:796` 預設 off、`:799-800` 升級判準、§9.9）。`distinct_tag_time_ratio` 未被誤設為 runner 閘門（`:798`「維持觀察值」；`:803` 之 ≥0.5 為規則 6 的產品驗收 KPI，非 runner 閘門）。修訂單調性（rev 14→15）：刪除 12 行＝標題＋`PLAN_REVISION` 行＋§9 內 10 行被替換的驗收條文；rev 14 修訂紀錄**原樣保留**、rev 15 以 `:92-100` 追加 → **無就地改寫舊修訂**。
- 以下為本輪新發現（皆**非阻斷**）：

### N1〔中〕主要歸因閘門的 flags-only 判讀有量尺假陽性通關縫隙，且 `10月底` baseline 陳述與釘版量尺輸出不一致 — `plan.md:720-722`（另 `:721`）
- 實證：釘版量尺輸出 `quality/coverage/coverage_qwen27b.md:107` 與 `coverage_gemma31b.md` 對 **F061（10月底）標 ✅**（B2：matched group 3 @2020,2023）；但 B2 實際紀錄 `data/cache/e2e/p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md` **grep `10月底`＝0 命中**，plan `:721` 亦自述離線判缺「`10月底` 四家全缺」→ 兩套 baseline（離線人工判缺 vs 量尺 flags）未分寫，且量尺對 gate 條目存在假陽性實例（R28 已知）。
- 影響：若只以 `facts[].covered` flags 判「逐筆命中」，理論上存在「flag 轉正、內容未真的寫入」的通關路徑 → 這正是 F1 要消滅的指標遊戲縫隙（窄，但具體）。
- 具體修法（文字級，不重規劃）：`:721-722` 明寫 baseline 為「**離線人工判缺（方法：四份逐字稿×四份紀錄）**」；E2E 逐筆命中除 flags 外，**要求留存該事實於新紀錄的原文片段**（人工可核）於驗收紀錄；若僅 flag 轉正而片段缺失 → 判未達並登錄量尺假陽性案例。**不阻斷本修訂核准**（D1 側 F021／F024／F025／F061 現全為 ❌，`coverage_gemma31b_d1.json`，仍須真實改變才會轉 ✅；此修法是把守門再收緊）。

### N2〔低〕「輪數 >1／wall 退步 >25%＝未達」的可執行細節 — `plan.md:758-759`
- (a) 未指明 baseline 欄位：可用 `e2e/attempt-D1-gemma31b-p3/attempt.json`（`duration_seconds=1227.2`；pipeline `total=738.8`）→ 請釘明比對欄位。(b) **輪數目前不可結構化讀取**：`pipeline_metrics`（`attempt.json:128`）含 `merge_rounds` 但**不含補強輪數**（補強輪數現僅存在 log「第 N 輪」）→ 建議把 `refinement_rounds` 納入 metrics／E2E 產物。(c) 未寫「未達」後處置（如實記錄＋根因，沿用 F1③ 精神）。不阻斷。

### N3〔低〕雲端 byte 不變（I-2）驗證方法未落 plan 文字 — `plan.md:756-757`
- 兩次 live 雲端不可比（temperature>0 不可重現；§9.11-2 亦自承 C5 無 stored-bytes SHA）→ 建議明寫以「**固定輸入之函式級 golden 對照（prompt＋issues＋後處理輸出 byte 相同）**」驗證，並納入 B-F2 的「落地時內化」義務清單。不阻斷。

### N4〔低〕研究文件 §12 仍殘留舊口徑「16 個 required checks」 — `…研究與優化規劃.md:1170`（另 `:881` 引歷史「16 項 required checks 全過」）
- plan 已改 14/15 並給出對帳；研究文件本輪未修（rev15 宣告僅 `plan.md` 可動）。建議下次研究文件修訂時一行校正（歷史 16/16 可保留為「16 鍵／15 required」）。不阻斷。

## D. Bottom-up 抽查（本輪重新實證 ≥5 條，指令可重現）

1. hash 三方一致：`shasum -a 256 plan.md`＝`a7ea4be6…`＝snapshot；`plan_sha256.txt` 同值。
2. 清單釘版：`shasum -a 256 quality/fact_checklist.json`＝`cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`；`facts=67／core=28`＝plan 所載。
3. required 計數：`scripts/e2e/run_owned_e2e.py:1291-1307`（4＋10；`--template`＋1）；`e2e/attempt-B2-27b-fix/run_summary.json`＝16 鍵（15 required＋1 非 required）→「14/15＋16 鍵對帳」成立。
4. 修訂單調：`diff attempt-11/snapshot_plan.md plan.md`＝`<12 / >57` 行；12 刪除＝標題＋rev 行＋§9 被替換驗收條文；rev14 紀錄保留。
5. 輪數語意：`config.py:270` `LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2`；`summarization.py:2377-2387` 收斂保護（簽章不變即停）。
6. gate 條目落地：清單實存 F024（600）／F025（800,17,13600）／F021（週一）／F061（10月底）；D1 量尺四條全 ❌、C5 F021／F061 ✅。
7. **新證據（N1）**：`coverage_qwen27b.md:107` F061 ✅ 但 B2 產物紀錄 grep「10月底」＝0 → 量尺假陽性於 gate 條目之實例。
8. `plan.md:796-798`：`--quality-mode` 預設 `off`、門檻映射全用既有值、`distinct_tag_time_ratio` 觀察值；`:679`：`required` 升級不在本波。
9. 如實性：`:675`「本節是規劃（尚未實作）」、`:884`「本節全部未實作」；Windows 各節 `[UNVERIFIED]` 齊備。

## E. 閘門（唯一）

**`PLAN_APPROVED`** — **核准的是 `PLAN_REVISION 15`＋sha256 `a7ea4be6a06c30abd9bb68fd51c46c525e1da1ddec52cf6e45bdc0d3ac3a35fb`**。

- attempt-11 之 F1（阻斷）／F2／F3／F4／B-F1 **已實質收斂**（證據與行號見 §B）；B-F2／B-F3 之延後有明確理由且不影響決策有效性。
- 本輪**無阻斷項**。N1（中）＋N2／N3／N4（低）為**非阻斷**後續：建議在 Stage 03 Handoff 時以 1-2 行文字落實（尤其 N1 的「原文片段可核」與 N2 的 `refinement_rounds` 結構化），不要求再遞增 `PLAN_REVISION`。
- 若 `plan.md` 於本判定後再變更，本核准失效力，須遞增修訂並重審。

---
- 本審查未修改產品碼與 `plan.md`；只新增 `review/attempt-12/{review.md,snapshot_plan.md,plan_sha256.txt}`；`attempt-11/` 及更早 attempts 未動。
- 審查窗口：2026-09-23 04:10–04:18 CST。
