# Handoff — 修復 macOS LM Studio 空摘要、錯誤切塊與逐字稿重複

## TASK
- TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/plan.md
- PLAN_REVISION: 1
- PLAN_SHA256: 7f1b5c3ff36d76f60f82242d0ca5b3e362097747dc56c9778c18e0117a6bd78a
- REVIEW_REQUIRED: YES
- REVIEW_REPORT: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/review/attempt-01/review_report.md
- REVIEWED_PLAN_REVISION: 1
- REVIEWED_PLAN_SHA256: 7f1b5c3ff36d76f60f82242d0ca5b3e362097747dc56c9778c18e0117a6bd78a
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: FOCUSED_REGRESSION + CONTRACT_INTEGRATION + FRESH_CACHE_TRUE_E2E
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR

- **PRIMARY_OUTCOME**：原始會議音檔 → MLX ASR → 唯一已載入的任意 LM Studio LLM → 產生**非空、結構完整、可下載的「會議紀錄」DOCX**。
- **SUCCESS_EVIDENCE**：在無逐字稿快取的隔離環境完成真實上傳；DOCX 標題為「會議紀錄」、無摘要失敗警告、必要章節有實質內容、清理後逐字稿可獨立下載、全程沿用啟動時唯一選出的 loaded instance。
- **MUST_NOT_BREAK**：不硬編碼/載入/卸載/切換 LM Studio 模型；保留零/一/多模型與 optional exact override 選模契約；保留 NVIDIA/Ollama、Gemini 與「摘要失敗仍保存逐字稿」降級路徑；**不新增依賴、不變更 task state、不變更 HTTP response schema**；不建立跨 repository 耦合。

## CRITICAL_PATH

1. 先寫**會以正確原因失敗**的 production-shaped regression tests（33k-token 單行、reasoning-only response、YAML precedence、correction amplification、repetition loop）。
2. 恢復 token-budget chunk invariant（每個 fragment/chunk 都 ≤ budget，provider 呼叫前拒絕不合法 chunk）。
3. 修正 LM Studio parameter precedence、context headroom、reasoning-aware bounded retry。
4. 熔斷 BEST_EFFORT correction 的 provider-level failure，讓摘要核心路徑優先執行。
5. 跑 focused/contract/full tests，再以隔離 fresh-cache 完成真實 Mac E2E 與 DOCX 全頁 QA。

## SEMANTIC_INVARIANTS

以下語意邊界**不可變更**，否則視為語意契約變更需重新 Review：

1. **health ready ≠ generation success**：`health ready` 只代表 LM Studio 可達且有唯一可選 loaded LLM，不代表每次 generation 已成功。
2. **generation success 必須有非空 final content**；reasoning 不得被當成正式摘要，也不得輸出到文件或 log。
3. **chunk input budget 是硬性正確性 invariant**；overlap 是 best-effort enrichment，不能突破預算。
4. **LLM correction 是 BEST_EFFORT**，不得形成全域 veto，也不得在相同 provider-level 錯誤後繼續放大呼叫。
5. **DOCX fallback 是必要 fail-safe，但不是 PRIMARY_OUTCOME 成功訊號**。
6. **config precedence 是 load-bearing contract**：backend 只讀環境變數／`.env`／Field default；legacy YAML 不得覆蓋執行中各摘要階段的顯式參數。

## BEST_EFFORT_DO_NOT_GATE

以下元素失敗時**必須局部降級、保留原文並繼續**，不得阻擋核心摘要：

- LLM 同音／專有名詞校正（correction）
- 段落可讀性（paragraphization）
- token diagnostics
- overlap enrichment

## DEFERRED_NOT_THIS_TASK

- 不針對個別 Qwen/模型家族建立專屬 thinking disable adapter。
- 不為逐字稿增加 speaker diarization、時間戳版面或語意段落重建。
- 不重新校準 ASR decoder（mlx-whisper 0.4.3 不暴露 repetition penalty/no-repeat n-gram）。
- 不宣稱 NVIDIA hardware E2E；只執行其可用的 regression tests。

