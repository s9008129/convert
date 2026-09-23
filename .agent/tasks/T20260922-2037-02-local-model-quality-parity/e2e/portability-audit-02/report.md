# 跨模型／跨作業系統可移植性稽核（portability-audit-02）

- 稽核日期：2026-09-23（Asia/Taipei）
- 稽核基準：分支 `fix/qwen-local-quality-parity`，HEAD `f374c27`（工作樹除 E3 進行中產物外乾淨）
- 角色：唯讀稽核員。本檔為**唯一新增產物**；未修改任何既有檔、未 `git add`／`commit`
- 待驗主張：①品質優化機制**模型無關**（非只針對 Qwen／Splash）②可移植到 **Windows 11＋Ollama（RTX 4090）**
- 稽核期間 E3（Qwen3.8-27B-Splash）仍在跑（`pgrep` pid 20940 存活）；未觸碰其目錄

**一句話結論**：`[VERIFIED]` 四個品質槓桿（P4-A／B／C／D）在程式碼層**沒有任何以模型名／家族／量化為條件的分支**，且全數掛在 LM Studio 與 Ollama **共用**的 `_summarize_with_local_pipeline`；跨 OS 的兩個硬障礙（tzdata import 崩潰、process group 終止）已於 `a412884` 修掉。**模型無關＋跨 OS 可移植在程式碼結構上成立**；唯二殘留的模型相關程式碼在「Ollama 選模 helper」（非品質槓桿），而「Windows／Ollama 實機行為」仍為 `[UNVERIFIED]`。

## 一、稽核方法（實際執行過的指令）

1. 全套回歸：`DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py`
   → 本次輸出 `1042 passed, 2 skipped in 12.73s`
2. 針對性測試（P4 接線＋取樣同源＋P4-D＋跨 OS runner 測試）：
   `... pytest tests/test_t20260923_p4a_record_coverage.py tests/test_t20260923_p4b_fidelity_wiring.py tests/test_t20260923_p4d_source_tag_diversify.py tests/test_t20260922_regression.py tests/test_owned_e2e_acceptance.py -q`
   → `94 passed in 1.05s`
3. `rg` 靜態掃描（皆含檔名行號，見 §二）：
   - `rg -n -i "qwen|gemma|mlx|gguf|lmstudio-community|splash" backend/services/summarization.py backend/core/fidelity_checks.py backend/core/text_postprocess.py backend/core/config.py`
     → `summarization.py` 19 命中／`config.py` 9 命中；`fidelity_checks.py`、`text_postprocess.py` **0 命中**
   - `rg -n -i 'gemma|qwen' backend/ --glob '!**/*.md'` 再過濾條件式 → 僅 4 處（見 §2.1）
   - `rg -n "os\.fork|SIGKILL|fcntl|import resource|/tmp/|zoneinfo|tzdata|Asia/Taipei|platform\.|sys\.platform"`（四品質檔＋runner）→ 僅 runner 命中
   - `rg -n "pgrep|shasum|\blms\b|shell=True|sys\.platform|os\.name" scripts/e2e/run_owned_e2e.py` → 僅 `os.name` 兩處
   - `rg -n "import fcntl|import resource|os\.fork|signal\.SIGKILL|killpg" backend/` → **0 命中**
4. 唯讀探測：`python3` 讀取 E2 證據 JSON 鍵集合；`pgrep -fl "e2e/run_owned"` 確認 E3 狀態
5. `awk` 逐行取 runner 精確行號（74-95／262-302／1935-1945）

## 二、逐項判定表

