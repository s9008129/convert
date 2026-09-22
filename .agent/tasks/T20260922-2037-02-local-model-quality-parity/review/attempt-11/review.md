# Stage 02 獨立計劃審查（attempt-11）

- 受審對象：`T20260922-2037-02-local-model-quality-parity` / `plan.md` 的 **`PLAN_REVISION: 14`**（§9 P4 波，`plan.md:664-839`）＋配套研究文件 §12（`doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md:1057-1245`）。
- 受審 sha256：`a3acc7d7d6d1efce288935b7fe09b0d07e39a94d0edadd83c055e26c36831038`（2026-09-23 03:53 CST 量測；`review/attempt-11/snapshot_plan.md` 為同刻副本、`plan_sha256.txt` 同值）。**本判定只綁此修訂與此 hash**。
- 審查者：fresh context、read-only（產品碼與 `plan.md` 未修改；本審查只落檔 `review/attempt-11/`）。舊核准（attempt-10 對 rev 13 的 `PLAN_APPROVED`）**不得沿用**。
- 可用輸入：`/tmp/p4a_design.md`、`/tmp/p4b_design.md`、`/tmp/p4d_design.md`、`/tmp/p4_crossos_design.md`（存在）；**`/tmp/p4/review_grounding.md` 不存在**（該目錄僅 `doc_s12.md`、`p4a_fixtures.json`、`verify_c5.md`）→ 本審查所有斷言均由我自行對 repo 重驗（見 §C）。

## A. Goal Baseline（自行重建；來源：使用者原話＋plan §0／§7／§8.0／§9.1＋事實清單）

1. **主要成果（N-4，plan:323-325 引使用者原話）**：Mac＋LM Studio 以 `section_meeting` 生成的會議紀錄（Qwen3.8-27B dense、Gemma 4 31B），品質「接近／追上雲端 Gemini」；**未量測前不得宣稱達成**。
2. **機制要求（N-5／N-7）**：品質槓桿必須**模型無關**（換模型不改機制）；macOS（LM Studio）與 **Windows 11＋RTX 4090（Ollama）一體適用**（N-8）。
3. **邊界**：雲端＝**對照基準、byte 級不動**（N-9）；使用者指定**只測 Qwen3.8-27B**（不以 `qwen3.6-35b-a3b-splash` 為受測目標）；Windows 實機未到前一律 `[UNVERIFIED]`。
4. **量尺事實（本次核對通過）**：D1 Gemma `coverage_all 0.5075／core 0.6786`（`quality/coverage/coverage_gemma31b_d1.json`）；B2 27B `0.8209／0.8929`（`coverage_qwen27b.md`）；C5 雲端 `0.8060／0.8929`＋28 標註全 `00:00:00`（`attempt-C5-cloud-baseline/coverage.json`、`record_quality.json`）；清單 67 條＝core 28（sha256 `cf012d1f…`）。量尺自身 18.2% 假陰性、不看文體（R28）→「差距」不能只看這把尺。
5. **本波合理核心語意**：把「模型真漏寫的事實」可靠推回第二輪補回（P4-A）；忠實度（禁捏造／無依據歸屬）進補強清單（P4-B）；E2E 不再 false PASS＋標註可檢索（P4-D）；P4-C／E／G 支援性；雲端本身不修（P4-F 只登記）。

## B. Top-down 發現（目標對齊／必要性／閘門比例性／耦合／設計經濟）

### F1〔阻斷〕P4-A 驗收之「歸因治理」不足（量尺釘版、跑次、可達性、聯動）— `plan.md:703-706`（相關：§9.8 `:795-806`、§9.9 `:810`、§9.11-5 `:837`）

**先更正一個前提**：P4-A **不是**「量尺側的期望集合擴充」——它是**產品側**（地端補強問題清單，呼叫點 `summarization.py:2367／:2419`）；量尺 `measure_coverage.py` 為獨立工具、清單 sha 釘死（`coverage_qwen27b.md` 實證）→ P4-A **不改變分母**。但「數字變好、內容沒真的變好」的真實路徑仍有三條，plan 未擋：

