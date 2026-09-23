# 政府智慧會議紀錄生成系統 - 變更紀錄

## [v4.10.1] - 2026-09-23

### 🎯 主題：P5 波——「一定要修的 ASR 固定誤辨」改成跨 OS／跨模型共用的資料檔，並修掉校正層耗時膨脹

使用者需求：Mac ＋ LM Studio 的地端模型（本輪聚焦 `qwen3.8-27b-splash` 與
**`gemma-4-31B-it-MLX-4bit`**）生成的會議紀錄品質要拉近雲端 Gemini；品質機制必須**模型無關**，
日後在 Windows 11 ＋ RTX 4090 ＋ Ollama 也一體適用（明示不測 MoE `qwen3.6-35b-a3b-splash`）。

### 🔧 修正

1. **P5-A 確定性誤辨層（資料檔驅動）**：新增 `data/glossary/確定性誤辨校正.txt`
   （43 組 `錯=>對`、`!複合詞` 排除語法、行尾註解與逐筆證據註解）＋ `backend/core/glossary.py`
   的 `apply_known_corrections()`（長形優先；單字配對須同時登錄排除詞才放行）。套用三層：
   逐字稿清理層 `text_postprocess.py::apply_official_term_fixes`、校正層
   `correction.py::correct_transcript`（逐段先確定性修、再交模型）、紀錄層
   `text_postprocess.py::apply_record_term_fixes`（僅 `mode=="local"`）。
   **無 ground truth 的錯形一律不登錄**（寧可留錯字，也不把不確定寫成規則）。
2. **P5-A.1 詞表 11→43 組並延伸到紀錄層**（`5247436`）；`CorrectionReport` 新增
   `deterministic_changes`／`known_fixes_applied`（不污染既有「採納 N 處」計數）。
3. **P5-A.2 校正層觸發判定改看「確定性修正後」文字**（`ce99502`）：已登錄錯形既已修掉，
   就不該再為它們付一次 LLM。實測同一份 0903 逐字稿 45 段觸發 **35→12 段**，
   校正階段由 14.5 分鐘級回到 **103 s**。
4. **同音閘門保護詞護欄**：`correction.py::_would_destroy_protected_term` 以同一份詞表推導保護詞，
   ±24 字視窗內不得把正確詞改成錯的。
5. **詞表讀取改 `utf-8-sig`＋壞檔 fail-soft**（`58e65de`）：Windows 記事本存檔加的 BOM
   原本會讓**第一行配對靜默失效**；誤存 Big5／ANSI 原本會讓 `UnicodeDecodeError` 往上拋
   （改為跳過該檔並告警）。附 2 項回歸測試（BOM／CRLF／壞檔）。

### 📊 實測（同一支音檔 `0903-科務會議.m4a`、同一份 ASR 快取、同一模板 `section_meeting`）

「亂碼」＝19 型已登錄 ASR 錯形清單的命中數（可重跑，腳本見 `e2e/attempt-E5-qwen27b-p5/README.md`）。

| 場次 | 模型 | 逐字稿亂碼 | 紀錄亂碼 | 紀錄字元 | 亂碼／千字 | `coverage_all` | `coverage_core` | 任務耗時 | runner verdict |
| --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | --- |
| E4（P5 前） | qwen3.8-27b | 46 型／109 次 | 7 型／10 次 | 2,717 | 3.68 | 0.7015 | 0.8214 | 985.2 s | — |
| **E5 #1（P5 後）** | qwen3.8-27b | **13 型／15 次** | 4 型／5 次 | 3,132 | **1.60** | 0.6866 | 0.7857 | 1,273.7 s | （runner 被執行環境回收，見下） |
| **E5 #2（P5 後）** | qwen3.8-27b | **13 型／15 次** | 7 型／11 次 | 5,423 | 2.03 | **0.8507** | **0.9643** | 1,662.1 s | **PASS（16/16）** |
| **E5（P5 後）** | **gemma-4-31B-it-MLX-4bit** | **12 型／14 次** | **1 型／1 次** | 2,375 | **0.42** | 0.5522 | 0.7143 | 2,127.6 s | **PASS（16/16）** |
| C5（對照） | 雲端 gemini-3.5-flash-lite | 1 型／1 次 | 2 型／2 次 | 2,593 | 0.77 | 0.8060 | 0.8929 | — | — |

- **逐字稿亂碼 109 → 15 次（-86.2%）**，且 qwen 兩場完全相同（13 型／15 次）→ 確定性層是
  **可重現**且**模型無關**的（gemma 亦為 12 型／14 次）。
- qwen E5 #2 的 `coverage_core` 0.9643 **高於雲端 0.8929**；但同一顆模型 #1 場只有 0.7857 →
  **單場抽樣變異（16.4 個百分點）大於「地端 vs 雲端」的差距**，兩場都必須一起看。
- gemma 的紀錄亂碼率（0.42／千字）**低於雲端（0.77／千字）**，但覆蓋率較低 →
  「字面精準」與「內容完整」是兩個獨立的軸。
- **未達項（如實登錄）**：使用者自訂門檻「紀錄亂碼 ≤3 處」在 qwen 兩場（5、11）**未達**；
  gemma 達標（1 處）。`Windows 11 ＋ Ollama` 實機仍未驗 `[UNVERIFIED]`。

### 🧪 獨立稽核與驗收（皆為可重跑證據）

- `e2e/attempt-E5-qwen27b-p5b/`、`e2e/attempt-E5-gemma31b-p5b/`：runner 完整產物（`verdict=PASS`、
  16/16 checks、`coverage_observation.json`、`record_quality.json`、`sha256_manifest.json`）。
- `e2e/model-agnostic-audit-01/report.md`：模型無關性稽核 → **六個品質層全部 `MODEL_AGNOSTIC`**。
- `e2e/crossos-p5-audit-01/report.md`：Windows 11 可攜性稽核 → `WINDOWS_SAFE_WITH_NOTES`（本版已修掉其中兩條）。
- `e2e/gemma-e5-preflight-01/report.md`：gemma 模型 id 對應（`gemma-4-31B-it-MLX-4bit` 目錄名 ↔
  API `gemma-4-31b-it-mlx`）與 48 GiB 記憶體可行性。
- `e2e/glossary-replay-verify-01/report.md`：離線重播獨立複核（43 組 115 次替換、43/43 全命中可重現）。
- `e2e/residual-gap-01/report.md`：優化建議落實盤點與殘餘風險誠實清單。

### 🔍 更正

`5247436` 訊息中的「亂碼命中 60 處 → 11 處」**不可重現**（獨立複核：同一份校正前逐字稿在 20 型
清單下 PRE=**24** → POST=**11**；六種可查核定義為 24／22／57／116／126／128）。「→11 處」
「115 次替換」「43 組配對全數命中」成立；排除複合詞實為 47 條（非 45）。自本版起一律採用可重跑基準。

### 📚 文件

- `doc/操作手冊/地端模型品質優化與驗證手冊_v4.10.md`：新增 §2.5（P5-A 資料檔語法與護欄）、
  §6.5（兩模型實測對照）、§5.4-4（Windows 詞表編碼）、§8-10～16（殘餘風險）與附錄更新。

## [v4.10.0] - 2026-09-23

### 🎯 主題：地端會議紀錄「事實留存」的模型無關四槓桿＋跨 OS 修補（P4 波）

使用者需求：Mac ＋ LM Studio 的地端模型（本輪聚焦 dense `Qwen3.8-27B-Splash` 與
`gemma-4-31B-it-MLX-4bit`）生成品質要拉近雲端 Gemini；**品質機制必須與模型無關**，
日後在辦公室 Windows 11 ＋ RTX 4090 ＋ Ollama 也一體適用；並明確要求不測 MoE 35B-A3B。

### 🔧 修正

1. **P4-A 逐條對帳由 1 類擴到 4＋1 類**（`_validate_record_source_coverage`）：
   議題／決議／數字／日期四類期望集合改由萃取筆記＋逐字稿推導，重用既有對稱正規化與
   LCS ≥0.6 比對器；**期望集合為空一律 `log.warning` ＋ `cov_*` 指標**，修掉「零告警靜默 no-op」。
   呼叫點僅地端，雲端提示詞與輸出 byte 級不變。
2. **P4-A 假陽性兩波修補**（`0054db4`、`f374c27`）：修掉引用標頭污染 LCS、議題粗體標題、
   空殼條目、複合決議子句（改子句 AND）、斜線日期正規化（`11/1 ≡ 11月1日`）、議題詞級覆蓋；
   每波皆附離線重播（0 模型成本）＋負向對照（該判缺的仍判缺）。
3. **P4-B 忠實度絆索**（`backend/core/fidelity_checks.py`，純函式、無 I/O、fail-soft）：
   自創專名／無依據歸屬／數字失真三類檢查掛進地端與雲端既有呼叫點，**只回報、不改寫、不刪句**，
   問題丟進既有補強清單；`LOCAL_FIDELITY_TRIPWIRES=false` 一行回退。
4. **P4-C 兩引擎取樣同源**：Ollama `options` 由寫死的 `top_p/top_k/repeat_penalty` 改讀**同一份
   config**（LM Studio 早已如此），並補上補強路徑「無法附逐字稿」WARNING；`context_window_source` 落檔。
5. **P4-D runner 品質閘門＋標註辨別力**：`--quality-mode {off,observe,required}`（**預設 `off`
   ＝ byte 級不變**）＋ `--coverage-checklist`（永遠只做觀測）；正文標註吸附新增規則 6
   （同標籤同時戳去重複化，保留首筆、其餘改到同標籤 ±120 s 內未使用的真實段首）。
6. **跨作業系統修補（Windows BLOCKER）**：runner 移除對 `tzdata` 的 import-time 依賴
   （Windows 無 IANA tz database，原寫法會讓 runner 直接載入失敗），改為 `Asia/Taipei` 常數位移；
   附 2 項回歸測試。

### 📚 新增文件與獨立分析（皆附可重跑證據）

- `doc/操作手冊/地端模型品質優化與驗證手冊_v4.10.md`：四槓桿與開關／回退、macOS＋LM Studio 與
  Windows 11＋Ollama 操作步驟、兩把量尺用法、疑難排解、殘餘風險（引用皆附 `檔案:行號`）。
- `quality-parity-01/report.md`：地端 vs 雲端「量尺以外」落差分析（46 項細節探針、ASR 亂碼殘留、
  出處標註辨別力、取捨策略）＋ 6 條優化建議與各自驗收指標。
- `timing-forensics-02/report.md`：階段耗時拆解與瓶頸歸因（dense 27B prefill ≈98 tok/s × 每次 1.8–2 萬 token）。
- `pre-push-review-01/report.md`：推送前獨立審查（`PUSH_SAFE_WITH_NOTES`；確認未動門檻常數、
  `off` 模式行為、雲端提示詞與 `task_processor.py:259/262`）。
- `verify_independent.md`＋`run_notes_addendum.md`：Stage 05 獨立驗收（E4＝`ACCEPTED_WITH_GAPS`）
  與 `run_notes.md` 兩處更正（階段標籤對調、E3 輪數誤值）＋決議類 no-op 補登錄。

### 📊 實測（同一支 `0903-科務會議.m4a`、`section_meeting`、釘版 `coverage-1.0.0`＋清單 `cf012d1f…`）

| 場次 | 模型 | 補強輪數 | 牆鐘 s | `coverage_all` | `coverage_core` | 字元數 |
|---|---|---|---|---|---|---|
| C5（雲端基線） | `gemini-3.5-flash-lite`＋地端校正 | 1 | 無資料 | **0.8060** | **0.8929** | 2593 |
| **E4（最終驗收，`818b71e`）** | **`Qwen3.8-27B-Splash`（地端）** | **1（停損）** | **992.2** | **0.7015** | **0.8214** | **2717** |
| E3（P4-A 修補後） | `Qwen3.8-27B-Splash`（地端） | 2 | 1396.1 | 0.7761 | 0.8571 | 3396 |
| B2（上一版） | `Qwen3.8-27B-Splash`（地端） | 2 | 1710 | 0.8209 | 0.8929 | 4062 |
| E1／E2 | `gemma-4-31B-it-MLX-4bit`（地端） | 2 | 2278.8／2107.9 | 0.6119 | 0.8214 | 2552／2318 |
| D1（P4 前） | `gemma-4-31B-it-MLX-4bit`（地端） | 0 | 1227.2 | 0.508 | — | — |

- 四場 P4 後地端 E2E（E1／E2／E3／E4）皆 `verdict=PASS`、16/16 checks、`failure_reasons=[]`；DOCX 結構檢查全綠。
- **三項缺陷修補在 E4 in-run 生效**：議題假陽性 1→0、B1 歸屬假陽性 14→0、數字子字串假命中→正確揭露 2 筆真缺口；
  補強由 2 輪降為 1 輪（問題集合逐輪相同 → 停損），牆鐘 **992.2 s＝−28.9% vs E3、−19.1% vs D1**。`[VERIFIED]`
  證據：`e2e/attempt-E4-qwen27b-p4-final/run_notes.md`＋`verify_independent.md`。
- **地端 27B 與雲端的事實留存差：E3 場 3.0 pp（all）／3.6 pp（core）；E4 場 10.4 pp／7.2 pp**
  ——同一模型兩次抽樣擺動達 7.5 pp，**不可宣稱已達雲端水準**，聚合宣稱需更多取樣。`[VERIFIED 量尺重跑一致]`
- 跨模型／跨 OS 可移植性獨立稽核：四槓桿**零模型名稱分支**、LM Studio 與 Ollama **共用同一條 pipeline**、
  Windows 靜態相容 PASS（`e2e/portability-audit-02/report.md`）。

### ⚠️ 未達項與新發現（如實登錄，未放寬任何門檻）

1. **補強輪數在 27B 已降為 1（E4，停損收斂）**；gemma 的 E1／E2 仍為 2 輪。時間成本 E4 −28.9% vs E3、
   −19.1% vs D1（達標）、gemma +71.8%／+85.7%（未達）。
2. **§9.4「牆鐘 ≤+25%」在 gemma 上自相矛盾**：單輪生成 ≈485 s 已 = +39.5% → 任何 gemma 場必然未達，
   已升級為 planner 決策（`.agent/tasks/T20260922-2037-02-local-model-quality-parity/escalation.md`）。
3. **Qwen 場 `cov_expected_decision=0`**（決議期望集合為空、連 3 次 WARNING）：決議類補強在該場為 no-op，
   最終 decision 9/9 是模型本身寫到，功勞不得歸 P4-A。
4. **P4-B 忠實度觀測值已投影**（`record_quality.json.unsupported_entities_count`：E2＝2／E3＝4／E4＝3），
   本項解除。新登錄：絆索 A 對 ASR 變體（逐字稿「煙酒文神穀股」→紀錄「煙酒文宣股」）會產生軟性噪音，
   且同一數字缺口會被「覆蓋率對帳」與「絆索 C」各報一次 → 問題數灌水。
5. **E4 `coverage_all` 0.7015 低於 E3 0.7761、亦低於雲端 0.8060**；`coverage_core` 0.8214 亦低於雲端 0.8929。
   真缺口仍在（15%／600／100 元／下週一內稽／社交工程郵件／搬遷細節），**模型補寫能力才是目前上限**：
   E4 的補強輪輸出與首版逐字相同（2706 字元／2051 tokens）＝對 27B 而言是 no-op。
6. **Windows／Ollama 實機未驗**：`[UNVERIFIED]`（靜態與 payload 級已驗；需 4090 實機量測）。

### 📌 下一步建議

1. ~~修掉括號詞組假陽性~~／~~B1 邊界假陽性~~／~~數字子字串假命中~~ 已完成（`849e934`／`eb9dfeb`／`818b71e`），
   E4 已驗；接續處理**真缺口補寫**：27B 對「15%／600」的補強輪為逐字 no-op → 需分段提示或更強模型。
2. 去重複揭露（同一缺口被覆蓋率與絆索 C 各報一次）、絆索 A 對 ASR 變體的軟性噪音。
3. 27B 目前 n=2 且擺動 7.5 pp：聚合宣稱需多次重跑取中位數。
4. planner 裁決 §9.4 門檻語意與 preflight 證據完整性（空目錄／`attempt.json`）。
5. 在 Windows 11 ＋ RTX 4090 ＋ Ollama 以同一支音檔跑一次實機驗收（同尺量測）。

## [v4.9.0] - 2026-09-22

### 🎯 主題：地端紀錄「可查核性」的模型無關修復——出處標註時間戳確定性吸附、量測儀器強化與量尺更正

使用者新需求：品質優化機制**必須與模型無關**，日後在辦公室 Windows 11 ＋ RTX 4090 ＋ Ollama 跑
Gemma 4 31B 也要一體適用，不得只為 LM Studio 的 Qwen 客製；且本輪只測 dense 27B
（`qwen3.8-27b-splash`）。實作因此全部落在 L1–L3（逐字稿 ground truth／確定性後處理／確定性閘門），
不新增任何模型名稱、家族或引擎參數分支。

### 🔧 修正

1. **出處標註吸附（`snap_source_tags_to_transcript`，`backend/core/text_postprocess.py`）**：
   以逐字稿段落時間表為 ground truth，把模型寫的時間戳吸附到真實段落起點，4 條優先序規則、
   fail-soft（不可回溯者原樣保留、絕不刪除或改寫發言者歸屬）、位移上限
   `TAG_SNAP_MAX_SHIFT_SECONDS=120`（避免把「大概第 4 分半」硬拉成 `00:00:00`）。
   掛在 `_finalize_record_text(mode="local")` 之鏈中，最終生成與**每一輪補強寫回**都走同一條。
2. **修復位置即模型無關證據**：`_summarize_with_local_pipeline` 以 `_generate_with_local_engine`
   分派 `ollama`／`lmstudio`，兩者共用同一條後處理；遠端 Ollama（`OLLAMA_BASE_URL` 指向 Windows
   主機）自動受益，不需為新引擎另寫一份。**唯一硬前提是逐字稿段落列格式**，格式不同時吸附全部
   no-op（fail-soft）並由量測指標示警。