| # | 必查項目 | 判定 | 關鍵證據（檔案:行號） | 影響 |
|---|---|---|---|---|
| 1 | 模型無關性（品質槓桿路徑無模型名分支） | **PASS**（附 1 項註記） | `summarization.py:1691,1892,3412,3969,864(text_postprocess)`；模型條件式僅 `summarization.py:4523-4527,4600`（選模 helper，非槓桿） | 機制可套用到任意地端模型；選模 helper 殘留為註記 |
| 2 | 兩引擎共用同一 pipeline、四槓桿兩邊都掛 | **PASS** | 共用入口 `summarization.py:2917`；分派 `2872-2916`（`2891` ollama／`2902` lmstudio）；P4-A `3056,3113`；P4-B `3059,3116`；P4-D `3039,3101`→`text_postprocess.py:1213` | LM Studio 與 Ollama 品質語意同一套 |
| 3 | Ollama 取樣同源（P4-C）＋`context_window_source` 落檔 | **PASS**（落檔 **PARTIAL**） | `3423-3431`（讀同一份 config）、`3513`（payload 展開）、`3973-3976`（LM Studio 同兩欄位）；`context_window_source` 只在 `2938-2950`／`3475-3480` 的 **log** | 同源已證；跨機對帳證據僅存在 backend log（見 §三-2） |
| 4 | Windows 靜態相容 | **PASS**（實機 `[UNVERIFIED]`） | tz fallback `run_owned_e2e.py:74,81-91`；終止分支 `267-300`；`start_new_session=(os.name=="posix")` `1941`；無 shell=True／shasum／pgrep／lms | 靜態無會炸的 POSIX 假設；實機未跑見 §四 |
| 5 | 設定／開關可攜性＋一行回舊行為 | **PASS** | 見 §2.5 表；`config.py:287-318`；`summarization.py:1707-1714,1907,3420-3432`；`text_postprocess.py:864-881` | 與 OS／引擎／模型皆無關；rollback 皆一行且有 golden 測試 |
| 6 | 僅實機可驗邊界 | 已列 `[UNVERIFIED]` | 見 §四 | 不得宣稱 Windows／Ollama 已驗 |

### 2.1 模型相關程式碼「全命中」清單與解讀

**唯一 4 處真正的條件式（都在 Ollama 選模／錯誤訊息 helper，不在品質槓桿內）：**

- `backend/services/summarization.py:4523-4527`：`_select_preferred_model()` 對 `gemma4:31b` 候選加權（`gemma4:31b-it-q4_k_m` +180、`^gemma4:31b(?:-it)?-q4` +120）→ 影響「同名多變體時挑哪個 tag」，屬**選模偏好**。
- `backend/services/summarization.py:4600-4601`：`_build_ollama_pull_command()` 對 `gemma4:` 固定回 `ollama pull gemma4:31b` → 僅**錯誤訊息字串**。

**其餘命中均為非行為性：**

- 註解／實測註記：`summarization.py:1414,1463,3455,3491,3582,3962-3966,4002,4538-4539,4818`；`config.py:244-248`（Qwen model card 建議、Gemma4 實測背景、KV heuristic 說明）。
- 預設值（可一行改，非分支）：`config.py:53-55` `LOCAL_LLM_MODEL` 預設 `gemma4:31b`。
- `LOCAL_LLM_DISABLE_THINKING`（`config.py:333-336`）：說明文字提到 gemma4，但實作**無條件套用所有模型**——Ollama `think:false`（`summarization.py:3495`）與 LM Studio `reasoning_effort:"none"`（`3957-3977`，含 HTTP 400 逐級降級 `3949-3955`）。屬**通用**開關，非模型分支。
- `fidelity_checks.py`（含 `analyze_fidelity` `:863`）與 `text_postprocess.py`：模型關鍵字 **0 命中**；兩檔的 IO 皆 `os.path.join/abspath`＋`open(..., encoding="utf-8")`（`fidelity_checks.py:277-313`），Windows 安全。

### 2.2 兩引擎共用性（四槓桿接線）

