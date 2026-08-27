# Plan Review Report — Revision 2

## REVIEW_METADATA
- TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
- REVIEW_ATTEMPT: 02
- REVIEWED_PLAN_REVISION: 2
- REVIEWED_PLAN_SHA256: 7ecccb5633b6c35f618e8b2901d16ca65f6ea44c160aa181f318e8d8ba654731
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/review/attempt-02/plan_snapshot.md
- Repository anchor observed: main @ 42531ec8ad8bd76dd68ffd5c21d446edfe720145 (plan commit); ANCHOR_HEAD 96e6e7416a0791b674b0ef5f17f8ba34355ef5c5 present in history; working tree clean
- Supersedes: review/attempt-01 (revision 1) — its approval is void for revision 2
- Reviewer runtime/model: informational only

## OWNER_VERDICT

目標是：上傳原始會議音檔後，以 fresh-cache MLX ASR 轉錄、以啟動時唯一選定的 LM Studio LLM 產出非空、結構完整、保留尾端決議／待辦且可下載的「會議紀錄」DOCX。Revision 2 是 escalation replan：Revision 1 已實作並宣稱 495 tests 通過，但兩個 current-code true E2E 仍失敗，推翻「一次 reasoning retry 足以恢復」與「merge 將 provider max_tokens 壓到 visible target 仍可成功」兩個 load-bearing 前提。

計畫正確鎖定五個根因（merge budget 語意混用、recovery state machine 未涵蓋 stop+empty、silent tail truncation、overlap 模型不匹配、runtime provenance 無法區分 stale/current process），並以「先寫會失敗的測試 → 分離三種 token 語意 → 擴充有界 recovery → 移除 hard truncation → 對齊 overlap → 新增 provenance」的順序推進。

必要項目（非空正文、merge 不得讓 reasoning 吃完輸出、決議／待辦不得無聲截斷、恢復流程有界）與輔助項目（overlap 放大、provenance）分類正確；全域 veto 只保留在「無法唯一選模／context 預算不可能／bounded recovery 耗盡／merge 無法不丟資料收斂」四種情況，且都有明確安全理由。最大殘餘風險（reasoning 模型隨機回空 content）以「最多三次 response-aware recovery + 禁止 hard truncation + production-shaped tests + owned-process true E2E」控制，符合設計經濟原則。

複雜度判定：三種 merge budget 分離、三階段 recovery state machine、merge progress 證明與 provenance 都是針對已證實失敗的最小必要機制，非過度設計。

## GOAL_BASELINE

（由權威來源重建：使用者本次人工 E2E 失敗報告 + 已核准前置 Mac dual-runtime task 對「任意唯一 loaded LLM」與真實 E2E 的明文要求 + Revision 1 的 escalation 證據）

- PRIMARY_OUTCOME：原始會議音檔 → fresh-cache MLX ASR → 唯一已載入 LM Studio LLM → 非空、結構完整、保留尾端決議／待辦、可下載的「會議紀錄」DOCX。
- SUCCESS_EVIDENCE：隔離 fresh-cache 環境完成真實上傳；DOCX 標題「會議紀錄」、無失敗警告、必要章節有實質內容、尾端決議／待辦存在、逐字稿可獨立下載、全程沿用啟動時唯一選出的 loaded instance。
- MUST_NOT_BREAK：不硬編碼/載入/卸載/切換模型；保留零/一/多模型與 optional override 選模契約；保留 Ollama、Gemini、task state 與「摘要失敗仍保存逐字稿」降級路徑；不新增依賴、不變更 database/schema/backfill、不建立跨 repository 耦合；health 僅允許新增向後相容 nullable `build_revision`。
- NON_GOALS：不重構整套摘要架構；不重新校準 ASR decoder；不新增模型 allowlist 或模型專屬 prompt 分支；不把昂貴 generation probe 加入一般 startup/global readiness；不以更換 loaded model 作為根因修復。

## GOAL_ALIGNMENT

