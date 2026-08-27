# LM Studio E2E 空摘要根因修復 — Escalation Replan

## META

- `TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary`
- `PLAN_REVISION: 2`
- `PLAN_STATUS: READY_FOR_REVIEW`
- `DEBUG_STATUS: READY_FOR_IMPLEMENTATION`
- `FIX_TYPE: MIXED`
- `TASK_MODE: ESCALATION_REPLAN`
- `TASK_CLASS: CRITICAL`
- `REVIEW_REQUIRED: YES`
- `INDEPENDENT_ACCEPTANCE_REQUIRED: YES`
- `E2E_REQUIRED: YES`
- `ACCEPTANCE_MODE: FAIL_FIRST_REGRESSION + CONTRACT_INTEGRATION + OWNED_PROCESS_FRESH_CACHE_TRUE_E2E + DOCX_FULL_PAGE_QA`
- `NEXT_STAGE: 02_PLAN_REVIEW`
- `BRANCH: main`
- `ANCHOR_HEAD: 96e6e7416a0791b674b0ef5f17f8ba34355ef5c5`
- `WORKING_TREE_AT_REPLAN_TIME: CLEAN; main ahead of origin/main by 8 commits`
- `ENVIRONMENT: Apple Silicon; MLX ASR; LM Studio; one loaded qwen3.6-35b-a3b-mlx instance`
- `CREATED_AT: 2026-08-27T11:27:42+08:00`
- `REVISED_AT: 2026-08-27T14:27:37+08:00`
- `SUPERSEDES: PLAN_REVISION 1`
- `STALE_ARTIFACTS: review/attempt-01 approval and current handoff.md apply only to revision 1 and MUST NOT authorize implementation`

## OWNER_CHECK

### Plain-language owner view

- **主要目標：** 使用者上傳原始會議音檔後，系統必須完成 MLX 語音辨識、使用啟動時唯一選定的 LM Studio LLM 生成正式會議紀錄，並提供可下載、可閱讀且內容完整的 DOCX。
- **必要項目：** CORE generation 必須取得非空正文；merge 不得讓 reasoning 吃完輸出預算；決議、待辦與尾端內容不得被無聲截斷；所有恢復流程必須有明確上限。
- **輔助項目：** 降低 chunk overlap 造成的呼叫放大，讓 health/startup log 可證明 E2E 跑的是哪一版程式及哪個端口。
- **最佳努力項目：** LLM 同音／專有名詞校正與 overlap enrichment；失敗時保留原文字並繼續，不能阻擋摘要主流程。
- **可阻擋全流程的條件：** 無法選出唯一 loaded LLM、context 預算不可能成立、CORE generation 的 bounded recovery 耗盡、或 merge 無法在不丟資料的前提下收斂。這些情況若繼續輸出會產生空白或不完整會議紀錄，因此必須 fail loudly。
- **最大殘餘風險：** reasoning 模型可能隨機回傳空 content；以最多三次的 response-aware recovery、禁止 hard truncation、production-shaped tests 與 owned-process true E2E 控制。

## GOAL_CONTRACT

### PRIMARY_OUTCOME

