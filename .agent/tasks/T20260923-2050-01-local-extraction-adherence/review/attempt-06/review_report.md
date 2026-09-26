# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260923-2050-01-local-extraction-adherence
- REVIEW_ATTEMPT: attempt-06
- REVIEWED_PLAN_REVISION: 6
- REVIEWED_PLAN_SHA256: 79a92f9ec0e71a031a04656adcb7a5f081ad99574fab4d1fb11334a97d883f72
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-06/plan_snapshot.md`
- Repository anchor observed: `scripts/e2e/run_owned_e2e.py`; `.gitignore:55`; `backend/api/routes.py:36-45,168-171`; `backend/core/config.py:599-604`; branch `fix/qwen-local-quality-parity`, HEAD `ab2528b718e8c91557fd72db174b0f9bb78d3a68`
- Reviewer runtime/model: Codex API runtime; no model inference, backend, tests, baseline, or E2E executed

## OWNER_VERDICT
目標對齊：計畫仍以「縮小地端與 Gemini 的會議紀錄差距、保住既有覆蓋與密度、誠實回報數字」為核心，沒有把 runner 或證據格式取代成主要目標。必要項是 CORE-A～F、反 gaming、local contract、byte rollback、平台無關性，以及有效的 E2E provenance；C3 配對、S3/S4/S5 與跨場差異明確為 supporting/best-effort。全域阻斷只用於核心品質、must-not-break、E2E decision-validity 與閉合正確性，且有局部降級或 scoped blocker 路由。

rev6 已正確把 runner 的整個 artifacts dir 與 runtime raw output 都放在主工作樹 `data/cache/e2e/<key>/` 的 gitignored raw 分層，並與 `.agent` 下只存 allowlist derivative 的 redacted evidence 分離。最大的剩餘風險是執行者必須遵守 allowlist 與 Stage 05 read-only 查證，不得受 runner 舊 docstring/CLI 的「redacted artifacts」說法誤導；plan 已明文指定以實際 raw 行為為準。

## GOAL_BASELINE
- PRIMARY_OUTCOME: 讓地端模型會議紀錄品質至少不要與 Gemini 差太多，並以改善百分比與差距數字白話回報；不可宣稱已達雲端水準。
- SUCCESS_EVIDENCE: 覆蓋、尾段事實、密度、成本、DOCX 可用性及反 gaming 的可觀測驗收證據；gemma/qwen 分開報告。
- MUST_NOT_BREAK: 模型／平台無關與跨 OS 同碼路徑；禁測 `qwen3.6-35b-a3b-splash`；既有雲端行為、off/no-log、輸出順序、摘要失敗隔離、既有品質門檻與 byte rollback。
- NON_GOALS: 不追求地端等同 Gemini；不把 Windows/Ollama 未實機驗證說成已驗證；不擴大到未必要的支持配對場或未量測的改善宣稱。
- CRITICAL_PATH: Stage 04 以零呼叫／生成／萃取核心變更取得 focused evidence，再於固定產品測試 commit 的 detached clean worktree 執行四場有效 E2E，Stage 05 只讀複核 CORE 與 provenance，閉合後才 push。

## GOAL_ALIGNMENT
rev6 的 Goal Contract 與權威目標一致。CORE-1 解決萃取漏寫，CORE-2 解決已在筆記但未進交付的遵循度，CORE-B/D 保住既有覆蓋與密度，CORE-E/F 與 anti-gaming 確保品質改善不是以不可用或不可驗證的代價換來。模型名只出現在固定驗收場次／報告標籤，新增邏輯仍要求同一路徑、無模型／平台分支；這符合使用者的模型無關約束。

## NECESSITY_AND_TRACEABILITY
| Material item | Class | Traceability / evidence |
|---|---|---|
| C1b 4500 ceiling、C1c extraction budget | CORE | 直接處理區塊內漏寫；§3、§5、replay evidence；pre-I/O all-or-nothing 測試 |
| C2a/C2c/C2b local-only refinement | CORE | 分別處理事實粒度與遵循度；保留雲端共享值、提示詞及輸出不變 |
| C3 proper-noun normalization | CORE mechanism but gate-off in required E2E | 確定性 registry/近音安全網；開關預設關、配對場 supporting，避免混淆核心歸因 |
| CORE-A～F、ANTI-GAMING、LOCAL-CONTRACTS、BYTE-ROLLBACK、PLATFORM-INDEPENDENCE | CORE / MUST_NOT_BREAK | 直接證明品質、可用性、語意回退及跨平台要求 |
| FULL-SUITE、STATUS-CONTRACT-FIXTURES、E2E-COMMIT-PROVENANCE | SUPPORTING / repository-health or decision-validity | 明確區分 goal criticality 與 closure gate；各自有 baseline、failure route、不可自行 waiver 規則 |
| S1/S2/S3/S4/S5、跨場差異 | SUPPORTING/BEST_EFFORT | 明確非阻斷；不取代核心驗收 |

## GATE_AND_VETO_AUDIT
CORE 品質、DOCX、反 gaming 與語意回退用 HARD_CLEAN，理由是其失敗會使主要結果不成立或不安全。`FULL-SUITE` 是 SUPPORTING/BASELINE_DELTA，不 veto 核心品質；缺基線只使 closure pending。`E2E-COMMIT-PROVENANCE` 是 SUPPORTING/MUST_NOT_BREAK/HARD_CLEAN，但其 veto 範圍被限制為 E2E decision-validity 與依賴該場的 CORE acceptance，不降級 implementation，也不把 supporting failure 擴散成全域產品 blocker。C1c 超限只阻斷單一摘要並走逐字稿-only/明確失敗，並非全域服務 veto。上述範圍與理由足夠且比例適當。

## COUPLING_AND_FAILURE_CONTAINMENT
Plan 把 raw cache、redacted derivative、`.agent` evidence 及 detached worktree 分開；C1c/C2 budget 的失敗也限定在單次本地摘要或補強輪。Stage 05 provenance 失敗保留 Stage 04 狀態、將 CORE acceptance scoped BLOCKED，不改寫 implementation。這是與 §7 狀態語意一致的最窄安全邊界。

## DESIGN_ECONOMY
主方案集中於既有 local pipeline，新增旋鈕均有具體缺口或 rollback/成本目的；S1/S2/S3/S4/S5 不進主阻斷路徑。C3 雖增加確定性後處理，但 registry 優先、唯一性、不捏造、log/skip reason 與 gate-off required E2E 限制了風險。未見把未來跨 OS 實機、尾段備援或重複觀測誤升為本波必要交付的情形。

## CRITICAL_PATH_AND_PRIORITY
執行順序 S1 → CORE-3 → CORE-2 → CORE-1 → 四場 E2E 仍在核心證據之前先做便宜的零呼叫工作；supporting 消融只在核心之後且資源允許。四場 E2E 必須在 focused tests 後先 commit，再於 detached clean worktree 執行；Stage 05 後才依 closure 條件 push，與使用者的 commit+push 要求及 runner clean gate 相容。

## REQUIREMENT_FIDELITY
已涵蓋固定素材、模板、quality mode、禁測模型、模型無關／跨 OS、不宣稱 Gemini 等硬約束；也保留 commit message 意圖／實作／下一步要求。§8.8 將 push 延後至 Stage 05 PASS、required checks closure-satisfied、無 blocker，並禁止 force-push；remote 前進或 push 拒絕時停止，符合安全與使用者要求。

## GROUNDING_AND_DRIFT
[VERIFIED] `scripts/e2e/run_owned_e2e.py:1764` 支援 `--expected-revision`；`2093-2118` 將 expected/actual revision 與時間寫入 run summary；`1947-1963` 將 health actual revision 與 expected revision 比對，mismatch fail-closed。`backend/api/routes.py:36-45,168-171` 提供 health `build_revision`，`backend/core/config.py:599-604` 接收 runner 注入值。

[VERIFIED] `.gitignore:55` 的 `data/cache/*` 命中四個 planned keys 的 `runner-output-raw/` 與 `runtime-raw/` 路徑；本審查時 `p7c-gemma-e1/e2`、`p7c-qwen-e1/e2` 四個 key 均不存在。runner 的實際 raw writes 包含 `health_snapshot.json`、`model_snapshot*.json`、`provider_info.json`、`task_final.json`、`run_summary.json`；plan 沒有再把它們誤稱為 redacted，而是把整個 artifacts dir 視為 raw。

[VERIFIED] branch/HEAD 與 plan 起始 anchor 一致：`fix/qwen-local-quality-parity` / `ab2528b718e8c91557fd72db174b0f9bb78d3a68`。rollback anchor 的 `ab2528b` 僅新增 escalation artifact，產品樹仍為前波產品狀態。

## ARCHITECTURE_AND_CONTRACTS
`--artifacts-dir` 與 `--runtime-dir` 都以絕對路徑指向同一主工作樹 cache key 下的不同 raw 子目錄，且 detached worktree 只承載固定產品/test commit；runner 的 `REPO_ROOT` 來自 detached script 路徑，不會重寫絕對路徑。`--expected-revision`、detached HEAD、porcelain、health expected/actual/match 四者在 plan 中均要求逐場記錄，足以形成 provenance 證據。

`FULL-SUITE` 在驗證矩陣、基線步驟與狀態路由中名稱一致，且 BASELINE_DELTA 不是全庫 HARD_CLEAN。四個 cache keys、絕對 raw paths、ignore precondition、allowlist derivative 與 hash 對照的契約彼此一致。

## DATA_SECURITY_RELIABILITY
Plan 正確把 raw response、TaskInfo、error body、backend log、transcript、DOCX 與 DATA_DIR 留在 gitignored task-scoped cache；`.agent` 只允許 alias、repo-relative cache key、SHA、固定指標/fact IDs、revision match 與穩定錯誤分類。Stage 05 只讀核對原件與 hash，只有 CORE-A/ANTI-GAMING 必要時取最短去識別引文，且不得複製 raw payload。這符合最小暴露與 retention 原則；清理只限本任務建立且已核實可刪的暫存 worktree。

## IMPLEMENTATION_SEQUENCE
前置條件（完整基線、focused tests、product/test commit、四個 key/子目錄不存在且各自 gitignored、detached HEAD/zero porcelain、expected revision）均已列出。若超過預註冊 4 chunks，plan 明確停止後續 E2E、記錄具名狀態並 replan，不暗中放寬 budget。Stage 05 先讀 execution snapshot，再決定是否 PASS/FAIL/BLOCKED；push 明確晚於 Stage 05，且不要求 Stage 05 自身寫入產品 commit，因此不與 clean worktree 順序衝突。

## TESTABILITY_AND_ACCEPTANCE
驗證矩陣逐項標示 `GOAL_CRITICALITY`、`EVIDENCE_ROLE`、`CLOSURE_GATE`、baseline、failure class、waiver policy；所有本計畫 checks 都 `WAIVER_ALLOWED=NO`/`NONE`。CORE thresholds 使用兩場集合語意、固定時鐘來源、成本事前門檻，沒有用觀察值替代阻斷條文。`STATUS_CONTRACT_FIXTURES` 覆蓋 canonical incident、implementation blocked、CORE fail/blocked/not-run/not-required、replan、baseline unavailable/delta、hard-clean debt、formal waiver、independent pending/block/product defect、矛盾狀態、legacy normalization 與所有 DONE 前提，且要求 Stage 05 保留 Stage 04 immutable snapshot。

## SCOPE_AND_COMPLEXITY
Scope 維持在 P7-C 的兩個主要品質缺口及其必要安全/驗證邊界；沒有把 supporting provenance 當產品功能，也沒有把 Windows/Ollama 實機驗證假裝已完成。raw/derivative 雙層、detached worktree 與 status fixtures 增加流程成本，但分別支付隱私、runner decision-validity 與 closure correctness 的具體風險。

## FINDINGS
無 BLOCKER 或 MAJOR。以下為不改變 gate 的 residual minor notes：

- `RV-008` — severity `MINOR`; category `GROUNDING`; affected §8.5 / runner documentation. Repo runner docstring 與 CLI help 仍把 `--artifacts-dir` 描述成只放 redacted evidence（`scripts/e2e/run_owned_e2e.py:23-28,1747-1753`），但實作在 artifacts dir 寫入 raw `health_snapshot`、`task_final` 等。rev6 plan 已明確承認此 drift，並要求兩個 cache 子目錄都當 raw，因此不是 approval blocker。Stage 04/05 必須依 rev6 allowlist 執行，不能把 runner 的舊說明當作安全證據。
- `RV-009` — severity `MINOR`; category `TEST`; affected §8.5 / E2E provenance. 本次只做靜態/檔案核查，沒有執行 `git check-ignore` 以外的 runner、health 或 redaction test；這符合本審查禁止跑 E2E/backend/tests 的範圍。Stage 04/05 仍需逐場保存 expected/actual/match、HEAD/porcelain、原件 hash 與 allowlist review，否則應按 plan 的 scoped BLOCKED 路由處理。

## REQUIRED_PLAN_CHANGES
無。`RV-008`/`RV-009` 已由 rev6 的 raw-cache、allowlist、read-only、hash、expected-revision、health revision 與 scoped blocking 條文處理；不需要再修改 canonical plan。

## RESIDUAL_MINOR_NOTES
- Windows/Ollama 實機仍是 `[UNVERIFIED]`，不可在最終回報中寫成實機 PASS。
- n=2 且小於 10pp 的變化只能作觀察值。
- 本審查未執行 tests、FULL-SUITE baseline、backend、模型 inference 或 E2E；不得把本報告解讀成 implementation/acceptance 結果。

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: Stage 03 Handoff for PLAN_REVISION 6 with SHA-256 79a92f9ec0e71a031a04656adcb7a5f081ad99574fab4d1fb11334a97d883f72