PRIMARY_OUTCOME 與 GOAL_BASELINE 一致。CORE_ACCEPTANCE_SIGNAL 是「可觀察的產物證據」（DOCX 標題、章節實質內容、尾端決議／待辦存在、逐字稿可下載、沿用唯一選模），而非「實作完成度」。無任何 supporting 工具/來源/欄位被偷渡成專案目標。MUST_NOT_BREAK 完整覆蓋選模契約、降級路徑與 schema 相容性。

## NECESSITY_AND_TRACEABILITY

DECISION_CONTRIBUTION_MATRIX 對每個 material 元素都給出「分類 → 缺失行為 → 目標貢獻」，可追溯。分類合理：

- CORE：唯一 immutable model selection、provider completion 與 visible target 分離、bounded empty-content recovery、merge 全量收斂禁止截斷、transcript cleanup/chunk invariant（input）。
- SUPPORTING：220-token overlap cap、build revision/actual port。
- BEST_EFFORT：LLM correction。
- CORE safety：transcript fallback。

無 untraceable 的顯著工作。cleanup/chunk invariant 被標為「CORE input」而非獨立 veto，正確——它控制輸入品質但失敗時保守保留原文，不新增全域 veto。

## GATE_AND_VETO_AUDIT

全域 veto 僅四項，且每項都有明確安全/正確性理由：

1. 無法選出唯一 loaded LLM → 無法確定本次用哪個模型。
2. context 預算不可能成立 → 硬性正確性 invariant 被違反。
3. CORE generation 的 bounded recovery 耗盡 → 會議紀錄成功的最低充分條件不成立。
4. merge 無法在不丟資料前提下收斂 → 會輸出空白或不完整會議紀錄。

correction、overlap、paragraphization、diagnostics、build metadata 明確不得 veto（BEST_EFFORT/SUPPORTING 局部降級）。health revision 是 E2E freshness gate，但 unknown revision 不得使一般 startup/global health 失敗——正確分離了「E2E 驗收門檻」與「一般產品 readiness」。

## COUPLING_AND_FAILURE_CONTAINMENT

- correction 的 provider-level 失敗被熔斷（遇 StableServiceError 停止後續 LLM 呼叫、保留原文），與核心摘要路徑解耦；維持 Revision 1 行為。
- 三種 token 語意（merge input / visible target / provider completion）被明確分離，不再共用單一欄位——這是對 RC-1 的正確解耦。
- semantic retry、network retry、merge rounds 分開計數且各自有界，不互相重置上限。
- 無低價值 adapter 成為單點失敗；LM Studio 是唯一外部依賴，其失敗已由既有 fallback DOCX 承接。

## DESIGN_ECONOMY

新增機制逐一通過 deletion test：

- 三種 merge budget 分離：刪除則 reasoning 繼續吃完 900-token visible target，PRIMARY_OUTCOME 失敗。必要。
- 三階段 recovery state machine（initial → growth retry → stop replay）：刪除則 `stop + reasoning + empty content` 無法恢復，PRIMARY_OUTCOME 失敗。必要。
- 移除 hard truncation + `LOCAL_LLM_MERGE_NOT_CONVERGED`：刪除則決議／待辦無聲遺失。必要。
- 220-token overlap cap：刪除則 call amplification 重現。必要（SUPPORTING，但已證實）。
- build revision/actual port：刪除則 E2E 命中 stale process 無法偵測。必要（SUPPORTING）。

無為假設性未來需求而建的抽象。無新依賴、無新 task state、無新跨層協調點。

## CRITICAL_PATH_AND_PRIORITY

WAVE 順序正確：fail-first evidence lock → 修 CORE merge/output contract → 收斂 supporting amplification/provenance → 完整驗證與獨立驗收。核心路徑（merge budget 分離 + recovery + 禁止截斷）先於 supporting（overlap/provenance）。無 ancillary 細節成為重複 blocker。Stage 05 通過前不切換本機 9527，避免 stale-process 混淆。

## REQUIREMENT_FIDELITY