使用 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a`，經 fresh-cache MLX ASR 與唯一已載入的 LM Studio LLM，產生非空、結構完整、保留尾端決議／待辦且可下載的「會議紀錄」DOCX。

### CORE_ACCEPTANCE_SIGNAL

- E2E backend 由驗收流程自行啟動、擁有及終止，health revision 必須等於待驗收 Git HEAD。
- DOCX 標題為「會議紀錄」，不含摘要失敗警告、traceback 或 fallback title。
- 現有 formatter/parser 定義的必要章節存在且具有實質內容。
- 尾端決議／待辦抽查資訊仍存在，沒有 merge hard truncation。
- 清理後逐字稿可獨立下載，明顯病態連續重複已被保守清除。
- 全流程沿用啟動時唯一選出的 immutable LM Studio model/instance。

### MUST_NOT_BREAK

- 不硬編碼、載入、卸載或切換 LM Studio 模型。
- 保留零／一／多模型與 optional exact override 的既有選模契約。
- 保留 Ollama、Gemini、task state 與「摘要失敗仍保存逐字稿」的降級路徑。
- 不新增第三方依賴、database/schema/backfill 或跨 repository 耦合。
- health response 僅允許新增向後相容的 nullable `build_revision`；其他 HTTP contract 不變。
- correction、overlap、paragraphization、diagnostics 與 build metadata 缺失不得升級成全域 veto。

### NON_GOALS

- 不重構整套摘要架構或引入新的 orchestration framework。
- 不重新校準 ASR decoder，不保證所有同音字或專有名詞都能自動修正。
- 不新增模型 allowlist、模型專屬 prompt 分支或 LM Studio lifecycle 管理。
- 不把昂貴 generation probe 加入一般 startup/global readiness。
- 不以更換目前 loaded model 作為本次根因修復。

## ACCEPTANCE_FAILURE_TRIGGER

Revision 1 已完成實作並由 commit `96e6e7416a0791b674b0ef5f17f8ba34355ef5c5` 宣稱 focused/full tests 通過，但後續人工與 fresh-process true E2E 仍失敗。新證據推翻「一次 reasoning retry 足以恢復」與「merge 將 provider `max_tokens` 壓到 visible target 仍可成功」兩個 load-bearing 前提，因此依 semantic-contract 規則進入同一 `TASK_ID` 的 escalation replan，而不是 bounded implementation fix。

## EXPECTED_VS_OBSERVED

### Expected

原始音檔經 fresh ASR、cleanup、BEST_EFFORT correction、19 個合法 extraction chunks、hierarchical merge 與 final generation 後，應輸出正式會議紀錄，並保留來源後段的重要資訊。

### Observed — user manual E2E

- 使用者產物：`/Users/hsiaojohnny/Downloads/20260827133508_逐字稿(會議紀錄生成失敗).docx`。
- Page 1 顯示「逐字稿（會議紀錄生成失敗）」與 `RuntimeError: 摘要生成失敗：結果為空`。
- 文件共 26 頁；全頁 render 顯示版面沒有 clipping、overlap 或缺字，但語意產物只是 fallback transcript。
- 逐字稿仍可見「個人專案管理」、「應該是右邊」、單字與「請看影片」等病態連續重複，證明該次請求沒有執行目前 cleanup 實作。
- `logs/e2e_app.log` 對應服務於 09:26 啟動，早於 12:28 的修復 commit；13:35 人工上傳命中了 stale pre-fix process。runtime stack line numbers亦與目前程式不一致。

### Observed — isolated current-code E2E

- Fresh process 於 12:30 啟動，使用 commit `96e6e74` 之後的程式與隔離 `DATA_DIR=/Users/hsiaojohnny/dev/e2e-t20260827/data`。
- Task `8fd56c54`：extraction 最後一段初次回應為 `length + reasoning + empty content`；提高到 `max_tokens=6522` 後第二次回應為 `stop + reasoning_chars=828 + content_chars=0`，現行 exactly-one retry 隨即失敗為 `LMSTUDIO_NO_FINAL_CONTENT`。
- Task `90fdb193`：19 個 extraction chunks 均完成；merge 呼叫卻使用 `max_tokens=900` 且 `allow_reasoning_retry=False`，回應 `finish_reason=length, completion_tokens=899, reasoning_chars=2778, content_chars=0`，再次失敗為 `LMSTUDIO_NO_FINAL_CONTENT`。
- Fresh transcript 為 36,925 characters、estimated 32,264 tokens；19 個 chunks 範圍 2,519–3,111，皆符合 3,112 budget，證明 Revision 1 的核心 chunk invariant 已修復，不應重做。
- Fresh cleanup 將 38,190 characters 降為 37,009，collapsed 7 pathological loops；Revision 2 應保留並鎖定此修復。
- 完整 suite 為 `495 passed, 3 skipped`，但沒有覆蓋上述 production-shaped merge/retry 行為，不能視為 E2E 成功證據。

## SYSTEM_BOUNDARY

`Web upload -> task orchestration -> MLX ASR/cache -> deterministic transcript cleanup -> BEST_EFFORT LLM correction -> local context plan/chunking -> immutable LM Studio selection -> extraction -> hierarchical merge -> final/refinement -> quality validation -> DOCX/TXT persistence`

- **Last known-good boundary：** fresh ASR、cache/TXT persistence、cleanup、19 個合法 chunks 與大部分 extraction generations。
- **First current-code known-bad boundaries：** extraction reasoning retry 後仍 `stop + empty content`；merge 將 visible target 誤用為 provider completion cap 且禁用 recovery。
- **External dependency：** LM Studio 本地服務與已載入模型。模型已多次在充足 completion budget 下產生正文，故不是永久不可用或 selection/lifecycle 問題。
- **Fallback：** 摘要失敗仍保存逐字稿的安全路徑有效，但 fallback DOCX 不是 PRIMARY_OUTCOME 成功訊號。

## CONFIRMED_ROOT_CAUSE

### RC-1 — Merge budget semantic conflation

`LocalContextPlan.notes_merge_budget_tokens` 同時承擔三個不同目的：來源 notes 分組大小、合併後 visible notes 目標，以及 provider completion `max_tokens`。對 reasoning model 而言，`max_tokens` 包含 hidden reasoning；900 tokens 全被 reasoning 消耗時不可能留下 final content。

現行關鍵機制：

```python
reasoning_retry_allowed = allow_reasoning_retry and expand_output_budget
```

而 `_merge_notes_until_fit` 又以 `expand_output_budget=False` 呼叫 generation，因此明確禁止 merge recovery。這也違反 Revision 1 計畫對「visible content 仍受限，但 reasoning retry 應可成功」的語意承諾。

### RC-2 — Recovery state machine does not cover empty stop response

現行只允許 `length + reasoning + empty content` 後增加一次 budget。實際模型可能在該次 retry 以 `finish_reason=stop` 結束 reasoning、仍不提供 content。這不是 context exhaustion，也不是 network transient；需要一次同 model/instance/prompt/temperature、同目前 token cap 的最終 replay，且總呼叫數必須有界。

### RC-3 — Silent tail truncation violates meeting-record correctness

merge 達輪數上限或收斂不足時會呼叫 `_truncate_to_token_budget`，尾端內容被直接省略。後續 validator 只比較已截斷 notes，無法偵測消失的決議／待辦。即使先修復空 content，這條路徑仍可能輸出看似成功但資料不完整的 DOCX。

### RC-4 — Planner/chunker overlap model mismatch amplifies stochastic calls

context planner 以 220-token overlap 估算 chunk step，但 assembler 可保留最多半個 chunk 的 carry。真實 clean transcript 因此產生 19 個 chunks，高於粗估約 12 個，增加模型呼叫、wall time 與隨機空回應機率。這是 SUPPORTING 性能／可靠性缺陷，不得阻擋 CORE path。

### RC-5 — Runtime provenance cannot distinguish stale and current services

health 只回 semantic version `4.7.2`，兩個不同 commit 的 process 無法區分；startup log 又固定印出 9527，即使 uvicorn 實際監聽 9631。人工 E2E 因而能在不知情下命中 stale process。

## FALSIFIED_ALTERNATIVES

- **不是 chunk budget 再次失效：** current-code 19 個 chunks 全部 `<= 3,112`。
- **不是 cleanup 未實作：** current-code static/fresh probe collapsed 7 loops；使用者 DOCX 命中的是 stale process。
- **不是模型或 LM Studio 永久不可用：** 多數 extraction calls 以及多次 reasoning growth retry 已取得正文。
- **不是 network transient 主因：** decisive responses 均為 completed HTTP responses，帶明確 finish reason 與 usage。
- **不是換模型／disable thinking 可普遍解決：** Revision 1 已確認目前模型不支援可靠的 thinking-off contract；本計畫維持 provider-agnostic recovery。
- **不是既有 unit tests 足以證明成功：** 495 tests 通過後仍有兩個 current-code true E2E failures。

## SEMANTIC_CONTRACT_AUDIT

- generation success 必須有非空 final content；reasoning 不得當作正式摘要或寫入 DOCX/log。
- provider total completion budget 與 orchestration visible-output target 是不同契約，不能共用一個 token 欄位。
- merge 必須保留全部來源事實並確定性收斂；不能以 hard truncation 偽造成功。
- semantic retry、network retry、merge rounds 必須分開計數且各自有界。
- correction 是 BEST_EFFORT；CORE extraction/merge/final 才能啟用 reasoning recovery。
- health revision 是 E2E freshness gate，但 unknown revision 不得使一般產品 startup/global health 失敗。
- fallback transcript 是必要安全機制，不得被 acceptance 誤判為正式會議紀錄成功。

## DECISION_CONTRIBUTION_MATRIX

| 元素 | 分類 | 缺失／失敗時行為 | 目標貢獻 |
|---|---|---|---|
| 唯一 immutable model selection | CORE | 明確摘要失敗 | 確保全流程使用同一既載入模型 |
| Provider completion 與 visible target 分離 | CORE | preflight stable failure | 防止 hidden reasoning 吃完正文預算 |
| Bounded empty-content recovery | CORE | 耗盡後 `LMSTUDIO_NO_FINAL_CONTENT` | 吸收已觀察的隨機 reasoning-only 回應 |
| Merge 全量收斂、禁止截斷 | CORE | `LOCAL_LLM_MERGE_NOT_CONVERGED` | 防止決議／待辦無聲遺失 |
| Transcript cleanup/chunk invariant | CORE input | 保留 Revision 1 行為與 regressions | 控制輸入品質與 context 安全 |
| 220-token overlap cap | SUPPORTING | overlap 可降為零 | 降低 call amplification |
| Build revision/actual port | SUPPORTING | 一般執行允許 unknown | 避免 E2E 命中 stale process |
| LLM correction | BEST_EFFORT | 熔斷並保留原文 | 提升文字品質但不阻擋會議紀錄 |
| Transcript fallback | CORE safety | persistence failure 才全域失敗 | 摘要失敗時避免來源資料遺失 |

## CRITICAL_PATH

1. 先建立能重現兩個 current-code failure shapes 與 silent truncation 的 fail-first tests。
2. 分離 merge input、visible target、provider completion 三種 token 語意，恢復 reasoning-aware merge generation。
3. 擴充有界 recovery state machine，涵蓋 growth retry 後 `stop + reasoning + empty content`。
4. 移除 CORE hard truncation，改用有進度證明的 hierarchical compaction 與 stable non-convergence error。
5. 對齊 220-token overlap 實作與規劃假設，新增 bounded-call diagnostics。
6. 新增 revision/port provenance，執行 owned-process fresh-cache true E2E 與 DOCX 全頁 QA。
7. Stage 05 通過後才把本機 9527 切換到已核准 HEAD。

## CHANGE_MAP

### 1. Separate local merge budgets — CORE

將 internal `LocalContextPlan` 的單一 merge 欄位拆為：

- `merge_input_budget_tokens`：一個 merge group 可攜帶的來源 notes 上限；由 selected context window 減去 merge prompt overhead 與初始 provider completion reserve 後計算。
- `merge_visible_target_tokens`：合併後 notes 必須收斂到的可見 token 目標；保留目前約 900 tokens 的 final-stage fit 目的。
- `merge_provider_output_tokens`：LM Studio 初始總 completion cap；使用現有 `LOCAL_LLM_RESERVED_OUTPUT_TOKENS`（目前約 3,072），可依既有 provider headroom/retry cap 公式有限增加。

具體行為：

- `_group_texts_by_budget` 只使用 `merge_input_budget_tokens`，不得再以 900-token visible target 分組。
- Preflight 必須確認 context 能同時容納 merge prompt、至少兩份目標大小 notes 與 provider completion reserve；否則拋 `LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED`。
- Merge prompt 明示 `merge_visible_target_tokens`；provider `max_tokens` 使用 `merge_provider_output_tokens`。
- 回應超過 visible target 時，把它當作下一輪待壓縮 note，不以字串截斷修正。
- 一份 oversized note 允許單獨 compaction；多份 notes 優先依來源順序分組。
- 每輪必須減少 note 數或 estimated total visible tokens；保持原有 max rounds 作硬上限。
- 達輪數上限、模型持續超標或無實質進度時拋 `LOCAL_LLM_MERGE_NOT_CONVERGED`，進入既有明示 transcript fallback。
- 移除 `_merge_notes_until_fit` CORE path 對 `_truncate_to_token_budget` 的使用；不得省略尾端來源內容。

### 2. Bounded reasoning-only recovery state machine — CORE

- `allow_reasoning_retry` 單獨決定 semantic recovery；移除其與 `expand_output_budget` 的 conjunction。
- Visible-output orchestration 不再透過禁止 provider recovery 實現；merge 在 generation 後檢查 visible target 並階層式收斂。
- 每個 CORE logical generation 最多三次 completed provider calls：
  1. **Initial call**：caller 指定的初始 provider completion cap。
  2. **Growth retry**：只有 initial 為 `finish_reason=length + reasoning evidence + empty content` 時，沿用 Revision 1 的 instance headroom/configured-cap 公式增加一次 budget。
  3. **Stop replay**：只有 growth retry 為 `finish_reason=stop + reasoning evidence + empty content` 時，以相同 model、instance、prompt、temperature 與目前 token cap replay 一次。
- Initial 若直接為 `stop + reasoning evidence + empty content`，只做一次同 cap replay，總計兩次；不再接續 growth retry。
- Growth retry 再次 `length + empty content`、stop replay 仍空、無 reasoning evidence、或沒有可增加 headroom 時立即拋既有 `LMSTUDIO_NO_FINAL_CONTENT`。
- Network transient retries 與上述 completed-response semantic attempts 分開計數；不得互相重置上限。
- Correction 明確停用 semantic recovery；首次 `StableServiceError` 後保留該段及剩餘原文並熔斷，維持 Revision 1 行為。
- Diagnostics 只記 model/instance、finish reason、content/reasoning 字數、usage、cap、attempt type；禁止 prompt/reasoning 正文。

### 3. Preserve all source facts — CORE

- 新增 deterministic tail sentinel fixture，讓最後一份 note 包含唯一決議／待辦；完整 pipeline 最終輸出必須仍包含 sentinel。
- Quality validation 的輸入必須是完整 merge 結果，不能在 validator 前截斷來源。
- `LOCAL_LLM_MERGE_NOT_CONVERGED` 透過既有 stable-error/fallback 管道顯示，不能新增假成功 task state。

### 4. Bound chunk overlap and call amplification — SUPPORTING

- 建立共享內部常數 `LOCAL_LLM_CHUNK_OVERLAP_BUDGET_TOKENS = 220`，同時供 context plan 的 effective step 與 chunk assembler 使用。
- Assembler carry 同時受 220-token cap 與既有 `LOCAL_LLM_CHUNK_OVERLAP_LINES` 限制；必要時 overlap 可降為零。
- 保留 Revision 1 的 chunk postcondition、來源順序與非 overlap 內容完整覆蓋。
- 新增 structured metrics/log fields：logical generations、semantic attempts、network retries、merge rounds/groups、chunk count 與各階段 duration。
- 不建立依賴模型／硬體速度的固定 wall-time SLO；驗收只要求消除已證實的 correction/overlap/retry amplification。

### 5. Runtime provenance and E2E ownership — SUPPORTING

- Health response model 向後相容新增 `build_revision: string | null`。
- 以 `MEETINGSCRIBE_BUILD_REVISION` 作為執行期來源；local/E2E launcher 注入 `git rev-parse HEAD`，封裝或無 Git 環境允許 `null/unknown`。
- 一般 startup/health 不因 unknown revision 失敗；只有 E2E harness 將 revision mismatch 視為 acceptance failure。
- Startup log 改讀實際配置端口；E2E runner 使用同一端口值設定 uvicorn `--port` 與應用環境，移除固定顯示 9527。
- E2E runner 選擇 free port、使用隔離 temp `DATA_DIR`、記錄 child PID，只終止自己啟動的 process。
- E2E artifacts 保存 transcript、DOCX、backend log、health revision、model snapshot 與判定摘要，供 Stage 05 append-only attempt 使用。

## PUBLIC_AND_STABLE_CONTRACT_CHANGES

- **Additive HTTP field：** health response 新增 nullable `build_revision`; 現有 `status/version/services` 等欄位與狀態碼不變。
- **New environment input：** optional `MEETINGSCRIBE_BUILD_REVISION`; 未設定不影響一般執行。
- **New stable error：** `LOCAL_LLM_MERGE_NOT_CONVERGED`; 沿用既有 error description 與 fallback DOCX/TXT contract。
- **Internal type change：** `LocalContextPlan.notes_merge_budget_tokens` 拆成三個明確 budget 欄位；所有 local provider call sites 必須編譯／測試更新。
- **No migration：** 無 database、cache format、task state、model lifecycle 或依賴變更。

## IMPLEMENTATION_WAVES

### WAVE-01 — Fail-first evidence lock

- 加入 task `90fdb193` 的 merge `length/reasoning/empty` fixture。
- 加入 task `8fd56c54` 的 `initial length/empty -> growth stop/empty -> replay content` fixture。
- 加入 non-converging merge、tail sentinel、overlap 220-token 與 health revision compatibility tests。
- 在 product code 修改前確認新 tests 以預期原因失敗；保存實際 failure，不用敘事代替執行。

### WAVE-02 — Restore CORE merge/output contracts

- 實作三種 merge budgets、來源分組、visible-target compaction 與 preflight。
- 實作最多三次的 semantic recovery state machine。
- 移除 merge hard truncation，加入 bounded progress/non-convergence stable error。
- 執行 LM Studio adapter、summarization、fallback focused/contract tests。

### WAVE-03 — Contain supporting amplification and provenance

- 對齊 220-token overlap 與 diagnostics。
- 新增 optional build revision、actual port logging 與 owned-process E2E runner。
- 更新 health/config 文件，但不變更依賴或一般 readiness 語意。

### WAVE-04 — Full verification and independent acceptance

- 執行 focused tests、完整 `uv run pytest tests/ -q`、final diff inspection。
- 由獨立 Stage 05 context 執行原始音檔 fresh-cache true E2E、DOCX structural/full-page visual QA。
- 通過後才執行本機 stale-process replacement 與 9527 smoke verification。

## REGRESSION_AND_ACCEPTANCE

### Fail-first unit/contract cases

1. **Merge budget separation**
   - `merge_visible_target_tokens=900` 時，provider 初始 completion cap 仍為 reserved output，而不是 900。
   - reasoning-only growth retry 可成功；回傳 note 經 orchestration 最終收斂到 `<=900`。
   - merge 不會因 visible target 而設定 `allow_reasoning_retry=False`。
2. **Observed three-call sequence**
   - Initial `length/empty`、growth retry `stop/empty`、final replay content 成功。
   - 精確三次 calls，model、instance、prompt、temperature 不變；只有 growth retry 增加 token cap。
3. **Retry exhaustion**
   - 第三次仍空、第二次再度 length、無 reasoning、無 headroom 都回傳 `LMSTUDIO_NO_FINAL_CONTENT`，不再呼叫 provider。
4. **Correction degradation**
   - 相同回應 shape 用於 correction 時最多一次 provider call，保留當段及剩餘文字，摘要核心繼續。
5. **Merge progress/data integrity**
   - Context 可行時每組至少容納兩份目標大小 notes。
   - Single oversized note 可壓縮；持續不縮短時在既有 max rounds 內回傳 `LOCAL_LLM_MERGE_NOT_CONVERGED`。
   - Tail sentinel 永不因 truncation 消失。
6. **Overlap bound**
   - 每個 chunk boundary 重複 carry `<=220 tokens`，line cap 仍生效；所有非 overlap 來源內容保持順序與完整覆蓋。
7. **Compatibility**
   - `build_revision` 可為 null；舊 health consumer、zero/one/multiple selection、Ollama/Gemini、task fallback 不回歸。

### Integration/full suite

- 以接近真實 19 份 extracted notes 的 fixture 完成 extraction → merge → final generation。
- 現有必要章節均具實質內容，tail sentinel 出現在 final meeting record。
- Stable merge/reasoning errors 仍產出明示失敗的 transcript fallback，不新增 task state。
- 保留 Revision 1 的 sparse single-line chunk、pathological repetition cleanup、YAML precedence 與 correction circuit-break regressions。
- 依序執行 focused tests 與完整 `uv run pytest tests/ -q`；任何 failure 必須分類為 regression、pre-existing、environment 或 test defect。

### Independent owned-process true E2E

1. 以 free port、隔離 temp `DATA_DIR` 與 expected Git revision 啟動並擁有 backend child process。
2. Health `build_revision` 必須等於核准 HEAD；記錄唯一 loaded model/instance/context snapshot，不修改 LM Studio inventory。
3. 實際上傳 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a`，確定 fresh MLX ASR 執行。
4. Poll 到終態；不得為 `summary_failed`，不得出現 fallback title/warning、`max_tokens=1`、98-call correction amplification、hard truncation 或 merge non-convergence。
5. 驗證每個 chunk 合法、correction stable failure 後最多一次呼叫、semantic retries/merge rounds 符合各自上限、全流程 model selection 不變。
6. 下載逐字稿與 DOCX；必要章節非空，抽查尾端決議／待辦存在，逐字稿無達 cleanup threshold 的病態連續 run。
7. 以 OOXML 結構抽取加 LibreOffice/Poppler render 檢查 DOCX 每一頁；100% 檢查 clipping、overlap、缺字、亂碼、failure banner、空白頁與可讀性。
8. 保存完整 artifacts/log/result 至新的 Stage 05 append-only attempt；不得覆寫舊 E2E 證據。

