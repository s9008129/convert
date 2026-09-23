# P4 品質槓桿 Provider Parity 稽核：macOS／LM Studio vs Windows 11／Ollama

- 稽核日期：2026-09-23（Asia/Taipei）
- 稽核對象（工作樹，非 commit 快照）：分支 `fix/qwen-local-quality-parity`，HEAD `0054db4`（P4 波 `da37407` ＋ P4-A 假陽性修補 `0054db4`）
- 方式：唯讀（`rg`／`sed -n`／`git status`／讀既有 E2E 產物）；**未修改任何既有檔案、未 commit、未跑任何測試、未動執行中的 E2E 行程**。本報告為本次唯一新增檔案。
- 標記語意：`[VERIFIED]`＝本次唯讀可直接佐證；`[UNVERIFIED]`＝無實機證據。
- 稽核問題：使用者要求「品質優化機制必須模型無關，且 macOS(LM Studio) 與 Windows(Ollama) 都要適用」。本報告逐項驗證 P4 四類槓桿在 `ollama` 模式是否真的會走到，並列出不對稱點。

## 0. 抽象層定位（題目第 1 點）

| 介面 | 位置 | 說明 |
|---|---|---|
| provider 解析 | `backend/core/platform_config.py:46` `resolve_local_llm_provider` | `auto` 在 Apple Silicon → `lmstudio`；Windows/Linux `auto` 維持 `auto`（`platform_config.py:32-45`） |
| 引擎選擇 | `backend/services/summarization.py:2708` `_select_local_engine` | `lmstudio` 直接選（`:2712-2719`）；`ollama` 需 health 通過（`:2721-2727`）；非 Mac `auto`＝Ollama 優先、不可用才 LM Studio（`:2729-2743`） |
| 引擎分派 | `backend/services/summarization.py:2745` `_generate_with_local_engine` | `:2764 if engine == "ollama"` → `_summarize_with_ollama`（`:3307`）；`:2775 if engine == "lmstudio"` → `_summarize_with_lmstudio`（`:3506`）；未知引擎 fail loudly（`:2788`） |
| 共用管線 | `backend/services/summarization.py:2790` `_summarize_with_local_pipeline` | 本地模式（不分 provider）唯一進入點：`summarize_transcript` 於 `:501` 呼叫；Ollama／LM Studio 共用同一份 chunk→萃取→整併→生成→補強＋驗證流程 |
| context 來源登錄 | `summarization.py:2810-2823`（規劃時決定）＋`:3353`（Ollama 引擎層 log 讀回） | LM Studio＝`lmstudio_instance`／Ollama＝`settings` |
| 無 provider 分支的後處理 | `backend/core/text_postprocess.py`（`rg -i "provider|engine|lmstudio|ollama"` 只命中註解 `:166`）／`backend/core/fidelity_checks.py`（`:17` 明言共用本模組） | `[VERIFIED]` |

**核心結論（回答「ollama 模式下是否也會走到」）**：會。P4 槓桿全部掛在 `_summarize_with_local_pipeline`（provider 無關），provider 差異只存在於引擎層（`:2745` 分派後的傳輸、取樣、context 傳遞）。逐項證據見表一。

## 表一：P4 槓桿 × provider 生效矩陣

