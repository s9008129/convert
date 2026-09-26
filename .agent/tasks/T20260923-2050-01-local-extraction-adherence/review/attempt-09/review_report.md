# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260923-2050-01-local-extraction-adherence
- REVIEW_ATTEMPT: attempt-09
- REVIEWED_PLAN_REVISION: 9
- REVIEWED_PLAN_SHA256: 192f0d351f87f33d33d132a550eddcd5a153125ebce452e096a22c178f20b677
- PLAN_SNAPSHOT_PATH: /Users/hsiaojohnny/dev/convert/.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-09/plan_snapshot.md
- Repository anchor observed: branch `fix/qwen-local-quality-parity`, HEAD `a576b06fc93c4a9d057ae59cdb54f07426ce343d`
- Reviewer runtime/model: Codex API runtime; model identity not exposed

## OWNER_VERDICT
目標是取得四份真正走到本機模型推論的有效會議紀錄：Gemma 4 31B 兩場、Qwen 3.8 27B 兩場，固定音檔、`section_meeting`、observe mode，並以既有量尺評估相對 Gemini 的改善，不宣稱 parity。必要路徑是 detached clean worktree、先建置並驗證 Apple ASR helper、再跑四場 E2E 與 Stage 05 獨立驗收。S1–S5 與額外消融屬非阻斷支援項，計畫也有明確停損與 raw/derivative 分層。最大風險不是品質設計，而是環境恢復後仍有其他 E2E 阻斷；計畫對此有具名 stop/replan 路由。

目前不能核准的原因是 §8.8 額外要求 Stage 05 通過後向遠端 `origin/fix/qwen-local-quality-parity` push，並聲稱是「使用者要求」。權威最新請求只要求實際 E2E，未授權此遠端發布。這是與核心 E2E 無關的外部狀態變更，必須移除、降為明確另行授權的 optional action，或取得使用者明示授權。

## GOAL_BASELINE
- PRIMARY_OUTCOME: 完成實際本機 E2E，取得可計分的四份會議紀錄，改善地端會議紀錄品質相對 Gemini；不宣稱 parity。
- SUCCESS_EVIDENCE: 固定音檔、`section_meeting`、observe mode 下，Gemma 4 31B 與 Qwen 3.8 27B 各兩場真正到達 ASR→摘要→LM Studio 推論→DOCX，並由既有 CORE-A–F/ANTI-GAMING 與 Stage 05 驗收。
- MUST_NOT_BREAK: 禁用 Qwen 3.6；不把 ASR 前失敗算成模型品質樣本；保留固定輸入/模型/commit provenance、品質門檻、clean-worktree gate 與 raw/derivative 隱私分層。
- NON_GOALS: 修 Runner、改品質門檻或產品語意、下載新模型、額外 S3/S5 實驗、遠端發布（權威最新請求未包含）。
- CRITICAL_PATH: 固定 commit → detached worktree → Swift helper build/`--help`/clean 驗證 → 四場指定模型 E2E → allowlist derivative → fresh Stage 05。

## GOAL_ALIGNMENT
[VERIFIED] §0.7 Owner/Debug Contract 與上述 baseline 對齊；計畫明確記錄 E1 只在 ASR helper resolution 失敗、provider calls/chunks/rounds 為 0，不把它當模型結果。四個新 alias、兩模型各兩場、固定素材與 observe mode 均直接服務成功證據。

[VERIFIED] 計畫保留「相對 Gemini 改善、不宣稱等同」的非目標，沒有把 helper 或品質量尺本身變成主要成果。

