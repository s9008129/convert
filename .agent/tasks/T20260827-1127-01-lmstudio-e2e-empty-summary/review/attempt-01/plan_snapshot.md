# 修復 macOS LM Studio 人工 E2E：空摘要、錯誤切塊與逐字稿重複

## META

- `TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary`
- `PLAN_REVISION: 1`
- `PLAN_STATUS: READY_FOR_REVIEW`
- `DEBUG_STATUS: READY_FOR_IMPLEMENTATION`
- `FIX_TYPE: MIXED`
- `TASK_MODE: NEW_PLAN`
- `TASK_CLASS: CRITICAL`
- `REVIEW_REQUIRED: YES`
- `INDEPENDENT_ACCEPTANCE_REQUIRED: YES`
- `E2E_REQUIRED: YES`
- `ACCEPTANCE_MODE: FOCUSED_REGRESSION + CONTRACT_INTEGRATION + FRESH_CACHE_TRUE_E2E`
- `NEXT_STAGE: 02_PLAN_REVIEW`
- `BRANCH: main`
- `ANCHOR_HEAD: 9368e0419b7f0968be07a04bf45dc288aaa39c6a`
- `WORKING_TREE_AT_PLAN_TIME: CLEAN; main ahead of origin/main by 4 commits`
- `ENVIRONMENT: Apple Silicon; MLX ASR; LM Studio 0.4.21+2; one loaded qwen3.6-35b-a3b-mlx instance`
- `CREATED_AT: 2026-08-27T11:27:42+08:00`

## OWNER_CHECK

### Plain-language owner view

- **主要目標：** 使用者上傳會議音檔後，系統應完成 MLX 語音辨識、以目前唯一載入的 LM Studio LLM 生成正式會議紀錄，並提供可下載的 DOCX。
- **必要項目：** 正確切分任意形狀的長逐字稿、取得非空的最終模型正文、保留動態選模與逐字稿 fallback。
- **最佳努力項目：** LLM 同音／專有名詞校正；它失敗時必須保留原文並繼續，不能重複呼叫數十次後拖垮摘要。
- **可阻擋全流程的條件：** 只有缺少核心必要輸入、無法選出唯一 loaded LLM、上下文預算不可能成立，或 bounded retry 後仍沒有最終正文；原因是此時無法宣稱已生成會議紀錄。
- **最大殘餘風險：** 不同 reasoning 模型的內部 token 消耗無法事前精確預測，必須以有界的 response-aware retry 與真實 E2E 驗證，而非模型 allowlist 或硬編碼特例。

## GOAL_CONTRACT

### PRIMARY_OUTCOME

使用原始會議音檔，經 MLX ASR 與唯一已載入的任意 LM Studio LLM，產生非空、結構完整、可下載的「會議紀錄」DOCX。

### CORE_ACCEPTANCE_SIGNAL

在無逐字稿快取的隔離環境完成真實上傳流程；輸出 DOCX：

- 標題為「會議紀錄」，不含摘要失敗警告；
- 模板要求的必要章節存在且具有實質內容；
- 清理後逐字稿仍可獨立下載；
- 全流程沿用啟動時唯一選出的 LM Studio loaded instance。

### MUST_NOT_BREAK

- 不硬編碼、載入、卸載或切換 LM Studio 模型。
- 保留零／一／多模型與 optional exact override 的既有選模契約。
- 保留 NVIDIA/Ollama、Gemini 與「摘要失敗仍保存逐字稿」的降級路徑。
- 不新增依賴，不變更 task state 或 HTTP response schema。
- 不修改 `/Users/hsiaojohnny/dev/yt_down_txt` 或建立跨 repository 耦合。

### NON_GOALS

- 不重構整套摘要架構。
- 不保證所有 ASR 同音字或專有名詞都能自動修正。
- 不新增模型 allowlist、模型專屬 prompt 分支或 LM Studio lifecycle 管理。
- 不把 health check 升級為會主動執行昂貴生成的全域 readiness gate。

## EXPECTED_VS_OBSERVED

### Expected

上傳 `0818-優規需求確認會議.m4a` 後，MLX ASR 逐字稿應被分成符合預算的 chunks，LM Studio 應產出非空萃取筆記與正式會議紀錄，最後輸出成功 DOCX。

### Observed