- 共用入口：`_summarize_with_local_pipeline` `summarization.py:2917`（`engine = await self._select_local_engine()` `:2925`）。
- 單一生成分派：`_generate_with_local_engine` `:2872-2916`——`engine=="ollama"` `:2891` → `_summarize_with_ollama` `:3434`；`engine=="lmstudio"` `:2902` → `_summarize_with_lmstudio` `:3633`。所有階段（萃取／整併 `2473`／最終 `3028`／補強 `3090`）都經此分派。
- P4-A 逐條對帳：`_validate_record_source_coverage` `:1691`；首輪 `issues +=` `:3056`、補強輪 `:3113`。
- P4-B 忠實度絆索：`_validate_record_fidelity` `:1892`；`:3059`、`:3116`（fail-soft＋`LOCAL_FIDELITY_TRIPWIRES` 開關 `:1907`）。
- P4-C 取樣同源：Ollama `_ollama_sampling_options` `:3412-3432` → payload `**sampling_options` `:3513`；LM Studio `_lmstudio_extra_body` `:3957-3977`；context 來源 `:2938-2950`。
- P4-D 標註去重複化：`text_postprocess._source_tag_diversify_enabled` `:864-881`，消費點 `:1213`；由共用 `_finalize_record_text(mode="local")`（`:3039`、`:3101`）進入，文件明示「與引擎、模型無關」（`:3160-3166`）。
- 雲端路徑不得受污染：`test_雲端路徑不得呼叫覆蓋率與忠實度檢查`（已跑通過）；雲端自身驗證清單在 `:4259-4260`。
- **設計上的引擎不對稱（非槓桿缺掛）**：`allow_reasoning_retry` 僅 LM Studio（`:2887-2889`）；`expand_output_budget` 僅作用 Ollama `num_predict`（`:3650-3656`）；`repeat_penalty` 僅 Ollama 送（Splash 引擎對 penalty 欄位回 HTTP 400，`:3418-3421`、`config.py:314-318`）。

### 2.3 Ollama 取樣同源（已實際執行 payload 級驗證）

- 測試 `tests/test_t20260923_p4a_record_coverage.py:516-550`（`test_P01_ollama取樣參數讀同一份config_payload級`）：monkeypatch `LOCAL_LLM_SAMPLING_TOP_P/TOP_K/REPEAT_PENALTY` → 斷言 `/api/chat` payload `options` 同值；再改值→再斷言跟著改；`None`＝鍵不送；且 `LEGACY_OLLAMA_SAMPLING_OPTIONS == {"top_p":0.95,"top_k":64,"repeat_penalty":1.08}` 保留為一行 rollback。本檔測試已隨 §一-2 的 `94 passed` 通過。
- LM Studio 同源欄位：`top_p`／`top_k` 讀同兩個 config 欄位（`:3973-3976`）；temperature 由共用 pipeline 以同一組 settings 常數傳入（`:2993,3028,3090` 對照 `config.py:259-277`）。
- `context_window_source`：只寫入 backend log（結構化欄位 `:3475-3480`）；`rg -n "context_window_source" scripts/`＝**0**，runner 只解析／驗證 pipeline metrics 的 `logical_generations/semantic_attempts/merge_rounds`（`run_owned_e2e.py:746-790`、`:1617`），`cov_*` 只存在於原始 log 行 → **PARTIAL**（見 §三-2 建議）。

### 2.4 Windows 靜態相容