1. **同波聯動**：`§9.8` P4-G 要在**同一波**修量尺（18% 假陰性修正會直接墊高 coverage）；`§9.3` 驗收**未釘量尺版本** → 若 P4-G 先落地再量，P4-A 的增幅不可歸因（＝真正形態的指標遊戲風險）。
2. **單次抽樣變異**：同模型 D1 vs C1 差 6.0–7.1 pp（`attempt-D1-gemma31b-p3/attempt.json` note 自證）；單跑 +12～14 pp 的門檻本身分不清訊號與雜訊。
3. **可達性未證**：設計自驗的判缺只有 `600／800／17／13,600／15`＋`10月底`（＋D1 `週一`）→ 對清單至多 +F024（supporting）＋F025／F061／F021（core）＝ core 19→22/28＝**0.786＜0.80**、all 34→38/67＝**0.567＜0.65**；達標必須再靠「議題／決議抽取＋整份重生成」的連帶效果，而該良率 plan 自標 `[UNVERIFIED]`（`:837`，`merged_notes` 未落盤）。
4. **雙重歸因**：P4-B(C)（`:728`）也會把同一批漏寫數字丟進補強清單 → 同波落地時 F024／F025 的召回無法分辨是 A 還是 B 的功勞。

**做對、應保留**：驗收已含**產品輸出的逐條可觀察證據**——`600／800／17／13,600` 由 0/4→4/4、`10月底`／D1 `週一` 命中（以同一清單 `facts[].covered` 判讀，`:705-706`）。這正是要升格為**主要歸因閘門**的東西；`§12.10` 的落地序（D→A→B→C→E→G）也剛好支持「P4-A 驗收在 P4-G 之前量」——只要把釘版寫死。

**具體修法（文字級，最小）**：`§9.3` 驗收改寫為——
  (i) 「聚合門檻一律以 `coverage-1.0.0`＋checklist sha256 `cf012d1f…` 量測；P4-G 新尺（新 `metric_version`）數值**不得替代**本判定，只能並列」；
  (ii) 「**主要歸因閘門＝逐條事實**（CORE-3）；聚合 ≥0.65／≥0.80 列目標值，須 ≥2 次取中位數，否則結果一律註明『單次抽樣、不可歸因』」；
  (iii) 「若逐條達成、零誤判但聚合未達：如實記錄＋根因分析；**不得**為達門檻放寬量尺或擴類硬追」；
  (iv) 「P4-A 驗收場以 `LOCAL_FIDELITY_TRIPWIRES=false` 隔離（或明示與 P4-B 的共同歸因）」。

### F2〔中〕P4-B：雲端 byte 不變的驗收未進 plan；補強輪增量未寫成受控驗收 — `plan.md:730-731`（設計：`/tmp/p4b_design.md:272,314,372`）

- **雲端**：設計已有 observe＝只 log／metrics、I-2 測試＝observe 下雲端 issues 與 v4.8.0 **byte 級相同**——但 plan §9.4 的**驗收**只有「關閉開關＝byte 級不變」（語意偏地端 `LOCAL_FIDELITY_TRIPWIRES`）。雲端是使用者釘死的對照基準（N-9）→ 修法：§9.4 驗收補「**observe（預設）下雲端輸出與問題清單 byte 不變（I-2）**；`enforce` 不得在本波開啟」。
- **輪數**：P4-B 落地後 D1 由 **0 輪→≥1 輪**（每輪 ≈+350–400 s、整份重生成＝R23 已知負向風險）；plan 只在 P4-A 註記成本。修法：§9.4 驗收補「**額外輪次下 B2／D1 coverage 不退步＋不收斂保護實證（問題集合不變即停）**」；並在 §9.3／§9.4 共同載明本波每模型預期輪數／牆鐘增量的**接受決策**。
- **如實性附帶**：`/tmp/p4b_design.md:314` 寫「使用者已明確表示品質優先於時間」——plan §0／§7／§8.0／§9.1 **查無此陳述**。請引來源或改記為 planner 決策。

### F3〔中〕W-3／W-5（provider 拆分＋`mode_used` 斷言）只存在於敘述、未入 P4-D 驗收；runner 目前 0 Ollama 支援 — `plan.md:771-775`

- 實證：`rg -i ollama scripts/e2e/run_owned_e2e.py`＝**0 命中**；`:434-450`＋`:1291-1308` 的 `model_inventory_unique`／`model_snapshot_consistent` 硬綁 LM Studio snapshot → 「Windows／Ollama full E2E 必 FAIL」成立。P4-D 是 CORE，而 N-8（雙平台）是硬需求。
- 修法：§9.6 驗收新增**本機可執行**條目：(a) 非 LM-Studio provider 情境下 required＝共通項、provider 相依項不因缺席而 FAIL（單元測試）；(b) `mode_used`（後端實際生效模式）與請求不符 ⇒ FAIL；(c) 寫明 Ollama 模式下 inventory 檢查的替代／豁免方式（目前 runner 無任何 Ollama 分支，需定義 placeholder）。