- 兩次人工 E2E 都產出「逐字稿（會議紀錄生成失敗）」。
- 失敗文件：`/Users/hsiaojohnny/Downloads/20260827101638_逐字稿(會議紀錄生成失敗).docx`。
- Page 1 明示 `RuntimeError: 摘要生成失敗：結果為空`。
- 文件共 26 頁；版面沒有截斷或重疊，但逐字稿為單一長段，Page 8、15、18、25 可見詞組或單字連續重複數十次。
- 首次完整流程約 2,655 秒；快取逐字稿重跑仍約 1,081 秒並同樣失敗。
- 影響範圍集中在 macOS local pipeline 的長單行 ASR 輸入與會產生 reasoning 的 LM Studio 模型；Gemini 不走此 LM Studio generation path。
- 現有相關 focused tests 為 87 passed，證明目前測試未涵蓋此真實輸入／回應形狀。

## SYMPTOM_SIGNATURE

- 逐字稿長度約 38,190 characters、estimated 33,210 tokens、零換行。
- context plan：`context_window=8192`、`chunk_budget=3112`、`merge_budget=900`。
- 實際 splitter 只產出兩個 chunks，estimated tokens 分別約 33,206 與 33,210；兩者皆遠超 3,112 且近乎整份重複。
- 第一個 extraction LM Studio request 被壓成 `max_tokens=1`，回應正文空白。
- 語意校正分成 98 段，多數呼叫耗時約 38–44 秒且回傳空正文，幾乎沒有任何採納修正。

## SOURCE_OF_TRUTH

- **User goal / acceptance：** 使用者本次人工 E2E 失敗報告，以及已核准的前置 Mac dual-runtime task 對「任意唯一 loaded LLM」與真實 E2E 的明文要求。
- **Observed behavior：** 失敗 DOCX、兩次 task/output/log、現行 API config/health、直接 LM Studio probes。
- **Current implementation：** `backend/services/summarization.py`、`backend/services/correction.py`、`backend/core/text_postprocess.py`、`backend/services/task_processor.py`。
- **Configuration contract：** `backend/core/config.py`、`.env.example`、`config.macos.yaml`、README 與架構 ADR-3。
- **External API contract：** LM Studio OpenAI-compatible API 與 native chat reasoning 官方文件：
  - https://lmstudio.ai/docs/developer/openai-compat
  - https://lmstudio.ai/docs/developer/rest/chat

## SYSTEM_BOUNDARY

`Web upload -> task orchestration -> MLX ASR/cache -> deterministic transcript cleanup -> BEST_EFFORT LLM correction -> local context plan/chunking -> immutable LM Studio model selection -> extraction/merge/final/refinement -> quality validation -> DOCX/TXT persistence`

- **Last known-good boundary：** MLX ASR 成功、逐字稿快取／TXT 保存成功、摘要失敗時 fallback DOCX 成功。
- **First known-bad boundary：** `_split_oversized_line` / `_split_transcript_into_chunks` 產生超預算近重複 chunks。
- **External dependency：** LM Studio 本地服務與已載入模型；服務可達且模型可在較大 completion budget 下產生正文。
- **Retry/fallback：** network transient retries 已有界；reasoning-only completed response 未被辨識；correction 對 provider-level 穩定失敗沒有熔斷；最終 fallback 正確保留逐字稿。

## SEMANTIC_CONTRACT_AUDIT

- `health ready` 只代表 LM Studio 可達且有唯一可選 loaded LLM；不代表每次 generation 已成功。
- generation success 必須有非空 final content；reasoning 不得被當成正式摘要，也不得輸出到文件或 log。
- chunk input budget 是硬性正確性 invariant；overlap 是 best-effort enrichment，不能突破預算。
- LLM correction 是 BEST_EFFORT，不得形成全域 veto，也不得在相同 provider-level 錯誤後繼續放大呼叫。
- DOCX fallback 是必要的 fail-safe，但它不是 PRIMARY_OUTCOME 成功訊號。
- 配置 precedence 是 load-bearing contract：backend 應只讀環境變數／`.env`／Field default；legacy YAML 不得覆蓋執行中各摘要階段的顯式參數。

## DECISION_CONTRIBUTION_MATRIX

