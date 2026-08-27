# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
- REVIEW_ATTEMPT: 01
- REVIEWED_PLAN_REVISION: 1
- REVIEWED_PLAN_SHA256: 7f1b5c3ff36d76f60f82242d0ca5b3e362097747dc56c9778c18e0117a6bd78a
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/review/attempt-01/plan_snapshot.md
- Repository anchor observed: main @ d515f97 (plan commit); ANCHOR_HEAD 9368e04 present in history; working tree clean
- Reviewer runtime/model: informational only

## OWNER_VERDICT

目標是：上傳會議音檔後，用 MLX ASR 轉錄、以目前唯一載入的 LM Studio LLM 產出非空正式會議紀錄，並可下載 DOCX。計畫正確鎖定五個已證實的根因（分塊不守 token 上限、YAML 覆蓋 caller 參數、reasoning 吃光輸出額度、correction 對 provider 失敗放大呼叫、無句界重複迴圈未清理），並以「先寫會失敗的測試 → 修核心 invariant → 修 LM Studio 輸出契約 → 熔斷 best-effort 校正」的順序推進。

必要項目（正確分塊、非空正文、保留選模與 fallback）與最佳努力項目（同音校正）分類正確；全域 veto 只保留在「缺核心輸入／無法唯一選模／上下文預算不可能／bounded retry 後仍無正文」四種情況，且都有明確安全理由。最大殘餘風險（reasoning token 消耗不可預測）以「有界 response-aware retry + 真實 E2E」而非模型 allowlist 處理，符合設計經濟原則。

複雜度判定：新增的 reasoning retry 與 correction 熔斷是針對已證實失敗的最小必要機制，非過度設計。最大風險是 config precedence 變更對既有 YAML 使用者的行為影響，但已文件化且屬修正既有 bug，非新增風險。

## GOAL_BASELINE

（由權威來源重建：使用者本次人工 E2E 失敗報告 + 已核准前置 Mac dual-runtime task 對「任意唯一 loaded LLM」與真實 E2E 的明文要求）

- PRIMARY_OUTCOME：原始會議音檔 → MLX ASR → 唯一已載入 LM Studio LLM → 非空、結構完整、可下載的「會議紀錄」DOCX。
- SUCCESS_EVIDENCE：隔離 fresh-cache 環境完成真實上傳；DOCX 標題「會議紀錄」、無失敗警告、必要章節有實質內容、逐字稿可獨立下載、全程沿用啟動時唯一選出的 loaded instance。
- MUST_NOT_BREAK：不硬編碼/載入/卸載/切換模型；保留零/一/多模型與 optional override 選模契約；保留 NVIDIA/Ollama、Gemini 與「摘要失敗仍保存逐字稿」降級路徑；不新增依賴、不變更 task state 或 HTTP response schema；不建立跨 repository 耦合。
- NON_GOALS：不重構整套摘要架構；不保證所有同音字自動修正；不新增模型 allowlist 或模型專屬 prompt 分支；不把 health check 升級為全域 readiness gate。

## GOAL_ALIGNMENT

PRIMARY_OUTCOME 與 GOAL_BASELINE 一致。CORE_ACCEPTANCE_SIGNAL 是「可觀察的產物證據」（DOCX 標題、章節實質內容、逐字稿可下載、沿用唯一選模），而非「實作完成度」，符合「completeness is not validity」原則。無任何 supporting 工具/來源/欄位被偷渡成專案目標。MUST_NOT_BREAK 完整覆蓋選模契約、降級路徑與 schema 不變。

## NECESSITY_AND_TRACEABILITY

DECISION_CONTRIBUTION_MATRIX 對每個 material 元素都給出「分類 → 缺失行為 → 目標貢獻」，可追溯。分類合理：

- CORE：動態唯一選模、每 chunk 符合 budget、非空 final content、病態重複清理（input normalization）、逐字稿 fallback（safety）。
- SUPPORTING：段落可讀性、token diagnostics。
- BEST_EFFORT：LLM 同音/詞彙校正。

無 untraceable 的顯著工作。病態重複清理被標為「CORE input normalization」而非獨立 veto，正確——它降低 token 汙染但失敗時保守保留原文，不新增全域 veto。

## GATE_AND_VETO_AUDIT

全域 veto 僅四項，且每項都有明確安全/正確性理由：