## REPO_ANCHOR

- Project root: /Users/hsiaojohnny/dev/convert
- Branch: main
- Anchor HEAD: 9368e0419b7f0968be07a04bf45dc288aaa39c6a（plan 撰寫時）
- Current HEAD: 59d3ae7（review commit，僅新增 review 產物，未動 product code）
- Relevant dirty state: 工作樹 clean
- Drift since plan/review: 無 product code 變更

## CURRENT_STATE_DELTA

無。plan 撰寫後僅新增 review/attempt-01/ 產物，product code 未變。

## MUST_READ_PLAN

開始 FIRST_ACTION 前，**必須**先讀 plan.md 以下章節（其餘可略讀）：

- `GOAL_CONTRACT`（PRIMARY_OUTCOME / CORE_ACCEPTANCE_SIGNAL / MUST_NOT_BREAK / NON_GOALS）
- `ROOT_CAUSE`（五個根因，逐條對應修復）
- `FIX_TYPE_AND_ENVELOPE`（允許改的元件 + 需 Review 的語意變更 + 全域 veto 理由）
- `DO_NOT_TOUCH`（禁止改的範圍）
- `CHANGE_MAP`（1–4 四組變更的完整規格）
- `IMPLEMENTATION_WAVES`（WAVE-01~04 順序）
- `REGRESSION_AND_ACCEPTANCE`（focused/unit、integration/contract、independent true E2E）
- `DEGRADATION_AND_GATE_TESTS`
- `DEFINITION_OF_DONE`

## SETTLED_DO_NOT_REOPEN

以下已由 plan + review 定案，**不得重新討論或推翻**：

- 五個根因（H-1~H-6 已 falsified/confirmed，見 plan `FALSIFICATION_RESULTS`）。
- 選模契約：zero/one/multiple/override 規則不變。
- 不新增模型 allowlist、不新增模型專屬 prompt 分支、不新增 LM Studio lifecycle 管理。
- 不把 health check 升級為會主動執行昂貴生成的全域 readiness gate。
- config precedence 是 bug（H-5），修正方向是「backend 只讀 env/.env/Field default」，不是「保留 YAML 覆蓋」。

## REVERIFY_ON_START

僅以下**可變事實**需在開始時重新確認（其餘以 plan 為準）：