| 元素 | 分類 | 缺失／失敗時行為 | 目標貢獻 |
|---|---|---|---|
| 動態唯一模型選擇 | CORE | 明確局部摘要失敗 | 確定本次工作使用哪個既載入模型 |
| 每個 chunk 符合 token budget | CORE | provider 呼叫前 fail loudly | 防止 context overflow、重複萃取與無效輸出額度 |
| 非空 final content | CORE | bounded retry 後穩定失敗 | 會議紀錄成功的最低充分條件 |
| 病態重複迴圈清理 | CORE input normalization | 保守清理；不新增全域 veto | 降低 token 汙染並避免摘要被幻覺重複主導 |
| 段落可讀性、token diagnostics | SUPPORTING | 保留原文字並繼續 | 改善人工檢查與可診斷性 |
| LLM 同音／詞彙校正 | BEST_EFFORT | 熔斷、保留原文、摘要繼續 | 提升專有名詞品質但非摘要前提 |
| 逐字稿 fallback | CORE safety | 必須成功或明確回報 persistence failure | 摘要失敗時避免資料遺失 |

## CONFIRMED_FACTS

- LM Studio inventory 中恰有一個 loaded LLM：`qwen3.6-35b-a3b-mlx`；loaded context length 為 183,296。
- `max_tokens=64` 的最小 OpenAI-compatible probe 回傳 `finish_reason=length`、空 content、非空 reasoning，completion budget 全被 reasoning 使用。
- 同一模型以 `max_tokens=4096` 可回傳非空正文，故不是模型或服務永久不可用。
- `chat_template_kwargs.enable_thinking=false` 與 `/no_think` 對目前模型無效；native `reasoning:"off"` 被模型明確拒絕。
- `_split_oversized_line` 找到多個標點 fragments 後直接回傳，沒有重新切割仍超限的 fragment。
- overlap pruning 在剩一個超大 carry line 時停止，不能恢復 budget invariant。
- `_summarize_with_lmstudio` 以 `max(1, context - prompt - margins)` 靜默壓低輸出，且只讀 `message.content`。
- `_summarize_with_lmstudio` 透過 legacy YAML 覆蓋顯式 temperature/max_tokens，連 merge convergence cap 也被改寫。
- correction 捕捉每段 Exception 後繼續下一段，造成 provider failure amplification。
- 現有 sentence dedup 依賴句尾標點，無法處理「請看影片」「個人專案管理」或單字的無句界重複迴圈。
- 最新 Mac dual-runtime implementation commit 明確沒有宣稱 LM Studio 真實 E2E 已完成；本次是第一次取得 decisive failure evidence。

## UNKNOWNS

- 完整 extraction/final prompts 在修復後對目前 Qwen 模型的實際 reasoning token 消耗與 wall time，必須由 Stage 05 E2E 量測。
- 模型最終紀錄品質是否一次通過既有 quality validation，可能仍需既有 bounded refinement rounds。
- 這些未知不阻擋實作；它們已由 bounded retry、stable failure 與 true E2E 驗收涵蓋。

## HYPOTHESES

| ID | 機制 | Prediction | Probe | 結果 |
|---|---|---|---|---|
| H-1 | loaded model 缺失或選模歧義 | inventory 不會有唯一候選 | live `/api/v1/models` + app config | FALSIFIED |
| H-2 | LM Studio 服務或模型永久無法生成 | 增加 completion budget 仍無正文 | 同模型最小 direct probe | FALSIFIED |
| H-3 | 單行 sparse-punctuation transcript 突破 chunk budget | splitter 產出超過 3,112-token chunks | 對真實逐字稿執行現有 splitter | CONFIRMED |
| H-4 | reasoning 吃完 completion budget | empty content 同時有 length/reasoning usage | direct OpenAI-compatible probe | CONFIRMED |
| H-5 | YAML precedence 改寫各階段呼叫參數 | log 與 create kwargs 均為 0.2/3072 | static trace + runtime logs | CONFIRMED |
| H-6 | 文字清理只處理完整重複句 | 無句界詞組重複會原樣保留 | code inspection + DOCX visual QA | CONFIRMED |

## FALSIFICATION_RESULTS

- 兩次相同失敗排除偶發網路波動為主要根因。
- 唯一模型已選出且較大 budget 可成功，排除 selection/lifecycle 修復需求。
- 現行 `/no_think`、非標準 OpenAI kwargs 與 native reasoning-off 均不能普遍套用目前模型，排除模型專屬關閉 thinking 作為核心修復。
- 87 個既有 focused tests 全過但 production-shaped probe 失敗，確認測試覆蓋缺口而非已有測試所描述的契約。

## ROOT_CAUSE