| P4 槓桿 | LM Studio 生效？ | Ollama 生效？ | 證據（檔案:行） |
|---|---|---|---|
| `LOCAL_LLM_RECORD_COVERAGE_MODE`（off/observe/enforce）逐條對帳 | 是 | 是 | 驗證器實作 `summarization.py:1586`；mode 讀取 `:1602-1606`（off 連 metrics 都不留）；**呼叫點在共用管線**：首輪 `:2929-2931`、每輪補強後 `:2986-2988`；待辦空集合警告同樣讀 mode `:1260-1262`；設定欄位 `config.py:287-292`。管線內無 `if engine==...` 包覆 `[VERIFIED]` |
| `_validate_record_fidelity`／`fidelity_checks.py` 忠實度絆索 | 是 | 是 | 實作 `summarization.py:1765`（開關 `config.py:304-308`、fail-soft lazy import `:1785-1798`）；**呼叫點共用**：`:2932`、`:2989`；檢查器本身 `backend/core/fidelity_checks.py`（無 provider 判斷）`[VERIFIED]` |
| `text_postprocess` 標註吸附（snap_source_tags_to_transcript） | 是 | 是 | 地端收尾順序 `summarization.py:3015` → `:3070` 呼叫吸附；函式 `text_postprocess.py:1036`；引擎無關契約測試 `tests/test_platform_provider_routing.py:199-210`（parametrize `["ollama","lmstudio"]`）`[VERIFIED]` |
| 標註吸附「規則 6」同標籤同時戳去重複化（P4-D） | 是 | 是 | 由吸附內部呼叫：`text_postprocess.py:895` `_diversify_source_tag_times`（cap／位移常數 `:762-768`）；回退開關 `:864-883` 讀 `config.py:309-313`；純字串操作、無檔案 I/O／分支 `[VERIFIED]` |
| 跨節重複抑制 `dedupe_cross_section_items`（P1 波，與 P4-D 同收尾） | 是 | 是 | `summarization.py:3073`（收尾鏈最後一步）；實作 `text_postprocess.py:657`；僅 `general` 模板作用 `:675-676` `[VERIFIED]` |
| P4-C 取樣同源（top_p／top_k） | 是 | 是 | LM Studio：`summarization.py:3846-3849`（`extra_body` 讀 `LOCAL_LLM_SAMPLING_TOP_P/TOP_K`，`:3830`）；Ollama：`:3386` 併入 `options`，來源 `_ollama_sampling_options` `:3285-3303`；None＝不送語意兩邊一致 `[VERIFIED]` |
| P4-C 取樣同源（repeat_penalty） | **否**（設計排除） | 是 | 僅 Ollama 讀 `config.py:314-318` 並送出 `summarization.py:3298,3303-3304`；LM Studio 刻意不送 penalty 類欄位（Splash 引擎回 HTTP 400）：`:3839-3841`；400 降級路徑 `:3903-3910`。舊寫死值只在 rollback 常數 `:199` `[VERIFIED]` |
| P4-C context 預算來源對帳（`_context_window_source`） | 是（log） | 是（log） | 決定於共用管線 `:2810-2823`；Ollama 引擎層輸出 `:3346-3353`（`getattr(self, "_context_window_source", "settings")`）；LM Studio 未回印此欄（`:3574-3584` 只印 context_budget）→ 對帳資訊不對稱（表二 #1）`[VERIFIED]` |
| runner `--quality-mode`（off/observe/required）品質閘門 | 是（僅量測產物） | 是（僅量測產物） | `scripts/e2e/run_owned_e2e.py:1091-1300`（stage 7 以 subprocess 對最終 markdown 量測，與 provider 無關）；provider 拆分豁免測試 `tests/test_t20260923_p4d_runner_quality_gate.py:779-802`。注意：runner **不**設定後端 `LOCAL_LLM_RECORD_COVERAGE_MODE`（全檔 `rg` 無命中）→ `--quality-mode=off` 不會關掉後端 enforce（表二 #13）`[VERIFIED]` |

## 表二：Provider 不對稱點（含嚴重度與最小修法）

