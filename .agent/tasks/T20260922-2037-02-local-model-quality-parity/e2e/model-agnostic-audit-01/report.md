# 模型無關性稽核報告（model-agnostic-audit-01）

- 稽核型態：**唯讀靜態稽核＋純函式驗證**（零 LLM 推論、零網路、不接 LM Studio／Ollama、不修改產品程式碼）
- Repo／分支／HEAD：`/Users/hsiaojohnny/dev/convert`、`fix/qwen-local-quality-parity`、`ce99502`
- 稽核問題：地端品質優化機制是否**與模型無關**，能否套用到所有地端開源模型（macOS＋LM Studio：`qwen3.8-27b-splash`、`gemma-4-31B-it-MLX-4bit`；Windows 11＋RTX 4090＋Ollama）
- 判定用語：
  - `MODEL_AGNOSTIC`＝無「模型名／家族／量化」條件分支；
  - `MODEL_SPECIFIC`＝有上述條件分支；
  - `ENGINE_SPECIFIC`＝只依 provider／engine（`lmstudio`／`ollama`）分流，**不是**模型分支（不影響換模型，只影響換引擎）。

---

## 結論

**`MODEL_AGNOSTIC_WITH_NOTES`**

一句話：**六個品質層全部 `MODEL_AGNOSTIC`**（品質判定路徑零模型名分支）；唯一 `MODEL_SPECIFIC` 的程式集中在「Ollama 選模 helper」，它只決定「挑哪一顆模型」，不參與任何品質判定、不改變任何品質槓桿；另有數條 `ENGINE_SPECIFIC` 與 **config 驅動**的不對稱（§可疑點 S-2～S-6）——真正會讓「Ollama／非 Qwen 模型少拿到部分優化」的是 **context 預算與 provider 欄位支援度**，不是模型名分支。

判定依據（三項可重現證據）：

1. **函式介面掃描（純函式）**：15 個品質層函式（含 `analyze_fidelity`、`clean_transcript`、`gate_correction`、`_validate_record_source_coverage`、`_ollama_sampling_options`、`_lmstudio_extra_body` 等）的 signature **沒有任何參數名含 `model`／`provider`／`engine`** → `NO_MODEL_PARAM`。換句話說：這些槓桿在型別層就拿不到模型身分。
2. **AST 比對掃描**：`backend/**/*.py`（排除 test）中，模型名字串只出現在 9 處，全部是 config 描述字串／docstring／雲端預設值＋Ollama 選模 helper；**除 ASR 解析器（`backend/core/asr_model_resolver.py`，見 S-8）外，零筆「以模型名為條件的比較」**。
3. **純函式實跑**（`DATA_DIR=/tmp/model_agnostic_audit`，無任何模型）：`clean_transcript` 移除 1 行幻覺並套用詞彙表修正 `內機→內稽`；`apply_known_corrections("今天的內機作業報告")` → `內稽`；`analyze_fidelity(record, transcript, None)` 回傳 `metric_version=fidelity-1.0.0` 的完整報告。

---

## 品質層盤點表

### 0. 共用管線（六層的宿主）

- 位置：`backend/services/summarization.py:2995`（`_summarize_with_local_pipeline`）
- 引擎選擇：`summarization.py:2913`（`_select_local_engine`；provider 分流 `:2917`／`:2926`）
- 生成分派：`summarization.py:2950`（`_generate_with_local_engine`；engine 分流 `:2969`＝ollama、`:2980`＝lmstudio）
- 呼叫者：`backend/services/task_processor.py:335`（`summarization_service.summarize(..., mode=task.processing_mode, ...)`）
- 模型判斷：**無**（只有 provider／engine 分流）
- 判定：`MODEL_AGNOSTIC`（ENGINE_SPECIFIC 分流存在，但兩條引擎都走同一條 pipeline 與同一組槓桿）

### 1. 逐字稿清理層（確定性）