1. **Primary mechanical defect：** 分塊函式沒有保證每個 fragment/chunk 都符合 token 上限。
2. **Provider contract defect：** 規劃 context 與 provider 實際 context 混用、輸出不足被靜默降為 1 token，且未辨識 reasoning-only exhaustion。
3. **Semantic/design defect：** BEST_EFFORT correction 對系統性 provider failure 放大為數十次呼叫；legacy YAML 又違反 backend 單一設定來源並破壞 caller intent。
4. **Input-quality defect：** 無標點短單元重複迴圈未被確定性清理，污染摘要輸入並放大 token 數。
5. **Coverage defect：** mock tests 只涵蓋短、有換行、直接回正文的輸入／回應，且前次交付未執行真實 LM Studio E2E。

## FIX_TYPE_AND_ENVELOPE

- `FIX_TYPE: MIXED`
- **Allowed components：** shared transcript cleanup/chunking、LM Studio request/response adapter、correction failure containment、stable errors/config docs、focused/contract/E2E tests。
- **Semantic changes requiring Review：** config precedence；generation success/error contract；reasoning retry；BEST_EFFORT correction failure propagation。
- **Global veto rationale：** 只有無法滿足硬性 context invariant 或 bounded retry 後無 final content 才能使摘要失敗；correction、overlap、paragraphization 與 diagnostics 不得 veto。

## DO_NOT_TOUCH

- LM Studio zero/one/multiple/override selection 規則。
- 模型 load/unload/JIT/switch lifecycle。
- task states、fallback DOCX、Gemini contract。
- Ollama/NVIDIA provider 實作；只承接共享 chunk/cleanup regression。
- 無關版本升級、依賴、lockfile、格式化或 repository 外檔案。

## CRITICAL_PATH

1. 建立會在修復前失敗的 production-shaped chunk/reasoning/config/circuit-break regression probes。
2. 恢復 token-budget chunk invariant，provider 呼叫前拒絕不合法 chunk。
3. 修正 LM Studio parameter precedence、context headroom 與 reasoning-aware bounded retry。
4. 熔斷 BEST_EFFORT correction 的 provider-level failure，讓摘要核心路徑優先執行。
5. 執行 focused/contract/full tests，再以隔離 fresh cache 完成真實 Mac E2E 與 DOCX 全頁 QA。

## CHANGE_MAP

### 1. Input normalization and chunk invariants

- 新增 generic consecutive repetition-loop cleanup：
  - 1 字 primitive unit 連續至少 8 次才觸發；
  - 2–20 字 primitive unit 連續至少 4 次才觸發；
  - unit 間只允許空白或輕標點；
  - 保留兩次以避免刪除自然強調；
  - 記錄 collapsed runs/count，不新增特定詞黑名單。
- 對超過 600 字的單行逐字稿，優先依標點、其次空白、最後硬界線插入段落換行；只改 whitespace，不改非空白內容。
- 所有 sentence fragments 都要重新檢查 estimated tokens；超限時以二分搜尋最大合法 prefix，並在至少保留 60% budget 時優先回退到最近標點／空白。
- overlap 持續移除最舊 carry，直到 `carry + next <= budget`；可降為零，不能保留一個超大 carry。
- chunking postcondition：非空、每塊不超 budget、來源順序涵蓋；違反即在 provider I/O 前拋出 stable context error。

### 2. LM Studio generation contract

- 移除 summarization backend 對 `config*.yaml` 中 `llm.lmstudio.temperature/max_tokens` 的讀取。
- caller temperature/output cap 為權威；未傳入時使用 pydantic settings/default。
- context planning 保持保守 `LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`；LM Studio request/retry headroom 使用 selected instance context length，缺失才退回 planning context。
- 新增 optional env contract：`LMSTUDIO_REASONING_RETRY_MAX_TOKENS=8192`。
- 回應解析包括 final content、reasoning presence/count、finish reason、prompt/completion/reasoning token counts；禁止記錄 reasoning text 或 sensitive prompt。
- 初次回應只有在 `content empty + finish_reason=length + reasoning evidence` 時允許一次 semantic retry：
  - 沿用同一 immutable selection、prompt、temperature；
  - `retry_cap = min(provider_headroom, configured_cap, max(initial * 2, observed_reasoning + initial + 256))`；
  - observed reasoning tokens 缺失時以 reasoning text token estimate 代替，但不記錄文字；
  - cap 不能增加或重試後仍空，拋出 `LMSTUDIO_NO_FINAL_CONTENT`。
- 初始 caller budget 不得再被靜默壓成 1；不符合 request budget 時拋出 `LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED`。
- `expand_output_budget=False` 的 merge call 即使 reasoning retry 成功，也將 visible content 限制於 caller cap，維持 merge convergence。
- network transient retry 與 completed reasoning-only retry 分開計數且各自有界。