## LOCAL_ROLLOUT_AND_ROLLBACK

- Stage 05 通過前不替換目前 9527 使用者服務，也不宣稱 root cause 已完成。
- 通過後先以 PID、cwd、open files 與 command line 確認 9527/9631 listeners 的 ownership。
- 僅終止已證實是本 repo stale/test instance 的 process；無法證明時停止並回報，不猜測性 kill。
- 透過受管理的 macOS start/restart path 啟動核准 HEAD 至 9527，確保 PID file 建立；health revision 必須符合核准 commit。
- 執行便宜的 health/config smoke check，不重跑昂貴 E2E 作為一般 startup gate。
- 不刪除既有 transcript cache、outputs 或使用者失敗 DOCX。
- 若 target startup 失敗，不隱藏錯誤或假稱完成；保留 Stage 05 隔離產物作為可重現證據，重新進入 debug/replan。

## RISKS_AND_CONTROLS

- **Model stochasticity：** 最多三次 CORE semantic calls；correction 最多一次；所有 attempt 有結構化診斷。
- **Merge token growth：** visible target 與 provider cap 分離，但每輪需有 progress 且受 max rounds 約束。
- **Silent data loss：** 禁止 hard truncation，tail sentinel + stable non-convergence error。
- **Call/latency amplification：** 220-token overlap cap、來源 group budget、logical/physical counters；不虛構硬體無關 SLA。
- **Public compatibility：** health 僅 additive nullable field，新 env optional，無 schema migration。
- **Stale process confusion：** owned-process E2E + expected revision gate；一般 runtime unknown revision 不 block。
- **Scope growth：** 不變更模型 selection/lifecycle、ASR decoder、task states、provider architecture 或第三方依賴。