- 位置：`backend/core/text_postprocess.py`；入口 `clean_transcript` `text_postprocess.py:231`
- 子步驟：OpenCC 台灣正體 `:52`、幻覺行移除 `:106`、連續句去重 `:121`、重複迴圈折疊 `:159`、公務用字修正 `:201`（內部呼叫詞彙表 `:218-220`）
- 呼叫者：`backend/services/task_processor.py:242`（步驟 2「語意校正」之前）
- 模型判斷：**無**（`_get_s2twp` 只看 OpenCC 套件可用性 `:37`；無模型名／provider 讀取）
- 判定：`MODEL_AGNOSTIC`

### 2. 語意校正層

- 位置：`backend/services/correction.py`；入口 `correct_transcript` `correction.py:306`（class `:228`）
- 觸發判定：`_segment_needs_correction` `correction.py:277`
- 確定性先行：詞彙表 `錯=>對` 修正 `correction.py:338`（註解明言「**模型無關**、零 LLM 成本」`correction.py:335-337`）
- 同音驗證閘門：`gate_correction` `correction.py:156`、`is_homophone_swap` `:109`、保護詞 `_would_destroy_protected_term` `:137`
- 生成解耦：生成函式由呼叫端注入 `correction.py:307-315`；實際注入 `task_processor.py:261-270`（`summarization_service.generate_local` `summarization.py:3311`）→ 校正層與摘要層共用同一條引擎分派
- provider 穩定失敗＝熔斷（BEST_EFFORT，不放大呼叫）`correction.py:363-374`
- 模型判斷：**無**（prompt 為固定常數；溫度讀 config `config.py:275`）
- 判定：`MODEL_AGNOSTIC`（其溫度預設值源自模型實測，見 S-3；但仍是全域套用，非分支）

### 3. 紀錄後處理層

- 位置：`summarization.py:3220`（`_finalize_record_text`）
- 順序（地端）：`finalize_record` `:3260` → `apply_record_term_fixes` `:3274` → `snap_source_tags_to_transcript` `:3275` → `strip_source_tags_from_table_rows` `:3277` → `normalize_unfilled_placeholders` `:3278` → `dedupe_cross_section_items` `:3279`（嚴格最後一步）
- 呼叫點：最終生成後 `:3117`、**每一輪補強都重跑** `:3179`（避免補強把誤辨字寫回來，`:3177-3178` 註解）
- 模型判斷：**無**；唯一分流是 `if mode != "local"` `:3261`（＝處理模式，非模型）
- 相關的標註辨別力（規則 6）：`text_postprocess.py:931`（`_diversify_source_tag_times_impl`）、開關讀取 `:887`、掛進吸附 `:1059`
- 判定：`MODEL_AGNOSTIC`

### 4. 忠實度絆索（P4-B）

- 位置：`backend/core/fidelity_checks.py:881`（`analyze_fidelity`，純函式、無 I/O）
- 接線：`summarization.py:1970`（`_validate_record_fidelity`）→ 併入補強問題清單 `:3137`（首輪）、`:3194`（每輪）
- 三類檢查：A 自創專名 `fidelity_checks.py:436`；B 無依據歸屬 `:502`；C 數字／單位 `:765`、`:828`
- 開關：`config.py:304`（`LOCAL_FIDELITY_TRIPWIRES`）→ 讀取點 `summarization.py:1985`
- 量尺共用同一函式：`scripts/e2e/measure_record_quality.py:271`
- 模型判斷：**無**（`:513` 只是註解引用 Qwen 場次的假陽性統計，不是條件）
- 判定：`MODEL_AGNOSTIC`

### 5. 逐條對帳（P4-A，覆蓋率）

- 位置：`summarization.py:1767`（`_validate_record_source_coverage`）
- 期望集合來源：議題 `:1544`、決議 `:1558`（取萃取筆記）；數字 `:1664`、日期 `:1692`（取逐字稿）
- 比對器：`_find_missing_action_keys` `:1125`（門檻 `:163`）、議題詞級覆蓋 `:1229`（頓號 `:1206`）、數字整串邊界 `:1599`
- 呼叫點：首輪 `:3134`、每輪補強 `:3191`
- 模式：`config.py:287`（`enforce`／`observe`／`off`）；`off` 短路 `summarization.py:1784-1787`；欄位輸出 `:1955-1965`、`:3214`
- 模型判斷：**無**。E1 場（`gemma-4-31B-it-MLX-4bit` 真實筆記）修補的「整行粗體標題＝議題」知識已**通用化**，原始碼註解直接聲明「**不是模型名分支**（任何模型寫出同格式即生效）」`:1436-1446`；契約寫在 `:1485-1491`
- 判定：`MODEL_AGNOSTIC`