- `zoneinfo` 硬依賴已移除：`run_owned_e2e.py:74` import；`resolve_taipei_tz` `:81-91`（`ZoneInfoNotFoundError` → 固定 `+08:00`）；測試 `tests/test_owned_e2e_acceptance.py:1282-1327`（A：無 tzdata fallback；B：有 tzdata 維持原路徑）已跑通過。`tzdata` 未列入依賴（`pyproject.toml`／`uv.lock` 0 命中），故此 fallback 是 Windows 的必要條件。
- 程序終止：`terminate_owned_process` `:267-300`——POSIX 走 `os.killpg`＋`SIGTERM→SIGKILL`（`:275-293`），**非 POSIX 走 `proc.terminate()/kill()`（`:296-300`）**；`start_new_session=(os.name == "posix")` `:1941`。
- subprocess 全部 argv-list、無 `shell=True`（`:213,410,863`）；雜湊用 `hashlib`（`:58,396-401`），無 `shasum`；無 `pgrep`／`lms` CLI 依賴（runner 以 HTTP API＋`sys.executable` 驅動）。
- 品質路徑（`summarization.py`／`fidelity_checks.py`／`text_postprocess.py`／`config.py`）：`/tmp/`、`fcntl`、`resource`、`os.fork`、`SIGKILL`、`killpg` **全部 0 命中**；backend 全域亦 0（`rg` 見 §一-3）。
- 唯一的平台感知模組是 `backend/core/platform_config.py`（`platform.system()/machine()`，`:23-25`；非 darwin-arm64 回非 Apple 預設 `:44-56`、`:90-97`），屬**刻意設計**（ASR backend／provider 預設），與品質槓桿無關。

### 2.5 開關可攜性（與 OS／引擎／模型無關）

| 槓桿 | 開關（`backend/core/config.py`） | 預設 | 呼叫點 | 一行回舊行為 | 證據測試 |
|---|---|---|---|---|---|
| P4-A 逐條對帳 | `LOCAL_LLM_RECORD_COVERAGE_MODE`（`:287-292`） | `enforce` | `summarization.py:1707-1714`（`off`＝連 metrics 都不記） | `=off` | `test_T15/T15b`（`:376,394`）golden |
| P4-A 類別子集 | `LOCAL_LLM_RECORD_COVERAGE_CATEGORIES`（`:293-297`） | `topic,decision,number,date` | `_coverage_categories` `:1685-1690` | 改字串 | `test_T17`（`:457`） |
| P4-B 絆索 | `LOCAL_FIDELITY_TRIPWIRES`（`:304-308`） | `True` | `summarization.py:1907-1908` | `=false` | `test_I2`（`fidelity:211,224`）golden |
| P4-C 取樣 | `LOCAL_LLM_SAMPLING_TOP_P/TOP_K/REPEAT_PENALTY`（`:251-257,314-318`） | `0.8/20/1.08` | `:3423-3431`、`:3973-3976` | `LEGACY_OLLAMA_SAMPLING_OPTIONS` 一行（`:219,3420`） | `test_P01`（`:516`） |
| P4-D 標註 | `LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED`（`:309-313`） | `True` | `text_postprocess.py:864-881,1213` | `=false` | `test_規則6_開關關閉_byte級golden`（p4d:252） |

- 全部讀 `backend.core.config.settings`（env／`.env` 驅動）→ 同一個 `settings` 物件在 macOS／Windows 行為一致；未見任何 OS／引擎條件包住開關本身。
- `--quality-mode`（runner `:1790`）是**量測／閘門**旗標（observe 只寫證據不改品質；`off` 不執行儀器 `:1186-1188`），與產品行為開關解耦；產品側品質開關預設全開（`config.py:287,304,309`）。

## 三、反例與漏洞（Top 3）

1. **模型相關殘留（非品質槓桿，但屬「模型無關」主張的例外清單）**
   `summarization.py:4523-4527` 對 `gemma4:31b` 偏好 q4 變體、`:4600-4601` 對 `gemma4:` 硬編 pull 指令。兩者不改任何品質語意，但若要把「機制模型無關」講到 100%，需明確聲明「選模 helper 例外」或將其通用化（例如改為「同家族同尺寸時偏好與設定量化相符的變體」）。
2. **跨機對帳證據未投影進 stored evidence（PARTIAL）**
   `context_window_source`（`:2938-2950,3475-3480`）與 `cov_*`（`_record_coverage_metrics_fields` `:1869-1890`）都只出現在 backend log；runner 只驗 metrics 三鍵（`run_owned_e2e.py:746-790`）。而 backend log 位於 `runtime_dir`（gitignored）。→ 在 Windows／Ollama 上做「同一把尺」對帳時，唯一證據鏈是易失的 log。建議（additive）：runner 把 metrics 行的 `cov_*`／`context_window_source` 收進 `run_summary.json`。