- 範圍嚴格限定在 envelope 內（merge budget 分離、recovery state machine、禁止截斷、overlap cap、provenance、stable errors/docs、tests）。
- MUST_NOT_BREAK 明確列出選模規則、模型 lifecycle、task states、fallback DOCX、Gemini contract、Ollama 實作、無關升級。
- 語意變更（merge budget 語意、recovery state machine、禁止截斷、health additive field）被明確標記為「Public and stable contract changes」，未透過 IMPLEMENTER_FIX 偷渡。

## GROUNDING_AND_DRIFT

已驗證的 load-bearing 宣稱（對照實際程式碼，commit 42531ec）：

- **RC-1 成立**：`LocalContextPlan.notes_merge_budget_tokens`（summarization.py:64）同時用於 `_group_texts_by_budget`（:1028）、`merge_predict_cap = min(RESERVED, max(notes_merge_budget_tokens, 512))`（:1009-1010）與 `_truncate_to_token_budget`（:1059）。`_merge_notes_until_fit` 以 `expand_output_budget=False` 呼叫 generation（:1051），而 `reasoning_retry_allowed = allow_reasoning_retry and expand_output_budget`（:1928）因此禁止 merge recovery。
- **RC-2 成立**：`_generate_with_lmstudio` 只在 `finish_reason == "length" and reasoning_evidence and reasoning_retry_allowed` 時進入 `_retry_lmstudio_reasoning_only`（:1930-1936）；`stop + reasoning + empty content` 落入 else 直接 `LMSTUDIO_NO_FINAL_CONTENT`。`_retry_lmstudio_reasoning_only` 恰好一次 retry，無 stop replay 分支。
- **RC-3 成立**：`_merge_notes_until_fit` 達輪數上限或縮減停滯時 `break` 後呼叫 `_truncate_to_token_budget`（:1059），尾端內容被硬截斷；validator 只比較已截斷 notes。
- **RC-4 成立**：planner 以 `effective_chunk_step = max(chunk_input_budget - 220, 1)`（:403）估算，但 assembler 的 `max_overlap_tokens = max(12, max_input_tokens // 2)`（:556）允許最多半個 chunk 的 carry，兩者不匹配。
- **RC-5 成立**：`main.py:56` 固定印出「監聽端口: 9527」，`main.py:174` 固定 `port=9527`；`HealthStatus`（models/schemas.py:103）只有 `version` 欄位，無 `build_revision`。

無 anchor drift；ANCHOR_HEAD 96e6e74 在歷史中，工作樹 clean。

## ARCHITECTURE_AND_CONTRACTS

- 語意契約審計正確：generation success 必須有非空 final content；provider total completion budget 與 orchestration visible-output target 是不同契約；merge 必須保留全部來源事實並確定性收斂；semantic/network/merge 計數分離；correction 是 BEST_EFFORT；health revision 是 E2E freshness gate 但 unknown 不 block 一般 startup；fallback transcript 是 fail-safe 非成功訊號。
- 新 stable error `LOCAL_LLM_MERGE_NOT_CONVERGED` 沿用既有 exception/fallback 管道，不新增 task state、不變 HTTP schema。
- health 新增 `build_revision: string | null` 是 additive nullable 欄位，向後相容。
- recovery 沿用同一 immutable selection/prompt/temperature，不觸發 JIT load 或改選，符合 MUST_NOT_BREAK。

## DATA_SECURITY_RELIABILITY

- 無 database/schema/backfill/data migration。
- 新 env key `MEETINGSCRIBE_BUILD_REVISION` 為 optional，未設定不影響一般執行。
- 既有 transcript cache 不需 invalidation；deterministic cleanup 在 cache hit 後執行。
- diagnostics 只記 model/instance、finish reason、content/reasoning 字數、usage、cap、attempt type；禁止記錄 prompt/reasoning 正文——符合 security-privacy 原則。
- 回滾可移除新 retry/config/error 邏輯，逐字稿 fallback 始終保留。

## IMPLEMENTATION_SEQUENCE

WAVE-01 先寫會以正確原因失敗的 production-shaped 測試（merge length/reasoning/empty、initial length/empty → growth stop/empty → replay content、non-converging merge、tail sentinel、overlap 220-token、health revision compatibility），再修 production code，避免「先改碼後補測試敘事」。WAVE-02 修核心 merge/output contract，WAVE-03 收斂 supporting，WAVE-04 完整驗證與獨立驗收。順序無 rework 風險。