### 6. 詞彙表誤辨層

- 位置：`backend/core/glossary.py`；`load_glossary` `:46`、`apply_known_corrections` `:150`、`glossary_prompt_block` `:212`、`build_hotwords_string` `:102`、`english_protected_terms` `:118`、`protected_terms` `:128`
- 呼叫者：校正層 `correction.py:338`／prompt `correction.py:326`；清理層 `text_postprocess.py:218-220`；紀錄術語修正 `text_postprocess.py:572-574`；ASR hotwords `transcription.py:412`、`:452`；模板術語表 `templates.py:732` ← `task_processor.py:271`
- 模型判斷：**無**（資料驅動；本機實跑載入「121 詞、43 條已知誤辨修正」）
- 判定：`MODEL_AGNOSTIC`

### 7. 唯一 `MODEL_SPECIFIC`：Ollama 選模 helper（**不屬品質層**）

- `_select_preferred_model` 的 gemma4 量化偏好 `summarization.py:4601-4605`（`gemma4:31b-it-q4_k_m` +180／`gemma4:31b*-q4*` +120）
- pull 指令特例 `:4678-4679`；docstring 明言「Gemma4 31B 若有 q4 變體則優先採用」`:4620-4624`
- 有效模型名解析（provider 分流）`:4698-4710`
- 影響範圍：**只決定「挑哪顆模型／錯誤訊息」，不參與任何品質判定**（品質槓桿全在 pipeline `:2995` 內，見 §0）
- 判定：`MODEL_SPECIFIC`（可接受；但換模型時的行為差異見 S-1）

---

## 可疑點

### S-1｜Ollama 選模 helper 有 gemma4 專屬偏好（`MODEL_SPECIFIC`，影響選模不影響品質判定）

- 位置：`summarization.py:4601-4605`、`:4678-4679`、`:4620-4624`
- 影響：只有 `gemma4` 家族在「同家族多變體」時會被偏好 q4；**其他家族（含任何新模型）沒有量化偏好**，只靠通用規則（精確名 +1000／正規化名 +700／前綴 +400／同家族 +200／`:latest` −50，`:4591-4598`）。
- 換模型後品質是否會掉：**不會**（品質判定與生成參數與此無關）；風險僅在「挑到 :latest 或非預期量化變體」造成速度／顯存差異，屬可觀測的營運差異。

### S-2｜取樣預設值來自 Qwen model card，但**全域套用**（config 驅動，非模型分支）

- 位置：`config.py:244-250`（註解：官方 Qwen3.6／3.8 非思考建議 `temperature=0.7`、`top_p=0.80`、`top_k=20`）→ 預設值 `config.py:251-258`（`LOCAL_LLM_SAMPLING_TOP_P=0.8`、`LOCAL_LLM_SAMPLING_TOP_K=20`、`EXTRACTION=0.6`、`GENERATION=0.7`、`REFINEMENT=0.7`、`MERGE=0.6`）
- 事實：這組預設值對 `gemma-4-31B-it-MLX-4bit` 與任何 Ollama 模型**一樣生效**（沒有模型分支）——即「換模型仍吃到同一組優化」，但**不是針對新模型重調過的值**。
- 風險判定：`[UNVERIFIED]` 是否對非 Qwen 模型過窄（`top_k=20`）。緩解：`None` 即不送（語意寫在 `config.py:253`、`:257`），可一行 A/B。

### S-3｜溫度預設值源自模型實測，但**全域生效**（非分支）

- `LOCAL_LLM_CORRECTION_TEMPERATURE=0.3` `config.py:275-279`（描述：舊值 0.0 會讓 Splash 引擎走 GREEDY）；`task_processor.py:258-266` 註解引用官方 Qwen model card 與 45 段實測。
- 事實：Ollama 模型同樣吃這個 0.3（沒有分支）；對非 Splash 引擎只是「非 greedy」的一般設定。