3. **量測儀器強化（`measure_tag_traceability`／`scripts/e2e/measure_record_quality.py`）**：
   新增 `zero_time_tag_count`／`zero_time_tag_ratio`（`00:00:00` 標註；結構上必然命中段落起點、
   會膨脹主指標，故單獨列出）、`distinct_tag_time_count`／`distinct_tag_time_ratio`（標註辨別力）、
   `on_start_tag_ratio_excluding_zero`（排除 `00:00:00` 後的分母）。
4. **量尺更正（誠實登記）**：本專案先前把 dense 27B 的 `46/61（75.4%）` 與 MoE 的 `4/27（14.8%）`
   標為 `on_start_tag_ratio`，實際那是 **`exact_tag_ratio`**（要求發言者標籤一致）。以新儀器重測後，
   真正的 `on_start` 為 **27B 58/61 = 95.1%、MoE 10/27 = 37.0%**。研究文件 §10.3／§10.7 已更正並
   註明更正理由。

### 📊 實測（真實音檔 `0903-科務會議.m4a`、`section_meeting`、`local`、dense 27B）

| 指標 | A1（修復前） | **B2（修復後，本輪主角）** |
|---|---|---|
| runner verdict | PASS | **PASS**（16 checks、exit 0） |
| 全流程耗時 | 910 s | 1,710 s（多跑 2 輪補強，見下） |
| `on_start_tag_ratio` | 0.951（58/61） | **1.000（52/52）** |
| `on_start_tag_ratio_excluding_zero` | 0.944（51/54） | **1.000（45/45）** |
| `traceable_tag_ratio` | 1.000 | 1.000 |
| 表格出處標註 | 0 | 0 |
| 正文出處標註 | 61 | 52（≥ 退化防線 17） |
| 指示章節條目 | 21 | 25 |
| `distinct_tag_time_ratio` | 0.475（29 種） | 0.288（15 種）→ **新缺口 P1-16** |
| `unsupported_entities` | 3 | 3（P1-1／P1-6 待做） |

- 吸附日誌（最終輸出）：`出處標註吸附 40 處（段落內 1／跨發言者 39／不可回溯 0）`；
  第一輪輸出為 45 處（段落內 1／跨發言者 44／不可回溯 0）。`[VERIFIED]`
- **耗時構成**：ASR＋diarization 299 s（45 分鐘音檔、RTF 0.057）、抽取 80 s，其餘為 4 次大生成
  （整併 360 s／最終 334 s／補強 359 s／補強 351 s），解碼實測 **8.7–11.5 tokens/s**。
  A1 只跑 2 次大生成故 910 s；B2 因品質閘門抓到「待辦事項遺漏 11 項」多跑 2 輪補強。
  → 慢的原因是「dense 27B 的解碼速度 × 呼叫次數」，不是 M4 Pro 不夠力（ASR 只花 5 分鐘）。`[VERIFIED 日誌]`
- 全套測試 `886 passed / 2 skipped`（前波 885）；`bash scripts/check_docs.sh` 0 errors / 0 warnings。
- 雲端路徑不變：本次修正全在地端鏈（`mode="local"`），雲端提示詞與輸出 byte 級不變（既有測試釘住）。

### ⚠️ 新發現（已列入研究文件 §10.6／§10.7）

1. **標註辨別力不足**（新 P1-16）：52 個標註只用了 15 個不同時間戳，同一時間戳平均重複 3.5 次，
   其中 7 筆為會議起點 `00:00:00` → 「標註存在且可回溯」達標，但「指到哪一句」的資訊量仍低。
2. **覆蓋率未重測**：B2 沒有重跑事實探針，覆蓋率 `[UNVERIFIED]`，不得由可查核性推論。
3. **`unsupported_entities` 仍 3 筆**（徵收股／煙酒文神股／稽查股），與 A1 同級。

## [v4.8.1] - 2026-09-22

### 🎯 主題：地端紀錄契約收斂——彙整表出處標註確定性歸零、可確證 ASR 誤辨修正、general 跨節去重、驗收器模板感知

v4.8.0 之後，地端（LM Studio）紀錄仍有「模板契約不一致」與「忠實度」赤字：模型把發言來源標註
寫進四欄的「決議事項辦理情形彙整表」（實測 13/13 列都帶標註），違反 `section_meeting` 的
`forbidden_patterns`，且會原樣流入「列管資料」附件（附件是確定性抽取、不清洗）；提示詞兩輪補強
燒完仍留著。另有多個可確證的 ASR 同音誤辨（征收股／增收股／瑞裏）原樣落地。

### 🔧 修正（全部為地端專屬；雲端提示詞與輸出 byte 級不變）

1. **彙整表出處標註清除（W2b）**：新增 `strip_source_tags_from_table_rows`，只在模板契約明文
   禁止彙整表標註時啟用（`section_meeting`），且只動 `^\s*\|` 的表格列；正文（含正文句末標註）
   與其他模板一個字都不改。基線實測 13 → 0、正文 33 個標註逐字不動、列管附件同步不再帶標註。
2. **紀錄級 ASR 詞彙修正（W3）**：新增 `SECTION_MEETING_RECORD_TERM_FIXES`（4 條可逐條測試，
   `人事總數` 加語境錨定避免誤傷「人事總數為 45 人」）＋ `apply_record_term_fixes`；與雲端共用的
   `SECTION_MEETING_GLOSSARY_CORRECTIONS` 嚴格分離。
3. **general 跨節重複抑制（W5）**：新增 `dedupe_cross_section_items`（僅 `general`；只在「決議」與
   「主席裁示事項」之間，切除尾端（主辦單位…）metadata 後完全相等才判重，保留 donor）。
   fixture 期望值寫死：A 紀錄移除 10 條、B 紀錄移除 0 條、冪等。
4. **地端專屬提示詞導引（W2）**：`_build_record_generation_message`／`_build_record_refinement_message`
   新增 `mode`，僅地端追加 ≤2 行「來源標註只能寫在正文句末、不得寫進彙整表」規則。
5. **驗收器與儀器（W6／W8）**：runner 的 DOCX 正式性檢查改為模板感知（修掉「`--template section_meeting`
   必然 FAIL」的誤判）；新增 `scripts/e2e/measure_record_quality.py`（與產品共用同一份白名單與樣式）。

### 📊 實測（真實音檔 `0903-科務會議.m4a`、`section_meeting`、MoE 35B-A3B、E2E attempt-04）

- runner `verdict=PASS`（16 checks、exit 0）、**439.5 s**；雲端不變性：5 紀錄 × 4 模板 ＋ 72 提示詞案例 byte 相同。
- 彙整表出處標註 **13 → 0**、正文 **33 → 27**（未觸退化防線 17）、`tagged_item_ratio` 0.9706 → 1.0000、
  「（待確認）」13（與雲端 14 同級）、字元 3,238 → 3,368。
- 全套測試 `881 passed / 2 skipped`；`bash scripts/check_docs.sh` 0 errors / 0 warnings。

### ⚠️ 新發現（已列入研究文件 §8.6／§9 與 P1-12～P1-15）

1. **出處標註的可查核性退步**：27 個標註只有 10 個（37%）時間戳存在於逐字稿（基線 89%）；
   多個「時間戳」其實是逐字稿開頭發言者統計的累計時長 → 格式達標 ≠ 可查核。
2. **ASR 噪聲被實體化成具名人物**：逐字稿亂碼「李飛」被寫成「政風室李飛」並賦予 3 處發言歸屬
   （該段實為科長轉述局長廉政講習內容）→ 字面存在性不足以判定「有據」。
3. **科長指示章節空洞化**：條目數 9 → 2，且與彙整表列幾乎逐字重複。
4. 覆蓋率缺口仍在（餐費照時報銷、分地辦公／預佈缺、各股報 3 個名額、瑞里特殊個案）；
   彙整表 21 列 `解除列管`／`繼續列管` 全空、`辦理情形` 多為泛稱。
5. runner 的 required checks **不含** CORE-1／CORE-2 指標（量測儀器為獨立工具、永不 non-zero）→ 需 P1-12。

## [v4.8.0] - 2026-09-22

### 🎯 主題：地端（LM Studio）會議紀錄品質對齊雲端——移除與 context 脫鉤的固定天花板、最終生成改雙輸入、地端一體適用雲端紀錄契約

使用者判定地端深度會議紀錄品質「與雲端 Gemini 差距很大」。以同一支 `0903-科務會議.m4a`、
同一份 ASR 逐字稿、同一 `section_meeting` 模板，比對雲端 Gemini、地端 dense 27B
（`qwen3.8-27b-splash`）與地端 MoE 35B-A3B（`qwen3.6-35b-a3b-splash`）三份輸出後確認：
**差距的主因是管線，不是模型**——雲端與地端餵進最終生成的輸入不對稱，且地端每個階段都
撞到與 context 無關的固定上限。

### 🔍 根因（實測）

1. **最終生成輸入不對稱**：雲端餵「萃取筆記＋完整逐字稿」雙輸入
   （`_build_cloud_summary_message`），地端只餵整併後筆記（`_build_summary_from_notes_message`）；
   補強輪（refinement）同樣只餵筆記。第一階段沒進筆記的立場、理由、數據，後面永遠救不回來。
2. **與 context 無關的固定上限**：`chunk_input_budget` 被夾在 `3200`
   （`_build_local_context_plan`）、三階段輸出共用固定 `LOCAL_LLM_RESERVED_OUTPUT_TOKENS=3072`
   （`config.py`）、整併可見目標另夾 4096。已載入 instance 提供 128K context 時，實際只用到
   約 **2.6%**；11,712 est tokens 的逐字稿被切成 4 塊。
3. **有損整併且損失被靜默接受**：4 份萃取筆記合計 8,176 tokens 送進整併，輸出上限 3,072 且
   `finish_reason=length`（被截斷），最壞損失 62.4%，流程卻視為「已收斂」繼續，最終紀錄只
   承載逐字稿的 15.7%。
4. **雲端專屬機制地端缺席**：發言來源標註規則、會議年份依據規則與其對應驗證器、動態長度
   閘門（雲端 `_estimate_cloud_min_summary_chars` vs 地端固定 250 字）、範本骨架佔位符修復
   ——這四項過去只在雲端路徑生效。
5. **取樣參數不完整**：LM Studio 路徑只送 `temperature` 與 `max_tokens`，未送 `top_p`／
   `top_k`；校正階段 `temperature=0.0` 等同 greedy。Qwen3.6／3.8 官方 model card 對非思考
   模式的建議是 `temperature=0.7`、`top_p=0.80`、`top_k=20`，並明文警告勿用 greedy。

### 🔧 修正

- **輸出上限改由 context 推導**（`_resolve_local_output_tokens`，`summarization.py:557-588`）：
  下限維持 3072（絕不比舊行為更嚴格）、上限 `LOCAL_LLM_OUTPUT_TOKENS_CEILING=8192`、另留
  `LOCAL_LLM_CONTEXT_SAFETY_MARGIN_TOKENS=256`；萃取／最終生成／補強三階段皆適用
  （呼叫點 `summarization.py:2040`／`2076`／`2112`）。
- **分塊上限改由 context 推導**（`summarization.py:497-505`）：
  `LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING=0`（0＝推導，移除固定 3200；小 context 的推導值與
  舊值幾乎相同，行為不變）。
- **能不整併就不要整併**（`_consolidate_notes`，`summarization.py:1546-1604`）：筆記總量已被
  下游承接時改**零損串接**（比照雲端分段模式），只有真的超出下游預算才走 LLM 整併
  （`_merge_notes_until_fit`，`summarization.py:1408`）。
- **最終生成與補強改雙輸入**（`_build_record_generation_message`、
  `_resolve_final_generation_message`，`summarization.py:1268`／`1626`）：餵「筆記＋逐字稿」，
  並以 `_final_message_fits`（`summarization.py:1606`）判斷 context 餘裕，不足時自動退回只餵
  筆記（Ollama `num_ctx=8192` 行為不變）；補強輪同理（
  `_resolve_final_refinement_message`，`summarization.py:1649`）。開關
  `LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION`（預設 True）。
- **地端一體適用雲端紀錄契約**：地端驗證加入動態長度閘門、發言來源標註、年份依據
  （`RECORD_SPEAKER_TRACEABILITY_RULE`／`RECORD_DATE_GROUNDING_RULE`，
  `summarization.py:153-154`）；遺漏待辦問題字串改列出**具體項目**
  （`ACTION_ISSUE_PREVIEW_LIMIT=12`，`summarization.py:127`）；`_finalize_record_text`
  （`summarization.py:2157`）納入範本骨架佔位符修復，與雲端共用同一後處理。
- **LM Studio 取樣參數**（`_lmstudio_extra_body`／`_downgrade_extra_body`，
  `summarization.py:2876`／`2865`）：送官方建議 `top_p=0.8`／`top_k=20` 與階段溫度；本機
  Splash 引擎對 `min_p`／`presence_penalty` 非 0 值回 HTTP 400，故不送，端點拒絕取樣參數時
  逐級降級重送。
- **設定**：`backend/core/config.py:210-268` 新增 11 個 `LOCAL_LLM_*` 旋鈕（分塊／輸出上限、
  安全邊界、雙輸入、零損串接、`top_p`／`top_k`、五個階段溫度），皆可用環境變數覆蓋；關掉即
  回到舊行為。
- **校正階段溫度**：`backend/services/task_processor.py:268` 由硬寫 0.0 改讀
  `LOCAL_LLM_CORRECTION_TEMPERATURE`（0.3；避免 Splash 引擎走官方警告的 greedy 解碼）。

### ✅ 驗證

- **診斷基準（修正前，獨立 90 事實比對，同一逐字稿）**：雲端 Gemini 覆蓋 61.7%／出處標註
  25 處／同音錯字修正 84.6%；地端 dense 27B 覆蓋 53.9%／0 處／53.8%／1,029.9 秒；地端 MoE
  35B-A3B 覆蓋 75.6%（高於雲端）／0 處／15.4%／303.9 秒，另有 1 條捏造與 1 條自相矛盾。
  → 覆蓋率不是地端最弱的一環；**出處標註、同音校正、捏造抑制**才是。
- **測試**：`tests/test_t20260922_record_quality.py`（新增 12 項 fail-first 契約）、
  `tests/test_t20260922_regression.py`（擴充為 9 項：另含 LM Studio 取樣參數與逐級降級）、
  `tests/test_summarization_service.py`（3 項改鎖共用契約）。快速回歸（排除真音檔 E2E 1 項）
  於本次文件同步實測為 **818 passed／2 skipped／0 failed**（`uv run --no-sync pytest tests/ -q
  --ignore=tests/test_end_to_end.py -p no:randomly`；v4.8.0 實作期間回報為 806 passed／2 skipped）。
- **驗收條件（E2E，同一支 `0903-科務會議.m4a`＋`section_meeting`）**：地端深度紀錄需產生
  非 fallback 的正式 DOCX，並通過 `scripts/e2e/check_record_output.py` 的 `VERDICT:
  ACCEPTED`；再與雲端基準逐項比對覆蓋率、出處標註與同音錯字修正。

### 📌 下一步建議

1. **同音錯字修正是下一個最大缺口**（地端 15.4% vs 雲端 84.6%）：`task_processor.py:259-268`
   仍把校正階段硬寫成 `generate_local`，是否改走所選模式（含 LM Studio）屬語意契約變更，需
   獨立規劃與審查，不在本版範圍。
2. **Gemma 4 31B 從未在 Mac 實測**：v4.7.1 的驗證環境是 Windows／RTX 4090；「Gemma 比 Qwen
   準」目前沒有 Mac 上的 A/B 證據，建議用同一支音檔、同一逐字稿做一次控制變因比較。
3. **把品質指標制度化**：覆蓋率、出處標註數、同音修正率、捏造數建議納入每次模型／提示詞
   變更的固定驗收表，避免再次只用「看起來如何」判斷品質。

## [v4.7.4] - 2026-09-22

### 🎯 主題：LM Studio 深度會議紀錄不再失敗——整併目標改由 context 推導、LM Studio 關閉思考、規劃視窗以已載入模型為權威

使用者以 LM Studio 目前載入的模型跑 `0903-科務會議.m4a` 深度會議紀錄，任務「完成」但
`summary_failed=true`：下載檔為 `20260922134904_逐字稿(會議紀錄生成失敗).docx`（只有失敗
橫幅＋逐字稿，0 張表格、無任何會議紀錄章節）。三個根因（皆有實測 log 佐證）：

1. **RC-1b 固定 900-token 可見目標是與 context 無關的硬性 gate**：失敗原因字串即
   `LOCAL_LLM_MERGE_NOT_CONVERGED：萃取筆記整併在 3 輪內未收斂到可見目標（目前 1 份筆記、
   1754 tokens > 目標 900 tokens）`。900 是在 `num_ctx=8192` 假設下校準的常數；整併一旦
   收斂到單一 note 就再無分組可壓縮（merge prompt 要求保留全部事實，模型不保證縮小），
   必然在輪數上限拋錯 → **整份會議紀錄被 veto 成逐字稿 fallback**。
2. **RC-2 `LOCAL_LLM_DISABLE_THINKING` 只實作在 Ollama 路徑**：LM Studio 每次呼叫都先產生
   reasoning tokens（實測 233～4852），11 次呼叫中有 1 次 `finish_reason=length` 且
   `content=0` 字元 → `LMSTUDIO_NO_FINAL_CONTENT` → 語意校正熔斷（45 段中 0 段有修正）；
   整個 LLM 階段佔全任務 87.5%（1246s／1422.8s）。
3. **RC-3 規劃視窗被 settings 預設夾住**：`min(settings, instance ctx)` 使 `context_window=8192`
   成為瓶頸，但 LM Studio 實際載入的 instance 提供 32000（失敗當下）／128000（現況）。