## TESTABILITY_AND_ACCEPTANCE

- Fail-first unit/contract 覆蓋：merge budget 分離（provider cap 仍為 reserved output 而非 900）、三階段 recovery 精確三次 calls、retry exhaustion、correction degradation、merge progress/data integrity（tail sentinel 永不消失）、overlap bound、compatibility（build_revision null、舊 consumer、zero/one/multiple selection、Ollama/Gemini、task fallback）。
- Integration/full suite：接近真實 19 份 notes 的 extraction → merge → final generation；必要章節實質內容、tail sentinel 出現在 final record；stable errors 仍產出明示失敗的 transcript fallback。
- Independent owned-process true E2E：free port、隔離 temp DATA_DIR、expected Git revision gate、真實上傳原始音檔、fresh MLX ASR、DOCX 結構與全頁 visual QA、保存完整 artifacts 至 append-only attempt。
- 明確要求「focused 與完整 suite 取得實際通過結果，不能只引用本計畫前的 495-test baseline」——正確修正了 Revision 1 的驗證缺口。

## SCOPE_AND_COMPLEXITY

範圍聚焦單一問題（LM Studio 空摘要 + 長逐字稿 E2E），無無關重構、無依賴/lockfile 變更、無 repository 外檔案。複雜度集中在穩定邊界（merge budget、recovery state machine、禁止截斷、provenance），未散落各層。

## FINDINGS

無 BLOCKER、無 MAJOR。

- RV-01 [MINOR | CONVERGENCE] 三種 budget 分離後，`merge_provider_output_tokens` 使用 `LOCAL_LLM_RESERVED_OUTPUT_TOKENS`（3072），而 `merge_visible_target_tokens` 約 900，兩者差距 3.4x。這意味著 merge 單輪輸出可能高達 3072 tokens（含 reasoning），需再壓縮到 900，可能增加 merge 輪數。計畫已以「每輪必須減少 note 數或 estimated total visible tokens」+ 既有 `LOCAL_LLM_MAX_MERGE_ROUNDS`（預設 3）作硬上限，並以 `LOCAL_LLM_MERGE_NOT_CONVERGED` 收斂。建議 Stage 03 handoff 明確提示：若實測發現 3 輪不足以收斂，應優先調整 provider cap 或 visible target 的差距，而非無條件提高 max rounds（避免 call amplification）。
- RV-02 [MINOR | STOCHASTIC] 「stop replay」以相同 model/instance/prompt/temperature/cap 重播一次，對 `stop + reasoning + empty content` 的恢復成功率可能偏低（模型已決定停止）。但此步驟有界（恰好一次）、成本低，且失敗後正確落入 `LMSTUDIO_NO_FINAL_CONTENT`，屬合理 best-effort。無需修正，僅提醒 Stage 05 驗收時記錄 stop replay 的實際成功率，作為後續是否需調整的證據。
- RV-03 [MINOR | ESTIMATION] merge progress 證明依賴 `_estimate_tokens`（近似值）。計畫以「每輪必須減少」取代現有 `total_tokens >= previous_total_tokens * 0.9` 的停滯偵測，是更嚴格的準則，但需在 Stage 03 實作時以真實 merge 行為驗證此準則不會因估算誤差而誤判 non-convergence。此為實作注意事項，非計畫缺陷。

## REQUIRED_PLAN_CHANGES

無。三個 MINOR 均為提醒性質，不影響 goal alignment、實作、安全、相容、回滾或驗收。

## RESIDUAL_MINOR_NOTES

- RV-01/02/03 如上，均為 Stage 03/05 的注意事項，非計畫缺陷。

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: 對 revision 2（SHA-256 7ecccb5633b6c35f618e8b2901d16ca65f6ea44c160aa181f318e8d8ba654731）編譯 Stage 03 Handoff（編譯前依 harness 規則 archive Revision 1 handoff）。