## NECESSITY_AND_TRACEABILITY
- CORE: helper preflight 是到達真實 ASR/模型 E2E 的必要前置；四場指定樣本、既有量尺、DOCX、ANTI-GAMING、成本與 provenance 直接證明 primary outcome 或 decision validity。
- SUPPORTING: S1–S5、FULL-SUITE、STATUS-CONTRACT-FIXTURES、E2E-COMMIT-PROVENANCE；計畫說明它們提升觀測/回歸/證據可信度，且不替代核心品質結果。
- BEST_EFFORT: 跨場逐字稿差異與額外消融；計畫標明非阻斷。
- [VERIFIED] C1/C2/C3 新旋鈕都有刪除測試/byte rollback/局部失敗語意；不見無理由的 global veto。
- [MAJOR] §8.8 的 push 無法追溯到權威最新 user goal 或已列 scope，且不屬於四份有效樣本的必要證據。

## GATE_AND_VETO_AUDIT
[VERIFIED] E2E-ASR-HELPER-PREFLIGHT 雖標為 SUPPORTING/DIAGNOSTIC/HARD_CLEAN，但計畫明確說明：沒有 helper 就不能形成有效真實 E2E 結論，因此只阻斷 CORE acceptance，不把 implementation 改判失敗；這是 decision-validity rationale，不是 schema completeness veto。

[VERIFIED] `CALL_BUDGET` 超限在 provider I/O 前全有或全無，局部降級為逐字稿-only，不擴散成全域服務 veto。E2E-COMMIT-PROVENANCE 同樣只阻斷無效 E2E 證據，不追溯否決 implementation。

[VERIFIED] 全庫 `FULL-SUITE` 是 SUPPORTING/BASELINE_DELTA，不被提升為產品 CORE；waiver 全部明定不允許，避免自我豁免。

## COUPLING_AND_FAILURE_CONTAINMENT
[VERIFIED] E1 failure 以新 `GEMMA-E1R` cache key 重跑，保留舊 raw cache，不覆寫或計分；非 completed task 立即停止後續場次。raw runner/runtime 留在 gitignored cache，task evidence 只留固定 allowlist derivative。

[VERIFIED] helper build 只在 detached worktree 產生 ignored `.build`，符合 resolver 的 `configured → repo release artifact → PATH` 順序；repository `Package.swift` 無外部 package dependency，`.gitignore` 忽略 `apple_speech_cli/.build/`。

## DESIGN_ECONOMY
[VERIFIED] rev9 修復只新增環境前置與替代 cache key，不改 runner、產品語意、模型或門檻；對已確認的 E1 ASR 前置缺漏是最小必要設計。

[MINOR] 計畫歷史變更記錄很長，但本 rev9 的 owner/debug contract、root cause、stop condition 與驗證矩陣足以讓 Stage 04 執行，不構成 gate 問題。

## CRITICAL_PATH_AND_PRIORITY
[VERIFIED] 先 helper preflight，再模型 E2E；失敗不載入模型、不暗中重試、不以失敗樣本計分。四場必要 E2E 優先於資源允許的 S3/S5，符合 CORE 優先原則。

## REQUIREMENT_FIDELITY
[VERIFIED] 固定音檔 SHA、`section_meeting`、observe mode、Gemma 4 31B×2、Qwen 3.8 27B×2 與 Qwen 3.6 禁測均被保留。既有品質門檻與量尺未被放寬；n=2 的集合語意與噪聲帶限制也被明示。

[MAJOR] §8.8 寫成 Stage 05 通過後必須 commit + push，並註記「使用者要求」，但本審查可用的權威最新 user request 僅為「幫我進行實際E2E測試，你可以自己載入模型」，另列 approved scope 也未包含 push。計畫不能把遠端發布當成已授權要求。

## GROUNDING_AND_DRIFT
[VERIFIED] live branch/HEAD 與 plan §0/§8 一致；prior redacted E1 result 顯示 expected/actual revision match、模型推論未發生、四份品質樣本仍為 0/4。產品 helper resolver 與 detached build 路徑相符。

[UNVERIFIED] 本審查未執行 Swift build、載入模型或 E2E，符合 reviewer 禁止事項；helper build 後的實際執行成功仍由 Stage 04/05 證明。