### 🔧 修正

- **整併可見目標改由最終生成階段的輸入預算推導**（`_resolve_merge_targets`）：
  `merge_feasible_input = max(900, ctx − 2×輸出保留 − 最終提示詞開銷)` 為**硬性**下游可承接
  上限；`merge_visible_target = min(上式, 4096)` 為軟性壓縮目標（`LOCAL_LLM_MERGE_VISIBLE_TARGET_CEILING_TOKENS`）。
  `ctx=8192` 時推導結果為 900／900，與舊行為一致（絕不更嚴格）；大 context 時可見目標停
  在 4096 以維持最終生成聚焦。
- **單一 note 進入下游可承接預算即視為已收斂**（`_merge_notes_until_fit`）：僅記 WARNING、
  不再 veto 整份紀錄；真正超出硬性上限時仍 fail loudly 拋 `LOCAL_LLM_MERGE_NOT_CONVERGED`。
  **CORE merge path 仍永不硬截斷**（既有不變量保留）。
- **LM Studio 關閉思考**（`_lmstudio_chat_request`）：以 OpenAI 相容的 `reasoning_effort="none"`
  送出（`openai==1.12.0` 無具名參數，經 `extra_body` 傳遞）；端點不支援該欄位（HTTP 400）時
  降級為不帶欄位重送一次，與 Ollama 的 `think` 相容降級同語意。實測 A／B：關閉 → 1.8s、
  `reasoning_chars=0`、`completion_tokens=18`；開啟 → 6.2s、`reasoning_chars=234`、
  `completion_tokens=181`。
- **規劃 `ctx` 改以選定 loaded instance 的 `context_length` 為權威**：移除 `min()`，並在
  「本地摘要上下文規劃」log 標示來源（`lmstudio_instance`／`settings`）。

### ✨ 新增

- `tests/test_t20260922_regression.py`（7 項）：釘住三條修復契約（可見目標推導、單一 note
  收斂與 fail-loud 邊界、`reasoning_effort` 與 400 降級、規劃視窗權威來源）。修復前 6/7 以
  正確原因失敗（fail-first）。
- `scripts/e2e/rerun_local_summarize.py`：只重跑地端摘要階段（跳過 ASR／語意校正），以既有
  逐字稿快速驗證摘要修正。
- `scripts/e2e/check_record_output.py`：會議紀錄 artifact（MD／DOCX）確定性驗收檢查器——
  非 fallback、正式標題、模板必備樣式、決議與待辦、長度、佔位符、DOCX 結構、中文占比。

## [v4.7.3] - 2026-09-14

### 🎯 主題：雲端預設改回 Gemini、雲端萃取改單次呼叫、保留發言來源標註與會議日期防杜撰

雲端模式預設 provider 改回 **Gemini**（`gemini-3.5-flash-lite`、金鑰 `GEMINI_API_KEY`）：
Ollama Cloud 只是一個測試任務的臨時設定，使用者日常使用 Gemini；Ollama Cloud
（`deepseek-v4.1-flash`）保留為可選 provider（`CLOUD_LLM_PROVIDER=ollama_cloud` 啟用）。
雲端萃取同步改為「一次把整份逐字稿交給模型」（新增 `CLOUD_LLM_SEGMENTED_EXTRACTION`
回退開關；地端流程完全不變），並補上兩個紀錄品質防線：正文保留發言來源標註（雲端＋
科務會議模板）、會議日期不得杜撰（僅雲端）。警告清零與檔名規範一併收斂。

### ✨ 新增

- **雲端 provider 預設改回 Gemini**：`CLOUD_LLM_PROVIDER` 預設 `gemini`
  （`gemini-3.5-flash-lite`、金鑰 `GEMINI_API_KEY`）；Ollama Cloud 保留為可選 provider
  （`CLOUD_LLM_PROVIDER=ollama_cloud` 啟用、模型 `deepseek-v4.1-flash`）。背景：Ollama
  Cloud 只是一個測試任務的臨時設定，使用者日常使用 Gemini。
- **雲端萃取改為單次呼叫**：新增 `CLOUD_LLM_SEGMENTED_EXTRACTION`（預設 `False`）——
  雲端模式一次把整份逐字稿交給模型萃取重點；`True` 可回退 v4.3.3 的分段併發萃取
  （`CLOUD_LLM_CHUNK_TOKENS`／`CLOUD_LLM_MAX_CONCURRENT_REQUESTS` 僅在分段模式生效）。
  **地端流程完全不變**。理由：分段的原始動機是地端記憶體不足＋小模型注意力集中度低，
  雲端不存在這兩個限制。
- **會議紀錄保留發言來源標註（雲端＋科務會議模板）**：正文各項指示／裁示／交辦／他人
  意見句末加註「（發言者N，00:12:04）」，能判定身分時寫「（科長，00:12:04）」；新增
  確定性絆索——正文完全沒有來源標註就自動觸發一次補強；彙整表內不得出現來源標註
  （避免原樣流入列管資料附件）。開關：`MeetingTemplate.speaker_traceability`
  （科務會議 True；一般會議／採購評選 False）。根因：生成提示詞原本只要求「發言者N
  不得當人名」，從未要求保留歸屬，模型因此整段省略（實測 0 處）。
- **會議日期不得杜撰（新增防線）**：紀錄中的年份（如「113年」）必須在逐字稿出現過；
  逐字稿只用「今年／明年／去年」時，年份一律寫「（待確認）」，不得自行推算。做法＝
  提示詞規則（`CLOUD_DATE_GROUNDING_RULE`）＋確定性絆索
  （`_validate_cloud_date_grounding`，逐字稿沒有、紀錄卻出現的年份 → 觸發既有補強輪，
  fail-soft 不讓任務失敗）。只檢查年份（月份與日期交由提示詞要求，避免誤判「這個月／
  月底」等相對說法）。僅雲端流程。

### 🔧 修正

- **日期欄位不再吐出「範本骨架佔位符」（僅雲端）**：模型照抄提示詞骨架時，頭欄位會變成
  「時間：中華民國（年）年（月）月（日）日（星期）（時分）」「第（次）次」——看起來有填、
  實際上整欄沒有可用資訊，比官方規定的「（待確認）」更糟。新增確定性後處理
  `normalize_unfilled_placeholders`（`backend/core/text_postprocess.py`）＋雲端收尾包裝
  `_finalize_cloud_record_text`（`backend/services/summarization.py`）：把這些佔位符換回
  「（待確認）」。只處理開頭欄位與標題行、只拿掉沒有資訊的佔位符、不新增任何事實。
  地端仍走 `_finalize_record_text`，行為完全不變。
- **警告清零**：Pydantic `class Config` → `model_config`、`TranscriptionResult` 加
  `protected_namespaces=()`、websocket 測試關閉未 await 的 coroutine；
  `scripts/check_docs.sh` 舊版號掃描排除 `CHANGELOG.md`（歷史帳本記錄舊版號屬正常內容）。

### 📝 文件

- **檔名規範**：`doc/規格與設計/Implement_Plan.md` → `implement_plan.md`、
  `Tasks.md` → `tasks.md`（同步更新引用）。

### ✅ 驗證

- `PYTHONPATH=. DATA_DIR=./data .venv/bin/python -m pytest -q` → **798 passed, 2 skipped**
  （0 warnings）。
- `bash scripts/check_docs.sh` → 0 錯誤 0 警告。
- 雲端 E2E（`0903-科務會議.m4a`、科務會議模板、Gemini，同一支音檔累計三次實跑）：
  - `c7619708`（日期防線加入後）→ completed、73.8 秒；**紀錄中出現的年份全部有逐字稿依據**
    （紀錄年份集合為空）；補強 2 輪皆因「待辦事項遺漏 3 項」而非日期問題。前一版
    （`3f7f43ff`）同一支音檔曾寫出逐字稿沒有的「113年」。
  - `c49ecde9`（補強日期規則句後）→ completed、58.7 秒；年份同樣全部有據；但頭欄位出現
    骨架佔位符（「（年）年（月）月（日）日」），成為上列「範本骨架佔位符」修正的依據。
  - `bed317d6`（骨架佔位符修復後）→ completed、83.8 秒；年份仍全部有據、**頭欄位再無任何
    骨架佔位符**（「時間：中華民國（待確認）年（待確認）月（待確認）日（待確認）」）、
    26 組句末發言來源標註、彙整表 8 列；殘留的補強輪仍為既有「待辦事項遺漏」議題（非日期）。

### 🎯 主題：Apple SpeechAnalyzer 本機 ASR——macOS 26+ / Apple Silicon 唯一引擎（Windows 零影響）

Mac 上傳會議音檔改走 macOS 內建 SpeechAnalyzer 做本機轉錄（Mac 唯一 ASR 引擎：無
Whisper 選項、永不 fallback）：免下載 Hugging Face 模型；本機實測（macOS 26 /
Apple Silicon / 真實 helper）1658.958 秒（約 27.7 分鐘）MP3 的 ASR 轉錄 9.9 秒
（`elapsed_seconds=9.9`、`real_time_factor=0.006`、`helper_invocations=1`）
（`e2e/attempt-03`；未於本 repo 量測與 MLX-Whisper 的倍率）。
Windows / Linux / Docker 行為完全不變，也不會出現任何 Apple 設定、提示或 UI 字樣。
（2026-09-13 完成；版本號於發布時指派，本條目先掛 Unreleased。）

### ✨ 新增

- **Mac 唯一引擎自動解析**：`ASR_BACKEND=auto` 在 macOS 26+ Apple Silicon 解析為
  `apple`（`platform_config`／`asr_model_resolver` 雙點），單一引擎、**永不 fallback**；
  Mac 上顯式 legacy 值（`transformers`／`faster_whisper`／`mlx_whisper`）一律以穩定
  `ValueError` 拒絕。非 Mac 的 `auto` 維持既有解析（永不解析到 `apple`）；明確指定
  `ASR_BACKEND=apple` 於非 Mac 直接拒絕（fail-fast，訊息說明僅 macOS）。
- **顯式 `apple` fail-closed**：指定 `apple` 失敗（helper 缺失／不可執行、逾時、含輸出
  契約驗證失敗）直接回報、不偷換引擎；取消（`APPLE_CANCELLED`，離場碼 7）任何情況都
  不 fallback。
- **Swift helper（不提交 binary）**：`apple_speech_cli/` 為本機建置的 SwiftPM
  executable，對外契約為 stdout 單一 schema 1.0 JSON＋stderr 診斷；建置與實測見
  `doc/apple-speech-cli-build.md`。
- **前端顯示**：`accelerator=apple-neural` 時狀態列顯示「Apple 神經引擎（本機）」；
  Windows 常見 accelerator（cpu/cuda）不出現任何 Apple/Xcode/helper 字樣，既有
  `mlx-metal`／`mps`／`cuda`／`cpu` 顯示維持不變。
- **設定與文件**：新增 `APPLE_SPEECH_CLI_PATH`／`APPLE_LOCALE`（`zh-Hant-TW`）／
  `APPLE_PRESET`（`time-indexed`，可選 `plain`／`plain-alternatives`／`progressive`／
  `time-indexed-progressive`）／`APPLE_ENABLE_PREFLIGHT`；`.env.example`、
  `config.macos.yaml`（標註僅 macOS 生效）與
  [操作手冊](doc/apple-speech-analyzer-operations.md) 同步（錯誤碼 0/1/2/3/4/5/6/7
  對照、`data/logs/app_<日期>.log` 的 `ASR 引擎觀測` 行觀測 `helper_invocations`／
  `conversion_reason`、`/health?quick=true` 語意、常見問題）。
- **環境檢查與安裝守衛**：`scripts/verify_env.py` 僅在 macOS（darwin+arm64）檢查
  ffmpeg/ffprobe、Swift 工具鏈與 `apple_speech_cli/.build/release/apple-speech-cli`；
  缺工具鏈或 helper 只提示建置指令、不視為致命；非 macOS 完全跳過且不輸出 Apple 字樣。
  `install_deps.py --check` 提供同一提示（僅提示、不自動編譯、不下載模型），
  Windows 安裝流程零 Apple。

### ⚖️ 語意變更（Owner 指示，2026-09-13，T20260912-2242-01）

Owner 指示取代先前的 auto fallback 語意：**Mac 版沒有 Whisper 模型選項、也沒有
fallback**，唯一 ASR 引擎是 Apple 內建的 Apple SpeechAnalyzer。

- `ASR_BACKEND=auto`（Mac 預設）→ Apple SpeechAnalyzer：單一引擎、永不 fallback。
- `ASR_BACKEND=apple` → Apple SpeechAnalyzer，fail-closed：helper 缺失／不可執行、
  取消、逾時、輸出無效等任何 Apple 失敗都直接使任務失敗（不再有 `mlx_whisper` 備援）。
- Mac 上顯式 legacy 值（`transformers`／`faster_whisper`／`mlx_whisper`）→ 穩定
  `ValueError`：`ASR_BACKEND=<x> 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）`。
- Mac 不再有 Whisper 依賴、本機 Whisper 模型，也沒有「先 Apple 再 Whisper」路徑。
- **相依移除**：`pyproject.toml` / `requirements.txt` 的 macOS Whisper 平台相依
  （`mlx-whisper==0.4.3 ; Darwin/arm64`）已移除，`uv.lock` 同步收斂
  （一併移除 `mlx`／`mlx-metal`／`llvmlite`／`numba`／`scipy`／`tiktoken`／`more-itertools`
  等僅服務 MLX-Whisper 的傳遞相依）；`tests/test_apple_packaging_guard.py` 的守衛契約同步反轉為
  「本專案不得再有 MLX 相依」。Mac 端 `uv sync` 不會再安裝任何 Whisper runtime。
- Windows / Linux 完全不變：Whisper 引擎與 `auto` 解析行為與先前一致，`apple` 仍被拒絕
  （其相依本來就不含 MLX 平台套件）。

### 🔁 回滾

- Mac：**已無 `ASR_BACKEND=mlx_whisper` 回滾開關**（顯式 legacy 值一律被拒絕）；如需回到
  舊 Whisper 行為須回退版本。移除 `apple_speech_cli/` 只會使 Apple 失敗（fail-closed，
  任務 failed），不會回退其他引擎。Windows / Linux 無需任何動作。

## [v4.7.2] - 2026-08-20

### 🎯 主題：修復地端公文段落編號階層不符標準（雲端無此問題）

使用者回報：地端模式（Ollama gemma4:31b）產出的會議紀錄，段落編號階層不符合標準公文格式
（應為「一、」→「（一）」→「1、」→「（1）」層層遞進），雲端模式（Gemini）沒有這個問題。
以正式機同一逐字稿雲端／地端各跑一次實測比對確認：雲端版「各單位意見」欄位底下的子項目
以「一、二、三、四」中文數字起算，需要更細節時才往下用「（一）（二）」；地端版則整段跳過
中文數字層，直接用「1. 2. 3.…」阿拉伯數字條列，且完全沒有出現任何次層分項。

### 🔍 根因

生成最終會議紀錄的系統提示詞 `MEETING_RECORD_SYSTEM_PROMPT`（`backend/core/prompts.py`）
是**地端與雲端共用同一份**，除了「一、報告事項」「二、討論事項」「三、主席裁示事項」三個
最上層章節標題明文寫死之外，底下子項目（各單位意見、決議、裁示內容）完全沒有規定要用什麼
編號符號、也沒有講清楚每個欄位該不該各自獨立起算。雲端 Gemini 模型能力強，即使提示詞沒明講
也能依公文語境自行推斷出正確慣例；地端 gemma4:31b 推斷不出來，於是整份文件跳過中文數字層、
直接用阿拉伯數字或把多個子重點硬塞成一大段。

### 📚 研究：權威階層規範

查證行政院《文書處理手冊》「製作公文應遵守之全形、半形字形標準」，其分項標號規定：
「一、二、三、……」→「（一）（二）（三）……」→「1、2、3、……」→「（1）（2）（3）……」，
中文與阿拉伯數字後加全形頓號、括號本身以半形書寫；國立中央大學總務處文書組「公文分項標號
書寫原則」（直接引用同一份文書處理手冊）以官方公文管理系統實例進一步確認延伸的第五、六層
「甲、乙、丙……」→「（甲）（乙）（丙）……」共六層完整序列（獨立以 PDF 原文核對過）。
手冊歷經多次修正，未逐一核對每次修正是否異動本條，但此階層序列為長年穩定慣例，多方教材
互相印證一致，可信度高。
另查證「主旨、說明、辦法得靈活運用，可用1段完成者不必勉強湊成2、3段」之通則，對應到分項
標號即為「依內容繁簡選用必要層級，不必湊滿，但須由上而下依序使用、不可跳層」。
（本系統為求與既有大量已核可的模板／測試資料內部一致，括號統一維持既有的全形寫法、阿拉伯
數字層維持既有的「1.」句點寫法，未逐字改為官方半形括號與頓號寫法——此為刻意的相容性取捨，
非研究結論本身。）

### 🔧 修復

- `backend/core/prompts.py`／`config.yaml`：`MEETING_RECORD_SYSTEM_PROMPT` 新增「條列編號
  階層規則」段落，明講完整階層序列與標點慣例、要求各欄位（案由、說明、各單位意見、決議、
  裁示內容）**各自獨立**自「一、」起算、禁止跳過「一、」層級直接用阿拉伯數字或「-」「•」、
  並附具體範例（不與地端／雲端分流，兩者共用同一份提示詞，雲端本已正確不受影響）。
- `backend/core/prompt_templates/section_meeting.py`、`isms_meeting.py`：原本寫死「條列編號
  層次固定為…三層」，改為「三層通常已足夠，若確有需要可依序延伸（1）→甲、→（甲）」，避免
  真的遇到需要第四層以上內容時模型無所適從或亂編符號。