### F4〔中〕P4-C「兩引擎同級（≤0.03）」驗收**本機不可執行**（Mac 的 Ollama 無任何模型：`ollama list`＝空）— `plan.md:746`

- W-1 修法本身可本機驗（payload 級：Ollama `options` 值＝config），但「兩引擎同級」需 Windows 實機。修法：§9.5 驗收拆兩條——本機＝fake-engine payload 斷言＋`context_window_source` 落檔欄位測試；跨引擎比較＝**Windows-gated `[UNVERIFIED]`**（不得以 Mac 上兩次 LM Studio 跑代替）。W-2 維持「只登錄」，把「登錄欄位存在」寫成明確斷言即可。

## C. Bottom-up 發現（repo 落地性／契約／如實性）

### B-F1〔低〕「16 項 required checks」計數錯誤：實為 **14**（`--template` 時 **15**）— `plan.md:706`、`:730`、`:754`（研究 §12.6 同）
實證：`:1291-1308`＝4 smoke＋10 full＝14，加 `template_applied`＝15；D1 實跑命令確有 `--template section_meeting`。修法：改為「14（`--template` 時 15）」或重述。此計數出現在三個驗收句內，屬驗收文本正確性，請一併更正。

### B-F2〔低〕設計細節檔僅存 `/tmp`（不可持久）＋W 編號雙軌 — `plan.md:664-668`、`:773`
rev 14 的觸發事實③宣稱「研究 §12＋跨 OS 稽核已完成」；研究 §12 已入 repo（`:1057+`），但四份設計細節與「P4 跨 OS 稽核」只在 `/tmp`（`research/` 目前僅 audit-02／03，為 P2／P3 期）；且研究 §12.9 的 W-1/2/3 與稽核表的 W-1..W-14 是**兩套編號**（plan:773 引用的「W-5」是稽核表編號）。修法（建議）：四份設計檔收入 `.agent/tasks/.../research/p4/`（tracked）＋加一行 W 編號對照。非阻斷。

### B-F3〔低〕研究 §12.9「Ollama 固定 8192／16384」精確性 — doc `:1206-1212`
實查：Ollama 取 context 走 `settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`（預設 8192，`config.py:188-191`；`summarization.py:2709-2716`）；`16384` 只出現在 GPU compose 與 KV 記憶體估算（`summarization.py:4085,4093`）。結構主張（不同源）成立，數字可補「16384＝GPU compose」出處。可不修。

### C.2 核對通過（非發現；我抽查的斷言，>5 條）
1. `summarization.py:148`（LCS 0.6）、`:161-162`（否定詞／`\d{2,}` 守衛）✓；`:1112-1139`（抽取器只認 ≥3 欄表格列）、`:1208`（expected 來源）、`:1222-1250`（log／issues 全在 `if missing_actions`＝靜默 no-op）✓。
2. 呼叫點：地端 `:2367`／`:2419`；雲端 `:3527`／`:3565`（**P4-A 不動雲端路徑**，符合 N-9）✓。
3. W-1：`:2779-2782` 寫死 `top_p=0.95／top_k=64／repeat_penalty=1.08`；LM Studio 走 config（`config.py:241-267`：0.8／20；溫 0.6/0.6/0.7/0.7/0.3）；400 降級 `:3215-3224` ✓。W-2：`:2263-2268`（instance `context_length`）vs 設定預設 8192 ✓。
4. W-3：`:1291-1308` required 清單＋`:434-450` inventory 檢查（LM Studio 專屬）✓；runner 0 Ollama 分支 ✓。
5. P4-D：`--quality-mode` 預設 `off` ✓（設計:37、plan:760）；門檻映射全用既有值、**`distinct_tag_time_ratio` 維持觀察值＝未被誤當閘門**（`:761`）；`required` 升級需 ≥3 場 observe＋兩引擎＋逐場個別過關＋max−min ≤0.02＋獨立審查（`:763-766`、`:816-817`）✓。
6. 量尺數字：B2 52／15／0.288、D1 24／16／0.667、C5 28 全零時／0.036（三份 `record_quality.json`）✓；D1／B2／C5 coverage 值 ✓。
7. 其他落地點：`measure_record_quality.py:210` ✓；`prompts.py:18-25`（忠實性只在提示詞）✓；`apple.py:494-497`（Apple 不吃 hotwords）✓；`glossary.py:63-80`（`utf-8`、`except OSError` 過窄）✓；`templates.py:474`（`record_term_fixes` 凍結 4 條）✓；`data/glossary/公務詞彙.txt` 非註解 `=>` 條目＝0（1270 bytes）✓；`config.py:552`（`DATA_DIR=/app/data`）✓。
8. **修訂單調（機械證明）**：`git diff HEAD`（HEAD＝rev 13 已落版）＝ `plan.md` **+183／−2**，兩處刪除**恰為**標題行與 `PLAN_REVISION: 13` 行；§9 全數新增；研究文件 **+191／−0**（純追加）→ **無就地改寫舊修訂**。
9. **如實性**：§9 開頭自聲「規劃（尚未實作）」（`:666-668`）、§9.11-6「本節全部未實作」（`:838`）✓；CORE（A/B/D）／SUPPORTING（C/E/G）／全域阻斷理由分列（§9.10）✓；Windows 各節均標 `[UNVERIFIED]`（:677-680、:742-748、:772-776、:833-835）✓；未發現「已完成」之不實宣稱（B-F2 為耐久性建議，非不實）。