1. 缺核心必要輸入 → 無法宣稱已生成會議紀錄。
2. 無法選出唯一 loaded LLM → 無法確定本次用哪個模型。
3. 上下文預算不可能成立 → 硬性正確性 invariant 被違反。
4. bounded retry 後仍無 final content → 會議紀錄成功的最低充分條件不成立。

correction、overlap、paragraphization、diagnostics 明確不得 veto（BEST_EFFORT/SUPPORTING 局部降級）。這符合「influence is not veto authority」——低影響元素未取得不當的阻擋權。health ready 與 generation success 的語意被正確分離（health 只代表可達+可選模，不代表每次生成成功），且明確「不以 active generation probe 作為全域 readiness gate」，避免把昂貴生成偷渡成啟動門檻。

## COUPLING_AND_FAILURE_CONTAINMENT

- correction 的 provider-level 失敗被熔斷（遇 StableServiceError 停止後續 LLM 呼叫、保留原文），與核心摘要路徑解耦；candidate-specific empty/gate rejection 維持逐段局部處理，不誤升級為 circuit-break。失敗被收斂在最窄邊界。
- 獨立訊號未被摺疊成單一 all-or-nothing validity flag：chunk budget 是硬 invariant（provider 前 fail loudly），overlap 是 best-effort enrichment（可降為零），兩者分離。
- 無低價值 adapter 成為單點失敗；LM Studio 是唯一外部依賴，其失敗已由既有 fallback DOCX 承接。

## DESIGN_ECONOMY

新增機制逐一通過 deletion test：

- reasoning-aware bounded retry：刪除則 reasoning 模型仍回空正文，PRIMARY_OUTCOME 失敗。必要。
- correction circuit-break：刪除則 98 次放大呼叫重現，拖垮摘要。必要（移除已證實的重複複雜度）。
- 重複迴圈清理：刪除則 token 汙染與幻覺重複主導摘要。必要（input normalization）。
- `expand_output_budget` 旗標：刪除則 merge 收斂被 reasoning retry 破壞。必要（維持 merge convergence 的語意契約）。

無為假設性未來需求而建的抽象。無新依賴、無新 task state、無新跨層協調點。config precedence 變更是「修正既有 bug」而非新增複雜度。

## CRITICAL_PATH_AND_PRIORITY

WAVE 順序正確：fail-first regression → 修 chunk invariant → 修 LM Studio 輸出契約 → 熔斷 correction + 文件同步。核心路徑（分塊 + 非空正文）先於 best-effort（correction）與 supporting（paragraphization/diagnostics）。paragraphization 明確「排在核心 invariant 之後，不能成為 gate」，避免 PRIORITY_INVERSION。無 ancillary 細節成為重複 blocker。

## REQUIREMENT_FIDELITY

- 範圍嚴格限定在 envelope 內（shared cleanup/chunking、LM Studio adapter、correction containment、stable errors/docs、tests）。
- DO_NOT_TOUCH 明確列出選模規則、模型 lifecycle、task states、fallback DOCX、Gemini contract、Ollama/NVIDIA 實作、無關升級。
- 語意變更（config precedence、generation success/error contract、reasoning retry、correction failure propagation）被明確標記為「Semantic changes requiring Review」，未透過 IMPLEMENTER_FIX 偷渡。

## GROUNDING_AND_DRIFT

已驗證的 load-bearing 宣稱（對照實際程式碼）：

- `_split_oversized_line`（summarization.py:415）在找到多個標點 fragment 後直接回傳，未重新檢查仍超限的 fragment → H-3 成立。
- `_summarize_with_lmstudio`（summarization.py:1652-1667）以 `get_config_value` 讀 YAML 覆蓋 temperature/max_tokens，並以 `max(1, context_budget - prompt_tokens - 64)` 靜默壓低輸出 → H-5 成立。
- 回應解析只讀 `response.choices[0].message.content`（summarization.py:1743），空則 `RuntimeError("摘要生成失敗：結果為空")`（:1747-1749）→ 與失敗 DOCX banner 一致，H-4 成立。
- correction.py:305-309 每段 `except Exception` 後 `continue`，無 provider-level 熔斷 → 放大呼叫成立。
- `dedup_consecutive_sentences`（text_postprocess.py:121-140）依句尾標點分句 → 無句界重複迴圈無法處理，H-6 成立。

無 anchor drift；ANCHOR_HEAD 9368e04 在歷史中，工作樹 clean。

## ARCHITECTURE_AND_CONTRACTS