- `backend/core/prompt_templates/procurement.py`：補上「（一）（二）」次層之後的延伸規則
  （「1、2、3」供詢答逐項或簡報子點使用），並在詢答欄位說明與生成增補訊息中同步提醒。
- `backend/services/summarization.py`：`_build_refinement_message`（`_build_cloud_refinement_message`
  共用同一底層訊息）新增一句簡短提醒，避免補強重寫輪次把原本正確的編號階層改壞。
- 萃取／整併提示詞（`LOCAL_EXTRACTION_PROMPT`／`LOCAL_NOTES_MERGE_PROMPT`）**維持不變**：
  中繼筆記是萃取階段的事實骨架，其 Markdown 巢狀結構（議題／討論重點／決議）已足夠讓最終
  生成步驟判斷是否需要往下分層，格式轉換完全是生成階段的責任，逼萃取階段做格式轉換反而可能
  犧牲萃取品質。
- `backend/services/docx_converter.py`：核對後**無需改動**——各模板的 `docx_section_pattern`
  皆為嚴格白名單（僅最上層章節標題才加粗放大），子層級編號（一、（一）、1.）一律落入一般
  段落渲染路徑，不會被誤判為章節標題。
- 未新增格式驗證層檢查：既有「決議：1. …」「各單位意見：- …」等寫法已被既有測試 fixture
  視為「合格摘要」的一部分，若加入強制符號檢查極易誤傷既有正常輸出；判斷精準的提示詞修復
  已是本次主要且風險最低的槓桿，故驗證層維持不動。

### ✅ 驗證

- `tests/test_system_prompt_validation.py` 新增 `TestNumberingHierarchyRule`／
  `TestDomainTemplateHierarchyRule`：以字串斷言驗證共用提示詞與三個領域模板皆已納入完整
  階層序列、禁用符號、各自獨立起算與不可跳層規則；`test_prompt_token_budget_is_local_model_friendly`
  上限由 1200 調整為 1600（新增段落使主提示詞估算 tokens 由 ~1196 升至 ~1431，相對 8192
  context 仍屬小幅佔用）。
- `python -m pytest tests/ -q`：440 passed, 3 skipped，另有 15 個既有環境性失敗（缺
  opencc／faster_whisper，與本次改動無關）。

## [v4.7.1] - 2026-08-20

### 🎯 主題：修復 v4.7.0 迴歸——done_reason=length 被誤判為可重試錯誤，導致整份紀錄失敗

v4.7.0 為串流層新增「done_reason≠stop 併入瞬時重試」的分類，本意是攔截連線中斷等
異常結束，但把 `length`（輸出撞到 `num_predict` 上限、被正常截斷）也一併歸類其中。
`length` 是**確定性結果**——同樣的輸入、同樣的 `num_predict`，重試 2 次必然停在
同一個截斷點，尤其整併呼叫本就刻意把輸出綁在預算內、撞上限是設計內行為。結果是
重試 2 次全部失敗、整份會議紀錄改吐逐字稿 fallback 文件。正式機 docker 預設
`LOCAL_LLM_RESERVED_OUTPUT_TOKENS=2048`，長會議的最終紀錄很容易超過此上限而觸發。

根因由失敗 DOCX 內「失敗原因」行（v4.6.2 診斷鏈的直接產物）定位——v4.6.x
（`stream:false` 時代）從不檢查 `done_reason`，靜默接受截斷內容，交由下游驗證／
補強迴圈把關格式，此行為已經過實證可用；v4.7.1 恢復同樣的「接受＋警告」精神。

### 🐛 修復

- `_stream_ollama_chat_once`：`done_reason=length` 不再拋出 `OllamaStreamRetryable`，
  直接回傳已完整累積的內容；其餘非 `stop`/`length` 的異常結束原因維持可重試。
- `_post_ollama_chat`：成功路徑偵測到 `done_reason=length` 時記錄
  WARNING（含 `eval_count`／`num_predict`），不重試、照常接受內容繼續流程。
- `_log_generation_metrics`：INFO 行新增 `prompt_eval_count`，用以觀測每次呼叫
  實際佔用多少 context，作為後續調校 `num_predict` 擴大幅度的觀測依據。

### 🔧 治本：依 context 餘裕自動擴大 num_predict

- `_summarize_with_ollama` 新增 `expand_output_budget`（預設 `True`）：context
  規劃已保證輸入在預算內，故將 prompt 用不完的 context 全數讓給輸出上限
  （`num_ctx - 已用估算 - 安全邊界`），從源頭降低撞上限機率；估算誤差無害——
  即使仍然撞到上限，也已落入上述「接受＋警告」的安全路徑。
- 整併呼叫（`_merge_notes_until_fit` 內 `_generate_with_local_engine`）明確傳入
  `expand_output_budget=False`：`merge_predict_cap` 是整併收斂機制的核心（每輪
  輸出必須小於預算，才能保證多輪整併最終收斂成一份），自動擴大會破壞此保證。
- 其餘呼叫點（分塊萃取、最終生成、補強、`generate_local`）維持預設值，自動受益。

## [v4.7.0] - 2026-08-19

### 🎯 主題：VRAM offload 徹底根治——串流生成＋ASR 子程序隔離＋自我修復降級（研究驅動）

v4.6.2 讓失敗「可見、可診斷、可重試」；本版根除劣化本身。方案由兩路深度研究驅動：
(1) 參考專案 D:/dev/local（同一顆 gemma4:31b、同級 4090）的量產實證移植；
(2) Ollama/CUDA/Windows 最佳實踐網路研究（含官方 issue 佐證）。

### 🔧 根治手段

- **Ollama 呼叫全面串流化**（`stream:true`）：
  - 原 `stream:false` 讓 600s read timeout 變成「總時長硬上限」（完成前零位元組
    回傳）——合法長會議被誤殺的直接原因（參考專案已文件化同一教訓）
  - 新語意：`LOCAL_LLM_STREAM_IDLE_TIMEOUT`（120s，chunk 間閒置＝真卡死，快速偵測）
    ＋`LOCAL_LLM_REQUEST_TIMEOUT`（放寬至 1800s 總時長上限——寧可等待不截斷）
  - 串流層可重試分類（移植參考專案）：中途 error chunk／結束無 done／
    `done_reason≠stop`（如 length 截斷）→ 併入瞬時重試
  - 每呼叫記錄 `load_duration`（冷啟動 vs 推理分離）與 **tokens/s**；
    低於 `LOCAL_LLM_MIN_TOKENS_PER_SECOND`（5.0）即警告疑似 offload
- **ASR 子程序隔離**（`backend/workers/asr_worker.py`＋`backend/services/asr_subprocess.py`）：
  - 研究確認：長駐程序的 CUDA context／分配器殘留**只有程序退出才保證釋回**
    （faster-whisper#992 實測每次殘留 ~312MB）——蠶食 Ollama 可用 VRAM 是
    offload 的長期累積因子
  - 預設 `ASR_ISOLATION=subprocess`：轉錄在獨立子程序執行，進度以 stdout JSON
    lines 回傳，結束即歸還全部 VRAM；spawn 失敗自動退回 in-process（回退桿）
- **Warmup 2.0——驗證＋自我修復＋降級**（主機不可控時的自動保底）：
  - 載入時帶 `options.num_ctx`（與後續 chat 一致——ctx 不一致會觸發 runner
    整顆重載，參考專案實證教訓）
  - 偵測 offload → 卸載→等待→重載（自我修復一次）→ 仍 offload → **本任務
    降級 `num_ctx=LOCAL_LLM_DEGRADED_CONTEXT_TOKENS`（8192）**並以降級 ctx
    預載；降級值顯式貫穿分塊規劃與所有生成呼叫
  - **KV 量化生效 heuristic**：/api/tags 磁碟大小 vs /api/ps 載入大小之差
    （f16@16K≈3.1GB 特徵 vs q8≈1.5GB）→ 主機 env 未生效直接在 log 點名
- **主機側雙軌**（因應「setx 設了沒生效、疑似被管制」）：
  - `scripts/diagnose_ollama_host.ps1`：registry 實際值／服務型態／server.log
    生效傾印／載入量四路診斷，判讀 setx 失效原因
  - `scripts/start_ollama_optimized.ps1`：**行內程序級環境變數**啟動
    （不經 registry，GPO 管制通常擋不到）＋自動 /api/ps 與吞吐驗證
    （防 Ollama#9683 KV 量化反而變慢的已知案例）
- **設定調整**：keep_alive 10m→30m（對齊參考專案）；windows-gpu compose
  `MAX_CONCURRENT_TASKS` 預設 2→1（單卡序列化原則）；`LOCAL_LLM_MODEL`
  註記 gemma4:26b 一行 fallback（~16GB 全 VRAM、快 5.8 倍、品質略降）

### 🧪 測試與驗證

- 新增 16 項測試：串流解析（happy／error chunk／無 done／length 截斷）、
  重試分類、num_ctx 覆蓋貫穿、warmup 自我修復（成功不降級／失敗降級／
  跨任務殘留重設）、KV heuristic 兩向、ASR worker 與父程序 wrapper 全流程
- 觸及模組 63 項全數通過；全套件 423 passed（僅本機缺 opencc/faster_whisper
  的既有環境性失敗）
- 部署手冊新增 v4.7.0 捷徑（含主機腳本操作與 PASS 判準）

## [v4.6.2] - 2026-08-19

### 🎯 主題：地端排程任務「空白會議紀錄」根因修復——冷啟動逾時＋LLM 管線重試

### 🐛 根因修復（地端模式排程任務必出 fallback「僅逐字稿」文件）

- **問題現象**（2026-08-18 使用者回報）：地端模式從佇列取出的任務，下載到的
  「會議紀錄」實為 fallback 文件——標題「逐字稿（會議紀錄生成失敗）」＋警告
  banner ＋逐字稿，且**沒有「失敗原因」行**，任務又顯示「完成」，極易誤認為
  正常紀錄。
- **根因鏈**（由 fallback 檔案證據＋程式碼追蹤確認）：
  1. 單卡 VRAM 交接設計：每個任務 ASR 前強制卸載 Ollama 模型
     （`task_processor.py`），故 ASR 後第一個 LLM 呼叫必為**冷啟動**——
     重載 ~20GB gemma4:31b（num_ctx=16384 實測 23.0/24GB，貼近上限）。
  2. 貼近上限＋長駐程序的 VRAM 殘留 → Ollama 將部分層 offload 至 CPU，
     推理速度崩跌。
  3. 每次 `/api/chat` 600s 逾時後拋 `httpx.ReadTimeout`——**其 `str()` 為空**，
     `summary_error = str(e)` 得到空字串 → 文件的「失敗原因」行被 `if` 條件
     整個略過，診斷資訊全失。
  4. 本地管線 12+ 次連續呼叫（分塊萃取／合併／最終生成／補強）**全部無重試**
     → 單一逾時毀掉整份紀錄。33K 字長會議＝約 12 個分塊，暴露面極大。
  5. 佐證：fallback 檔逐字稿仍含同音錯字——語意校正層（同走 Ollama、失敗被
     靜默吞掉）也已失敗，早期警訊被隱藏。
  6. 「排程任務才失敗」是假相關：所有任務都走佇列；真正變因是
     「新音檔（需 ASR→冷啟動）＋長會議（多分塊）」。
- **修法**：
  - `backend/core/errors.py`（新增）：`describe_exception()` 保證任何例外至少
    帶出類別名稱；task_processor／summarization 全部改用，關鍵失敗點改
    `log.exception` 記完整 traceback；文件「失敗原因」行改為**無條件輸出**
  - 模型預熱：ASR 後、校正前以 load-only 請求（`/api/generate` 不帶 prompt）
    用專屬逾時先載回模型，冷載入不再吃生成呼叫的逾時額度；並查 `/api/ps`
    記錄 `size` vs `size_vram`——**CPU offload 直接可視化於 log（WARNING）**
  - 瞬時錯誤重試：每次 Ollama 呼叫對 timeout／連線中斷重試
    （`LOCAL_LLM_TRANSIENT_RETRIES`，預設 2，線性退避）；HTTP 4xx/5xx 與
    程式例外不重試。分塊重試後仍失敗維持「整份失敗」——公務紀錄忠實性優先，
    不產部分缺漏紀錄（使用者決策）
  - 新 env（雙 compose 佈線）：`LOCAL_LLM_REQUEST_TIMEOUT`、
    `LOCAL_LLM_WARMUP_TIMEOUT`、`LOCAL_LLM_TRANSIENT_RETRIES`、
    `LOCAL_LLM_RETRY_BACKOFF_SECONDS`、`CLOUD_LLM_REQUEST_TIMEOUT`、
    `CLOUD_LLM_MAX_RETRIES`
- **雲端模式一併補強**（使用者未實測到，但同構風險確認存在）：
  - `_gemini_chat` 增加串流層瞬時重試（SDK max_retries 不涵蓋串流中途斷線），
    原本無保護的最終生成與補強輪自動被覆蓋
  - Gemini client 顯式設定 `timeout`／`max_retries`
- **失敗呈現**（使用者決策：完成＋顯著警告）：
  - `TaskInfo`／`ProgressMessage` 新增 `summary_failed`，隨 WebSocket 推送
  - 前端結果區顯示紅色警告 banner「⚠️ 會議紀錄生成失敗，本次結果僅包含逐字稿」
  - 下載檔名改為 `{時間戳}_逐字稿(會議紀錄生成失敗).docx/.md`，不再偽裝成
    「會議紀錄」
- **同場修復**：
  - 移除從未生效的 `TASK_TIMEOUT_SECONDS`（整任務逾時對長會議不合理，
    逾時控制改在每次請求層級）
  - `check_lmstudio_health` 同步 client 阻塞 event loop → `asyncio.to_thread`

### 🧪 測試與驗證

- `tests/test_errors.py`（新）：空訊息例外還原類別名稱（3 項）
- `tests/test_task_processor.py`：失敗原因保底行、例外類別入文件、
  warmup 時序＋逾時後任務仍完成且 `summary_failed=True`（3 項）
- `tests/test_summarization_service.py`：瞬時重試／放棄／不誤重試、think 400
  降級保留、warmup load-only payload／offload 警告／永不拋出、Gemini 串流
  重試（9 項）
- 本次觸及模組 47 項全數通過；全套件僅本機缺 opencc／faster_whisper 之
  既有環境性失敗，與本次變更無關

## [v4.6.1] - 2026-08-11

### 🎯 主題：DOCX 章節誤判修復——編號條列項目不再整段粗體放大

### 🐛 根因修復（雲端紀錄 DOCX「標題與內文全成粗體」問題）

- **問題現象**（2026-08-11 使用者回報）：雲端模式轉出的會議紀錄 DOCX，
  「各單位意見」「決議」「裁示事項」底下的條列內文全部變成粗體藍色放大字，
  與章節標題無法區分，整份文件看似全粗體。
- **根因**：`docx_section_pattern` 過度寬鬆（`^[一二三四五六七八九十]+、`）。
  公文格式中「章節標題」（一、報告事項）與「條列項目」（決議的一、二、三）
  共用同一種編號，僅靠行首字元無法區分；雲端模型（Gemini）依 v4.3.3 豐富度
  要求慣以「一、二、三、」條列意見與決議，每一條都被誤判為章節，套上
  `_add_record_section` 的粗體＋15pt＋藍色樣式。本地模型多以「1.／-」條列，
  故此問題在雲端模式特別明顯。寫入器本身自 v4.0 起無回歸（git-blame 確認）。
- **修法（章節名白名單）**：章節標題是「有限已知集合」、條列項目是開放集合，
  故以白名單鎖定前者、其餘一律內文（`backend/core/templates.py`）：
  - `general`：僅「報告事項／討論事項／主席裁示事項／臨時動議／散會／其他事項」
    （容許「（後續管考與追蹤）」等括注）為章節，並**錨定行尾**——
    「三、報告事項所列各案均照案通過。」這類以章節關鍵字開頭的長句也不誤判
  - `section_meeting`：僅「科長轉知／科長指示／臨時動議／散會」（官方格式
    章節可帶行內值，不錨定行尾）
  - `isms_monthly`：官方會議記錄表無公文章節列，改為永不匹配（退回一般渲染
    時「一、…」皆為內容／決議事項條列）
  - `procurement_evaluation`：維持原樣——「壹貳參…」字元集與子項「一、／（一）」
    不相交，無誤判風險
  - `MeetingTemplate` dataclass 預設值改為**永不匹配**：章節樣式必須由模板
    明確宣告，新模板不得再繼承寬鬆預設（防呆）
- **同場修復**：
  - 「案由一：／案由二：」編號案由納入 `general` 欄位標籤（原僅認「案由：」，
    編號案由整行淪為一般段落、標籤未加粗）
  - `_add_formatted_runs` 粗體判斷改用 split 索引奇偶（單一擷取群組的奇數索引
    必為 `**…**` 內文）；原以內容比對，同一行出現相同文字的粗體與非粗體片段
    時會前後誤置（如「重要**重要**」）

### 🧪 測試與驗證

- `tests/test_templates.py` 新增 `TestGeneralDocxSectionPattern`（3 項，
  含實際誤判文件句子回歸）、`section_meeting`／`isms_monthly` 章節 pattern
  補強斷言
- `tests/test_docx_converter.py` 新增 `TestNumberedItemsRenderAsBody`（3 項，
  模擬雲端條列輸出端到端驗證章節粗體、項目內文、案由標籤）＋粗體奇偶回歸 1 項
- 全套件 407 passed、3 skipped，四模板既有行為零回歸

## [v4.6.0] - 2026-07-28

### 🎯 主題：「ISMS月工作會議」專屬模板＋表單式 DOCX 官方版面（模板系統再擴充）

### ✨ 新功能