3. **「同一份 config」≠「同一組最終 payload」＋參數面跨引擎不等價（可攜性風險）**
   - Ollama 少 LM Studio 的 top-level `reasoning_effort`（改送 `think` 欄位、模型不支援時 400 降級 `:3491-3495`、測試 `test_P02` `:556`）；LM Studio 不送 `repeat_penalty`（Splash 400）。
   - 品質上限常數為 context 驅動：`LOCAL_LLM_MERGE_VISIBLE_TARGET_TOKENS=900`（歷史下限，`:318-330`）＋輸出預算由 context 推導（`:2975-2990,3013-3025`）；LM Studio 128K instance vs Ollama `num_ctx`（`config.py:198`，預設 8192）會產生不同 chunk／merge 幾何。
   → 槓桿本身模型無關，但**在 Mac/128K 校準出的預設值搬到 Windows/Ollama/8K 後，品質結果不保證等價**；這是目前最實質的跨平台品質風險，需實機 A/B（§四）。

補充（非反例，已如實登錄）：`_select_local_engine` `:2835-2871` 的 auto 順序在非 Mac＝Ollama 優先、Mac＝LM Studio；provider 事後斷言（`run_owned_e2e.py:1352-1370`）已在 E2 場生效。

## 四、只有 Windows／Ollama 實機才能驗的項目（`[UNVERIFIED]`）

1. `[UNVERIFIED]` Ollama 實機對 `top_p`／`top_k`／`repeat_penalty` 的 sampler 行為（payload 已證同源；「真的改變分佈」未證）。
2. `[UNVERIFIED]` Ollama `/api/chat` 對 `think:false` 欄位的接受度與 400 降級實況（payload／降級路徑已測，端點行為未測）。
3. `[UNVERIFIED]` Windows 上 runner 全流程：tz fallback 實際觸發、`terminate_owned_process` 非 POSIX 分支、`start_new_session=False`、`uv`／`git` 前置需求。
4. `[UNVERIFIED]` Windows/Ollama 場的 `context_window_source=settings`（8192）對帳與品質槓桿在 8K context 的實際效果（Mac 為 `lmstudio_instance`／128K）。
5. `[UNVERIFIED]` RTX 4090 上 KV 量化 heuristic 的提示準確度（Windows-only 腳本 `scripts/diagnose_ollama_host.ps1` 已存在，但未在稽核中執行）。

**最小實機驗證步驟（建議）**：Windows 11 機器 → `ollama serve`＋`ollama pull gemma4:31b` → 設 `LOCAL_LLM_PROVIDER=ollama` → 跑 `uv run python scripts/e2e/run_owned_e2e.py --audio <同一支 0903> --template section_meeting --processing-mode local --quality-mode observe --coverage-checklist ...` → 比對 `coverage_all/core` 與 Mac 場（E1/E2/E3）＋確認 log 出現「Ollama 取樣參數（P4-C 同源 config）」與 `context_window_source=settings`。

## 五、結論

`[VERIFIED]` 「品質優化機制模型無關＋跨 OS 可移植」在**程式碼結構**上成立：四槓桿無模型名分支、全掛共用 pipeline；tzdata 與 process-group 兩個 Windows 硬障礙已修並有測試。缺的是**實機證據**（Ollama sampler／Windows runner）與兩項小缺口：模型相關殘留僅存於 Ollama 選模 helper（建議聲明或通用化）、品質對帳欄位未進 stored evidence（建議 runner additive 收鍵）。未發現任何足以推翻「模型無關」主張的直接事實；最實質的殘餘風險是「Mac/128K 校準的參數面在 Windows/8K 是否等價」——只能靠實機 A/B 回答。