| # | 面向 | LM Studio 實際 | Ollama 實際 | 嚴重度 | 最小修法 | 證據 |
|---|---|---|---|---|---|---|
| 1 | context window 預算來源／量級 | 讀「本次 selected loaded instance 的 `context_length`」；實機 E2E 為 **71936** tokens | 永遠讀 settings；Windows compose 預設 **16384**、程式碼預設 **8192** | **MAJOR** | 兩邊都是「同一條管線、不同把尺」：短期文件化＋Windows E2E 對帳；中期讓 Ollama 以 `/api/show` 讀模型上限或把兩側統一由一個 provider-aware resolver 供給 | `summarization.py:2811-2823`（LM 覆蓋、來源標記）；`:3277-3283` `_effective_context_tokens`；`config.py:198-201`（8192 預設）；`docker/docker-compose-windows-gpu.yml:118`（16384）；實測 `attempt-E1-gemma31b-p4/model_snapshot.json`（`context_length: 71936`）`[VERIFIED]` |
| 2 | 切塊／呼叫次數（#1 的下游效應） | 71936 context → chunk 預算 ≈ 66–68k，長會議常 1–2 塊 | 16384 → chunk 預算 ≈ 11–13k；8192 → ≈ 3–4.5k（`max(1200, ctx-3072-overhead)`；overhead 依模板而異） | **MAJOR**（同 #1，合併計為同一根因；此列為其可觀察後果） | 同上；另在 runner 加「兩 provider 呼叫數對帳」觀測欄位（現只有 `chunk_count`／`merge_rounds` metrics，`:2998-3003`） | `summarization.py:565` `chunk_input_budget`；`:2809-2831` 規劃 log；`:2996-3010` pipeline metrics `[VERIFIED]` |
| 3 | `num_ctx` 可控性 | **不可送**：context 由 LM Studio 載入設定決定，程式只能讀 | 顯式送 `num_ctx`（`:3387`），且 warmup 可自動降級 | MINOR（設計使然，但與 #1 疊加） | 文件明載；未來若要求同源，需 LM Studio 端 API 支援或由使用者固定 instance context | Ollama 送值 `:3387`、降級 `:4769-4784`；LM 只做 budget preflight `:3546-3562` `[VERIFIED]` |
| 4 | 逾時／卡死偵測 | 單一 SDK 總逾時 `LOCAL_LLM_REQUEST_TIMEOUT`（1800s），**無閒置偵測**；卡死要等滿 1800s 才進 transient 重試（×2＋backoff） | 串流：idle 120s（`LOCAL_LLM_STREAM_IDLE_TIMEOUT`）＋總時長 asyncio 1800s；idle 逾時可快速重試，總時長逾時不重試直接失敗 | **MAJOR** | 為 LM Studio 加串流或 watchdog（例如改用 stream=True 或對 create 包 asyncio.timeout 分段檢查） | Ollama：`:3146-3151`（connect 10／read 120／write 30／pool 10）、`:3155`、`:3254-3259`（TimeoutError 不重試）；LM Studio：`:414-419`（timeout=1800, `max_retries=0`）、`:3865`＋`:3919-3928`（僅 transient 分類後重試）`[VERIFIED]` |
| 5 | 空回應復原（reasoning-only） | 有界 semantic recovery：growth retry／stop replay 最多 3 次 provider 呼叫 | 只有 2 次「升溫重試」（temperature→max(t,0.3)），無 reasoning 專屬復原 | MINOR | 若 Windows 實測出現 reasoning-only 空回應，再把 LM 的 recovery 抽成共用策略 | LM：`:3603-3616`、`:3619-3800`、上限 `config.py:329-333`＋`:3739`；Ollama：`:3369`、`:3382-3383` `[VERIFIED]` |
| 6 | 停止序列／關思考／keep_alive | `reasoning_effort="none"`（`:3844-3845`，400 降級 `:3903-3910`）；無 stop；無 keep_alive | `think:false`（`:3231`，400 降級 `:3236-3241`）、`stop` 停止標記 `:3389`、`keep_alive` `:3380` | MINOR | 文件化；stop 對 LM Studio OpenAI 端點可評估加 `stop` 參數（需端點支援） | 如上 `[VERIFIED]` |
| 7 | seed（可重現性） | 不送 → 端點預設 | 不送 → 端點預設 | MINOR（OK 語意，但不可重現） | 若要 A/B 可重現，兩邊都加 seed（Ollama options.seed／LM Studio extra_body） | 全 backend `rg -w seed` 無命中（只有註解提及 min_p 等）`[VERIFIED]` |
| 8 | 瞬時重試參數 | `LOCAL_LLM_TRANSIENT_RETRIES`（預設 2）＋線性 backoff 5s | 同左（同源設定） | OK | 維持 | `:3865`／`:3229`；`config.py:363-368` `[VERIFIED]` |
| 9 | 並行度 | 本機生成為序列呼叫（單一 job 逐步 chunk）；無 local semaphore | 同左 | OK | 維持（`MAX_CONCURRENT_TASKS` 預設 1；semaphore 只存在於雲端分段萃取） | `config.py:40`；`summarization.py:4055`（雲端 semaphore，本地無）`[VERIFIED]` |
| 10 | warmup／VRAM 自我修復 | 無（設計：本 app 不 load/unload LM Studio 模型） | 有：offload 偵測→重載→失敗則降級 num_ctx 8192 | MINOR | 文件化；Windows 主機建議已在 `.env.example:102` 提示 KV 量化 | 僅 Ollama 分支 `:4724-4725`、`:4768-4789`；`docker/docker-compose-windows-gpu.yml:233`（主機 KV 量化建議）`[VERIFIED]` |
| 11 | 硬編碼模型名／能力判斷 | 選模無名稱白名單；`LMSTUDIO_MODEL=None` 時要求唯一 loaded LLM，否則 fail loudly（不亂選） | 預設模型 `gemma4:31b`；名稱解析對 `gemma4:31b` 有 q4 變體偏好；pull 建議寫死 `ollama pull gemma4:31b` | MINOR | 新模型不會「走錯分支」（偏好分支僅在 family==gemma4 成立），但預設值／錯誤訊息仍以 gemma4 為中心，建議改讀 `LOCAL_LLM_MODEL` | `config.py:54-55`；`summarization.py:4396-4401`、`:4473-4474`、`:199`；多載入歧義 `:2618-2622`；compose `:87`；`.env.example:45` `[VERIFIED]` |
| 12 | `allow_reasoning_retry`（BEST_EFFORT 呼叫） | 生效（correction 傳 False） | 忽略（維持既有行為） | MINOR | 文件化；若 Ollama 端也出現 thinking 模型空回應，再抽共用 | `summarization.py:2760-2762`；校正呼叫端 `backend/services/task_processor.py:265-270` `[VERIFIED]` |
| 13 | `num_predict` 擴張語意 | caller cap 為權威＋嚴格 preflight（不足即 fail loudly），recovery 才加 cap | 有餘裕自動擴大 `num_predict` 填滿 context（merge 呼叫除外） | MINOR | 保留（兩者失敗語意不同：LM fail loudly、Ollama 接受截斷並交由驗證/補強把關） | LM `:3546-3562`；Ollama `:3339-3343`、`:3245-3252`（done_reason=length 接受＋警告）；merge 呼叫 `:2331-2335` `[VERIFIED]` |
| 14 | runner 品質模式 vs 後端對帳模式 | ——（同一條） | ——（同一條） | MINOR | 文件明載兩者正交；如要 runner 控制後端 mode，需顯式接線 | `run_owned_e2e.py:1091-1300`；全 repo 無 runner→`LOCAL_LLM_RECORD_COVERAGE_MODE` 的環境變數寫入 `[VERIFIED]` |