- **ISMS 月工作會議模板**（`backend/core/prompt_templates/isms_meeting.py`）：
  - 格式逐段對齊使用者提供之官方範本（ISMS 月工作會議記錄表）：置中標題＋
    勾選行（■月工作會議）→ 主表格（專案名稱／會議議題／地點·主席／
    日期·記錄／參加人員／內容／追蹤事項／決議事項＋臨時動議）→ 簽到表
  - 十四欄位標籤契約（機關名稱／專案名稱／會議議題／地點／主席／日期／
    記錄／機關單位／廠商單位／參加人員／內容／追蹤事項／決議事項／
    臨時動議）；日期強制民國點分＋週別（例：115.07.28（二））
  - 人名、廠商名實名照逐字稿；未提及一律「（待確認）」；追蹤事項與
    臨時動議「未提及≠無」，不得自行填「無」
  - 允許雲端處理（會議本身即有外部廠商顧問參與，使用者確認比照科務會議）；
    ISMS 領域術語表（資通安全、風險評鑑、內部稽核、外部驗證、營運持續
    演練、弱點掃描等）＋同音誤辨修正注入 LLM 語意校正層
- **表單式 DOCX 版面基礎設施**（模板系統新能力，任何表格式官方範本皆可掛）：
  - `MeetingTemplate.form_layout`（`FormLayoutSpec`）：宣告式描述官方表格
    版面（開頭段落、表格欄寬、儲存格內容、跨欄合併、簽名列最小高度），
    純資料放 `templates.py`，維持「不 import docx_converter」的匯入紀律
  - `extract_form_fields()`：由本文 Markdown「確定性抽出」欄位 dict（不靠
    LLM 二次生成），容錯全形空白標籤與全半形冒號、水平線後逐字稿附錄
    不吞入欄位、缺漏補「（待確認）」，永不拋例外
  - `docx_converter` 新增表單渲染分支：固定欄格線（`tblLayout fixed`）＋
    XML 框線（確保 Office 2024/M365 相容）＋ span 跨欄合併；本文未命中
    適用樣式（如摘要失敗 result 為逐字稿）或渲染例外時自動退回一般段落
    渲染，`convert()` 介面不變、永不因表單版面拋例外

### 🧪 測試與驗證

- `tests/test_templates.py` 新增 `TestIsmsMonthlyTemplate`（12 項）與
  `TestIsmsFormFieldExtraction`（7 項）
- `tests/test_docx_converter.py` 新增 `TestIsmsFormDocx`（10 項，含表單
  版面結構驗證與退回一般渲染的防線測試）
- 全套件 399 passed、3 skipped，既有模板（general／procurement_evaluation／
  section_meeting）行為零回歸

### 📝 文件

- 系統架構與程式設計書 §6.5 補充 `form_layout` 欄位、內建模板第 4 項、
  表單式模板新增步驟

## [v4.5.1] - 2026-07-22

### 🎯 主題：雲端模型升級 gemini-3.5-flash-lite ＋ 環境變數生效機制根治

### 🔧 變更

- **雲端模型升級**：預設 Gemini 模型 `gemini-3.1-flash-lite` → `gemini-3.5-flash-lite`
  （已於開發機以 OpenAI 相容端點實測連通，HTTP 200）。
  同步更新 `backend/core/config.py`、`.env.example`、`config.macos.yaml`、
  README、系統架構書、部署更新手冊。

### 🐛 根因修復（正式機模型不生效問題）

- **問題現象**：正式機（GPU 版）依手冊 `git pull` → `restart` 後，
  `/api/config` 的 `cloud_llm_model` 仍回報舊模型。
- **根因鏈**（三層疊加）：
  1. GPU 版 compose 未定義 `GEMINI_MODEL`，值僅來自 `env_file: ../.env`
     或程式內預設值；而程式內預設值仍是舊模型。
  2. `env_file` 內容在容器**建立**時凍結，`docker compose restart`
     不會重讀 `.env` → 手冊「步驟四改 `.env` ＋ 步驟六 restart」的
     組合對 `.env` 變更從未真正生效。
  3. 標準版 `docker-compose.yml` 在 `environment` 寫死 `GEMINI_MODEL`，
     優先權高於 `env_file`，堵死 `.env` 覆蓋能力。
- **修法**：
  1. `config.py` 預設值升級（backend/ 為 volume 掛載，`git pull` ＋
     `restart` 即生效，作為無 `.env` 設定時的正確回退）。
  2. 標準版 compose 移除 `environment` 寫死的 `GEMINI_MODEL`，
     統一「`.env` > 程式預設值」的單一生效路徑。
  3. 部署手冊新增 v4.5.1 捷徑與「`env_file` 凍結陷阱」說明：
     凡動過 `.env` 一律改用 `up -d`（秒級重建容器、零下載），
     未動 `.env` 照舊 `restart`。

## [v4.5.0] - 2026-07-20

### 🎯 主題：「科務會議」專屬模板＋列管資料附件輸出（模板系統首次擴充）

### ✨ 新功能

- **科務會議模板**（`backend/core/prompt_templates/section_meeting.py`）：
  - 格式逐段對齊使用者提供之官方範本（115年7月份第1次科務會議紀錄／列管資料）：
    時間／地點／主持人（＋紀錄同行）／出席人員（如後附簽到表）→
    歷次列管案件 → 決議事項辦理情形彙整表（四欄表格：案由及承辦單位｜
    辦理情形｜解除列管｜繼續列管）→ 三層條列（一、→（一）→1.）→ 散會
  - 交辦事項規則：凡指派承辦股／同仁之決議每項一列入彙整表；
    「辦理情形」欄只填承辦者名＋全形冒號（內容留待事後填報）；
    「解除／繼續列管」欄留空（下次會議勾選）——與範本慣例一致
  - 指示來源辨識：科長本人指示 vs 轉述局長／副局長／局務會議指示不得混淆
  - 人名股別實名照逐字稿（使用者確認）；未提及填「（待確認）」；
    歷次列管案件僅從逐字稿擷取、未提及填「（待確認）」由人工補
  - 允許雲端處理（非機敏強制本地類型）；科務術語表＋8 組同音誤辨修正
    （課務會議→科務會議、列冠→列管…）注入 LLM 語意校正層
- **附件輸出基礎設施**（模板系統新能力，任何模板皆可掛附件）：
  - `MeetingTemplate.attachment`（`AttachmentSpec`）：附件由「本文 Markdown
    確定性抽出」（程式抽表格，不靠 LLM 二次生成），保證本文與附件內容一致；
    抽取失敗補「（待確認）」骨架＋warning log，永不阻斷本文下載
  - `GET /api/tasks/{id}/result?format=docx&doc=attachment`：附件下載端點
    （沿用 mtime 快取；無附件模板→400；非 docx→400）
  - 前端結果區新增「下載列管資料 (Word)」按鈕：依任務實際使用的模板
    （任務狀態 API 的 `template_id`）動態顯示，一般會議／採購評選會不顯示
  - `/api/config` 模板清單新增 `has_attachment`／`attachment_label`

### 🧪 測試與驗證

- 新增 22 個測試（模板註冊、附件建構器邊界、附件 API、config 揭露），
  全套 371 passed／3 skipped；general 與採購評選會零回歸
- 真實 `docx_converter` 驗證：本文含四欄表格＋標籤加粗；附件兩張表與範本
  結構一致；Playwright 驗證三模板卡渲染與附件按鈕顯示邏輯

## [v4.4.0] - 2026-07-17

### 🎯 主題：會議模板系統＋「採購評選會」專用模板（機敏強制本地）

### ✨ 新功能

- **可擴充會議模板系統**（`backend/core/templates.py`）：每種會議類型一個
  `MeetingTemplate`，集中定義系統提示詞、萃取／生成增補規則、結構驗證樣式、
  記錄骨架、DOCX 公文層次樣式、領域術語表與 `local_only` 旗標。
  新增會議類型（如科室會議、局務會議）＝新增一個 prompt 模組＋註冊一筆，
  驗證、後處理、Word 輸出、前端選單全部自動生效。
- **採購評選會模板**（`backend/core/prompt_templates/procurement.py`）：
  - 紀錄結構對齊工程會「機關辦理最有利標簽辦文件範例 6-3 評選會議紀錄」
    （壹～拾陸國字段落），欄位符合採購評選委員會審議規則 §11 法定 12 款記載事項
  - 角色標註：主席（召集人）／評選委員／採購工作小組／承辦單位／廠商代表，
    依發言內容辨識；委員一律匿名（「委員提問」），廠商實名
  - 詢答逐項對應：「委員提問：／廠商答詢：」成對記載，統問統答自動拆對
  - 機敏防護（法規依據）：個別委員評分（最有利標評選辦法 §20）與底價
    （採購法 §34）一律不入紀錄，改記「（機敏資訊，不列入紀錄）」；
    驗證層以 forbidden patterns 掃描洩漏、命中即觸發補強重寫
  - 採購術語表＋20 組 ASR 高頻誤辨修正（最有力標→最有利標、續位法→序位法…）
    注入 LLM 語意校正層（刻意不進 ASR hotwords，避免污染逐字稿快取）
- **前端「選擇會議類型」選單**：卡片由 `/api/config` 動態渲染；
  選擇採購評選會即強制切換本地模式並鎖定雲端卡（顯示機敏提示）
- **後端第二道防線**：`local_only` 模板＋雲端模式上傳 → HTTP 400

### 🔧 架構重構（行為不變）

- 原寫死的公文格式常數（`summarization.py` 驗證樣式、`text_postprocess.py`
  記錄骨架、`docx_converter.py` 公文層次 regex）全部改由模板註冊表驅動；
  general 模板行為與 v4.3.3 byte-identical（golden 回歸測試把關）
- `template_id` 沿 upload → queue → TaskInfo → task_processor → summarize
  全線傳遞；本地上下文預算改以「模板增補後」的實際提示詞估算（P0-6 延伸）
- 新增 28 個測試（`tests/test_templates.py`＋API 強制測試），全套 349 passed

## [v4.3.3] - 2026-07-08

### 🎯 主題：雲端內容豐富度根治＋品牌字樣移除＋副標精簡放大

### 🐛 根因修復

- **雲端紀錄內容豐富度遠輸地端（0708 人工實測）**：v4.3.2 的兩段式管線
  仍是「整份逐字稿單發萃取」——LLM 輸出長度不會隨輸入等比放大，103 分鐘
  會議被單次萃取壓成一頁筆記；第二段生成又只看筆記，第一段丟失的立場、
  理由、數據與案例（如業務單位對系統斷續、效益不明顯的真實反映）永遠
  救不回來。地端勝出正是因為 context 限制迫使分塊萃取、逐段筆記密度有
  結構保證。v4.3.3 根治（backend/services/summarization.py）：
  1. 雲端萃取比照地端分塊密度分段「併發」萃取（`CLOUD_LLM_CHUNK_TOKENS`
     預設 3200、`CLOUD_LLM_MAX_CONCURRENT_REQUESTS` 預設 3），萃取提示詞
     追加豐富度規則（各方立場、理由、數據、案例、統一口徑必須完整保留）
  2. 分段筆記零損串接——雲端長上下文不需要地端的有損整併與硬截斷
  3. 生成與補強同時餵「筆記（涵蓋檢查表）＋原始逐字稿（細節來源）」，
     要求嚴禁把多句實質討論壓縮成單句
  4. 驗證新增動態長度下限（逐字稿 tokens÷15，區間 250–2000 字）——
     過薄輸出觸發帶逐字稿的補強輪，而非靜默通過（855 字案例將被攔截）
  5. 雲端串流進度區間修正為 86–94%，第二段生成不再把進度條倒退回 65%

### ✨ 介面與品牌

- **MeetingScribe 品牌棄用**：所有顯示層字樣（網頁標題、標題區品牌小字、
  頁尾、Swagger 標題、腳本橫幅、README 與全部文件）移除或改為
  「政府智慧會議紀錄生成系統」。小寫基礎設施識別字（docker image/
  container/volume/network 名、conda 環境名、pyproject 套件名）刻意保留：
  改名會使 6GB ASR 模型 volume 失聯觸發重新下載（頻寬紅線），並連鎖
  破壞 7 支以字串比對操作容器的部署腳本，顯示層以外無任何收益
- **副標題精簡並放大**：「AI轉錄・智慧生成，一鍵產出正式會議紀錄」→
  「AI轉錄・智慧生成」，字級 1rem → 1.25rem 等比放大並加少量字距

### 🧪 測試：320 passed（新增雲端分段萃取、雙輸入生成、動態下限等 4 例）

## [v4.3.2] - 2026-07-08

### 🎯 主題：雲端品質根治＋GPU 誤報修正＋排隊介面中文化

### 🐛 根因修復

- **雲端會議紀錄過薄（實測輸給地端）**：根因是雲端為「單發直出」——
  沒有萃取階段、驗證時筆記傳空字串導致涵蓋度檢查全部停用（103 分鐘
  會議僅 855 字、裁示 4 條 vs 地端 16 條）。改為與本地相同的兩段式管線：
  整份逐字稿一次結構化萃取（Gemini 長上下文）→ 依筆記生成正式紀錄 →
  帶筆記驗證與補強（涵蓋度檢查真正生效）
- **處理中顯示「GPU 未偵測」**：根因是偵測器把「可用 VRAM <4GB」
  （＝GPU 正被模型使用！）誤判為「GPU 不存在」並汙染快取狀態。
  改為區分「GPU 存在」與「目前忙碌」（gpu_busy），狀態列顯示
  「GPU: RTX 4090（使用中）」；並在釋放 Ollama 模型後輪詢 /api/ps
  確認真的卸載完成，避免 ASR 裝置偵測誤降級 CPU
- **排隊狀態中英夾雜**：根因是 WebSocket 初始訊息直接吐英文 enum 值
  （queued/transcribing）。後端統一中文標籤（排隊等候中/語音轉錄中…），
  含全狀態覆蓋測試
- **md 與 docx「內容不一致」查證**：逐行 diff＝0，兩檔內容其實完全一致；
  觀感差異來自 Word 呈現是同大小字牆。docx 轉換器新增公文結構辨識：
  「一、二、三」章節加粗放大（15pt 藍）、「會議名稱：/案由：/決議：」
  等欄位標籤加粗——Word 打開即具公文層次

### ✨ 介面

- 排隊卡改為「兩個數字欄＋狀態 badge 置中」，去除懸空單位與過大狀態字

## [v4.3.1] - 2026-07-08

### 🎯 主題：標題智慧化＋字級放大 20%＋動態模型資訊

- **標題/副標題**：主標「智慧會議紀錄系統」＋副標「AI 聽打・智慧彙整，
  一鍵產出可簽核的正式會議紀錄」（原品牌小字已於 v4.3.3 移除）
- **全站字級等比放大 20%**：root 字級 120%、所有 font-size 改以 rem 定義
  （之後再調整只需改一行）；按鈕高度 44→48px 配合放大
- **模式卡顯示實際模型名稱**：`/api/config` 新增 `local_llm_model`
  （後端自動解析後的生效名稱，如 gemma4:31b）與 `cloud_llm_model`；
  前端動態帶入「使用模型：gemma4:31b（已就緒）」——換模型自動同步，
  前端零寫死（含測試）

## [v4.3.0] - 2026-07-08

### 🎯 主題：前端介面全面改版（使用者已批准《前端網頁設計改版》提案）

純呈現層改造（index.html / style.css / app.js），後端 API 與處理流程零變動：

### ✨ 介面改版

- **設計系統**：USWDS 政府藍 `#005EA2` 取代消費藍；淡冷灰背景＋白卡片＋
  細邊框；系統原生字型 stack（零外連 CDN）；emoji 圖示全面改為內嵌單色 SVG
- **16:9 寬螢幕版面**：容器放寬至 1120px；步驟 1「模式選擇｜檔案上傳」
  左右並排；處理中／結果／錯誤維持 760px 閱讀寬度置中
- **常駐三步驟流程列**（設定與上傳→處理中→完成下載）：使用者隨時知道
  自己在哪一步；排隊與進度合併為同一張卡，畫面不再跳動
- **下載按鈕分主次**：Word（機關最常用）為唯一藍色主按鈕；Markdown／
  逐字稿為白底次按鈕並排對齊（文字不換行）；重新開始為文字按鈕
- **無障礙 AA**：次要文字對比修正（#86868B→#55565B）；狀態「符號＋文字＋
  顏色」三重編碼；上傳區與模式卡支援鍵盤 Enter/Space；aria-live／
  role=alert／focus-visible；尊重「減少動態效果」
- **文案**：錯誤訊息改白話並附下一步指引；「請聯絡系統管理員」；
  「會議記錄」錯字全面修正為「會議紀錄」

## [v4.2.3] - 2026-07-08

### 🎯 主題：交付文件瘦身＋下載檔名標準化＋前端快取根治

使用者實測 v4.2.2 部署後回報四個問題，本版全數修正：

### 🐛 修正

- **「已部署新版但網頁還是舊的」根治**：首頁回應加上
  `Cache-Control: no-cache`（每次向伺服器驗證新鮮度，內網 304 成本趨近
  零）；JS/CSS 的 `?v=` 快取參數改綁版本號。此前瀏覽器啟發式快取了舊
  index.html，導致「下載逐字稿」按鈕已部署卻看不到
- **頁尾版本寫死 v4.0.0**：改由 `/api/health` 動態帶入（唯一來源：VERSION 檔）
- **Word 標題錯字**：「會議記錄」→「會議紀錄」（H1 由後端 `_format_result` 產生）
- **「GPU 未偵測」**：根因為 v4.2.0 容器的 torch 是 CPU 版（R6，v4.2.2 的
  compose 已改回 faster-whisper 修正）；v4.2.3 部署後健康檢查已回報
  `gpu_available: true`（RTX 4090）

### ✨ 變更

- **下載檔名標準化**：md/docx 一律 `YYYYMMDDhhmmss_會議紀錄`、逐字稿
  `YYYYMMDDhhmmss_逐字稿`；檔名由後端 Content-Disposition 統一決定，
  前端不再自行拼檔名（先前錯字與 task_id 檔名皆源於前端硬編）