- LM Studio 是否仍只有一個 loaded LLM（預期 `qwen3.6-35b-a3b-mlx`，loaded context length 183,296）。
- LM Studio 服務可達性（`/api/v1/models`）。
- 音檔 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a` 是否存在。

## TRIGGERED_POLICIES

- goal-alignment-design-economy.md
- plan-review-gate.md
- testing-verification.md
- debugging-recovery.md
- dependencies-contracts.md
- security-privacy.md
- git-change-hygiene.md

## FIRST_ACTION

**WAVE-01**：在 `tests/` 下新增 production-shaped regression tests，先觀察它們以正確原因失敗，**不得先改 production code 再補測試敘事**。至少涵蓋：

1. 單行 sparse-punctuation 33k-token shape 的 chunk 測試（現有 splitter 會產出兩個近整份重複、遠超 budget 的 chunks）。
2. reasoning-only response（`content` 空 + `finish_reason=length` + 非空 reasoning）的 LM Studio 回應解析測試。
3. YAML precedence 覆蓋 caller temperature/max_tokens 的測試。
4. correction 對 provider-level 穩定失敗放大呼叫的測試。
5. 無句界重複迴圈（如「請看影片」「個人專案管理」或單字）未被清理的測試。

## IMPLEMENTATION_WAVES

- **WAVE-01 [CORE]** — Fail-first regression：新增上述 5 類測試，確認以正確原因失敗。
- **WAVE-02 [CORE]** — 恢復 CORE input invariants：token-aware fragment splitting、overlap pruning、chunk postcondition、保守 repetition-loop collapse；paragraphization 排在核心 invariant 之後，不能成為 gate。
- **WAVE-03 [CORE]** — 恢復 CORE LM Studio output contract：config precedence、provider context headroom、response diagnostics、reasoning retry、stable errors、merge cap。
- **WAVE-04 [SUPPORTING/BEST_EFFORT]** — 熔斷 correction + 同步文件：correction circuit-break、no-reasoning-retry call site、更新 env/README/ADR-3。

詳細規格見 plan `CHANGE_MAP` 1–4，此處不重複。

## ACCEPTANCE_CONTRACT

**CORE（必須全過）**：

- production-shaped transcript 在 budget 3,112 下產生多個合法 chunks，所有 chunks `<= budget`，不再出現兩個近整份重複 chunks。
- CJK、Latin、無空白、稀疏標點與 overlap boundary 都維持順序與涵蓋。
- pathological loops 被壓縮；低於 threshold 的「對對對」等自然重複不變。
- LM Studio caller 參數分別保留 correction `0.0`、extraction/merge `0.1`、final `0.2` 與 merge cap，不受 legacy YAML 影響。
- reasoning-only 初次回應後**恰好一次**成功 retry；cap 有界、model selection 不變、reasoning 不外洩。
- retry 後仍空、非 reasoning 空回應、context invariant failure 都回傳正確 stable code。
- correction provider stable failure 最多呼叫一次，後續原文完整保留。
- task fallback 包含 stable actionable detail，逐字稿 TXT/DOCX 仍可取得。
- zero/multiple/wrong override/unreachable LM Studio contracts 維持。
- health selection readiness 不被 generation history 改成全域 veto。
- Ollama/Gemini/shared chunk paths 與現有 task processing regression tests 通過。
- 完整執行 `uv run pytest tests/ -q`；任何 failure 必須分類為 regression、pre-existing、environment 或 test defect。

**Independent true E2E（DoD 核心）**：

1. `mktemp` 建立隔離 `DATA_DIR`，在未使用 port 啟動 fresh-cache macOS backend；不刪除既有 cache/output。
2. 確認 LM Studio 只有一個 loaded LLM，記錄 model/instance/context snapshot；不由測試自動修改 inventory。
3. 經實際 Web upload journey 上傳 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a`，選 local mode。
4. 驗證 MLX ASR 確實執行、summary 非空、DOCX 標題「會議紀錄」、必要欄位/章節有實質內容、逐字稿可下載。
5. 驗證 transcript 不含達 cleanup threshold 的重複 run；log 無 `max_tokens=1`、無 98-call correction amplification、無 Ollama request、無 load/unload/switch。
6. 記錄 full 與 cached wall time；performance gate 是消除已證實的 retry amplification，不虛構固定 SLA。
7. 用 documents render workflow 將 DOCX 轉成每頁影像，逐頁檢查 clipping、overlap、failure banner、巨型單段與可讀性。

## STOP_AND_ESCALATE_IF

遇到以下任一情況，**停止並回到 Stage 01 escalation replan**，不得自行決定：

- 需要模型 allowlist、模型專屬 prompt 分支或 LM Studio lifecycle 管理。
- 需要改變 selection readiness 語意。
- 需要變更 task state、fallback DOCX 或 HTTP response schema。
- 發現與 plan 不同的 root-cause decision。
- 需要新增依賴或 lockfile 變更。
- 需要修改 `/Users/hsiaojohnny/dev/yt_down_txt` 或建立跨 repository 耦合。

## HISTORICAL_TASK_DEPENDENCIES

- T20260826-2310-01-mac-m4-dual-runtime（前置 Mac dual-runtime task）：本 task 承接其「任意唯一 loaded LLM」與真實 E2E 的明文要求；其 commit 明確未宣稱 LM Studio 真實 E2E 已完成。

---

TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
HANDOFF_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/handoff.md
PLAN_REVISION: 1
STATUS: READY_FOR_IMPLEMENTATION
NEXT_STAGE: 04_IMPLEMENT