## DEFERRED_OR_BEST_EFFORT

- 不針對 Qwen 或個別模型家族建立專屬 thinking-disable adapter。
- 不新增 speaker diarization、時間戳排版、語意段落重建或 ASR decoder tuning。
- 不為 build revision 建立一般產品 readiness veto。
- 不承諾所有自然重複都被刪除；cleanup 保持高 threshold 與保守策略，避免誤刪語意。
- 不宣稱 NVIDIA hardware E2E；只執行可用的 shared regression tests。

## DEFINITION_OF_DONE

- Revision 2 的 fail-first tests 先以預期原因失敗，再於修復後通過。
- Merge 三種 budget 語意分離，reasoning recovery 不再被 visible target 禁用。
- `initial length/empty -> growth stop/empty -> replay content` production shape 有真實 regression coverage，最多三次 calls。
- CORE merge 不存在無聲 hard truncation；無法收斂時使用 stable error/fallback，tail sentinel 保留。
- Revision 1 的 chunk invariant、cleanup、config precedence、correction circuit-break 與跨 provider tests 不回歸。
- Focused 與完整 suite 取得實際通過結果；不能只引用本計畫前的 495-test baseline。
- Owned-process fresh-cache true E2E 使用原始音檔生成正式「會議紀錄」DOCX，revision/model/limits 均符合契約。
- 最新 DOCX 完成結構與全頁 visual QA，無失敗 banner、空白必要章節、clipping、overlap、亂碼或已知病態重複。
- 本機 9527 僅在 Stage 05 通過且 ownership 證實後切換到核准 revision。
- 最終 diff 僅含核准 envelope，無 dependency/lockfile、模型 lifecycle、task-state 或無關變更。