- **交付文件只留會議紀錄本文**：處理資訊（檔案/時間/模式/裝置）與語意
  校正對照表改記錄於伺服器 log；逐字稿不再附錄於文件內（由「下載逐字稿」
  獨立提供）——md/Word 打開即是可直接陳核的紀錄

## [v4.2.2] - 2026-07-07

### 🎯 主題：會議紀錄「內容過薄」根因修復＋逐字稿獨立下載

使用者實測回饋 103 分鐘會議僅產出 965 字紀錄。根因分析與修正詳見
`doc/計畫與報告/後續優化計畫.md`，本版重點：

### 🐛 根因修復

- **R1 思考型模型吃掉輸出預算（主因）**：gemma4 的 thinking 與正文共用
  num_predict，導致正文極短甚至為空（先前「偶發空回應」同根因）。所有
  Ollama 呼叫預設 `think:false`（`LOCAL_LLM_DISABLE_THINKING`，不支援
  的模型自動相容降級）；實測每次生成提速 25-70%
- **R2 合併漏斗過窄**：4090 實測 `num_ctx=16384`（VRAM 23.0/24GB、速度
  不變）寫入 GPU compose 預設，合併筆記預算放大 4 倍
- **R6 GPU 容器 torch 為 CPU 版**：Dockerfile 安裝順序 bug（先裝 PyPI
  torch、CUDA 版被 pip 視為已滿足而跳過）→ CUDA torch 改為先裝；
  重建映像前 compose 暫回 `faster-whisper + Breeze-ASR-25`（CT2 自帶
  CUDA、模型已在 volume、零下載）
- **R7 OpenCC 誤傷簡繁共用字**（干預→幹預）：改為「先偵測、僅轉換含
  簡體字的行」，正體文字一字不動
- **VRAM 競爭**：ASR 開跑前主動請 Ollama 釋放常駐模型，避免 keep_alive
  導致 ASR 降級 CPU
- `CORRECTION_SCOPE` 預設 all→auto（全文校正實測 69 分鐘、淨效益趨近 0）

### ✨ 新增：逐字稿獨立下載

- 逐字稿（經確定性清理＋語意校正）另存獨立 .txt 檔
- 新 API：`GET /api/tasks/{task_id}/transcript`（紀錄生成失敗仍可下載）
- 前端新增「📝 下載逐字稿」按鈕（P1-11 部分落地）

### 📄 文件

- 新增 `doc/計畫與報告/後續優化計畫.md`：五大根因分析（附實測證據）＋
  下一輪優化清單 O-1~O-10（依 BooookScore/CoD/LongWriter 等研究實證排序）

### 🧪 測試：312 passed（新增 OpenCC 共用字保護、逐字稿路徑等）

## [v4.2.0] - 2026-07-07

### 🎯 主題：語意校正機制上線＋《系統改善及優化計畫》P0/P1/P2 落地

依《系統改善及優化計畫.md》逐項執行（各項編號對照該計畫），本版重點：

### ✨ 新增：語意校正機制（四層防線）

- **第一層（P1-1）機關詞彙表 hotwords**：新增 `data/glossary/公務詞彙.txt` 與 `backend/core/glossary.py`；faster-whisper 路徑經 `hotwords` 每視窗注入，transformers 路徑併入 initial prompt；支援「錯誤寫法=>正確寫法」登錄已知誤辨
- **第二層（P1-2）確定性後處理** `backend/core/text_postprocess.py`：OpenCC s2twp 統一台灣正體（取代 45 字硬編碼偵測）、Whisper 幻覺黑名單（請訂閱／字幕由…提供）、連續重複句去重、公務用字白名單
- **第三層（P1-3）選擇性 LLM 校正** `backend/services/correction.py`：分段 400 字、附前文唯讀上下文、temperature=0、詞彙表注入、few-shot 含「無錯誤原樣輸出」負例；可由 `ENABLE_TRANSCRIPT_CORRECTION` / `CORRECTION_SCOPE` 開關
- **第四層（P1-4）同音驗證閘門**：LLM 的每處替換以 pypinyin 注音比對（含台灣口音 zh/z、in/ing 等近音容錯），非同音近音一律退回原文；單段改動 >10% 整段放棄；全部修改輸出「語意校正對照表」供人工複核

### 🐛 P0 嚴重缺陷修復

- **P0-1** `initial_prompt` 在 `language=auto` 下永不套用 → 無論語言模式一律套用
- **P0-2** transformers 生產路徑 30 秒硬切 → 改用 pipeline 原生重疊分塊解碼（`chunk_length_s=30, stride=(5,5)`），保留舊視窗切割為回退
- **P0-3** 設定黑洞 → `config.yaml` 頂部加大字警告（後端只讀環境變數）；後端啟動時記錄全部實際生效參數
- **P0-4** 兩套 compose ASR 設定統一為 transformers＋Breeze-ASR-26＋auto
- **P0-5** 摘要失敗不再偽裝成功 → 輸出檔標題與首段顯著警告「僅逐字稿」、進度訊息明示
- **P0-6** 最終生成 token 預算納入完整 System Prompt 開銷，杜絕 Ollama 靜默截斷
- **E2E 實測追修**：筆記整併迴圈加入收斂保護（輪數上限＋縮減停滯偵測＋輸出綁定預算＋硬截斷保底），修復預算收緊後 merge 無限重壓縮的無窮迴圈；校正分段器支援無標點 ASR 逐字稿；transformers `prompt_ids` 需 `return_tensors="pt"`；ASR allow-pattern 補 `model.safetensors`
- **P0-7** Ollama `keep_alive` 0 → 10m（可設定），多階段流程不再反覆重載 20GB 模型
- **P0-8** 版本號單一來源（VERSION 檔）；清理 main.py/schemas.py/config.py 等陳舊版號

### ✨ P1 品質建設

- **P1-6** faster-whisper 實證參數組：`condition_on_previous_text=False`、`compression_ratio_threshold=2.2`、`no_speech_threshold=0.5`、`repetition_penalty=1.1`、`no_repeat_ngram_size=3`、VAD `min_silence` 2000→500ms
- **P1-8** 驗證器改容錯 regex（允許空格/全半形差異），降低無謂補強輪次
- **P1-9** 後處理與驗證順序重構：記錄級清理（英文移除/結構補全）移入 summarization 於「驗證前」執行，驗證成為最後一關，本地與雲端路徑一致
- **P1-10** 英文行清理加入詞彙表白名單保護，刪除行為記入 log

### 🚀 P2 部署與效能

- **P2-1** Docker 零 rebuild：windows-gpu compose 掛載 backend/frontend/VERSION/glossary，改 code/prompt 只需 `restart`；刪除所有 `--no-cache` 教學；明文禁止 `down -v`（防 6GB 模型 volume 被清）
- **P2-2** `.env.example` 完整補充 ASR/校正/keep_alive/num_ctx 參數與 Ollama 主機建議（`OLLAMA_FLASH_ATTENTION=1`、`OLLAMA_KV_CACHE_TYPE=q8_0`）
- **P2-7** CORS 收斂：`ALLOWED_ORIGINS` 環境變數；`*` 時依規範停用 credentials
- **P2-8** 死碼清理：`_summarize_with_local_llm`、app.js 重複 `setDownloadButtonsEnabled`、task_processor 廢棄結構修補函式
- **uv 環境管理**：新增 `pyproject.toml`（uv sync 一鍵還原環境；CPU torch 索引，開發機不再誤載 2GB CUDA wheel）

### 🧪 測試

- 新增 `tests/test_correction_service.py`（同音閘門/校正流程/確定性清理）
- 更新 `tests/test_task_processor.py`（P0-5 失敗顯性化、P1-9 不改寫已驗證本文、P1-10 白名單）
- 全套件 308 passed

## [Unreleased]

### 🚀 Breeze-ASR-26 升級

- 官方 ASR 預設路線升級為 `MediaTek-Research/Breeze-ASR-26`（Transformers），並保留 `faster-whisper` / Breeze-ASR-25 回滾能力
- 新增 `ASR_BACKEND`、`WHISPER_MODEL_REVISION`、安全 allow/deny patterns、backend-aware transcript cache
- 新增 `scripts/download_models.py` 與 `scripts/run_asr26_validation.py`，固定 revision 下載並產生 10 分鐘混語驗收產物
- Windows GPU compose 預設切換至官方 ASR-26，CPU / mac 路徑維持較保守設定
- 本地模式預設 LLM 改為 `gemma4:31b`，若只安裝 Gemma4 相容標籤可由後端自動解析

### 🐛 修復

- 修復官方 ASR-26 的 revision 處理、安全下載限制、CPU fallback retry 與路徑 containment 問題
- 修復 DOCX 下載失敗時前端/後端錯誤處理，避免只看到 JSON 錯誤內容
- 修復前端上傳流程遺失 `setDownloadButtonsEnabled()` 輔助函式，避免選檔後在送出 `/api/upload` 前就因 `ReferenceError` 完全無反應
- 修復 Windows + NVIDIA 原生安裝容易誤裝 `torch ... +cpu` 的問題：新增 `requirements.windows-cuda.txt` 精確鎖定 CUDA wheel、`install_deps.py` 自動選擇 GPU 安裝路徑，並讓 `scripts/verify_env.py` 明確攔截 CPU-only torch
- 新增 60 秒與 10 分鐘驗收產物，詳見 `data/validation/` 與 `doc/計畫與報告/驗收報告.md`

## [v4.1] - 2026-06-04

### 🎯 主題：會議紀錄品質根治與 System Prompt 硬化

實測發現「音檔→逐字稿→會議紀錄」流程產出的會議紀錄品質不佳：夾雜非必要英文、口語贅字、語意校正過程，甚至杜撰不存在的單位／人名／決議。以一次 Gemini 雲端實測（`tests/會議記錄_20260604.docx`）為證據進行根因分析，確認 **問題不在模型能力，而在 System Prompt 架構與輸出後處理**。本版以「政府機關承辦人員」視角，採多代理對抗方式硬化提示詞並修補相關程式碼。

### ✨ 變更

- **重寫 System Prompt（`backend/core/prompts.py`）**
  - 移除會誘發「原樣回吐」的 `### 評估標準` 區塊與 `[請從文本中提取…]` 方括號模板。
  - 新增「只輸出本文」硬規則：回應第一個字元必須是「會議名稱：」，嚴禁前言、開場白、英文分析、複述提示詞。
  - 新增閉合式 **不杜撰** 規則：未明示一律標註「（待確認）」，禁臆測、禁套用範例人名、不得補寫／捏造。
  - 新增 **去贅字／去自我更正** 規則（呃、嗯、那個…；自我更正只採最終版本）。
  - 加入台灣公務用語與陸式用語對照表（信息→資訊、質量→品質、項目→計畫、落實→確實辦理），並修正公文挪抬法制（僅尊長挪抬）。
  - `config.yaml` 的 `system_prompt` 由 `prompts.py` 程式化同步，避免雙來源漂移。
- **雲端模型升級**：預設 Gemini 模型 `gemini-2.5-flash-lite` → `gemini-3.1-flash-lite`（同步更新 `backend/core/config.py`、`docker/docker-compose.yml`、`config.macos.yaml`、`.env.example`）。
- **`VERSION`**：4.0 → 4.1。

### 🐛 修復

- **清理器裁不掉新格式英文前言（`summarization._clean_ollama_output`）**：原僅裁切到第一個 Markdown 標題，但正式公文以「會議名稱：」開頭，英文前言因此永遠殘留；裁切錨點改為同時支援「會議名稱：」與 Markdown 標題，取最靠前者。
- **缺英文／回吐偵測**：新增 `_contains_english_or_rubric_leakage`，偵測 `Analysis of the Transcript`、`Evaluation Criteria`、`Let's infer`、回吐評估標準字串、方括號殘留與整行英文啟發式，並接入 `_validate_summary_quality`。
- **雲端路徑無防護**：將「驗證＋自動補強重寫」迴圈擴及 Gemini 雲端路徑（原僅本地萃取式管線有此防護，而出問題的正是雲端路徑）；重構出共用的 `_gemini_chat` 與 `_build_cloud_refinement_message`。
- **待辦召回假陽性**：原以逐字精確比對，導致良好摘要僅因改寫待辦字句即被誤判「待辦遺漏」而無止盡觸發補強；改為「包含式比對 ＋ 僅取待辦清單表格」（`_extract_action_table_keys`）。
- **後處理強化（`task_processor._remove_english_segments`）**：移除英文前言行（模組層級 `_ENGLISH_PREAMBLE_RE`）、保護含「（待確認）」的合法缺漏標記不被英文比例規則誤刪、保留技術名詞（OAuth2、GitHub Actions 等）。

### ✅ 測試

- 新增／更新提示詞契約、清理、驗證、後處理離線單元測試（`tests/test_system_prompt_validation.py`、`tests/test_summarization_service.py`、`tests/test_task_processor.py`），涵蓋：無方括號模板、禁英文前言、`config.yaml` 與 Python 來源一致性、英文／回吐偵測、（待確認）與技術名詞保護。
- 新增 `test_config_yaml_prompt_matches_python_source` 將提示詞雙來源漂移由「靠人記得」升級為 CI 擋住。

### 📄 文件

- 新增 [部署更新手冊_v4.1.md](doc/操作手冊/部署更新手冊_v4.1.md)：給非技術人員的逐步更新部署手冊，含「要不要重建映像／會不會吃網路流量」的精確判斷（標準版免重建、GPU 版用普通 `build` 不下載、僅套件清單變動才需 `--no-cache`）。
- 精簡 README.md：移除內嵌的逐版變更深掘段落，回歸「介紹用途／架構／理念／簡易操作」定位，變更紀錄統一回歸本檔。

> ⚠️ **Docker 部署注意**：System Prompt 內嵌於容器映像（GPU 版）或經 volume 連動（標準版），需重新套用映像／重啟容器後方可生效，提示詞無法經 API 注入。詳見 [部署更新手冊_v4.1.md](doc/操作手冊/部署更新手冊_v4.1.md)。

---

## [v4.0] - 2026-02-28

### ✨ 新增 DOCX (Word) 下載功能

- **新功能**：會議記錄支援下載為 Word (.docx) 格式，相容 Office 2024 / M365
- **API 擴展**：`GET /api/tasks/{task_id}/result?format=docx` 回傳 Word 文件（向後相容，預設仍為 Markdown）
- **前端按鈕**：結果頁面新增「📄 下載 Word」按鈕
- **專業排版**：A4 頁面、CJK 字型（微軟正黑體標題 + 新細明體內文）、完整表格框線、標題行灰底
- **快取機制**：首次轉換後快取 .docx 檔案，後續下載直接回傳
- **新增依賴**：`python-docx>=0.8.11`
- **測試覆蓋**：28 項單元測試（標題/表格/粗體/列表/字型/頁面設定/端到端）

## [v3.5.5] - 2025-12-18

### 📚 文件驅動開發（SDD）核心精神實施

#### 問題診斷

經過人工驗證，v3.5.5 的環境修復已完成，但發現**文件系統嚴重過時、不同步、對非技術人員不友善**的根本問題。

**痛點分析**：
1. **文件過時**：多數文件仍停留在 v3.5.4，未反映最新架構
2. **文件混亂**：45 個 Markdown 檔案散落各處，無清晰導航
3. **非技術不友善**：充滿技術術語，非工程師難以理解
4. **文件不同步**：程式碼已更新，文件未跟進
5. **缺乏維護機制**：無自動化文件檢查工具

#### 實施方案

**根據文件驅動開發（Specification-Driven Development）最佳實踐**：

1. **在 INSTRUCTIONS.md 新增第零部分**：文件驅動開發核心精神
   - 定義文件優先順序（使用者文件 > 維護者文件 > 技術文件）
   - 建立文件同步強制規則
   - 制定文件品質標準（可讀性、完整性、友善性）

2. **徹底重寫 doc/README.md**（v3.5.5）
   - 建立清晰的文件導航中心
   - 新增情境化查找（「我是第一次使用」「我想使用 GPU」）
   - 完整的文件分類與命名規範
   - 疑難排解章節

3. **新增自動化檢查工具**：`scripts/check_docs.sh`
   - 版本號一致性檢查
   - 文件命名規範檢查
   - 文件結構完整性檢查
   - 連結有效性檢查（基本）

4. **封存過時文件**
   - 將舊的 doc/README.md 移至 README_old.md
   - 確保 old/ 目錄包含所有歷史文件

#### 文件驅動開發原則（已加入 INSTRUCTIONS.md）

```
文件 → 設計 → 實作 → 測試 → 文件更新
  ↑                             ↓
  └─────────── 持續同步 ─────────┘
```

**核心理念**：
- 文件先行：功能開發前先撰寫文件
- 文件即規格：文件是唯一真實來源
- 文件可執行：範例必須可運行
- 文件友善：非技術人員可理解

#### 修改檔案清單

| 檔案 | 動作 | 說明 |
|------|------|------|
| `.github/INSTRUCTIONS.md` | 新增 | 第零部分：文件驅動開發核心精神 |
| `doc/README.md` | 徹底重寫 | v3.5.5 版本，完整導航中心 |
| `doc/README_old.md` | 封存 | 舊版文件備份 |
| `scripts/check_docs.sh` | 新增 | 文件健康檢查工具 |
| `CHANGELOG.md` | 更新 | 本次變更紀錄 |

#### 驗收結果

```bash
$ ./scripts/check_docs.sh

【檢查 1】版本號一致性
  ✅ VERSION 檔案: v3.5.5
  ✅ README.md 版本號正確
  ✅ doc/README.md 版本號正確

【檢查 2】文件命名規範
  ✅ 所有檔案名稱符合小寫規範
  ✅ 所有檔案名稱使用底線分隔

【檢查 3】文件結構完整性
  ✅ 所有必要目錄和檔案存在

【檢查 4】連結有效性
  ✅ doc/README.md 存在

總結：⚠️ 發現 3 個警告（舊版本引用，已在 old/ 目錄中）
```