### 3. BEST_EFFORT correction failure containment

- `generate_local` / internal provider call 增加 `allow_reasoning_retry`，預設 core call 為 `True`；correction 明確傳 `False`。
- correction 遇 `StableServiceError` 時，保留當段及所有剩餘原文、記錄一次 report error 並停止後續 LLM 呼叫。
- candidate-specific empty/gate rejection 可維持逐段局部處理；不得誤升級為 provider circuit-break。

### 4. Contracts and documentation

- stable errors 新增 `LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED` 與 `LMSTUDIO_NO_FINAL_CONTENT`；沿用既有 exception/fallback 管道，不新增 task state。
- `.env.example` 記錄 reasoning retry cap。
- README／架構 ADR-3 移除「LM Studio backend 可由 YAML 覆蓋」的矛盾描述；YAML 僅保留 legacy tooling/reference。
- 將 `LOCAL_LLM_DISABLE_THINKING` 說明限定為 Ollama／provider 支援時的行為；LM Studio 使用 response-aware bounded retry。

## IMPLEMENTATION_WAVES

### WAVE-01 — Fail-first regression

- 加入單行 sparse-punctuation 33k-token shape、reasoning-only response、YAML precedence、correction amplification、repetition loop regression tests。
- 先觀察它們以正確原因失敗；不得先修改 production code 後補測試敘事。

### WAVE-02 — Restore CORE input invariants

- 實作 token-aware fragment splitting、overlap pruning、chunk postcondition。
- 實作保守 repetition-loop collapse；paragraphization 排在核心 invariant 之後，不能成為 gate。
- 跑 chunk/cleanup focused tests。

### WAVE-03 — Restore CORE LM Studio output contract

- 修正 config precedence、provider context headroom、response diagnostics、reasoning retry、stable errors 與 merge cap。
- 跑 LM Studio provider、summarization、task fallback contract tests。

### WAVE-04 — Contain BEST_EFFORT work and synchronize docs

- 實作 correction circuit-break 與 no-reasoning-retry call site。
- 更新 env/README/architecture contract；不變更依賴。
- 跑完整 tests、diff inspection 與 independent E2E handoff prerequisites。

## REGRESSION_AND_ACCEPTANCE

### Focused/unit

- production-shaped transcript 在 budget 3,112 下產生多個合法 chunks；所有 chunks `<= budget`，不再出現兩個近整份重複 chunks。
- CJK、Latin、無空白、稀疏標點與 overlap boundary 都維持順序與涵蓋。
- pathological loops 被壓縮；低於 threshold 的「對對對」等自然重複不變。
- LM Studio caller parameters 分別保留 correction `0.0`、extraction/merge `0.1`、final `0.2` 與 merge cap，不受 legacy YAML 影響。
- reasoning-only 初次回應後恰好一次成功 retry；cap 有界、model selection 不變、reasoning 不外洩。
- retry 後仍空、非 reasoning 空回應、context invariant failure 都回傳正確 stable code。
- correction provider stable failure 最多呼叫一次，後續原文完整保留。

### Integration/contract

- task fallback 包含 stable actionable detail，且逐字稿 TXT/DOCX 仍可取得。
- zero/multiple/wrong override/unreachable LM Studio contracts 維持。
- health selection readiness 不被 generation history 改成全域 veto。
- Ollama/Gemini/shared chunk paths 與現有 task processing regression tests 通過。
- 完整執行 `uv run pytest tests/ -q`；任何 failure 必須分類為 regression、pre-existing、environment 或 test defect。

### Independent true E2E