## ARCHITECTURE_AND_CONTRACTS
[VERIFIED] 計畫以既有 runner clean gate、既有 helper resolver、既有量尺與狀態路由為邊界，不繞過 runner 或改寫語意。C2a/C2c off 狀態與 BYTE-ROLLBACK、status fixtures、Stage 04→05 immutable snapshot 均具體化。

## DATA_SECURITY_RELIABILITY
[VERIFIED] 計畫禁止把 raw response、TaskInfo、prompt、transcript、DOCX 或絕對路徑寫入 task evidence；只在本機 gitignored cache 保存 raw，並以 cache key/hash 供 Stage 05 read-only 對照。E1 cache 保留、無 destructive cleanup。

[VERIFIED] failure-handler `NameError` 被正確視為獨立 runner defect；計畫不假稱它是 ASR 根因，也不在未重新規劃下修 runner。

## IMPLEMENTATION_SEQUENCE
[VERIFIED] Stage 03 archive/recompile → fresh Stage 04；先核對 baseline、focused/contract checks 與 commit，再 detached helper preflight，最後四場 E2E，Stage 05 只讀獨立驗收。遇到前提失效走 escalation/replan。

[MAJOR] push 若保留在同一 execution sequence，會把核心 E2E/acceptance 與未授權遠端變更耦合；最小修正是刪除 §8.8 的 push，或明確改為「需使用者另行授權的 post-closure optional action」，且不得成為本任務 closure gate。

## TESTABILITY_AND_ACCEPTANCE
[VERIFIED] CORE-A–F、ANTI-GAMING、LOCAL-CONTRACTS、BYTE-ROLLBACK、FULL-SUITE、E2E provenance、ASR helper preflight 與 status fixtures 均有結果/阻斷語意；PASS/FAIL/BLOCKED/NOT_RUN 不混用，Stage 05 保存 Stage 04 snapshot。

[UNVERIFIED] 真實 LM Studio 推論、ASR、DOCX 與品質數值仍待 Stage 04/05；計畫沒有把 preflight 當成品質證明。

## SCOPE_AND_COMPLEXITY
核心修復範圍與 approved E2E scope 相稱。新增 helper preflight 與 E1R cache alias 的複雜度各自直接服務到達有效樣本與保留證據。額外 push 是唯一明顯超出本次 scope 的 material action。

## FINDINGS

### RV-001
- severity: MAJOR
- category: SCOPE
- affected plan: §8 step 8 / §0.6 Stage 05 後發布
- evidence: 權威最新 user request 只要求實際 E2E；approved scope 列有固定素材、模板、observe mode、Gemma/Qwen 場次與禁測模型，未列 commit/push。計畫 §8.8 卻寫「使用者要求」並要求 push 到 `origin/fix/qwen-local-quality-parity`。
- failure/rework mechanism: Stage 05 PASS 後會對遠端分支造成外部狀態變更，且可能發布使用者未要求的產品/測試 commit；這與「完成四場 E2E」無關，也會把未授權 action 混入 closure 路徑。
- smallest correction: 從本 revision 移除 push；若確有需要，改成明確需使用者另行授權的 optional post-closure action，並寫明不影響 E2E/CORE/closure gate。

## REQUIRED_PLAN_CHANGES
1. 修訂 §8 step 8，使本任務只完成核准的 E2E/Stage 05 acceptance；移除「使用者要求」push 及其必做語意，或將其隔離為另行明示授權後才可執行的非 closure action。
2. 保留 rev9 的 helper preflight、E1R alias、failure stop/replan、raw/derivative 分層與四場固定 E2E contract；這些不需因 RV-001 重設。

## RESIDUAL_MINOR_NOTES
- [MINOR] 既有歷史條目與目前 rev9 contract 同檔共存，執行者應以 rev9 段落與最新 hash 為準；這是可讀性提醒，不是阻斷。
- [UNVERIFIED] 實際 helper build、LM Studio availability、四場品質與 Stage 05 結論尚未執行，不能在本 review 宣稱通過。

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID; remove or separately authorize the §8.8 remote push action, then request a fresh Stage 02 review for the new plan revision.