---

## [v3.5.5-env-fix] - 2025-12-18

### 🔧 環境統一與日誌系統升級

#### 問題診斷（第一性原理分析）

**問題表徵**：上傳音訊檔案後持續出現 `No module named 'av'` 錯誤

**根本原因分析**：
1. **多個啟動腳本衝突**：
   - `start_service.sh` 使用 conda meetingscribe 環境 ✅
   - `scripts/start-mac-native.sh` 使用 venv 環境 ❌
   - 用戶執行錯誤腳本導致環境不一致

2. **venv 環境配置錯誤**：
   - `venv/bin/python3` 指向 `/opt/anaconda3/bin/python3`（base 環境）
   - base 環境無 av、mlx-whisper 等關鍵模組
   - 導致 ImportError

3. **日誌系統不完善**：
   - 僅控制台輸出，無持久化日誌
   - 無法追蹤問題歷史

#### 修復方案

**Phase 1：環境統一**
- ✅ 刪除混亂的 `venv/` 目錄（已備份）
- ✅ 修改 `scripts/start-mac-native.sh` 使用 conda meetingscribe
- ✅ 修改 `scripts/restart-mac-native.sh` 使用 conda meetingscribe
- ✅ 更新 `start_service.sh` 加入環境驗證
- ✅ 新增 `scripts/verify_env.py` 環境驗證腳本

**Phase 2：日誌系統升級**
- ✅ 升級 `backend/core/logger.py` 至 v2.0
- ✅ 新增檔案日誌（每日輪轉，保留 30 天）
- ✅ 新增錯誤日誌（獨立檔案，保留 90 天）
- ✅ 新增 JSON 結構化日誌（用於分析）
- ✅ 新增任務 ID 綁定功能

**Phase 3：測試驗證**
- ✅ 新增 `scripts/test_full_pipeline.py` 完整管線測試
- ✅ 所有測試 7/7 通過

#### 使用 Context7 MCP 最佳實踐

**查詢的技術文件**：
| 來源 | Library ID | Benchmark Score | 用途 |
|------|-----------|-----------------|------|
| Loguru | /delgan/loguru | 94.2 | 日誌系統設計 |
| Structlog | /hynek/structlog | 91.1 | 結構化日誌參考 |
| uv | /astral-sh/uv | 87.2 | 依賴管理參考 |
| PyAV | /pyav-org/pyav | 86.4 | 音訊處理依賴 |

#### 修改檔案清單

| 檔案 | 動作 | 說明 |
|------|------|------|
| `venv/` | 備份刪除 | 統一使用 conda 環境 |
| `scripts/start-mac-native.sh` | 修改 | 改用 conda meetingscribe |
| `scripts/restart-mac-native.sh` | 修改 | 改用 conda meetingscribe |
| `start_service.sh` | 修改 | 加入環境驗證 |
| `scripts/verify_env.py` | 新增 | 環境驗證腳本 |
| `scripts/test_full_pipeline.py` | 新增 | 完整管線測試 |
| `backend/core/logger.py` | 修改 | 升級至 v2.0 |
| `doc/系統改善計劃.md` | 新增 | 系統改善計劃 |
| `doc/implement_and_tasks.md` | 新增 | 實施計畫與任務清單 |
| `doc/v3.5.5_系統修復驗證報告.md` | 新增 | 驗證報告 |

#### 驗證結果

```
環境驗證：✅ 所有關鍵模組通過
完整管線測試：7/7 通過
日誌系統：app/error/json 三種日誌正常運作
```

---

## [v3.5.4-stable-patch] - 2025-12-07

### 🔧 依賴修復（Dependency Fix）

#### 1. PyAV 版本兼容性修復

**問題診斷**：
- PyAV 14.0.1（來自 Conda）與 FFmpeg 7.1.1 不兼容
- 編譯錯誤：`AV_OPT_TYPE_CHANNEL_LAYOUT` 在 FFmpeg 7.1 中已移除
- 替換為新 API：`AV_OPT_TYPE_CHLAYOUT`

**第一性原理分析**：
- 層級 1 - 源代碼層面：PyAV 舊 API 與 FFmpeg 7.1 新 API 不匹配
- 層級 2 - 版本兼容性：FFmpeg 6.1+ 開始廢除舊 API，7.0+ 完全移除
- 層級 3 - 依賴管理：faster-whisper 1.0.1 依賴 av 11.x，但系統有 14.0.1
- 層級 4 - 系統環境：macOS ARM64 + FFmpeg 7.1.1 需要最新 PyAV

**修復方案**：
1. **升級 PyAV 到 16.0.1**
   - 從 GitHub 源代碼編譯（預編譯 wheels 仍包含舊 API）
   - 新版源代碼已修復 FFmpeg 7.1 兼容性
   ```bash
   git clone https://github.com/PyAV-Org/PyAV.git
   pip install -e ./PyAV
   ```

2. **升級 faster-whisper 到 1.2.1**
   - 支持 av >= 11.0（包括 16.0.1）
   - 改動：`requirements.txt` 中 faster-whisper==1.0.1 → 1.2.1

**修改清單**：
- ✅ PyAV：14.0.1 → 16.0.1（從源代碼編譯）
- ✅ faster-whisper：1.0.1 → 1.2.1
- ✅ requirements.txt：更新版本號

#### 2. 使用 Context7 MCP 最佳實踐

**查詢過程**：
1. 使用 Context7 MCP 解析庫 ID：`/pyav-org/pyav`
2. 查詢官方文檔了解 FFmpeg 7.0+ 支持
3. 確認 `pip install av --no-binary av` 不適用（預編譯 wheels 更新）
4. 決策：從源代碼編譯最新版本

**文檔參考**：
- PyAV 官方支持 FFmpeg 版本 7.0+
- 預編譯 wheels 可能滯後，源代碼編譯獲得最新修復
- Source Reputation: Medium，Benchmark Score: 86.4

#### 3. 驗證結果

**依賴驗證**：
```
✓ PyAV 16.0.1（支持 FFmpeg 7.1.1）
✓ FastAPI 0.109.2
✓ Faster-Whisper 1.2.1（支持 av >= 11.0）
✓ 所有核心依賴檢驗通過
```

**編譯狀態**：
```
[✓] 虛擬環境已設置
[✓] 依賴安裝完成
[✓] 資料目錄已建立
[✓] 環境檢查通過
```

**性能**：
- 使用 Apple MPS 加速
- 效能提升 3-5 倍（v3.5.0 原生模式）

#### 4. 影響範圍

**直接影響**：
- ✅ PyAV 編譯成功（移除編譯錯誤）
- ✅ faster-whisper 依賴解決
- ✅ 完整依賴鏈可用

**向後兼容**：
- ✅ API 完全兼容（no breaking changes）
- ✅ 功能無變化
- ✅ 配置無需修改

#### 5. 部署步驟

```bash
# 步驟 1：更新 requirements.txt
git pull origin main

# 步驟 2：更新虛擬環境
source venv/bin/activate
pip install -r requirements.txt --prefer-binary

# 步驟 3：確認依賴
python -c "import av, faster_whisper; print(f'PyAV {av.__version__}, FW {faster_whisper.__version__}')"

# 步驟 4：啟動服務
bash scripts/start-mac-native.sh
```

---

## [v3.5.4-stable] - 2025-12-07

### 🛡️ 版本控制強化（Version Control Enhancement）

#### 1. 確立穩定版本基準

**變更內容**：
- 將 main 分支回退至 commit `7100d81`（v3.5.4 穩定版本）
- 建立 `develop` 分支保存後續開發內容（v3.5.5 ~ v3.6.1）
- 新增版本控制最高原則至 `.github/INSTRUCTIONS.md`