嚴重度統計：**BLOCKER 0；MAJOR 2 個根因**（#1／#2 同根因、表中 2 列；#4 1 列 → MAJOR 列共 3 列）；其餘 MINOR／OK。

## 表三：測試覆蓋缺口（只描述，未修改、未新增測試）

| # | 缺口 | 現況證據 | 影響 |
|---|---|---|---|
| 1 | 沒有「管線 → `_summarize_with_ollama` → `_post_ollama_chat` → `_stream_ollama_chat_once`」全鏈同一測試跑通的案例 | 三段各自有測試但邊界被 mock：`tests/test_summarization_service.py:568-628`（只測 stream）、`:632-741`（只測 post，stream 被 mock）、`:743-816`（只測 `_summarize_with_ollama`，post 被 mock）；`tests/test_t20260923_p4a_record_coverage.py:516-556`（P-01，payload 級） | Ollama 傳輸層「真函式串接」無回歸網；P4 槓桿在此層之前已生效，但傳輸層回歸會影響兩 OS 共同品質 |
| 2 | P4 管線級測試全部把引擎 stub 成 `lmstudio` | `tests/test_t20260923_p4a_record_coverage.py:629,663`；`tests/test_t20260923_p4b_fidelity_wiring.py:281,314`；`tests/test_t20260922_2037_p3_parity.py:447,486`；`tests/test_wave01_merge_budget_separation.py:128,148,192,281,364` | P4-A/B/D 的「管線整合」只在 LM Studio 名下被驗證；Ollama 僅共用同一段程式碼的結構性保證（`[VERIFIED]` 於碼、`[UNVERIFIED]` 於行為） |
| 3 | 無跨 provider 的 context 規劃等價測試 | 有 LM 的 32768 vs settings 8192（`tests/test_t20260922_regression.py:330-374`）、有 override 縮減（`tests/test_summarization_service.py:818-830`）、有 8192 假設（`:158-173`）；但無「同一逐字稿 × 兩 provider → chunk 數／merge 輪數／呼叫數」對照 | 表二 #1/#2 的品質效應（切塊密度不同）無自動量測；只有 log／metrics 可事後觀察 |
| 4 | 無 Ollama 真實音檔 E2E 證據 | `.agent/tasks/.../e2e/attempt-*/provider_info.json` 只有 E1／E2 兩筆，兩筆都是 `effective_local_llm_provider: "lmstudio"`；E1 的 `run_summary` quality mode＝`observe`；其餘 attempts 無 provider_info | 「Windows＋Ollama 品質等同 macOS」目前不可證 `[UNVERIFIED]`；P4 的 enforce 預設在 Ollama 實機的效果、`repeat_penalty=1.08` 的實際解碼效應皆未量測 |
| 5 | 沒有 Windows 執行環境／CI 攔截 | `.github/` 只有 `copilot-instructions.md`、`instructions.md`（無 workflows） | Windows 專屬問題（如跨 OS 稽核已記錄的 tzdata）不會在 CI 現形；P4 runner 的 provider 分割測試只在執行機跑（`tests/test_t20260923_p4d_runner_quality_gate.py:779-802`） |
| 6 | `repeat_penalty 永不進 LM Studio payload` 無契約測試 | LM 的 `_lmstudio_extra_body`（`:3830-3850`）只被測 `reasoning_effort`／`top_p`／`top_k`（`tests/test_t20260922_regression.py:223-266,249-265,308-329`）；沒有「penalty 鍵不存在」的斷言 | 若未來有人在 `_lmstudio_extra_body` 加 penalty 類欄位，無測試攔 Splash 400 |
| 7 | `_context_window_source` 標籤內容無測試 | 只有 log／`getattr`（`summarization.py:2823,3353`），無斷言；`generate_local`（`:3106-3128`）路徑未設 `_context_window_source`，log 會回退 `"settings"` | 對帳欄位可能誤導（correction 呼叫顯示 settings 即使實際 provider 是 LM Studio） |