## D. 可重現指令（節錄）
```bash
shasum -a 256 .agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md   # a3acc7d7…
git diff HEAD -- .agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md | grep -c '^+'
rg -i ollama scripts/e2e/run_owned_e2e.py            # 0 命中
sed -n '1291,1308p' scripts/e2e/run_owned_e2e.py     # required＝14（+template 15）
ollama list                                          # 空（Mac 無 Ollama 模型）
python3 -c 'import json;d=json.load(open(".agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json"));print(len(d["facts"]),sum(1 for f in d["facts"] if f["tier"]=="core"))'  # 67 28
```

## E. 閘門（唯一）

**`PLAN_REVISION_REQUIRED`** — 綁定 `PLAN_REVISION 14`＋sha256 `a3acc7d7d6d1efce288935b7fe09b0d07e39a94d0edadd83c055e26c36831038`。

阻斷項：**F1**（P4-A 為本波主交付 CORE；其聚合驗收在「量尺未釘版＋同波量尺修訂＋單次抽樣＋可達性未證＋與 P4-B 重疊歸因」下，通過與否都無法支撑結論＝決策有效性缺口）。

**最小必要修正清單**（全部為 §9 文字級改寫，不需重規劃）：
1. **F1**：§9.3 驗收加 (i) 量尺釘版（`coverage-1.0.0`＋`cf012d1f…`，P4-G 新尺不得替代）；(ii) 逐條事實（CORE-3）升為主要歸因閘門＋聚合門檻 ≥2 次中位數（或註明不可歸因）；(iii) 未達時「如實記錄＋根因分析、不得放寬量尺／擴類」；(iv) 驗收場與 P4-B 隔離（或明示共同歸因）。
2. **F2**：§9.4 驗收加「雲端 observe 預設 byte 不變（I-2）＋enforce 不開啟」與「額外輪次下 B2／D1 coverage 不退步＋不收斂保護實證」；輪數成本改記為 plan 決策（來源或決定）。
3. **F3**：§9.6 驗收加 provider 拆分＋`mode_used` 斷言之本機可執行測試，並定義 Ollama 模式下 inventory 檢查的處置。
4. **F4**：§9.5 驗收拆「本機 payload 級 surrogate」與「Windows-gated 跨引擎比較」。
5. **B-F1**：三處「16」改為 14／15（或重述）。

建議（非阻斷）：B-F2（設計檔收入 repo＋W 編號對照）、B-F3（8192／16384 精確化）。

---

- 本審查未修改產品碼與 `plan.md`；`review/attempt-11/` 僅含 `review.md`、`snapshot_plan.md`、`plan_sha256.txt`。舊 `attempt-01..10` 未動。
- 審查窗口：2026-09-23 03:53–04:05 CST。若 `plan.md` 於本判定後再變，本判定失效力，須遞增 `PLAN_REVISION` 並重審。