- 語意契約審計正確：health ready ≠ generation success；reasoning 不得當正式摘要或輸出到 log；chunk budget 是硬 invariant、overlap 是 best-effort；correction 是 BEST_EFFORT 不得全域 veto；DOCX fallback 是 fail-safe 非成功訊號；config precedence 是 load-bearing contract。
- 新 stable errors（`LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED`、`LMSTUDIO_NO_FINAL_CONTENT`）沿用既有 exception/fallback 管道，不新增 task state、不變 HTTP schema。
- reasoning retry 沿用同一 immutable selection/prompt/temperature，不觸發 JIT load 或改選，符合 MUST_NOT_BREAK。

## DATA_SECURITY_RELIABILITY

- 無 database/schema/backfill/data migration。
- 新 env key `LMSTUDIO_REASONING_RETRY_MAX_TOKENS=8192` 有 default，未設定者保持可運行。
- 既有 transcript cache 不需 invalidation；deterministic cleanup 在 cache hit 後執行。
- 回應解析記錄 reasoning presence/count 與 token counts，但「禁止記錄 reasoning text 或 sensitive prompt」——符合 security-privacy 原則（不洩漏敏感內容到 log）。
- 回滾可移除新 retry/config/error 邏輯，逐字稿 fallback 始終保留。

## IMPLEMENTATION_SEQUENCE

WAVE-01 先寫會以正確原因失敗的 production-shaped 測試（33k-token 單行、reasoning-only response、YAML precedence、correction amplification、repetition loop），再修 production code，避免「先改碼後補測試敘事」。WAVE-02/03 修核心 invariant 與輸出契約，WAVE-04 熔斷 best-effort 並同步文件。順序無 rework 風險。

## TESTABILITY_AND_ACCEPTANCE

- Focused/unit 測試覆蓋：合法 chunk 後置條件、CJK/Latin/無空白/稀疏標點/overlap boundary、病態迴圈壓縮與自然強調 negative test、caller 參數保留（correction 0.0 / extraction-merge 0.1 / final 0.2 / merge cap）、reasoning retry 恰好一次、stable error code、correction 熔斷。
- Integration/contract 覆蓋：task fallback、zero/multiple/wrong override/unreachable、health 不被 generation history 改成 veto、Ollama/Gemini/shared chunk 回歸。
- Independent true E2E：mktemp 隔離 DATA_DIR、fresh-cache、真實 Web upload、驗證 MLX ASR 執行、DOCX 標題/章節/逐字稿、log 無 max_tokens=1/無 98-call amplification/無 load-unload-switch、全頁 render QA。
- 87 個既有 focused tests 全過但 production-shaped probe 失敗，正確診斷為「測試覆蓋缺口」而非「契約已描述」。

## SCOPE_AND_COMPLEXITY

範圍聚焦單一問題（LM Studio 空摘要 + 長逐字稿 E2E），無無關重構、無依賴/lockfile 變更、無 repository 外檔案。複雜度集中在穩定邊界（chunking、LM Studio adapter、correction containment），未散落各層。

## FINDINGS

無 BLOCKER、無 MAJOR。

- RV-01 [MINOR | COMPATIBILITY] config precedence 變更（移除 YAML 對 `llm.lmstudio.temperature/max_tokens` 的讀取）是對既有 YAML 使用者的行為變更。計畫已於 CHANGE_MAP item 4 與 README/ADR-3 同步文件化，且屬修正已證實 bug（H-5），非新增風險。建議 Stage 03 handoff 明確提示此為「修正既有 bug 的契約變更」，避免被誤讀為無意破壞。
- RV-02 [MINOR | TEST] 重複迴圈清理的 false-positive 風險（高 threshold + 保留兩次 + 自然強調 negative test）已於 RISKS 明確標記並有測試對應，無需修正，僅提醒 Stage 05 驗收時確認「對對對」等自然重複未被誤刪。
- RV-03 [MINOR | TEST] token estimator 為近似值，計畫已以「fragment/chunk postcondition + provider preflight」而非估算敘事強制 invariant，處理正確，無需修正。

## REQUIRED_PLAN_CHANGES

無。三個 MINOR 均為提醒性質，不影響 goal alignment、實作、安全、相容、回滾或驗收。

## RESIDUAL_MINOR_NOTES

- RV-01/02/03 如上，均為 Stage 03/05 的注意事項，非計畫缺陷。

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: 對 revision 1（SHA-256 7f1b5c3ff36d76f60f82242d0ca5b3e362097747dc56c9778c18e0117a6bd78a）編譯 Stage 03 Handoff。