1. 以 `mktemp` 建立隔離 `DATA_DIR`，在未使用 port 啟動 fresh-cache macOS backend；不刪除既有 cache/output。
2. 確認 LM Studio 只有一個 loaded LLM，記錄 model/instance/context snapshot；不由測試自動修改 inventory。
3. 經實際 Web upload journey 上傳 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a`，選 local mode。
4. 驗證 MLX ASR 確實執行、summary 非空、DOCX 標題為「會議紀錄」、必要欄位／章節有實質內容、逐字稿可下載。
5. 驗證 transcript 不含達 cleanup threshold 的重複 run；log 無 `max_tokens=1`、無 98-call correction amplification、無 Ollama request、無 load/unload/switch。
6. 記錄 full 與 cached wall time；performance gate 是消除已證實的 retry amplification，不虛構固定 SLA。
7. 使用 documents render workflow 將 DOCX 轉成每頁影像，逐頁檢查 clipping、overlap、failure banner、巨型單段與可讀性。

## DEGRADATION_AND_GATE_TESTS

- correction provider failure：只局部降級，保留清理後原文並繼續摘要。
- paragraphization／diagnostics failure：不得阻擋核心摘要；保留既有文字。
- reasoning retry exhausted：摘要子系統明確失敗，但逐字稿 fallback 必須成功。
- zero/multiple loaded LLM：只阻擋 local summary，不使 ASR 或 transcript persistence 無效。
- provider context 未知：使用 conservative planning context；若仍不能容納 caller budget，preflight fail loudly。
- 不以 active generation probe 作為 service startup/global readiness gate。

## MIGRATION_COMPATIBILITY_ROLLBACK

- 無 database/schema/backfill/data migration。
- 新 env key 有 8,192 default，未設定者保持可運行。
- 既有 transcript cache 不需 invalidation；deterministic cleanup 在 cache hit 後執行，可直接修復現有樣本。
- no HTTP schema/task-state changes；stable errors 透過既有 error description/fallback 管道呈現。
- 回滾可移除新 retry/config/error 邏輯；逐字稿 fallback 始終保留，且不需復原資料。

## DEFERRED_OR_BEST_EFFORT

- 不針對個別 Qwen/模型家族建立專屬 thinking disable adapter。
- 不為逐字稿增加 speaker diarization、時間戳版面或語意段落重建。
- 不在本 task 重新校準 ASR decoder；mlx-whisper 0.4.3 不暴露現有 faster-whisper repetition penalty/no-repeat n-gram options，使用 provider-independent deterministic cleanup。
- 不宣稱 NVIDIA hardware E2E；只執行其可用的 regression tests。

## RISKS

- **Reasoning retry latency：** exactly one retry + 8,192 cap + same immutable model；BEST_EFFORT correction 禁用該 retry。
- **Retry amplification：** network 與 semantic retry 分開計數，correction 遇 stable error 熔斷。
- **False-positive repetition cleanup：** 採高 threshold、限定連續 primitive units、保留兩次，並加入自然強調 negative tests。
- **Token estimator approximation：** 不依靠估算敘事；以每個 fragment/chunk 的 postcondition 與 provider preflight 強制 invariant。
- **Config compatibility：** backend 行為回歸已公開的 env-only contract；legacy tooling YAML 保留，不刪檔。
- **Model-specific output quality：** 由 existing quality validation/refinement 與 independent true E2E 驗收，不以模型 allowlist 解決。

## DEFINITION_OF_DONE

- 原始 failure shape 的 fail-first tests 在修復後通過。
- chunk、LM Studio、correction、fallback、跨 provider 與完整 test suite 取得真實結果。
- fresh-cache true E2E 使用原始會議音檔成功生成正式會議紀錄 DOCX。
- 最終 DOCX 完成全頁 render/visual QA，無 failure banner、clipping、overlap、病態重複或巨型單段可讀性問題。
- final diff 僅含核准 envelope，無 hardcoded model、model lifecycle、dependency/lockfile 或無關變更。
- Stage 02 對 revision 1 回傳 `PLAN_APPROVED`；之後才可編譯 Stage 03 handoff。
- Stage 05 independent acceptance 通過前不得宣稱此 E2E root cause 已完成修復。

## HANDOFF_HINTS

- Reviewer 必須先從本檔的 OWNER_CHECK / GOAL_CONTRACT 重建 Goal Baseline，不直接接受 ROOT_CAUSE framing。
- top-down 優先挑戰：reasoning retry 是否必要且有界、correction 是否確實 best-effort、health/generation validity 是否被混淆、repetition cleanup 是否過度。
- bottom-up 優先驗證：chunk hard invariant、YAML precedence、LM Studio response shape、merge convergence、stable error/fallback consumer。
- Review snapshot 必須記錄本 revision 的 SHA-256；任何修改 plan revision 都會使舊 approval 失效。
- Stage 04 發現需要模型 allowlist、改變 selection readiness、變更 task state/fallback 或新增不同 root-cause decision 時，必須停止並進入 Stage 01 escalation replan。

## ARTIFACT_GATE

- `TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary`
- `PLAN_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/plan.md`
- `PLAN_REVISION: 1`
- `DEBUG_STATUS: READY_FOR_IMPLEMENTATION`
- `FIX_TYPE: MIXED`
- `REVIEW_REQUIRED: YES`
- `NEXT_STAGE: 02_PLAN_REVIEW`