## 結論

**1) 模型無關性（架構層）：信心＝高（HIGH）`[VERIFIED]`**
- 四類 P4 槓桿（覆蓋率對帳、忠實度絆索、標註吸附＋規則 6 去重複化、取樣/context 同源）都掛在 provider 無關的位置：驗證器在 `_summarize_with_local_pipeline`（`summarization.py:2929-2932`、`:2986-2989`），後處理鏈在 `_finalize_record_text(mode="local")`（`:3015`、`:3070-3073`），引擎分派只在 `:2764/:2775`。
- `text_postprocess.py`／`fidelity_checks.py` 無 provider／平台分支（`rg` 證據見 §0），且有「無平台分支」「引擎無關」契約測試（`tests/test_platform_provider_routing.py:180-210`）。
- 因此**不是**只對特定模型或特定 provider 生效；LM Studio 與 Ollama 兩條路徑都會走到。

**2) 兩 provider「實際生效」程度：信心＝中（MEDIUM）**
- Ollama 側「會走到」是碼級事實（同上）；但「以同一把尺生效」只成立於管線／驗證層，**不**成立於預算與解碼層：
  - context 預算：LM Studio 讀 instance（實測 71936）vs Ollama settings（Windows compose 16384／碼預設 8192）→ 切塊密度、merge 輪數、呼叫數不同（表二 #1/#2）。
  - 取樣：top_p／top_k 同源；`repeat_penalty` 只有 Ollama（LM 端點 400，刻意排除）（表一第 6／7 列）。
  - 逾時偵測：Ollama 有 idle 120s 快速偵測；LM Studio 只能等 1800s 總逾時（表二 #4）。
- 尚無任何 Ollama 實機品質數據可證明「同音檔、同設定」下兩 provider 產出同級。

**3) 雙 OS（macOS LM Studio／Windows Ollama）支援：信心＝低（LOW，就「品質等同」而言）**
- 支援性（能跑）先前跨 OS 稽核為「中」；但本稽核的主張是品質槓桿的**效力等同**：目前 repo 內所有真實 E2E 證據都是 macOS LM Studio（`attempt-E1`／`E2` provider_info 皆 lmstudio；model_snapshot context 71936），Windows 側 context 只有 16384，且無 Windows 執行／CI 攔截。
- 要提升到「中／高」，最小代價依序為：(a) 在 Windows/Ollama 跑一次同音檔 E2E（含 `cov_*` metrics 與 record quality）；(b) 以 `LOCAL_LLM_RECORD_COVERAGE_MODE=observe`＋同尺模板留基線；(c) 量測 chunk 數／merge 輪數／呼叫數與品質指標是否隨 context 16384 退化。

**不確定項（`[UNVERIFIED]`）**
1. `[UNVERIFIED]` Windows＋Ollama 實機上 P4-A/B/D 的實際輸出效果與品質數字（無實機證據）。
2. `[UNVERIFIED]` `LOCAL_LLM_SAMPLING_REPEAT_PENALTY=1.08` 對 Ollama 解碼品質的實際影響（無 A/B）。
3. `[UNVERIFIED]` context 16384 與 71936 的切塊差，對 `coverage_core/all`、發言標註比率等 P4 量尺的量化影響。
4. `[UNVERIFIED]` LM Studio 端 400 降級路徑（`top_p/top_k` 被拒後全丟）在非 Qwen／非 Splash 模型上的實際觸發率（程式有降級、無實測分布）。
5. `[UNVERIFIED]` Ollama warmup 降級（8192）在 Windows/4090（16384 設定）的觸發率；降級後與 LM Studio 的差距會擴大（未量測）。