### S-4｜引擎不對稱（`ENGINE_SPECIFIC`，兩邊各自有界，不改變判定語意）

- LM Studio 專屬：`allow_reasoning_retry` `summarization.py:2961`、`:2965-2967`（Ollama 路徑忽略）；growth retry `:3875-3900`；`reasoning_effort="none"` `:4050`；400 相容降級 `_downgrade_extra_body` `:4024-4033`。
- Ollama 專屬：`num_predict` 依 context 自動擴大 `:3545-3548`；空回應重試時抬升溫度 `:3588`（`max(temperature, 0.3)`）；`keep_alive` `:3585`（`config.py:319`）；`think=False`＋400 降級 `:3436`、`:3441-3443`。
- 判定：這些是「引擎能力差異的補償」，**與模型名無關**；兩條路徑都保留同樣的 P4-A～D 判定。

### S-5｜Ollama／8K context 會自動退回「只餵筆記」（config 驅動，最實質的品質風險）

- 位置：`summarization.py:2631-2659`（`_resolve_final_generation_message`：context 不夠就退回只餵筆記，並留 `log.warning`）；觸發前提是 `LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION` `config.py:234` 且 context 餘裕不足。
- 逐字稿內文提到「例如 `num_ctx=8192` 的 Ollama」`:3107-3110`；Ollama 的 context 來源＝settings `config.py:198`（LM Studio＝instance `context_length`，`:3016-3028`）。
- 影響：同一顆模型在 8K 引擎上會少掉「筆記＋逐字稿雙輸入」這個覆蓋率槓桿 → **換引擎（不是換模型）品質可能掉**。可調 `LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS` `config.py:198`。

### S-6｜E2E 驗收的 provider 專屬豁免（影響證據強度，不影響紀錄品質）

- 位置：`scripts/e2e/run_owned_e2e.py:192-193`（`PROVIDER_SPECIFIC_REQUIRED_CHECKS = ("model_inventory_unique", "model_snapshot_consistent")`）、排除邏輯 `:2082`
- 影響：非 LM Studio（＝Ollama）場次這兩項**不列入 required** → Ollama 場的「模型歸因唯一性」證據較弱（因為 snapshot 讀的是 LM Studio `/api/v1/models`）。

### S-7｜筆記格式知識若出現第三種寫法，該類別會 no-op（已通用化但仍需人工檢視）

- 位置：`summarization.py:1436-1446`（接受「整行粗體標題」與「`*決議*` 標記」）；空期望集合會 `log.warning` 且 `cov_expected_*=0`（`:1867-1872`、`:1781`）。
- 影響：**不是模型分支**；但新模型若寫出第三種格式，`cov_expected_topic=0` 屬量尺盲區，需人工看 log。

### S-8｜ASR 層仍有模型名比對（本稽核範圍外，但如實登錄）

- 位置：`backend/core/asr_model_resolver.py:144`、`:185-187`（比對 `DEFAULT_BREEZE_ASR_26_MODEL`／`..._MLX_MODEL` 決定 engine chain／revision）
- 影響：屬 ASR 引擎與版本解析，不屬本稽核定義的六個「會議紀錄品質層」。

---

## 取樣參數對照（LM Studio vs Ollama 是否同一份 config）

**答案：是同一份 config。** LM Studio 讀 `_lmstudio_extra_body` `summarization.py:4035`；Ollama 讀 `_ollama_sampling_options` `:3490`；兩者都只用 `settings.*`，無模型名分支。