## REVIEW_AND_HANDOFF_GATES

- Stage 02 必須以 fresh context 對 Revision 2 執行獨立 top-down/bottom-up review。
- Reviewer 優先挑戰：三次 retry 是否必要且有界、merge progress 是否可證明、禁止截斷是否會正確 fail loudly、provenance 是否保持 supporting/non-gating。
- Reviewer 必須 snapshot 本 plan 並記錄 Revision 2 hash；Revision 1 的 `review/attempt-01` approval 已失效。
- Revision 2 核准後才可重新編譯 `handoff.md`；再生成前依 harness 規則 archive Revision 1 handoff。
- Stage 04 若發現需改變 selection/readiness/task state/fallback、引入模型特例、或無法用本 plan 的 progress/retry contract 修復，必須寫 escalation 並返回 Stage 01，不得即席改語意。
- Stage 05 independent acceptance 通過前不得寫入完成 `result.md` 或宣稱使用者 primary outcome 已修復。

## ARTIFACT_GATE

- `TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary`
- `PLAN_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/plan.md`
- `PLAN_REVISION: 2`
- `PLAN_STATUS: READY_FOR_REVIEW`
- `DEBUG_STATUS: READY_FOR_IMPLEMENTATION`
- `FIX_TYPE: MIXED`
- `REVIEW_REQUIRED: YES`
- `INDEPENDENT_ACCEPTANCE_REQUIRED: YES`
- `E2E_REQUIRED: YES`
- `NEXT_STAGE: 02_PLAN_REVIEW`