**新增規範**：
- main 分支僅允許 Stable 等級的版本
- 所有新功能開發必須在 develop 或 feature/* 分支進行
- 合併到 main 必須經過完整的跨平台測試

#### 2. Push 防呆機制

**新增功能**：
- `scripts/hooks/pre-push` - Git pre-push hook
- 嘗試 push 到 main 時會顯示警告並要求確認
- 未包含 `[Stable]` 標記的 commit 需要手動確認

**安裝方式**：
```bash
cp scripts/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

#### 3. 文件新增

**新增文件**：
- `doc/guides/upgrade/windows_v3.5.4_upgrade_guide.md` - Windows 升級指南
- `doc/guides/git/branch_management_guide.md` - Git 分支管理指南（Vibe Coder 友善版）
- `doc/architecture/plans/project_restructure_plan.md` - 專案架構重整計劃
- `doc/reports/custom_format_status_report.md` - 自訂格式功能狀態報告

#### 4. 自訂格式功能說明

**現況**：
- 「自訂會議記錄格式」功能在 v3.5.5+ 版本開發
- 目前穩定版 v3.5.4 **不包含**此功能
- 功能完整實現在 develop 分支中
- 待完成跨平台測試後再合併到 main

---

## [v3.5.4] - 2025-12-06

### 🔥 重大改進（Critical Improvements）

#### 1. GPU 滿載時新 Session 無法開啟網頁問題修復

**問題描述**：
- 當 GPU 使用率達到 100% 時，新用戶開啟網頁會一直轉圈圈
- 原因：後端沒有實作請求級別的超時限制，導致等待 GPU 資源時阻塞整個 HTTP 請求
- 影響：所有新用戶無法訪問服務

**修復內容**：

1. **新增請求超時中間件（TimeoutMiddleware）**
   ```python
   # backend/middleware/timeout.py
   class TimeoutMiddleware(BaseHTTPMiddleware):
       - 所有 HTTP 請求加入 30 秒超時限制
       - 超時後返回 503 Service Unavailable
       - 防止長時間阻塞影響其他用戶
   ```

2. **Health Check 支援快速模式**
   ```python
   # backend/api/routes.py
   @router.get("/health")
   async def health_check(quick: bool = False):
       - quick=true: 使用快取資訊，不重新偵測裝置
       - quick=false: 完整健康檢查（預設）
   ```

3. **前端使用快速健康檢查**
   ```javascript
   // frontend/js/app.js
   fetch('/api/health?quick=true')  // 避免阻塞
   ```

**修復後狀態**：
```
✅ GPU 滿載時新用戶可正常開啟網頁
✅ 超時後顯示友善錯誤訊息
✅ 系統保持響應，不會完全阻塞
```

#### 2. 統一版本號管理

**問題描述**：
- 版本號硬編碼在多處（main.py, routes.py）
- 服務版本顯示不一致（v3.5.0 vs v3.5.4）
- 無法自動同步版本號

**修復內容**：

1. **創建 VERSION 檔案（Single Source of Truth）**
   ```
   # VERSION
   3.5.4
   ```

2. **創建版本號管理模組**
   ```python
   # backend/core/version.py
   def get_version() -> str:
       """從 VERSION 檔案讀取版本號"""
       with open('VERSION', 'r') as f:
           return f.read().strip()
   
   __version__ = get_version()
   ```

3. **所有版本號引用統一**
   - `backend/main.py` - 使用 `__version__`
   - `backend/api/routes.py` - 使用 `__version__`

**修復後狀態**：
```
✅ 版本號只需在 VERSION 檔案中定義一次
✅ 所有地方自動同步
✅ 服務重啟後立即生效
```

#### 3. 服務管理指南

**問題描述**：
- 不清楚何時需要重啟服務
- 缺乏服務管理工具

**解決方案**：

1. **創建服務管理腳本**
   ```bash
   # scripts/service_manager.sh
   - 查看服務狀態
   - 啟動/停止/重啟服務
   - 查看日誌
   - 顯示重啟指南
   ```

2. **明確重啟時機**
   | 變更類型 | 是否需要重啟 | 原因 |
   |---------|------------|------|
   | Python 程式碼（.py） | ❌ 否 | `--reload` 自動重載 |
   | 環境變數（.env） | ✅ 是 | 啟動時才讀取 |
   | 配置檔（config.yaml） | ✅ 是 | 啟動時才讀取 |
   | 靜態檔案（frontend/） | ✅ 是 | 需要重新掛載 |
   | 版本號變更（VERSION） | ✅ 是 | 需要重新載入 |
   | 依賴套件更新 | ✅ 是 | 需要重新載入模組 |

**修復後狀態**：
```
✅ 明確的服務管理指南
✅ 一鍵式服務管理工具
✅ 減少人為錯誤
```

### 🔍 跨平台兼容性驗證

#### Windows GPU 支援兼容性分析

**驗證方法**：
1. Git Diff 分析（v3.5.3 -> v3.5.4）
2. 程式碼審查
3. 邏輯推演

**變更檔案清單**：
```
backend/api/websocket.py          ✅ 安全（WebSocket 錯誤處理）
backend/middleware/timeout.py     ✅ 安全（新增超時中間件）
backend/core/version.py           ✅ 安全（版本號管理）
backend/api/routes.py             ✅ 安全（Health Check 優化）
backend/main.py                   ✅ 安全（整合中間件）
frontend/js/app.js                ✅ 安全（快速健康檢查）
VERSION                           ✅ 安全（版本號檔案）
scripts/service_manager.sh        ✅ 安全（服務管理工具）
```

**關鍵程式碼分析**：

1. **Timeout Middleware**
   - 影響範圍：HTTP 請求層
   - GPU 相關：無
   - Windows 兼容：✅ 完全兼容

2. **Health Check 快速模式**
   - 影響範圍：API 端點
   - GPU 相關：僅優化偵測邏輯
   - Windows 兼容：✅ 完全兼容

3. **版本號管理**
   - 影響範圍：元資料
   - GPU 相關：無
   - Windows 兼容：✅ 完全兼容

**Windows GPU 相關程式碼（未修改）**：
```
backend/core/platform_config.py      ❌ 未修改
backend/services/device_detector.py  ❌ 未修改
backend/services/transcription.py    ❌ 未修改
config.yaml                          ❌ 未修改
docker/docker-compose-windows-gpu.yml ❌ 未修改
```

**最終結論**：
```
✅ v3.5.4 完全不影響 Windows 版本的 GPU 支援
✅ 所有變更都在應用層（HTTP 處理、API 端點、版本管理）
✅ 零觸及基礎設施層（裝置偵測、GPU 運算）
✅ Windows 版本可以安全升級
✅ Windows 版本將獲得更穩定的服務響應
```

**證據鏈**：
1. **程式碼層面**：無任何 GPU/CUDA/裝置相關程式碼變更
2. **邏輯層面**：Timeout 和版本管理與 GPU 運算完全獨立
3. **測試層面**：53/53 測試通過，無 GPU 相關測試失敗
4. **Git 層面**：v3.5.3（Windows GPU 修復）與 v3.5.4 完全獨立

### 📝 技術細節

#### TimeoutMiddleware 設計
```python
# 設計原則
1. 優雅降級：請求超時返回友善錯誤，不影響其他請求
2. 非阻塞設計：使用 asyncio.wait_for() 實作超時
3. 可配置性：超時時間可調整（預設 30 秒）

# 實作細節
- 捕獲 asyncio.TimeoutError
- 返回 503 Service Unavailable
- 記錄詳細日誌
- 提供使用者建議
```

#### 版本號管理策略
```python
# Single Source of Truth
VERSION 檔案 -> version.py -> main.py & routes.py

# 優點
- 只需維護一個檔案
- 自動同步所有引用
- 支援 CI/CD 自動化
- 減少人為錯誤
```

### 🔍 驗證步驟

1. **服務版本驗證**
   ```bash
   curl http://127.0.0.1:9527/api/health | grep version
   # 應顯示: "version": "3.5.4"
   ```

2. **超時機制驗證**
   - GPU 滿載時開啟新瀏覽器標籤
   - 應在 30 秒內返回錯誤訊息（而非無限轉圈圈）

3. **快速健康檢查驗證**
   ```bash
   time curl http://127.0.0.1:9527/api/health?quick=true
   # 應在 < 1 秒內返回
   ```

4. **服務管理工具驗證**
   ```bash
   ./scripts/service_manager.sh
   # 應顯示服務管理選單
   ```

---

## [v3.5.4] - 2025-12-06 (舊版記錄)

### 🐛 重大錯誤修復（Critical Bug Fixes）

#### 1. WebSocket Broken Pipe 錯誤修復（Errno 32）

**問題描述**：
- 當客戶端意外斷開 WebSocket 連線時，伺服器端仍嘗試發送資料
- 導致 `[Errno 32] Broken pipe` 錯誤，前端顯示「處理失敗」
- 影響用戶體驗，造成系統不穩定

**診斷結果**：
```python
# 錯誤發生位置
backend/api/websocket.py:
  - send_progress(): 未處理連線中斷異常
  - websocket_endpoint(): 未處理發送失敗情況
```

**修復內容**：

1. **ConnectionManager.send_progress() 錯誤處理強化**
   - 捕獲 `BrokenPipeError`（連線中斷）
   - 捕獲 `ConnectionResetError`（連線重置）
   - 捕獲 `RuntimeError`（WebSocket 已關閉）
   - 自動清理失效連線
   - 新增詳細日誌記錄

2. **websocket_endpoint() 所有發送操作加入錯誤處理**
   - 初始狀態發送
   - 心跳回應（ping/pong）
   - 定期狀態更新
   - 確保連線中斷時優雅退出

3. **新增異常類型日誌**
   - 記錄具體異常類型（`BrokenPipeError`, `ConnectionResetError` 等）
   - 協助診斷連線問題

**修復後狀態**：
```
✅ WebSocket 連線中斷時不再拋出異常
✅ 自動清理失效連線
✅ 服務保持穩定運行
✅ 詳細日誌協助診斷
```

#### 2. 排隊顯示不一致問題修復

**問題描述**：
- 前端狀態欄顯示「排隊: 0」
- 但排隊狀態區塊顯示「您的排隊位置: 1」
- 造成用戶困惑

**根本原因**：
- 任務從隊列取出開始處理時，`total_queued` 立即更新為 0
- 但任務的 `queue_position` 可能仍為 1（或前端未及時更新）
- 前後端狀態同步存在時序問題

**修復內容**：

1. **前端 `handleProgressUpdate()` 邏輯優化**
   - 新增狀態檢查：只有 `status === 'queued'` 且 `queue_position` 存在時才顯示排隊區塊
   - 當任務開始處理（`status !== 'queued'`）時，立即隱藏排隊區塊
   - 避免顯示過時的排隊資訊

2. **後端 `broadcast_queue_update()` 改進**
   - 使用 `get_task_position()` 取得最新排隊位置
   - 確保 WebSocket 推送的資料是最新的
   - 減少前後端狀態不一致的可能性

**修復後狀態**：
```
✅ 排隊人數顯示正確
✅ 排隊位置顯示正確
✅ 任務開始處理時排隊區塊自動隱藏
✅ 前後端狀態同步一致
```

### ✅ 測試（Testing）

#### 新增測試套件：`tests/test_websocket_error_handling.py`

**WebSocket 錯誤處理測試（8 個測試，全部通過）**：
1. `test_broken_pipe_in_send_progress` - 測試 BrokenPipeError 處理
2. `test_connection_reset_in_send_progress` - 測試 ConnectionResetError 處理
3. `test_runtime_error_in_send_progress` - 測試 RuntimeError 處理
4. `test_multiple_connections_partial_failure` - 測試多連線部分失敗
5. `test_websocket_endpoint_broken_pipe_on_initial_send` - 測試初始發送失敗
6. `test_websocket_endpoint_broken_pipe_on_heartbeat` - 測試心跳失敗
7. `test_queue_position_updates_correctly` - 測試排隊位置更新
8. `test_queue_position_none_when_processing` - 測試處理中任務排隊位置

**測試結果**：
```bash
======================== 8 passed, 1 warning in 0.32s =========================
```

**現有測試驗證（全部通過）**：
- `tests/test_api_routes.py::TestUploadEndpoint` - 7 個測試通過
- 確保修復未破壞現有功能

### 📝 技術細節

**WebSocket 連線錯誤處理策略**：
```python
# 統一處理所有連線中斷異常
try:
    await websocket.send_json(message)
except (WebSocketDisconnect, RuntimeError, ConnectionResetError, BrokenPipeError) as e:
    log.debug(f"連線中斷 ({type(e).__name__}): {task_id}")
    # 清理失效連線
    dead_connections.add(websocket)
```

**排隊狀態同步改進**：
```python
# 前端：只在真正排隊時顯示排隊區塊
if (status === 'queued' && message.queue_position) {
    updateQueueDisplay(message.queue_position, totalQueued, message.message);
    return;
}

# 後端：確保推送最新排隊位置
current_position = task_queue.get_task_position(task_id)
message.queue_position = current_position or task.queue_position
```

### 🔍 驗證步驟

1. **WebSocket 錯誤處理驗證**
   - 執行測試：`pytest tests/test_websocket_error_handling.py -v`
   - 模擬客戶端斷線：強制關閉瀏覽器標籤
   - 檢查日誌：應顯示連線中斷訊息而非錯誤堆疊

2. **排隊顯示驗證**
   - 提交任務並觀察排隊狀態
   - 檢查「排隊人數」與「您的排隊位置」一致性
   - 任務開始處理時排隊區塊應立即隱藏

3. **系統穩定性驗證**
   - 執行完整測試套件：`pytest tests/ -v`
   - 啟動服務並進行端到端測試
   - 確認所有功能正常運作

---

## [v3.5.3] - 2025-12-06

### 🐛 重大修復

#### 1. 服務連線異常修復（macOS Native 模式）

**問題描述**：
- Safari 無法連接到服務器 `127.0.0.1:9527`
- 錯誤訊息：「Safari 無法打開網頁」
- 根本原因：Docker 容器 `meetingscribe-app` 已停止但佔用配置，導致 Native 服務無法正常啟動

**診斷結果**：
```bash
# Docker 容器狀態
meetingscribe-app (meetingscribe:mac)
  - 狀態: Exited (0)
  - 埠號綁定: 9527
  - 影響: 阻止 Native 服務啟動

# Native 服務狀態
  - PID 檔案存在但程序已終止
  - 埠號 9527 未被監聽
```

**修復內容**：

1. **安全移除衝突的 Docker 容器**
   - 移除已停止的 `meetingscribe-app` 容器
   - 釋放埠號 9527 綁定
   - **不影響 Windows Docker 版本**

2. **重新啟動 Native 服務**
   - 使用 `start_service.sh` 啟動服務
   - 驗證服務健康狀態
   - 確認 MPS 加速正常運作

3. **新增 Docker 清理腳本** (`scripts/cleanup_docker.sh`)
   - 自動檢測並移除 macOS 的 政府智慧會議紀錄生成系統 Docker 容器
   - 可選擇性移除 Docker 映像檔
   - 包含安全檢查，僅在 macOS 系統執行
   - **完全不影響 Windows 版本**

**修復後狀態**：
```bash
✅ 服務狀態: healthy
✅ 版本: 3.5.2
✅ GPU: Apple MPS (Metal Performance Shaders)
✅ 埠號: 9527 (LISTEN)
✅ LM Studio: 可用
✅ Gemini API: 可用
```

**安全保證**：
- ✅ 僅移除 macOS 本地的 Docker 容器
- ✅ Windows Docker 版本完全不受影響
- ✅ Docker 映像檔保留（可手動清理）
- ✅ 所有配置檔案未變更

## [v3.5.2] - 2025-12-06

### 🐛 重大修復

#### 1. MLX-Whisper 模型路徑與配置檔案修復

**問題描述**：
- macOS 版本轉錄時出現 404 Client Error
- 錯誤訊息：`Repository Not Found for url: https://huggingface.co/api/models/medium/revision/main`
- 根本原因：配置檔案名稱錯誤 + 模型路徑格式不正確 + 後端識別邏輯缺陷

**修復內容**：

1. **配置檔案重新命名** (`config.mac.yaml` → `config.macos.yaml`)
   - 問題：程式碼尋找 `config.macos.yaml`，但實際檔案為 `config.mac.yaml`
   - 修復：將 `config.mac.yaml` 重新命名為 `config.macos.yaml`
   - 影響：平台配置載入邏輯現在能正確合併 macOS 專屬設定

2. **Whisper 配置結構優化** (`config.macos.yaml`)
   - 修改前：`whisper.backend: mlx-whisper` + 缺少 `mlx.model` 配置
   - 修改後：新增完整的 `whisper.mlx` 區塊
   ```yaml
   whisper:
     backend: mlx-whisper
     mlx:
       model: mlx-community/whisper-medium  # 使用本地已安裝模型
       device: mps
       fp16: true
       language: zh
   ```
   - 優先使用本地已安裝的 `mlx-community/whisper-medium` 模型

3. **後端識別邏輯強化** (`backend/services/transcription.py`)
   - 新增後端名稱正規化邏輯：
   ```python
   if 'mlx' in backend.lower():
       self._backend = 'mlx'
   elif 'faster' in backend.lower():
       self._backend = 'faster-whisper'
   ```
   - 解決 `mlx-whisper` vs `mlx` 字串比對不匹配問題

4. **MLX-Whisper API 參數修正**
   - 修復前：將 `language` 作為位置參數傳遞（不正確）
   - 修復後：`language` 作為 `decode_options` 的關鍵字參數傳遞
   - 符合 MLX-Whisper 0.x 版本 API 規範

**測試驗證**：
- ✅ 測試 1: `test_meeting_1.wav` (156KB) - **通過**
- ✅ 測試 2: `test_meeting_2.wav` (156KB) - **通過**
- ✅ 直接 MLX-Whisper 呼叫測試 - **通過**
- ✅ 模型從本地快取載入，無需網路下載

**本地模型檢測結果**：
```bash
~/.cache/huggingface/hub/
├── models--mlx-community--whisper-medium (✅ 使用中)
└── models--mlx-community--whisper-large-v3-turbo (可用)
```

#### 2. MLX-Whisper 404 錯誤修復 (v3.5.1)

**問題描述**：
- macOS 版本啟動時出現 404 Client Error
- 錯誤訊息：`Repository Not Found for url: https://huggingface.co/api/models/medium/revision/main`
- 導致轉錄功能完全無法使用

**根本原因**：
- `config.mac.yaml` 的 Whisper 配置結構不正確
- 程式碼讀取 `whisper.mlx.model`，但配置只有 `whisper.model`
- 導致回退到預設值 `"medium"`（錯誤的模型路徑格式）

**修復內容**：
1. **config.mac.yaml**
   - 重構 Whisper 配置結構，新增 `whisper.mlx` 嵌套區塊
   - 正確設定模型路徑：`mlx-community/whisper-large-v3-turbo`

2. **backend/services/transcription.py**
   - 新增3層配置回退機制：`whisper.mlx.model` → `whisper.model` → 預設值
   - 增加警告日誌，當配置不完整時提示開發者

#### 2. 排隊邏輯顯示異常修復

**問題描述**：
- 顯示「目前排隊人數：0 人」但「您的排隊位置：1」
- 邏輯矛盾：排隊位置為1且不需等待，應該立即開始處理

**根本原因**：
- `backend/services/queue_manager.py` 的 `get_next_task()` 方法
- ✅ 有清除 `queue_position = None`
- ❌ 但未清除 `estimated_wait_seconds`（應設為 0）

**修復內容**：
1. **backend/services/queue_manager.py**
   - 在 `get_next_task()` 中新增 `task.estimated_wait_seconds = 0`
   - 確保任務從佇列取出時，排隊位置和等待時間都被清除

2. **backend/services/task_processor.py**
   - 更新註解，確保與實際狀態一致

#### 3. System Prompt 與健康檢查熱修

- 統一 `DEFAULT_SYSTEM_PROMPT`（config 與 summarizer 共用），補齊 COSTAR-X 標籤、100 字以內限制與完整性約束，消除不一致
- 健康檢查支援同步/非同步檢查結果，避免 mock 物件 await 錯誤並保留自訂 GPU 名稱
- 端到端整合測試補上 `@pytest.mark.asyncio`，確保整組測試可執行

### ✅ 驗證結果

**測試通過率**：100% (245/245 pytest)

#### 端到端測試
- ✅ MLX-Whisper 模型正確載入（404 錯誤已修復）
- ✅ MLX-Whisper 使用 MPS 加速
- ✅ 配置回退機制運作正常

#### 排隊邏輯測試
- ✅ 第一個任務從佇列取出時，`queue_position` 設為 `None`
- ✅ 第一個任務從佇列取出時，`estimated_wait_seconds` 設為 `0`
- ✅ 第二個任務自動晉升到第1位
- ✅ 佇列狀態計算正確（排隊中 vs 處理中）
- ✅ 任務狀態轉換正確（QUEUED → PENDING → COMPLETED）

**測試檔案**：
- `tests/test_end_to_end.py` - 端到端整合測試
- `tests/test_queue_fix.py` - 4個單元測試
- `tests/test_queue_integration.py` - 1個整合測試

**詳細報告**：
- `doc/evidence/mlx_whisper_e2e_test_evidence_v3.5.1.md` - 完整測試證據
- `doc/evidence/queue_logic_fix_evidence_v3.5.1.md` - 排隊邏輯修復證據
- `doc/reports/queue_logic_fix_report_v3.5.1.md` - 詳細修復報告

### 📁 文件組織重構

**重大改進**：重新組織 `doc/` 目錄，建立清晰的分類結構

#### 新增目錄結構
```
doc/
├── evidence/        # 驗證證據 - 測試驗證報告和證據
├── reports/         # 技術報告 - 技術分析和修復報告
├── guides/          # 部署指南 - 部署、操作、使用指南
├── analysis/        # 分析文件 - 系統分析、架構分析
└── README.md        # 文件導航說明
```

#### 檔案命名規範
- **驗證證據**：`{功能}_{類型}_evidence_v{版本}.md`
- **技術報告**：`{功能}_{類型}_report_v{版本}.md`
- **部署指南**：`{平台}_{類型}_guide.md`
- **分析文件**：`{主題}_analysis.md`

#### 文件重新組織
- 重新命名所有文件，使用有意義的英文名稱
- 依類型分類到對應目錄
- 新增 `doc/README.md` 提供文件導航
- 更新 `.github/INSTRUCTIONS.md` 定義文件組織規範

**總計**：
- 重新組織 30+ 個文件
- 建立4個分類目錄
- 統一命名規範

---

## [v3.5.0] - 2025-12-06

### 核心修復 🔧

#### 1. macOS Native 部署支援
- ✅ 移除 Docker 依賴（macOS 上 Docker 不支援 MPS）
- ✅ 改用原生服務模式部署
- ✅ 支援 LM Studio 本地 LLM
- ✅ 支援 MLX-Whisper（MPS 加速）

#### 2. 配置管理優化
- ✅ DATA_DIR 路徑修復：支援環境變數覆蓋
- ✅ 從 `/app/data` → `/Users/hsiaojohnny/dev/convert/data`
- ✅ 支援 native mode 和 Docker mode 自動適配

#### 3. 版本號同步
- ✅ API 版本號：2.2.0 → **3.5.0**
- ✅ 前端版本號：v2.1.0 → **v3.5.0**
- ✅ 後端版本號：2.3.6 → **3.5.0**

#### 4. Ollama 移除
- ✅ 刪除 Ollama 模型（gemma3:27b-it-qat）
- ✅ 終止 Ollama 進程
- ✅ 完全遷移至 LM Studio

#### 5. Python 依賴修復
- ✅ 安裝 python-multipart（Form 資料支援）
- ✅ 修復 transcription.py 重複 finally 區塊
- ✅ 確保所有依賴項可用

### 驗證結果 ✅

```
API 狀態: healthy
版本號: 3.5.0 ✅
GPU: Apple MPS (Metal Performance Shaders) ✅
Ollama: false ✅
LM Studio: 就緒
Gemini: 可用
MPS 加速: true ✅
```

### 部署方式

#### macOS (原生服務)
```bash
export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
/opt/anaconda3/bin/uvicorn backend.main:app --host 0.0.0.0 --port 9527
```

#### 配置檔案
- `config.mac.yaml` - macOS 專用配置
- LLM: LM Studio (gemma-3-27b-it-qat)
- Whisper: MLX-Whisper (MPS 加速)
- GPU: Apple Metal Performance Shaders

### 技術細節

#### GPU 支援
- Apple MPS: ✅ 完全支援
- 自動偵測: ✅ 啟動時自動偵測
- 降級機制: ✅ MPS 不可用時自動切換至 CPU

#### 檔案管理
- 上傳目錄: `data/uploads`
- 輸出目錄: `data/outputs`
- 快取目錄: `data/cache`
- 自動清理: ✅ 每日凌晨 3:00 執行

#### 任務處理
- 最大同時任務: 1
- 佇列大小: 20
- 任務超時: 3600 秒
- 預估時間: 4 分鐘/任務

### 已知限制 ⚠️

1. LM Studio 需手動啟動（不包含在本專案中）
2. 模型需預先載入至 LM Studio
3. 本地模式需要 16GB+ 記憶體

### 後續改進

- [ ] 自動檢測並啟動 LM Studio
- [ ] 支援多模型切換
- [ ] 優化 MPS 記憶體管理
- [ ] 增加 Windows 原生部署支援

---

## [v3.4.6] - 2025-12-05

### 改善
- 優化 system prompt 為 Gemma3 模型
- 更新文件

### 修復
- 修正 Gemini API 金鑰驗證

---

## [v2.3.6] - 2025-12-01

### 新增
- FastAPI 整合
- WebSocket 支援
- 任務排隊系統
- 批次上傳支援

### 改善
- 優化 Whisper 轉錄效能
- 改進 Ollama 整合

---

## [v2.1.0] - 2025-11-20

### 新增
- 完整參數化設計
- 支援環境變數配置
- 多模型支援（Ollama, Gemini）

---

## [v1.0.0] - 2025-11-01

### 初始版本
- 基本 Whisper 轉錄
- Ollama LLM 整合
- CLI 介面

## [v3.5.0-完整版] - 2025-12-06 12:30

### 🎉 macOS Native 部署完整版

#### 核心修復 🔧
- ✅ LM Studio URL 修復：從 `host.docker.internal:1234` → `localhost:1234`
- ✅ Ollama URL 修復：從 `host.docker.internal:11434` → `localhost:11434`
- ✅ 移除所有 Docker 路徑依賴
- ✅ DATA_DIR 環境變數支援

#### 新增配置 📝
- ✅ **config.mac.yaml** - macOS 專屬完整配置檔
  - LLM 設定（本地 + 雲端）
  - Whisper 設定（MLX 優化）
  - GPU 設定（MPS 加速）
  - 檔案管理
  - 服務設定
  - 任務處理
  - 效能調校

#### 新增文件 📚
- ✅ **doc/MACOS_DEPLOYMENT.md** - 完整 macOS 部署指南
  - 系統需求（硬體 + 軟體）
  - 快速開始（6個步驟）
  - 配置說明
  - 常見問題（Q&A）
  - 效能優化
  - 故障排除
  - 與 Windows 版本差異

#### 測試驗證 ✅
```
API 版本號：3.5.0 ✅
GPU：Apple MPS (Metal Performance Shaders) ✅
MPS 加速：可用 ✅
服務狀態：healthy ✅
前端版本號：v3.5.0 ✅
LM Studio URL：localhost:1234 ✅
測試通過率：6/7 (86%) ✅
```

#### 平台隔離保證 🔒
- ✅ macOS 配置：`config.mac.yaml`
- ✅ Windows 配置：`config.yaml`
- ✅ 兩版本完全獨立，互不影響
- ✅ 共享底層邏輯，配置分離

#### 已知問題 ⚠️
- Ollama 進程檢測仍顯示可用（但不影響功能）
- LM Studio 需手動啟動
- 本地模式需 16GB+ 記憶體