| 參數 | config 鍵（`backend/core/config.py`） | LM Studio 讀取／送出 | Ollama 讀取／送出 | 備註 |
|---|---|---|---|---|
| temperature（萃取／生成／補強／整併／校正） | `:259`（0.6）／`:263`（0.7）／`:267`（0.7）／`:271`（0.6）／`:275`（0.3） | 由 pipeline 傳入 `summarization.py:3075`／`:3110`／`:3172`；`:3780` log | 同一組呼叫點；payload `:3588`（首呼叫用原值） | 兩引擎同源；Ollama 重試時抬升為 `max(temperature, 0.3)` |
| top_p | `:251`（預設 0.8） | `extra["top_p"]` `:4051-4052` | getattr `:3501`→送出 `:3504-3505` | 同一份；`None`＝不送 |
| top_k | `:255`（預設 20） | `extra["top_k"]` `:4053-4054` | getattr `:3502`→送出 `:3506-3507` | 同一份；`None`＝不送 |
| repeat_penalty | `:314`（預設 1.08） | **不送**（Splash 對 penalty 欄位回 400，`:4044-4046`、`config.py:316-317`） | getattr `:3503`→送出 `:3508-3509` | 唯一「只單邊生效」的取樣鍵（引擎限制，非模型限制） |
| num_ctx | `:198`（預設 8192） | 改用 loaded instance `context_length` `:3016-3028` | `options["num_ctx"]` `:3592`＝settings | Ollama 受 8192 預設約束（S-5） |
| num_predict | `:202`（`LOCAL_LLM_RESERVED_OUTPUT_TOKENS`）、`:228` 註解 | `max_tokens=num_predict` `:2986`；由 `_resolve_local_output_tokens` `:654` 依 context 推導 | `options["num_predict"]` `:3593`；可依 context 擴大 `:3545-3548` | 兩邊皆 context 驅動 |
| keep_alive | `:319` | 不適用 | payload `:3585` | Ollama 專屬 |
| 關閉思考 | `:333`（`LOCAL_LLM_DISABLE_THINKING`） | `reasoning_effort="none"` `:4050` | `think=False` `:3436` | 兩引擎都套同一開關 |

一行 rollback：Ollama 舊寫死值 `LEGACY_OLLAMA_SAMPLING_OPTIONS` `summarization.py:227`（`top_p=0.95`／`top_k=64`／`repeat_penalty=1.08`）。

---

## 未驗證（`[UNVERIFIED]`）

1. `[UNVERIFIED]` **Windows 11＋RTX 4090＋Ollama 實機未跑**：本稽核為純靜態＋純函式，未接任何 Ollama 端點；sampler 對 `top_p`／`top_k`／`repeat_penalty` 的實際分佈影響未證。
2. `[UNVERIFIED]` **`qwen3.8-27b-splash` 以外的模型在 LM Studio 接受 `top_k=20`**：`config.py:257` 描述 Splash 上限 32，但非 Splash 引擎（例：`gemma-4-31B-it-MLX-4bit`）是否吃同一組欄位未實機驗。
3. `[UNVERIFIED]` **非 gemma4 家族在 Ollama 的選模結果**（S-1）：沒有量化偏好時可能選到 `:latest` 變體，未實機驗。
4. `[UNVERIFIED]` **8K context 對雙輸入的實際覆蓋率折損幅度**（S-5）：機制已讀實作（`:2631-2659`），未在 Windows/Ollama 實機量測 `coverage_all`／`coverage_core`。

### 附註（非模型無關性議題）

- 根目錄 `VERSION`＝`4.9.0`、`CHANGELOG.md:3` 標題為 `v4.10.0`：版本標示不一致，建議後續對齊（不影響本稽核判定）。

---

## 附錄：可重現指令（唯讀）

```bash
# 1) 模型名／provider 名稱掃描（人眼覆核）
rg -n -i '\b(qwen|gemma|splash|llama|mistral|phi-?\d|deepseek|yi-)\b' backend -g '*.py' | grep -v -i test
rg -n 'provider\s*==\s*"|== "lmstudio"|== "ollama"' backend -g '*.py'

# 2) AST 掃描：模型名字串＋比較運算式（本次實際執行腳本見 /tmp/agnostic_scan.py）
uv run python /tmp/agnostic_scan.py

# 3) 純函式驗證：函式 signature 無 model/provider 參數＋三支純函式實跑
DATA_DIR=/tmp/model_agnostic_audit uv run python /tmp/model_agnostic_audit/probe.py
```

（本稽核未執行：任何 LLM 推論、任何 LM Studio／Ollama 端點呼叫、pytest 全套。）
