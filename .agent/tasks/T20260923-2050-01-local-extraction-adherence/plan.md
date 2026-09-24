# P7-C 優化規劃：地端摘要品質 parity — rev15

- `TASK_ID`: T20260923-2050-01-local-extraction-adherence
- `TASK_MODE`: ESCALATION_REPLAN
- `PLAN_STATUS`: INVESTIGATION_ONLY
- `PLAN_REVISION`: 15
- `TASK_CLASS`: STANDARD（有語意變更 ⇒ `REVIEW_REQUIRED: YES`）
- `REVIEW_REQUIRED`: YES
- `INDEPENDENT_ACCEPTANCE_REQUIRED`: YES
- `E2E_REQUIRED`: YES
- `ACCEPTANCE_MODE`: E2E（前置診斷波為 read-only / no-score）
- 前波：`T20260923-1810-01-local-record-fidelity-density`（P7-B，rev4）。前波**兩條阻斷條文皆未達**，
  已依 §7 提出 `escalation.md`（`ab2528b`），本波即為該升級要求的重規劃。
- 分支：`fix/qwen-local-quality-parity`（HEAD `a576b06fc93c4a9d057ae59cdb54f07426ce343d`）
- 素材（固定）：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…2828`）、
  模板 `section_meeting`、`--quality-mode observe`
- 禁測：`qwen3.6-35b-a3b-splash`
- 量尺（既有、不改定義）：`scripts/e2e/measure_coverage.py`（coverage-1.0.0）、
  `scripts/e2e/measure_record_quality.py`、`quality/fact_checklist.json`（sha256 `cf012d1f…`）

## 0. rev2 變更紀錄（回應 Stage 02 attempt-01 的 I1–I13）

審查 artifact：`review/attempt-01/review.md`（`GATE: PLAN_REVISION_REQUIRED`，受審快照 `325e8487…`）。

| 項 | 處置 | 位置 |
|---|---|---|
| **I1 成本自相矛盾** | 廢除 `≤1,500 s`／`≤2,600 s` 兩個無推導值，改為「**實測基線＋已量測增量**」推導的絕對上限，並明示時鐘來源＝`run_summary.json` 的 `started_at`→`finished_at`（牆鐘），不可用 pipeline total | §5 CORE-E、§6 |
| **I2 n=2 中位數語意不明／容差 < 噪聲帶** | 全部阻斷條文改為**集合語意**（「2 場皆 ≥地板」＋「至少 1 場 ≥目標」），容差以本專案自訂噪聲帶（±10pp；28 條制 ≈3 條）為下限，並登錄「<10pp 的差異 n=2 不可判定」 | §5 |
| **I3 CORE-2a 與自身證據相反** | C2a 目標改對準 **gemma F048 型**（事實級期望集合）；qwen 型（遵循度）改由**新增 C2c 零呼叫槓桿**承擔，C2b 不再當唯一手段 | §3 CORE-2 |
| **I4 主槓桿未釘死值／預設值互斥** | plan 內**寫死** E2E 配對 `ceiling=4500`、`CALL_BUDGET=4`；定義 `CALL_BUDGET` 語意＝**總萃取呼叫數上限**、**預設 0（不限制）**；引用重播證據的 5 條預註冊（含 FALSIFIER）；加註碎片塊護欄 | §3 CORE-1、§5、§11 |
| **I5 gemma 腿缺整體保真度地板** | 新增 **CORE-B**（gemma `coverage_core` 地板＋重現條款）與「不得再回退」觀察清單（F048 型） | §5 |
| **I6 `LOCAL_LLM_TAG_SNAP_SIMILARITY` 不存在** | S2 改用**正確的既有**槓桿名稱（模組常數 `TAG_SNAP_TOLERANCE_SECONDS`／`TAG_SNAP_MAX_SHIFT_SECONDS`、`LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED`），並註明若需新旋鈕屬語意變更、本波不做 | §4 S2 |
| **I7 R1 引註階段錯誤** | 改引萃取階段 diagnostics（`19:34:00` completion 1,356／`19:37:03` 1,248、`max_tokens=8192`） | §2 R1 |
| **I8 R4 標籤過強** | R4 降為 `[SUPPORTED]`，補註 E5／E5b 的 SHA 差異與中間 commit 的 byte 等價性 | §2 R4 |
| **I9 CORE-C 升級未推導／名實不符** | 密度改為**阻斷地板＋重現條款**並寫明升級理由（本波兩條新槓桿有回吐密度風險）；近似重複對改為**純觀察值**（明文：不得單獨通過或否決） | §5 CORE-D |
| **I10 C3 缺安全網** | 加入 registry 白名單優先、候選定義、唯一性判準（沿用既有近音原語）、替換 log／計數與 `skipped_reason`、反 gaming 斷言 | §3 CORE-3 |
| **I11 C3 評法與場次預算不相容** | 閘門 4 場一律 **C3 關**；C3 開／關配對場降為 SUPPORTING（資源允許才跑） | §3 CORE-3、§9 |
| **I12 缺「E2E 前先 commit」** | §8 加入顯式前置步驟（runner 對 dirty worktree fail-closed） | §8 |
| **I13 已量測的便宜槓桿未列** | 新增 §11「方案 A（尾段補萃取）vs C1b（全域細塊）」比較與決策理由、備援啟用條件 | §11 |

**受審快照規則**：本 rev2 的指紋以 `shasum -a 256 plan.md` 於 attempt-02 開審時登錄；rev1 的審查
（`review/attempt-01/`）為 append-only 歷史，不覆寫。

## 0.1 rev3 變更紀錄（回應 Stage 02 attempt-02 的 RV-001–RV-004）

受審來源：`review/attempt-02/review.md`（rev2 SHA-256：`32e6ac0fe2473a951cc8d1e8217ffa1385722bdb5b59f302f726bf608390b1d2`）。

| 項 | rev3 處置 | 位置 |
|---|---|---|
| **RV-001 狀態／閉合語意不足** | 依 workflow-routing.md §7 增加逐項驗證矩陣、全庫測試基線政策、Stage 04 execution.md 與 Stage 05 不可變快照及 PASS／FAIL／BLOCKED／NOT_RUN／重規劃／閉合路由 | §8 |
| **RV-002 重播文件引用過寬** | C1b 僅引用重播 README 的塊數／事實落點及預測項 1–3、5；明示 §3 項 4 的 `CALL_BUDGET=2` 為舊預測、非本計畫依據；rev3 預設 `0`、E2E=`4` 為唯一有效值 | §3 CORE-1、§5 |
| **RV-003 Qwen 成本上限依據不等價** | 以 P7-B Qwen 同音檔／同地端路徑實測的完整萃取 427.6 s 作為保守新增萃取 allowance（不再借用 Gemma 的 150.5 s）；Qwen 上限修訂為 2,650 s，推導見 §5 | §5、§9、§11 |
| **RV-004 萃取呼叫逾限語意未定** | 改為 provider I/O 前全有或全無預檢；超限時只中止該次本地摘要、不丟塊、不消耗部分筆記、不產出可接受的部分紀錄；增加零呼叫邊界測試及 Stage 04/05 路由 | §3 CORE-1、§6、§8 |

僅更新本任務 canonical `plan.md`；不改 attempt-01／02、重播 evidence、prep 落點圖或產品碼。rev3 必須由全新 Stage 02 attempt-03 審查；舊核准／快照不可沿用。

## 0.2 rev4 變更紀錄（回應 Stage 02 attempt-03 的 RV-005／RV-006）

受審來源：`review/attempt-03/review.md`（rev3 SHA-256：`9d653b5c335dc4aaace45f65df37e83193411b9545413b7271d49125c66971c8`）。

| 項 | rev4 處置 | 位置 |
|---|---|---|
| **RV-005 補強輪數設定同時作用於雲端** | 保留舊共享上限及雲端呼叫點不變；新增 local-only `LOCAL_LLM_MAX_LOCAL_REFINEMENT_ROUNDS`，`0` 表示沿用舊共享值以保相容，四場 E2E 顯式設 `3`；測試鎖定雲端仍使用共享值且 local-only 覆寫不影響雲端 | §3 CORE-2、§6–8 |
| **RV-006 狀態閉合缺少可逐項驗證案例** | 增加狀態契約 fixture inventory，逐例涵蓋 §7 路由、baseline/waiver、legacy 正規化、矛盾狀態及每項 DONE 前提；Stage 04 留下結果、Stage 05 只讀獨立複驗，不更動快照 | §8.1–8.2 |
| **RV-005 次要提醒：補強 budget 逾限行為未明** | 明定停止後保留最後一版有效摘要，不丟逐字稿或回滾到無效部分；記觀察 log 並由 CORE 門檻決定結果 | §3 CORE-2 |
| **證據路徑精確度** | 將 Qwen E8 成本依據展開成 repository 內完整路徑 | §5 |

rev4 只改受 RV-005／RV-006 及其直接依賴影響的計畫決策；同一 TASK_ID，必須由 fresh Stage 02 attempt-04 複審。

## 0.3 rev5 變更紀錄（回應 Stage 04 preflight escalation）

受審前提失效證據：`execution.md`／`escalation.md`（rev4 SHA-256：
`355e0bf8fffc79fb4e8d4f973b48da2b594666bbff1a2e99db86c5425a12f920`）。Stage 04 確認主工作樹的本任務
`.agent/tasks/T20260923-2050-01-local-extraction-adherence/` 會出現在 `git status --porcelain`；runner
`scripts/e2e/run_owned_e2e.py:421-428,1888-1895` 將任何非空 porcelain 視為 dirty，且在 backend 啟動前 fail-closed。
原 §8 只承諾提交產品碼＋測試，無法使仍含本任務證據的主工作樹 clean。Stage 04 未改產品／測試／runner，未跑基線或 E2E。

| 項 | rev5 決定 | 位置 |
|---|---|---|
| **E2E-PROVENANCE 隔離路徑** | 保留 runner 全工作樹 clean gate 與任務證據原位；產品碼＋測試提交後，新增 detached clean worktree 固定於該 commit 執行四場 E2E。E2E `--artifacts-dir` 指向主工作樹任務目錄、且在 detached worktree 之外的絕對 redacted 證據路徑；`--runtime-dir` 指向主工作樹 gitignored `data/cache/e2e/<attempt>`，raw 輸出不混入證據目錄。每場前核對 HEAD SHA／零 porcelain；任何不符即不啟動／不計分，停止並回報 scoped blocker。 | §8、§8.1 |
| **不繞過 clean gate** | 不修改 runner、git ignore/exclude/config，不隱藏、搬走、刪除或提交本任務 planning/review/execution 證據以製造 clean 狀態。輸出路徑須保持 append-only，且 redacted/runtime 分層沿用 runner 既有契約。 | §8、§8.1 |
| **Stage 04 狀態延續** | 保留 rev4 前置 escalation 與 `execution.md` 歷史；核准 rev5 後由 fresh Stage 04 在同 artifact 追加新 revision/attempt 記錄，不回寫 rev4 的 `ESCALATED`／`REPLAN_REQUIRED` 歷史或虛構已開始實作。 | §8 |

rev5 同一 TASK_ID；rev4 review/handoff 不適用。須 fresh Stage 02 attempt-05 核准本 revision/hash，再由 Stage 03 歸檔舊 handoff 並編譯新版本。

**歷史決定註記**：0.3 所述「`--artifacts-dir` redacted」只記錄 rev5 當時判斷；已被 attempt-05 的 RV-007 證據推翻。自 rev6 起，唯一有效 E2E 路徑以 §8／§8.1 為準，runner 整個 artifacts dir 一律視為 raw。

## 0.4 rev6 變更紀錄（回應 Stage 02 attempt-05 的 RV-007）

受審來源：`review/attempt-05/review.md`（rev5 SHA-256：
`940bc274ca61f77340b19fd256b62ad848affdb64dcbbf340d8eb786e2305e69`）。Reviewer 對照的 runner SHA-256：
`3a6557fcdda65b2ccb726416a3b79b094853caf09e4d0bf7ef9c8e72621d975b`。

| 項 | rev6 決定 | 位置 |
|---|---|---|
| **RV-007 runner 證據目錄含 raw response** | 不再把 runner `--artifacts-dir` 當 redacted。整個 runner output（含 health/model `raw_response`、task API metadata、任何 error body）與 raw runtime 都先寫到主工作樹 gitignored、每場專屬的 `data/cache/e2e/<attempt>/` 下不同子目錄；絕不直接寫入 `.agent/tasks/.../e2e/`。 | §8、§8.1 |
| **redacted task evidence** | Stage 04 僅在 `.agent/tasks/.../e2e/<attempt>/` 追加固定 allowlist 摘要、repo-relative cache key 與來源檔 SHA-256；不複製 JSON／response body／輸入音檔名稱／使用者 prompt／絕對路徑／transcript／DOCX。Stage 05 在本機 read-only 核對 cache 原件及 hashes，輸出亦限最少必要指標／fact IDs／hash，勿暴露 raw payload。 | §8、§8.1 |
| **保留 rev5 clean worktree 路徑** | E2E 仍從固定產品測試 commit 的 detached clean worktree 執行；runner 全工作樹 clean gate、`--expected-revision`、主工作樹任務證據原位及 raw/runtime 分層保持不變。 | §8、§8.1 |
| **Stage 05 後發布** | 保留使用者明確要求的 commit + push：產品／測試 commit 可先在本機供 E2E 使用，但只有 Stage 05 通過且所有 required checks closure-satisfied 後才 push 至指定分支；未通過或仍有 blocker 時不發布、不 force-push，先走修復／重規劃。 | §8 |
| **全庫檢查名稱一致** | 將 §8 對全庫 baseline check 的引用統一為驗證矩陣中的 `FULL-SUITE`。 | §8、§8.1 |

rev6 保留 attempt-05 與 Stage 04 rev4 escalation/execution 作歷史證據；必須 fresh Stage 02 attempt-06 審查 rev6。Stage 03 只能在新核准後 archive 舊 handoff 並重新編譯。

## 0.5 rev7 變更紀錄（回應 Stage 04 rev6 escalation：C2 all-off rollback 矛盾）

受審前提失效證據：`escalation.md` 的「Stage 04 rev6 escalation — CORE-2 all-controls-off rollback contradiction」與 `execution.md` rev6 escalation snapshot。核准的 §6 列出的全關組態未能關閉 C2a fact coverage／C2c adherence prompt；而舊 `LOCAL_LLM_RECORD_COVERAGE_MODE` 預設為 `enforce`，不能以切到 `off` 假裝回復 P7-B 預設行為。

| 項 | rev7 決定 | 位置 |
|---|---|---|
| **C2a 獨立回退** | 新增 `LOCAL_LLM_RECORD_FACT_COVERAGE_ENABLED`（預設 `false`）；只有開啟才加入 fact-level coverage 類別／metrics。保留既有 coverage mode 與 categories 預設，off 時不得新增 fact prompt/issue/metrics bytes。 | §3 CORE-2、§6–8 |
| **C2c 獨立回退** | 新增 `LOCAL_LLM_RECORD_ADHERENCE_ENABLED`（預設 `false`）；只有開啟且 local refinement 有 issues 時才加逐項處置區塊；關閉時提示詞 bytes 與 P7-B 完全相同，雲端永不受影響。 | §3 CORE-2、§6–8 |
| **保留主目標與實驗強度** | 四場必要 E2E 明確開啟上述兩項（其餘原固定旋鈕不變），比較的是核准的 C2a/C2c 改善；全關 byte-rollback 測試在現有預設 coverage mode/categories 下證明 P7-B 相容。 | §3、§6、§8 |
| **重用有效 baseline／保護既有 scratch** | Stage 04 rev6 已於產品／測試修改前在 HEAD `ab2528b` 完成 `1129 passed, 2 skipped`；新 Stage 04 僅在檢查 execution evidence、基準 SHA 及前置時序有效後重用。任何重跑須用新建、空的 task-specific `DATA_DIR`，不得覆寫既有 `/tmp/test_scratch` 或 baseline cache。 | §8 |

rev7 僅重定義 C2a/C2c 開關、全關相容、對應驗證及 Stage04 re-entry；其餘 rev6 quality gates、raw-cache/redaction、detached-worktree、使用者 commit/push 與 status routing 決策保持不變。此 revision 必須由 fresh Stage 02 attempt-07 審查；rev6 approval/handoff 不可沿用。

## 0.6 rev8 變更紀錄（回應 Stage 02 attempt-07）

受審來源：`review/attempt-07/review_report.md`（rev7 SHA-256：`a84b06b71a5d6d57b80bfbf1823a91cc5545eb45f5ace314fe46544636bb46e9`）。

| 項 | rev8 決定 | 位置 |
|---|---|---|
| **MAJOR-01：BYTE-ROLLBACK 可重現性** | 將固定基準釘為完整 commit `ab2528b718e8c91557fd72db174b0f9bb78d3a68`；指定零模型呼叫、同一固定合成輸入、舊 coverage 預設 `enforce`／`topic,decision,number,date`，逐項比較兩個 C2 flag、local prompts、coverage issues／metrics、最終輸出與 cloud prompts／輸出的 UTF-8 bytes。基準 SHA-256 只存於測試 fixture；Stage 04 留 hash-only 對照證據，不留 prompt／輸出／逐字稿原文。 | §8 step 3、§8.1 `BYTE-ROLLBACK` |
| **MAJOR-02：fixture ID 唯一性** | 審查報告稱 `SCF-03-CORE-FAIL` 重複；但 rev7 canonical plan 與其受審 snapshot 各只含一列（已以精確 ID 搜尋核實）。不刪除正確案例；新增 fixture 執行前的唯一 ID assertion `len(ids) == len(set(ids))`，讓任何日後重複都明確失敗。 | §8.2 |

rev8 只補足回退證據程序與 fixture inventory 的唯一性檢查；C2a/C2c 的開關語意與 rev7 核准方向不變。須由 fresh Stage 02 attempt-08 審查本 revision/hash；舊 review approval 與 rev6 handoff 均不可沿用。

## 0.7 rev9 變更紀錄（回應 Stage 04 rev8 的實際 E2E 失敗）

受審前提失效證據：`execution.md`「Stage 04 rev8 — first LM Studio E2E attempt and escalation」及
`e2e/attempt-01/result.md`。GEMMA-E1 使用正確且乾淨的產品測試 commit，LM Studio 亦回報已載入 Gemma；但 detached worktree 沒有 Apple ASR helper，任務在 ASR 前停止，模型推論／chunks／補強呼叫皆為 0。原始失敗資料保留在既有 ignored cache，GEMMA-E1 不得計入四份品質樣本。

| 項 | rev9 決定 | 位置 |
|---|---|---|
| **E2E-ASR-HELPER-PREFLIGHT** | 每個唯一 detached worktree 先執行 repo 內既有命令 `swift build -c release --package-path apple_speech_cli`；確認 release helper 存在且 `--help` 可啟動，確認 build output 僅在該 worktree 的 gitignored `.build/` 且 porcelain 仍為空。Package manifest 無外部 package dependencies。建置失敗、helper 不可執行或 clean 狀態不符時，不載入模型／不啟動 E2E；記為具名環境阻斷，不複製主工作樹 binary、不改 runner、不暗中重試。 | §8、§8.1 |
| **唯一 Gemma 補跑** | 保留並封存已佔用的 `data/cache/e2e/p7c-gemma-e1`；不覆寫／清除。以新 alias `GEMMA-E1R` 與新 key `data/cache/e2e/p7c-gemma-e1r` 取代失敗的品質樣本；四個有效樣本仍是 `GEMMA-E1R`、`GEMMA-E2`、`QWEN-E1`、`QWEN-E2`（兩模型各兩場），門檻與素材不變。 | §8、§8.1 |
| **Runner failure-handler defect** | 保持 `scripts/e2e/run_owned_e2e.py` 不變；未定義 `_write_transcript_and_docx` 是 ASR 失敗後的次生錯誤，不是缺 helper 的原因。成功路徑不依賴它；如再遇非 completed task，保留原始輸出、只抽取 allowlist 衍生欄位並立即停止後續 E2E，先另行評估／replan，不以此錯誤或失敗場充作模型結果。 | §8、§8.1 |
| **沿用已測產品版本** | 無產品／測試碼需因 E1 改動；四場仍固定在既有 commit `a576b06fc93c4a9d057ae59cdb54f07426ce343d`。不新增 commit、不更改門檻／模型設定語意；helper build 是 detached worktree 的 ignored 執行前置。 | §8 |

### rev9 Owner / Debug Contract

- **PRIMARY_OUTCOME**：取得四場真正到達 LM Studio 推論、可依 §5 計分的會議紀錄，評估核准的地端改善；不宣稱等同 Gemini。
- **CORE_ACCEPTANCE_SIGNAL**：Gemma 4 31B 與 Qwen 3.8 27B 各兩場均有效完成，逐條套用既有 CORE-A–F／ANTI-GAMING 門檻及 Stage 05 獨立驗收。
- **MUST_NOT_BREAK**：固定輸入 SHA、`section_meeting`、observe mode、原核准模型／設定／門檻、產品 commit provenance、raw/derivative 隱私分層；不得測 Qwen 3.6、覆寫 GEMMA-E1 cache、或把未完成推論算成品質結果。
- **NON_GOALS**：修 Runner、改產品語意、下載新模型、改品質門檻、測 Windows/Ollama、額外 S3/S5 場次。
- **CRITICAL_PATH**：核對 rev9 handoff 與固定 commit → detached worktree 建置並驗證 helper → 每場檢查 clean HEAD 與唯一 ignored cache → 僅載入指定的本機 Gemma／Qwen 3.8 模型 → 執行四場且只追加 allowlist 結果 → fresh Stage 05 驗收。
- **OWNER_VIEW**：真正必要的是四份有效輸出；helper 建置只是讓測試能走到模型的前置條件。Runner 修補和額外實驗不阻擋成功路徑。最大風險是建置後仍出現其他環境／任務失敗；此時保留證據並停止，不把失敗歸咎模型品質。

### rev9 根因與可反證假設

- **EXPECTED / OBSERVED**：預期 ASR → 本地摘要 → LM Studio 推論 → 會議紀錄／DOCX；實際第一次場次在 detached worktree helper resolution 停止，`provider calls/chunks/rounds = 0`，所以並未測到模型。
- **SYSTEM_BOUNDARY**：E2E runner → backend health/model availability → upload/task → Apple ASR helper → transcript → local summarization/provider → record/DOCX → raw cache / redacted derivative。已知最後通過模型可用性快照；第一個失敗邊界是 helper resolution；ASR 之後的模型結果未知。
- **H-1（已確認）**：detached worktree 缺少未追蹤的 Swift release build artifact；helper resolver 不會自動編譯。預測在該 worktree 執行固定 SwiftPM build 後可產生 helper；若仍不可啟動則此恢復路徑被反證並停測。
- **H-2（未排除）**：helper 就緒後，ASR／本機服務／模型呼叫仍可能有另一個環境故障。建置與 helper smoke check 不證明模型品質；首場重跑必須依實際 task/provider 指標確認推論是否發生。
- **H-3（獨立 Runner defect，已確認）**：任務未完成分支呼叫未定義 helper function，會造成次生 runner exit error。它不解釋 ASR helper 缺失；原始 `task_final.json` 與 `run_summary.json` 可判別任務是否完成。此波不改 Runner。
- **ROOT_CAUSE**：GEMMA-E1 的模型品質測試未開始，原因是隔離 checkout 缺少必需且不會自動生成的 ignored ASR binary；屬環境前置缺漏，不是模型輸出或產品品質失敗。E1 raw evidence 仍完整保留。

### rev9 修復範圍、驗證與路由

- **FIX_TYPE**：執行環境前置／機械性測試恢復；不改產品或 Runner 的語意、程式碼、測試、模型提示或 acceptance contract。
- **FIX_ENVELOPE**：只在每個 detached worktree 以現有 Swift Package 建置 release helper，驗證可執行與 ignored/clean 狀態；另以唯一 `GEMMA-E1R` key 重做先前無推論的樣本。
- **DO_NOT_TOUCH**：GEMMA-E1 raw cache、固定素材／manifest、既有產品測試 commit、runner/ignore rules、設定與品質門檻、Stage 04/05 歷史證據、Qwen 3.6。
- **HYPOTHESIS DISCRIMINATION**：helper build + `--help` 只驗證前置工具；E2E 的 provider-call/chunk/task/DOCX 證據才證明是否抵達真實模型。模型未呼叫或任務未完成＝該場無效／環境阻斷，不是模型品質 FAIL。
- **REGRESSION / ACCEPTANCE**：沿用 §8.1 CORE-A–F、ANTI-GAMING、`E2E-COMMIT-PROVENANCE`；新增 `E2E-ASR-HELPER-PREFLIGHT`（SUPPORTING／DIAGNOSTIC／HARD_CLEAN）。其 hard gate 僅為避免再次產生無效 E2E 證據；失敗只阻斷 CORE acceptance，不把 implementation 改判失敗。
- **STOP CONDITION**：build/helper smoke、HEAD/clean、模型家族／唯一 cache 或資料隔離任一不符，即不開跑；任何後續任務未完成／runner 非零退出，封存 raw、記錄 allowlist 摘要並停止剩餘場次，先 escalation/replan。不可只靠多跑幾次直到成功。
- **ROLLBACK / COMPLEXITY**：不改 tracked product files，無產品回退需求；Swift `.build/` 是可重建且被 package `.gitignore` 排除的 local artifact。僅新增一個前置檢查及一個替代 cache key，是到達原 CORE outcome 的最小改動。

rev9 必須由 fresh Stage 02 attempt-09 審閱本 Plan hash；核准後 Stage 03 archive 舊 handoff 並生成 rev9 handoff，再由 fresh Stage 04 執行。Stage 04 實際 E2E 前不得載入／切換模型或建置 helper。

## 0.8 rev10 變更紀錄（回應 Stage 02 attempt-09 的 RV-001）

受審來源：`review/attempt-09/review_report.md`（rev9 SHA-256：
`192f0d351f87f33d33d132a550eddcd5a153125ebce452e096a22c178f20b677`）。審查者未取得原始 user-supplied
task brief，因此將已存在的條件式 commit/push 指示判為未授權。此處補足其權威來源與作用範圍；rev10 不擴大當前 E2E 執行權限。

| 項 | rev10 決定 | 位置 |
|---|---|---|
| **RV-001：條件式發布授權來源** | 原始 user-supplied task brief（2026-09-23）明確要求：只有完成 Stage 05 且驗收通過後才 commit/push。本波保留此既有明確授權，並維持既有 closure 條件；它不代表現在即可發布，也不由 E2E 請求本身推導。push 只能在 Stage 05 PASS、required checks closure-satisfied、無待修／待審／硬閘門後執行；remote 已前進或無法 fast-forward 即停止。未授權 force-push／rebase／改寫歷史仍禁止。 | §8 step 8 |
| **當前操作邊界** | rev10 工作仍只涵蓋 Apple helper preflight、四場 LM Studio E2E 與 Stage 05；在 Stage 05 真正通過前，不執行任何 push。review attempt-09 的 finding 已由原始任務授權來源澄清，rev9 的 helper/cache/stop policy 其餘不變。 | §0.7、§8 |

rev10 必須由 fresh Stage 02 attempt-10 審閱本 Plan hash。核准前不得 Stage 03、建置 helper、載入／切換模型或執行 E2E。

## 0.9 rev11 變更紀錄（回應 Stage 04 rev10 helper-preflight escalation）

受審前提失效證據：`escalation.md`「Stage 04 rev10 follow-up escalation — helper smoke-check premise is invalid」及
`e2e/attempt-02/result.md`。attempt-02 的 release build、helper presence、ignored `.build/` 與該執行環境回報的 HEAD／porcelain 檢查皆為 PASS；`apple-speech-cli --help` 回傳 exit 5。源碼與測試證明這是 CLI 對不支援旗標回傳的預期 `APPLE_INPUT_ERROR`，不是 helper runtime 壞掉。attempt-02 的原始 `BLOCKED` 紀錄保留，不回寫；它不能證明 Apple Speech 語系可用，也不是模型品質樣本。父工作樹另未觀察到新增 detached worktree registration；本機觀察與 Stage 04 執行環境不一致，故下一場必須在啟動 runner 的同一 repo context 內記錄 detached/HEAD/clean/script-root 對應證據，不猜測或重用舊 worktree。

| 項 | rev11 決定 | 位置 |
|---|---|---|
| **修正 ASR helper 診斷命令** | 移除 `--help` exit 0 要求（CLI 無此選項）。在新 detached worktree 建置後，執行正式唯讀命令 `apple-speech-cli probe --locale zh-TW`；stdout/stderr raw JSON 只留新的 gitignored `data/cache/e2e/p7c-asr-helper-probe-r11/`，檢查 exit 0、`locale_supported=true`、`transcriber_is_available=true`，只把固定 allowlist boolean/enum、cache key 與 hash 寫入任務證據。probe 不呼叫 `AssetInstallFlow`、不跑語音或 LLM 推論。 | §8、§8.1 |
| **Apple 語音資產授權界線** | probe 的 `locale_installed`／`asset_status` 只作固定 enum/boolean 觀察。若 locale asset 尚未安裝，停止在 ASR 前、不載入 LLM／不啟動任務；因實際 transcribe 路徑可能進行 Apple system asset installation，需另取得使用者明示授權後才能繼續。未安裝不可自行下載／安裝，也不可把此狀態算成模型品質 FAIL。 | §8、§8.1 |
| **worktree provenance 可觀測性** | 每個 E2E 必須由同一執行 repo context 證明其工作目錄為 task 新建的 detached worktree、HEAD 精確等於固定產品/test commit、runner script root 位於該 worktree、pre/post porcelain 為空；只記 boolean、commit SHA/hash，不記絕對路徑。不可重用目前已存在的舊 detached worktree。父 repo 是否能列出 subagent 隔離環境建立的 worktree不是單獨 gate；但若執行 context 無法產生以上可核對證據，該次 E2E 不啟動／不計分並回報具名 blocker。 | §8、§8.1 |
| **attempt-02 分類保留** | rev10 原結果維持 `E2E-ASR-HELPER-PREFLIGHT: BLOCKED`，不可追溯改成 PASS；rev11 的源碼結論只校正「原因分類＝smoke command/Plan check defect」，不聲稱實際 locale／ASR 可用。四份有效模型樣本仍為 0/4，Gemma replacement key 仍為 `GEMMA-E1R`。 | §8、§8.1 |

### rev11 Owner / Debug Contract（歷史；已由 rev12 取代）

- **PRIMARY_OUTCOME**：仍是四份真實到達 LM Studio 推論的有效結果（Gemma 4 31B、Qwen 3.8 27B 各兩份），依既有量尺比較，不宣稱 Gemini parity。
- **CONFIRMED_ROOT_CAUSE**：rev10 的煙霧測試命令不是 CLI 合法用法。`CLIArgumentParser` 僅接受 `probe`／`transcribe`；unknown command/flag 產生 `inputError`，穩定 exit code=5。`Runner.run` 將該錯誤碼傳回，因此 attempt-02 exit 5 不表示 helper 未啟動。
- **H-1 CONFIRMED**：`--help` 是無效 smoke command；已由 parser、runner、error mapping 與既有測試證實。預測若重跑同指令仍只會得到 `APPLE_INPUT_ERROR`／5，不能診斷 Speech 可用性。
- **H-2 UNKNOWN**：Apple Silicon/macOS/zh-TW Speech availability 與 asset installed 狀態仍未知。最低成本區辨是無推論、無安裝的 `probe --locale zh-TW`，其原始 JSON 僅留 ignored cache。
- **H-3 UNKNOWN**：attempt-02 的 worktree provenance 在父 repo 視角不可核實；由執行該 run 的 repo context 產生 commit/clean/root 對照 booleans 可區辨。無法產生即停，不猜測來源。
- **MUST_NOT_BREAK / NON_GOALS**：固定 input SHA、`section_meeting`、observe mode、已核准模型／門檻、raw/derivative 隱私、禁止 Qwen 3.6、Runner/產品語意不改；不安裝缺失的 Apple Speech 系統資產，除非使用者另行明示授權。
- **CRITICAL_PATH**：fresh Stage04 驗 rev11 hashes → 建立新的 detached worktree 並在同一執行 context 驗證 commit/clean/script root → build helper → probe 並檢查 locale/asset 狀態 → 若需要系統 asset installation 則停並詢問；否則以新 attempt-03 和 GEMMA-E1R 新 cache 啟動四場實際 E2E → Stage05 read-only acceptance。
- **FIX_TYPE / FIX_ENVELOPE**：只修訂測試程序／證據判讀，不改產品程式、CLI、runner、模型呼叫、品質 acceptance 或既有輸出語意。Attempt-02 保持歷史 BLOCKED。
- **PRIVACY / STOP**：probe JSON 含 host metadata 與 locale lists，raw 只可在固定 ignored preflight cache；任務證據只存 exit class、locale_supported、transcriber_is_available、locale_installed、asset_status enum、cache key/hash。不得原文輸出 probe JSON、host metadata 或絕對路徑。

rev11 必須由 fresh Stage 02 attempt-11 審閱本 Plan hash；核准後 Stage 03 archive 舊 handoff 並編譯 rev11。Stage04 在新核准 handoff 前不可 probe、載入模型或執行 E2E。

## 0.10 rev12 變更紀錄（歷史；由 rev13 取代）

受審前版本為 rev11，SHA-256：`1fedc179cb21b74618e342340781816e737eb36e020a34a699882a540e8f43f2`；其 Stage 02 核准的是「Qwen 3.8 27B、比較但不宣稱 parity」的舊目標。使用者已明確更正模型為 Qwen 3.8 27B，並要求 Gemma 4 31B、Qwen 3.8 27B 分別與專案雲端 Gemini 3.5 Flash-lite 的品質差距嚴格小於 10%。

| 項 | rev12 決定 | 位置 |
|---|---|---|
| 使用者目標／模型 | 改為 Gemini 3.5 Flash-lite 對照；本機模型精確記錄 Gemma 4 31B 與 Qwen 3.8 27B。刪除「不宣稱 parity」這項舊非目標。 | §1、§5、§8 |
| 10% 語意 | 定義為各 CORE 品質維度各自的相對差距，不是百分點、也不是跨維度平均。高分越好指標以 cloud score 為分母；差距必須嚴格 `<10%`，等於 10% 亦 FAIL。 | §5 |
| 公平比較 | 使用同一份已留存且核實 SHA 的 canonical transcript、`section_meeting` 模板與目前產品 `cloud`／`local` 摘要路徑，Gemini、Gemma、Qwen 各產生 3 份；兩個地端模型另各跑一次音檔→DOCX E2E，但其 ASR／逐字稿校正差異只作整合驗證、不混入摘要 parity 分數。 | §5、§8 |
| 指標語意 | 既有字面 coverage 保留作 deterministic observation；Stage 05 對 28 條 core facts 作逐條語意核對。另獨立判定事實／語意錯誤、來源可追溯性、結構與可用性；任何一維不得被其他維度平均抵銷。 | §5、§8.1 |
| attempt-03 路徑碰撞 | `[VERIFIED]` wrapper 預先建立 `runner-output-raw/`，但 runner 對該路徑以 `exist_ok=False` 建立，因此尚未啟動 backend 即 exit 1。舊 cache 與結果永久保留；下一次必須用新唯一 cache key，將未存在的 raw output/runtime 路徑交由 runner 建立，不預建 runner-owned directory。 | §8 |
| 執行路由 | Rev12 是驗收語意變更：保留同一 TASK_ID、Stage 01 僅更新本計畫；必須經 Stage 02 attempt-12 獨立審查與 Stage 03 新 handoff 後，才可 Stage 04。不得沿用 rev11 approval/handoff。 | §8 |

### rev12 Owner / Goal Contract（歷史；由 rev13 取代）

- **PRIMARY_OUTCOME（CORE）**：Gemma 4 31B 與 Qwen 3.8 27B 各自輸出的會議紀錄，在相同 transcript 與模板下，對專案雲端 Gemini 3.5 Flash-lite 的每個核心品質維度，差距嚴格小於 10%。
- **SUCCESS_EVIDENCE**：每個摘要路徑至少 3 份有效輸出；cloud、Gemma、Qwen 均使用同一 canonical transcript SHA 與 `section_meeting`。local 以 §5 固定的 P7-C 品質 profile 量測；因目前新增品質 flags 預設關閉，若 profile 達標，還須經後續 reviewed implementation 將有效設定落入實際產品設定並用最終設定重驗，不能只憑臨時環境覆寫宣稱已達成。兩模型皆須通過每個 CORE 維度與 hard-error 條件，另各有一場真正 audio-to-DOCX E2E，並由 Stage 05 獨立驗收。
- **MUST_NOT_BREAK**：雲端／地端路由隔離、目前產品設定與提示語意、P7-C byte rollback、任務失敗時不得把 partial notes 當成完整紀錄、模型身份與輸入 provenance、raw payload 隱私及 truthful status routing。
- **SUPPORTING**：牆鐘、provider 呼叫數、項目數／平均字數、near-duplicate、完整 audio-to-DOCX E2E 的非品質細節。它們須如實報告；除服務 timeout／既有呼叫安全預算外，不得單獨 veto CORE 品質結果。
- **BEST_EFFORT / NON_GOALS**：Windows/Ollama 實機；超出目前固定素材的跨會議泛化；本波不因測量結果自行改產品語意或調低 10% 門檻。若證據顯示產品修補必要，先依 Stage 01/02/03 重規劃。
- **OWNER_VIEW**：真正必要的是同一份逐字稿上，Gemma 與 Qwen 的每項品質分數都穩定達到 Gemini 中位數的 90% 以上，且沒有重大捏造。量測有效性所需的模型/input/hash 不符會讓 parity 結論失效；品質有效但未達標則是產品目標 FAIL，需重規劃修正。full E2E 的 ASR/helper 問題只阻斷該交付整合證據，不抹除有效品質分數。最大風險是單一會議無法證明跨會議泛化，且盲評 rubric 仍有人為判讀差異；另一個明確缺口是目前 flags default-off，profile 測通不等於使用者 runtime 已使用。
- **GLOBAL_GATES_AND_RATIONALE**：固定 transcript/model/provider/checklist provenance 是 parity 的分母與評分決策有效性必要條件，缺失時不能安全計算差距；重大捏造是事實正確性 hard fail；raw payload 隔離是隱私義務。ASR E2E/helper gate 只管 SUPPORTING delivery evidence，不 veto CORE parity。
- **COMPLEXITY_BUDGET**：重用既有摘要入口、固定 transcript 與 28-fact checklist；新增工作僅是 3×3 配對輸出、四個彼此不抵銷的人工評分維度、raw/hash evidence 與兩個 parity 通過後的 E2E。每項分別降低模型／輸入混淆、字面 coverage 誤判、摘要不可用、來源不實與端到端整合風險；不加新依賴、不建通用 benchmark framework、不擴資料集。
- **CURRENT_EXECUTION_STATE**：attempt-01／02／03 均沒有有效 P7-C 品質樣本；attempt-03 是 runner path collision，不是模型品質 FAIL。`execution.md` 尚停留在 attempt-03 啟動快照，Stage 04 恢復時須 append-only 登錄其終態，不得回寫舊結果。

## 0.11 rev13 變更紀錄（回應 Stage 02 attempt-12 的 RV-001／RV-002）

受審來源：`review/attempt-12/review_report.md`；受審 rev12 snapshot SHA-256：
`267285a36303537fd20a7d2d380915aecf2f82fd11bd94dd02efbc856481c34b`。Stage 02 gate 為
`PLAN_REVISION_REQUIRED`。本 revision 保留 rev12 的使用者品質目標、27B 模型身份、逐字稿／checklist、嚴格 `<10%`
公式、路徑碰撞修復、raw 隱私分層與 scoped E2E 語意，只補足從候選實驗到可交付產品設定的必要路徑，並凍結評分程序。

| 項 | rev13 決定 | 位置 |
|---|---|---|
| **RV-001：實驗 profile 未進入產品設定** | 把品質工作拆成候選 profile 3×3 → 若通過則持久化 → 用持久化後的正式產品 commit 再做全新的 3×3 parity。持久化的唯一程式設定來源為 `backend/core/config.py` 的六個地端專用 defaults，並同步 `.env.example`；不改 `.env`、使用者環境變數、雲端 provider/model、共用補強輪數或地端模型識別。執行時 `.env`／process environment 若覆蓋 profile，必須檢查並如實阻止該執行環境宣稱已採用正式 profile；不得靜默覆寫使用者設定。 | §0.12、§1、§5、§8、§8.1 |
| **RV-002：評分無法獨立重現** | Stage 04 在任何摘要輸出生成／閱讀前，凍結 `quality/rubric-v1.md` 並記錄 UTC 時間、plan revision/hash、transcript/checklist hash 及 rubric SHA-256。候選及 final cohort 使用獨立 alias `C-R01–C-R09`／`F-R01–F-R09`；候選由兩個獨立 blind contexts 評分，final 由 Stage 04 與 Stage 05 獨立 contexts 評分。模型對照僅留 ignored raw cache；重大分歧觸發第三位 blind scorer。 | §0.13、§5、§8、§8.1 |
| **關閉候選分數的閉合歧義** | 候選 3×3 PASS 僅授權進入 profile-persistence wave，不能關閉 PRIMARY_OUTCOME、`PROFILE-PERSISTENCE` 或 task closure；最終只認持久化後全新 3×3 分數與 Stage 05 獨立驗收。候選 FAIL 則帶證據 replan，不先改預設值、不跑 supporting E2E。 | §0.12、§1、§8、§8.1 |
| **執行路由** | 同一 TASK_ID、rev13 必須 fresh Stage 02 attempt-13 核准當前 snapshot/hash，再由 Stage 03 產生新 handoff；不得沿用 rev12 核准／handoff，核准前不執行模型生成、產品修改或 E2E。 | §8 |

### 0.12 rev13 Owner / Goal Contract

- **PRIMARY_OUTCOME（CORE）**：持久化後的產品地端路徑中，Gemma 4 31B 與 Qwen 3.8 27B 各自輸出的會議紀錄，在相同 transcript 與模板下，對專案雲端 Gemini 3.5 Flash-lite 的每個核心品質維度，差距嚴格小於 10%。
- **SUCCESS_EVIDENCE**：先以固定候選 profile 作 3×3 決策性先導比較；候選通過後，只持久化其六個 local-only defaults，再於新的產品 commit 使用該產品實際 effective settings 全新生成 cloud/Gemma/Qwen 各 3 份。最終 9 份須由 Stage 04 與 Stage 05 的 blind scorer 獨立評分並滿足 §5 每份、每維度門檻，profile/provenance/rubric hash 全部有效，無重大錯誤。之後 Gemma/Qwen 各一場 true audio-to-DOCX E2E 只作 SUPPORTING 整合證據。
- **MUST_NOT_BREAK**：Gemini/cloud 路徑、雲端 provider/model、使用者明確 `.env`／process environment 覆寫能力、共用 refinement defaults、模型選擇與呼叫介面、local/cloud 路由隔離、失敗時不得把 partial notes 當完整紀錄、raw payload 隱私及 truthful status routing。profile defaults 只影響產品本地摘要路徑。
- **SUPPORTING**：candidate 3×3 分數（決定是否進入持久化；不能取代最終分數）、牆鐘、provider 呼叫數、項目數／平均字數、near-duplicate、true E2E 的 ASR/DOCX 細節。它們如實報告；除明確服務安全限制外，不得單獨 veto 已有效的最終 CORE 品質分數。
- **BEST_EFFORT / NON_GOALS**：Windows/Ollama 實機、跨會議泛化、同 prompt 裸模型 benchmark；不得調低 10% 門檻、挑樣或修改已凍結 rubric。candidate 或 final 結果未達標均依證據走 fresh replan。
- **OWNER_VIEW**：要證明的是「產品正式預設真的用了被驗證的地端品質設定」，而不是只在一次 shell 命令臨時開旗標後得到好成績。必要步驟是先盲評同資料的候選比較；通過才改本地 defaults，然後依新 commit 再完整重跑及獨立盲評。環境變數／`.env` 若明確覆蓋正式 profile，不能替使用者擅自改寫；需將有效設定差異揭露，該環境不作 profile PASS。最大剩餘風險仍是單一會議與人工評分不能推論跨會議表現。
- **GLOBAL_GATES_AND_RATIONALE**：輸入/model/provider/config/rubric/output provenance 使相對差距可計算且可重現，缺失即阻止 parity 結論；重大捏造是事實正確性 hard fail；raw 隔離是隱私義務。candidate fail 是產品品質 FAIL 並需重規劃，不得靠 profile persistence 掩蓋；ASR E2E/helper gate 只管 SUPPORTING integration。
- **COMPLEXITY_BUDGET**：只追加一次候選 3×3 和一次持久化後正式 3×3，僅在候選通過時執行後者；使用既有摘要入口、固定 transcript/checklist、六個現有 local settings，不新增 dependency 或 benchmark framework。雙盲評、第三評分僅在具體分歧時觸發，為主觀量尺可重現性所需。
- **CURRENT_EXECUTION_STATE**：仍無有效 P7-C 摘要品質樣本；attempt-03 是 inference 前 runner path collision。rev13 審核、handoff 前不得載入模型或產生新輸出。

### 0.13 rev13 Scoring Freeze Contract（在首次摘要輸出生成前寫入 `quality/rubric-v1.md`）

`rubric-v1.md` 由 Stage 04 逐字匯出本 contract 的 rubric 條款；在任何 scorer 開啟首份輸出、也在任何摘要生成前完成凍結。凍結紀錄包含 `RUBRIC_VERSION=1.0.0`、UTC timestamp、Stage 04 owner/盲評 scorer IDs、核准 `PLAN_REVISION` 及 plan SHA-256、transcript/checklist SHA-256、rubric SHA-256。凍結後不可改；發現 rubric 缺陷須停止並 Stage 01 replan，另用新版本和新完整樣本，不得回頭重評以挑有利結果。

## 0.14 rev14 變更紀錄（回應 rev13 C-R03 非零退出與使用者確認 LM Studio 更新後重啟）

受審來源：rev13 Plan SHA-256 `2b663c68a8f49d0cf769000db5d6d7629c54e589bff8e6c62a5168bc34fbe588`；Stage 02 attempt-14 核准此 rev13。rev13 的 C-R03（Qwen 3.8 27B）退出 1、沒有輸出；同時間 LM Studio 記錄 `predict` error，但安全診斷無法判定子類別。使用者隨後告知 LM Studio 正在更新並已重新啟動。只讀檢查確認更新後 local API 可回應，Qwen 當下為 `not-loaded`；這不是推論成功或錯誤已修復的證據。

| 項 | rev14 決定 | 位置 |
|---|---|---|
| **單次、受限的環境恢復探針** | 保留舊 C-R03 原始失敗與 cache，不計分、不覆寫；在新 Stage 02／03 核准後，對同一 Qwen 3.8 27B 以相同逐字稿、模板、候選 profile 與已凍結量尺，只允許一個全新唯一 cache 的 recovery generation。成功且有完整輸出時，才作為候選 Qwen 第一份樣本；再次非零、timeout、無輸出或 model/provenance 不符即停止，不盲目重試。這是對使用者所述軟體更新／重啟的單次可反證檢查，不改一般 retry policy。 | §8 |
| **Window size 與候選條件** | 不因「可能較慢」而調 context/window size、量化、模型 key、temperature、prompt、profile 或 `<10%` 門檻；重載後核對 Qwen key `qwen3.8-27b-splash` 與原已觀察的 context `65,536`。不同即停並記為環境／provenance blocker。 | §5、§8 |
| **長時間等待** | Stage 04 外層 controller 不因累計 30 分鐘而取消模型工作；依使用者指示等待 LM Studio 回覆，記錄實際 elapsed。程式既有 `LOCAL_LLM_REQUEST_TIMEOUT` 是每次請求的 1,800 秒設定；本次 C-R03 有 `predict` error 而非可確認 timeout，rev14 不改產品 timeout，也不把它當作目前根因。若後續單一 API 呼叫明確觸及該 timeout，停止並以新證據另行規劃，不靜默改設定。 | §8 |
| **後續驗收** | recovery 成功後，沿用 rev13 候選 3×3、雙盲評分、候選 PASS 才持久化六個 local-only defaults、持久化後全新 final 3×3、兩場 supporting audio-to-DOCX E2E 與 fresh Stage 05；不因 recovery 成功而預先打分、持久化或宣稱 parity。 | §5、§8 |
| **執行路由** | 同一 TASK_ID、PLAN_REVISION=14；須由 fresh Stage 02 attempt-15 核准當前 Plan snapshot/hash，再由 Stage 03 封存舊 handoff 並編譯 rev14 handoff。未核准前不得載入模型、重跑候選、改產品或進行評分。 | §8 |

### rev14 Owner / Goal Contract 與目前狀態

- **PRIMARY_OUTCOME、四維嚴格 `<10%` 目標、輸入／模型／模板、不得降低門檻等 MUST_NOT_BREAK**：完全承接 rev13 §0.12、§5；本 revision 不改品質定義。
- **已完成的候選前置證據**：rubric 已在 C-R01 前凍結；C-R01 cloud 與 C-R02 Gemma 各有一次 exit-0 generation-only 證據，尚未評分。
- **第一個失敗邊界**：C-R03 的 Qwen model key 曾載入成功，隨後 LM Studio 出現 `predict` error；runner exit 1 且無 output，因此 provider inference completion 與品質結果皆 `[UNPROVEN]`。不把它分類成 Qwen 品質 FAIL 或 timeout。
- **CURRENT_EXECUTION_STATE**：候選 3×3 為 `[BLOCKED]`、整體 PRIMARY_OUTCOME `[UNKNOWN]`；下一個且唯一獲准的新執行是核准 handoff 後的單次 Qwen recovery。若 recovery 成功，才能續跑其餘六份候選；若失敗，回到 Stage 01，不繼續補跑。
- **NON_GOALS**：這一波不調整 context/window、效能配置、模型或程式碼；不查看/公開原始生成文字；不評分目前兩份輸出、不持久化 defaults、不啟動 final cohort／E2E／Stage 05。
- **OWNER_VIEW**：必要工作是得到有效且可盲評的 3×3 候選結果，再依原有核准門檻判斷是否值得持久化；重啟只讓我們有機會做一次新的 Qwen 樣本，不代表成功。速度診斷屬Supporting，不能藉由調小 window 讓品質實驗失去可比性。
- **GLOBAL_GATES_AND_RATIONALE**：精確 model/context/profile/input identity 是 parity 分母與重現性必要條件；單次 recovery 限制可避免失敗後不停重試、挑選有利樣本；raw 隱私界線不變。失敗只阻斷當前 candidate cohort，不能把 implementation 改判失敗。
- **COMPLEXITY_BUDGET**：僅新增一個有明確環境觸發條件的 recovery attempt 與一個新 cache key；不新增程式 abstraction、依賴或品質 gate。

## 0.13 rev15 變更紀錄（回應候選 3×3 之雙模型品質 FAIL 與 Stage 01b 根因複核）

本 revision 保留 rev14 的固定輸入、模板、產品 commit、Qwen 3.8 **27B** identity、raw/privacy 分層、候選／final cohort 隔離、profile persistence 條件、E2E provenance、byte rollback、status-contract fixtures 與既有歷史證據。僅更新品質目標的目前工程 proxy、診斷順序、根因可觀測性與其依賴的 acceptance/routing 條文。

| 項 | rev15 決定 | 影響 |
|---|---|---|
| **目前工程 acceptance** | 使用者最新目標取代本波的舊嚴格 `<10%` gate 作為目前工程迭代門檻：Gemma 4 31B、Qwen 3.8 27B 各自各 3 份 fresh output，四個 frozen dimensions 每一份皆須 `L_d >= 0.80 × C_d`，且不得有 adjudicated major fidelity hard fail。這是透明的 **provisional engineering proxy**，不是對使用者目標或客觀品質的等價宣稱。 | §1、§5、§8、§8.1 |
| **既有候選結果** | rev14 candidate 仍按當時核准的 `<10%` 規則記錄為雙模型 `FAIL`；不追溯改判、不重算舊分數、不將 proxy 倒套舊 cohort。後續 fresh cohort 才依 rev15 proxy 計分。 | §5、§8 |
| **診斷優先** | `DEBUG_STATUS: INVESTIGATION_ONLY`、`FIX_TYPE: UNKNOWN`，直到第一個可重現 divergence 被追到 final delivery；不先改 prompt、threshold、requiredness、gating、fallback 或 priority。 | §0.14、§8 |
| **階段邊界可觀測性** | 每個 local run 必須分別記錄 hash-only / allowlisted metadata：extraction raw、extraction cleaned、consolidation input（notes-only 或 notes+transcript）、final generation raw→cleaned→finalized、每輪 refinement raw→cleaned→finalized、guard accepted/discarded 與 final selection。`_finalize_record_text` 必須標出是否收到 source context。 | §0.14、§8 |
| **merge 證據解讀** | zero-loss concat／`merge_rounds=0` 僅排除本 cohort 的 LLM merge 這一條路；不排除 extraction truncation、cleaning、context omission 或 final/refinement loss。單次未重現不構成 falsification；確認須穿過 final delivery 並以 targeted control 複現或排除。 | §0.14、§5、§8 |
| **審查／路由** | threshold 語意變更與 root-cause uncertainty 使 `REVIEW_REQUIRED: YES`；先 fresh Stage 02 review，再 Stage 03 handoff。診斷波不得持久化 defaults、跑 supporting E2E 或宣稱 DONE。 | §8、§8.1 |

### rev15 Owner / Debug Contract

- **PRIMARY_OUTCOME（CORE）**：在正式產品 local-summary path 中，Gemma 4 31B 與 Qwen 3.8 27B 的 fresh 3×3 cohort 先達到 rev15 的 80% proxy；長期品質目標仍由使用者定義，proxy 不得被描述為 parity 或客觀品質證明。
- **CORE_ACCEPTANCE_SIGNAL**：每模型 3/3 outputs、每 output 四維 `L_d >= 0.80 × C_d`，且無 adjudicated major fidelity hard fail；`C_d <= 0`、identity/hash/rubric invalid 或 disagreement 無法按 protocol 裁決時為 scoped `BLOCKED`。
- **MUST_NOT_BREAK**：Qwen 3.8 27B identity、Gemma identity、Gemini 3.5 Flash-lite denominator、frozen rubric/checklist/transcript、strict per-output/per-dimension calculation、hard-fail semantics、raw/privacy boundary、local/cloud isolation、failure atomicity、truthful status routing。
- **NON_GOALS**：把 80% proxy 宣稱為 parity；重用 rev14 outputs 作 fresh evidence；只修 usability 而忽略 fidelity；改 rubric、checklist、model identity、context/quantization 或 cloud settings；用單次不重現推翻根因；在 investigation-only 階段持久化 profile 或執行 supporting audio-to-DOCX E2E。
- **CRITICAL_PATH**：fresh review of rev15 → stage-observable diagnostic run(s) in unique ignored cache → trace first divergence through final delivery and targeted control → only then plan the smallest product fix → fresh proxy cohort → conditional persistence/final cohort → independent acceptance。
- **CURRENT_STATUS**：rev14 candidate 3×3 已完成且在當時 `<10%` contract 下雙模型 `FAIL`；C-R02/C-R03 usability defects 與 C-R02/C-R03/C-R04 majority hard-fail are valid evidence。claim crosswalk/fact-label residuals remain scoped `BLOCKED` and do not overturn the gate。
- **DEBUG_STATUS**：`INVESTIGATION_ONLY`；`FIX_TYPE: UNKNOWN` until a first divergence is confirmed through final delivery and targeted control。
- **OWNER_VIEW**：必要的是先知道錯誤發生在 extraction、cleaning/context、final generation、refinement 或 finalization；單純再跑一份或只看字面 coverage 不能定位。診斷是 supporting to implementation correctness but blocks a safe fix because changing prompt/output semantics without localization risks regressions。
- **GLOBAL_GATES_AND_RATIONALE**：valid input/model/rubric/hash and privacy provenance are decision-validity CORE gates；stage traceability is a diagnostic prerequisite to avoid speculative semantic changes；unresolved scorer disagreement remains scoped to the affected claim/hard-fail decision and cannot be self-waived。

### rev15 Root-cause stage review

`Trigger → fixed transcript/profile → extraction raw → extraction cleaned → consolidation (notes-only or notes+transcript) → final generation raw → final cleaned → each refinement raw/cleaned/finalized → guard accepted/discarded → _finalize_record_text(source context) → delivered output → blind scoring`。

- `[OBSERVED]` C-R02 has the largest structural verbosity signature (high numbered-item volume, repeated sections, duplicate nontrivial lines); C-R03 is dense and over-granular; C-R04 has no broad usability defect.
- `[SUPPORTED]` Existing run logs show three extraction chunks, zero LLM merge rounds and zero-loss concatenation for the observed cohort, followed by final/refinement calls and guards that sometimes reduce missing sets but can stall. This excludes only lossy LLM merge for those runs; it does not prove extraction raw/cleaned completeness.
- `[SUPPORTED]` Anonymous issue IDs include repeated-section, wrong-destination, unsupported-detail, causal-direction, unsupported-personnel/room/admin findings. These are final-delivery symptoms, not yet a single confirmed mechanism.
- `[UNKNOWN]` Whether the first divergence is extraction omission, extraction cleaning, context omission, final generation, refinement reintroduction, or postprocess/finalization. No per-stage artifacts were retained in rev14.
- `[UNKNOWN]` A one-run non-reproduction is not falsification. Confirmation requires the same defect to be traced through final delivery and a targeted control that changes only the suspected boundary.

### rev15 Required diagnostic trace

Before any semantic product fix, a fresh controlled diagnostic run must preserve only allowlisted metadata plus hashes in a unique ignored cache. It must record, without copying raw payloads into task artifacts:

1. Each extraction chunk's raw and cleaned note hash, length/token counts, fact/decision/topic IDs, and truncation/cleaning counters.
2. Consolidation mode (`notes-only` or `notes+transcript`), input/output hashes and token counts; zero merge rounds must not be treated as proof that extraction was complete.
3. Final generation raw, cleaned and finalized hashes; whether `_finalize_record_text` received source context; parser/postprocess counters.
4. For every refinement round: raw/cleaned/finalized hashes, guard issue counts/IDs, accepted/discarded decision, and the exact selected final-stage hash.
5. A targeted control that bypasses or isolates the suspected boundary while keeping model, input, rubric and profile fixed. The diagnostic output is not scored as a replacement candidate sample.

### rev15 Falsifiable hypotheses and stop rules

| ID | Mechanism | Current evidence | Discriminator | Result handling |
|---|---|---|---|---|
| H15-1 | Extraction raw/cleaned truncation or cleaning drops/changes facts before final generation. | `[UNKNOWN]`; three chunks and zero merge do not exclude it. | Compare fact-ID/hash inventories raw→cleaned→consolidated. | Confirm only with a loss/change at that boundary; otherwise `[FALSIFIED]` for that run. |
| H15-2 | Final generation receives notes/context but emits unsupported or direction-reversed claims. | `[SUPPORTED]` by final issue IDs and high faithfulness/traceability defects. | Same-run final raw vs cleaned/finalized plus source-context flag and targeted final-generation control. | If reproduced through delivery, fix envelope may target final prompt/context handling; review required. |
| H15-3 | Refinement reintroduces defects or repeatedly fails to converge. | `[SUPPORTED]` aggregate logs show multiple guard rounds and stalled missing sets; per-alias attribution `[UNKNOWN]`. | Compare each refinement raw→cleaned→finalized and guard accepted/discarded against prior selected version. | Confirm only when a round changes a correct claim into a defect or retains a known defect; otherwise remain `[UNKNOWN]`. |
| H15-4 | Postprocess/finalization changes claims or source context. | `[UNKNOWN]`; no per-stage artifact. | Compare final refinement output with `_finalize_record_text` input/output hashes and source-context flag. | Confirm only on a deterministic transformation; otherwise `[FALSIFIED]` for that run. |
| H15-5 | Scorer disagreement alone explains the hard-fail result. | `[FALSIFIED]` as sole explanation: A/B majority hard-fail and frozen evidence still show decisive defects, while C disagrees. | Reconcile existing locked sheets under unchanged rubric; no favorable relabeling. | Preserve majority result; unresolved claim crosswalk remains scoped `BLOCKED`. |

No hypothesis is implementation-ready until its discriminator is observed across final delivery. A diagnostic failure, missing checkpoint, provenance/privacy fault, or inability to distinguish raw from cleaned data is a scoped `BLOCKED` and routes back to Stage 01; it is not a quality PASS/FAIL inference.

- **共通計分尺度**：四維皆正規化為 0–100，高分越好；每個理由必須附僅存 raw cache 的 fact/claim ID 與 transcript anchor。分數者只看各 cohort 的匿名輸出，不看模型/provider/生成順序；輸出文字可能讓人推測來源，故只宣稱遮蔽明示身份，不能宣稱絕對不可推知。
- **COMPLETENESS**：固定 28 core facts 逐條判 `HIT=1`（主要命題與必要主體／條件／方向完整）、`PARTIAL=0.5`（可辨識核心命題，但缺少不改變方向的必要細節）、`MISS=0`（未提或過於含糊）、`FABRICATED=0`（與 transcript 相反或無依據）；分數為分值加總÷28×100。任何對核心決定／人員歸屬／金額數字／日期／方向的重大 fabricated/contradicted claim 觸發 hard fail。
- **FAITHFULNESS**：將每份輸出切成原子事實主張（一個可獨立被 transcript 證真／證偽的命題；主體、行動、結果、條件或數值各自可變時分開）。有明確逐字稿支持且無反證為 grounded，否則 ungrounded/contradicted；分數＝grounded 原子主張數÷所有實質原子主張數×100。hard-fail 類別同上；語氣潤飾或純格式標題不算主張。
- **TRACEABILITY**：對相同原子主張逐一判可否找到正確 transcript 段落／時間標籤；分數＝有正確 anchor 的事實主張數÷所有實質事實主張數（包括未 grounded／fabricated）×100。缺 anchor、錯誤時間/發言者、偽標記均不計成功；分母為 0 時該輸出 invalid/BLOCKED，不以 100% 虛高。
- **USABILITY**：`U1-STRUCTURE`（結構清楚）、`U2-TOPIC-SEPARATION`（議題不混淆）、`U3-ACTION-DECISION-OWNERSHIP`（決定／待辦／責任與期限可辨）、`U4-READABILITY`（可讀性）、`U5-CONCISION`（非冗贅），各自 0/25/50/75/100，五項算術平均。每項共同錨點：0=缺失或不可用；25=嚴重缺陷使多數內容需重做；50=部分可用但有多處重大人工修訂；75=大致可直接使用僅有少數局部修訂；100=該面向無實質缺陷、可直接使用。評分者必須記下對應 rubric 項 ID，不得自行新增面向。
- **Blind assignment**：每個 cohort 的全部輸出先完成並 hash，再各自用新的隨機排列命名為候選 `C-R01–C-R09`、final `F-R01–F-R09`；mapping 與排列 seed 只存本機 gitignored raw cache。盲評者只收到匿名輸出、rubric、必要來源與 checklist，沒有 mapping、model ID/provider/run order。Stage 04 controller 不對輸出計分。候選由兩個獨立 Stage 04 blind contexts 評分；final 由 Stage 04 blind context 與 Stage 05 fresh independent context 各評一次。各自 score sheet hash-lock 後才揭露 mapping 以重算 parity，評分者不讀彼此分數。
- **Disagreement**：任何 core fact label、原子主張 grounded/contradicted 判定、source anchor 正確性或重大 hard-fail 判定不一致，或任一維度兩位 scorer 相差 `>5` 分，即由第三個 fresh blind scorer 評同一匿名組。離散判定採三者多數；數值維度採三者 median。若第三者仍無法決定單一輸出/維度，該項 scoped `BLOCKED`，不選較有利值。無觸發分歧時兩份分數取算術平均；hard fail 由兩位以上一致才定案，疑似重大錯誤交第三者。
- **Evidence linkage/privacy**：每筆 score sheet（含匿名 scorer ID、run alias、output SHA-256、transcript/checklist/rubric hash、dimension values、fact/claim IDs、hard-fail/disagreement status）及 adjudication record 的原件只在 gitignored raw cache；Stage 04/05 任務 artifact 只留 allowlisted aliases、SHA/hash、匿名 scorer IDs、各維度分數、fact/claim IDs 和狀態，不複製輸出、逐字稿、自由文字評論或對照 mapping。

## 1. Goal Contract（白話；rev15 生效）

使用者最新工程目標是：**先把正式產品地端路徑中的 Gemma 4 31B 與 Qwen 3.8 27B 各自提升到 Gemini 3.5 Flash-lite 對應維度中位數的至少 80%。** 這是透明的 provisional engineering proxy，不是把 80% 宣稱為 parity 或客觀品質；長期品質目標仍須以使用者後續明示要求為準。`backend/core/config.py` 的 `GEMINI_MODEL` 仍指向 `gemini-3.5-flash-lite`，`summarize(mode=cloud)` 仍進 `_summarize_with_gemini`。比較的是各自產品摘要路徑在相同文字輸入下的結果，不是同一 prompt 的裸模型比賽；兩路提示、萃取及後處理差異要記錄。

第一階段是決策性候選試跑：同一份 transcript 上 cloud/Gemma/Qwen 各 3 次，依凍結盲評 rubric 逐份計分。只有候選 profile 通過所有硬門檻，才有條件把六個既有地端專用 profile 值持久化為產品 defaults。持久化後必須用新 commit、新輸出和啟動時**實際有效**的 settings 再做全新 3×3；候選成績不算最終 parity，也不能因 default 設定改了就沿用。

**核心路徑**：fresh Stage 02 review → Stage 03 handoff → investigation-only stage trace → first divergence confirmed through final delivery and targeted control → smallest reviewed fix → fresh candidate 3×3 + blind score → each local model's 3 outputs meet `>=0.80 ×` Gemini median on every frozen dimension and have no adjudicated major fidelity hard fail → only then conditional persistence/final cohort → supporting E2E → Stage 05. Rev14's old `<10%` result remains historical evidence and is not retroactively reclassified. Effective failure cannot be hidden by density, word count, another dimension, or scorer disagreement.

### rev11 歷史量測（僅供根因與趨勢參考，非 rev13 acceptance）

| 模型 | P7-B 實測 | 未達條文 |
|---|---|---|
| gemma 4 31B | 核心覆蓋 21/28 → **25/28（+19.0%）** | §5 主驗收：尾段 7 條結構命中 **2/7**、**F044 未命中**（阻斷） |
| qwen 3.8 27B | 密度 78→37 條（−52.6%）、42.5→61.2 字（+44.0%） | `coverage_core` **27/28 → 25/28**（阻斷）；牆鐘 **+77.4%**（§7 觸發） |

以上是 P7-B 的歷史結果，保留作為本波根因資料；rev11 的「不宣稱 parity」非目標已由 rev12 明確取代。既有 byte rollback 與 local/cloud isolation 仍是不得破壞的工程不變式。

## 2. 根因（皆有 P7-B 實測證據）

- **R1｜萃取側區塊內漏寫（gemma）** `[VERIFIED]`
  gemma E8 的萃取筆記（`data/cache/e2e/p7b-gemma31b-e8/backend_data/debug/extraction-notes/notes-20260923-193703-2c452049.md`）
  經 `rg` 實查：**無**「政治」（F044 的實質內容）、**無**「禮堂／走廊／三樓」（F055）、
  **無**「新聞行銷處／局長室」（F066）；「選舉」只出現在「日期：未提及（僅提到近期為年底選舉前）」。
  ⇒ 這三條**不是生成階段掉的，是筆記根本沒抓到**。該場萃取階段 diagnostics 為
  `completion_tokens=1,356`（`19:34:00`）／`1,248`（`19:37:03`）、`max_tokens=8192`、
  `finish_reason=stop` ⇒ **排除 max_tokens 截斷**（註：`235–331` 是「逐字稿語意校正」階段的數字，
  非萃取階段——rev1 引註錯誤，已在 rev2 更正）。
  `chunk_count=2` 已生效 ⇒ 排除「沒有分塊」。離線重播另證實：**ceiling 6,000 時該塊（5,918 tokens）
  已含全部 7 條尾段 probe 的字面**，模型卻只寫到 `[00:32:34]` ⇒ 結論：**單次呼叫對 ~5,900 token 區塊的覆蓋不足**。
- **R2｜生成側遵循度（qwen）** `[VERIFIED]`
  qwen E8 漏掉的 F019／F056 **在它的萃取筆記裡本來就有**（Stage 05 指出 notes L47／L199，
  且 F056 的敘述比 gemma 的交付紀錄更精確）；補強第 2 輪的問題清單也明文寫了
  「議題遺漏：土地稅科倉庫漏水與土地卡重印」，模型仍未寫入 ⇒ **是「寫不出來」而非「沒聽到」**。
  **界線（rev2 修正）**：這代表瓶頸是**遵循度／收斂**，**不是**「清單裡沒有這一項」⇒
  只加一類同粒度期望（rev1 的 C2a）**不會**改變這型失敗（見 §3 CORE-2 的重指向）。
- **R3｜成本結構改變（qwen）** `[VERIFIED]`
  qwen 牆鐘由 E6b 1,023.2 s 升至 1,814.9 s（+77.38%）。機制是**呼叫數增加**
  （萃取 1→2、補強輪 1→2、logical_generations 3→5），不是單次變慢。
  另實測**每輪補強 ≈360 s**（`20:26:56`→`20:32:56`）、**單次尾段萃取 ≈150.5 s**、
  **整份萃取 ≈340.6 s**（`evidence/tail-extraction-probe/README.md` A4）⇒ 本波成本上限即以此推導。
- **R4｜門檻在實測變異內，單場不可判定** `[SUPPORTED]`
  qwen 歷史擺動 `0.7857 ↔ 0.9643`（18pp）。**標籤降級理由（rev2）**：兩場 SHA 不同
  （E5 `ce99502` vs E5b `eaa4f45`），中間有 `58e65de`；實查 `data/glossary/*.txt` **兩檔皆無 BOM**
  ⇒ 該 commit 對本場行為 byte 等價，擺動仍可視為抽樣變異 ⇒ 結論可用，但字面「同 build」不成立。
  **對本波的意義**：28 條制的 ±10pp ≈ ±3 條 ⇒ n=2 只能偵測 >10pp 的真回退（見 §5）。
- **R5｜既有標註門檻回退（gemma）** `[VERIFIED]`
  `on_start_tag_ratio` 0.9615（E7C）→ 0.84（E8）、`on_start_tag_ratio_excluding_zero` 0.95 → 0.8095；
  Stage 05 另發現 F054 的標註 `00:41:51` 與來源段 `[00:32:34-00:33:07]` 不符。

## 3. P7-C 既有改善設計（rev11 已落地；不是 rev13 parity 結果）

以下 C1/C2/C3 描述的控制已隨 HEAD `a576b06` 進入產品碼；它們只是 §5 所測的候選改善 profile，不是品質達標證據。rev12 的 CORE 是 §5 的同輸入語意 parity 四維評估。若這組 profile 不能達標，須按 §5 把實際 gap 轉成新修正計畫；不可重做以下已完成項目或把單元測試通過當成輸出品質 pass。

### CORE-1｜萃取側：把「區塊內覆蓋」變成可驗、可調（模型無關）

- **C1a 觀測先行**：`LOCAL_LLM_DUMP_EXTRACTION_NOTES`（P7-B 已存在，`config.py:664`，預設關）
  本波 E2E 固定開啟，並把**筆記層的尾段 7 條**列入 §5 量測（人工＋`rg`，附引文）。
- **C1b 區塊細化（值已釘死）**：E2E 使用 **`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS=4500`**。
  - 依據＝`evidence/chunk-replay-p7c/README.md`（零模型呼叫重播；重播值與產品實跑 log 對帳一致：
    依 context 推導上限 65,953、`estimated_transcript_tokens=11,711`）。
  - 該值在本場產生 3 塊（4,466／4,413／2,995），**F044 單獨落在 4,413 的塊**，其餘 6 條落在 2,995 的尾塊；
    6,000（P7-B 現值）則是 2 塊且**7 條全擠在同一塊 5,918 tokens**。審查另實測 5,500／5,860
    **不改變 F044 的處境** ⇒ 只有 ≤4,500 才能把 F044 隔進小塊。
  - 預註冊預測（含 FALSIFIER）引用 `evidence/chunk-replay-p7c/README.md` 的 §1–2 及 §3 項 1–3、5，並於每場開跑前登錄。
    該 README §3 項 4 是較早期預測，仍寫 `CALL_BUDGET` 預設 2，與本 rev3 契約衝突；不得引用或採用該項成本推論／預設值。
  - **碎片塊護欄（新）**：不得讓 E2E 落在會產生 <800 est tokens 尾塊的區間（4,000／3,000 會產生 151 tokens 碎片塊）。
    一般化的「極小尾塊併回前一塊（僅在併後仍 ≤ 預算時）」列為 **SUPPORTING S4**（非阻斷），
    因為它會改動分塊語意，需獨立測試。
- **C1c 呼叫數護欄（新旋鈕）**：`LOCAL_LLM_EXTRACTION_CALL_BUDGET`
  - **語意（明文定義，回應 I4c）**：**總萃取呼叫數上限（含所有 chunk）**；`0`＝不限制。
  - **預設值＝`0`**：使「全關 ⇒ byte 級回前波」成立（不與 C1b 互斥）。
  - E2E 顯式設 **4**（≥3 塊所需；仍有護欄作用且可被單元測試以 `2` 驗證逾限路徑）。
  - 逾限行為：在任何 provider/model 呼叫前，以完整 chunks 清單預檢；若 chunk 數大於非零 budget，**不得截斷、跳過尾塊或用部分筆記繼續生成**。中止該次本地摘要，沿用既有摘要失敗隔離流程：只回傳逐字稿並附明顯失敗警告（`summary=None`、`summary_failed=true`），不產生可被當成完整會議紀錄的部分摘要；不改 `task_processor.py:259/262`。記錄 `skipped_reason=extraction_call_budget_exceeded` 與要求／允許呼叫數。這是此單一會議的摘要降級結果，不是 observation-only skip；其他任務及全域服務不受影響。
  - 驗證：以 3 塊／budget 2 的確定性測試證明 provider 呼叫數為 0、沒有部分筆記／交付紀錄；budget 0 與 3 塊／budget 4 均照常完整處理。
- 語意不變式：`CEILING=6000`＋`CALL_BUDGET=0` ⇒ 回 P7-B 行為。

### CORE-2｜生成側：把「寫不出來」變成可觀測、可收斂（模型無關）

> rev2 重指向（回應 I3）：R2 的證據顯示 qwen 型漏寫**已進入清單仍未落實**，故本 CORE 拆成
> 「期望集合粒度」（C2a，對準 gemma F048 型）與「遵循度」（C2c，對準 qwen 型）兩條獨立機制。

- **C2a 事實級期望集合（對準 gemma F048 型）**：沿用既有逐條對帳迴圈（零新呼叫類型），
  把「**筆記已列、交付未寫**」以**事實級**粒度列出（現行期望多為議題級：議題寫了、該議題下的具體事實沒寫
  ⇒ 不會被列出）。P7-B 的 **F048 型**（E7C 有、E8 無）登錄為回歸探針。
  - 新開關 `LOCAL_LLM_RECORD_FACT_COVERAGE_ENABLED`，預設 `false`；關閉時保留既有
    `LOCAL_LLM_RECORD_COVERAGE_MODE` 與 `LOCAL_LLM_RECORD_COVERAGE_CATEGORIES` 設定，既有類別集合／issue bytes／metrics bytes
    均不得增加 `fact`。開啟時只在地端既有 coverage loop 加入 `fact` 類別與相應 metrics，不增加模型呼叫；雲端完全不讀此開關。
  - 四場 E2E 均顯式設為 `true`，以評估核准的 C2a 品質槓桿；預設關閉是為了讓所有新控制關閉時可逐位元回到 P7-B。
- **C2c 逐項處置重申（新，零呼叫的遵循度槓桿）**：在既有補強輪提示詞內（local-only 區塊），
  把上一輪未落實項目以**獨立區塊**重申，並要求模型**逐項顯式處置**（每項標明「已寫入」或
  「逐字稿無此資訊／不適用」）⇒ 讓「模型寫不出來」從靜默失敗變成可觀測輸出，且不新增任何呼叫。
  本項為 R2 型的**主要**手段。
  - 新開關 `LOCAL_LLM_RECORD_ADHERENCE_ENABLED`，預設 `false`；關閉時不插入任何新 prompt text，必須 byte 級等於 P7-B
    refinement prompt；開啟時才在 local refinement issue block 後加入逐項處置區塊，雲端路徑永不讀此開關。
  - 四場 E2E 均顯式設為 `true`；其結果不得被描述為新模型呼叫或雲端提示詞變更。
- **C2b 補強輪上限（輔助，非唯一手段；只作用於地端）**：不得把既有共享設定
  `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 由 2 改成 3；Gemini 雲端迴圈仍使用該共享值，設定與呼叫點均不變。
  新增 `LOCAL_LLM_MAX_LOCAL_REFINEMENT_ROUNDS`（地端專用，預設 `0`＝local loop 使用既有 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 作 effective limit；正值只覆寫 local loop；`0` 保持所有新旋鈕關閉時的舊行為），
  本波四場 E2E 均顯式設 **3**。另新增 `LOCAL_LLM_REFINEMENT_CALL_BUDGET`（只作用於地端，總補強呼叫數上限，`0`＝不限制、預設 `0`），四場 E2E 均顯式設 **3**。
  若非零 call budget 用盡但仍有問題，停止後續補強，保留最新完整生成且已通過既有 finalize/validation 的摘要版本，記錄
  `skipped_reason=refinement_call_budget_exceeded`；不可捨棄原始逐字稿／已完成 chunks，也不可改用半成品。這是局部品質降級觀測，不替代 CORE-A～E 判定；本波 E2E budget=3 與 local max=3，不預期觸發。
  成本已由 CORE-E 上限涵蓋（最多 +1 輪；Qwen 依自身實測 allowance，Gemma 依 §5）。
- 語意不變式：`LOCAL_LLM_RECORD_COVERAGE_MODE=off` ⇒ 完全不跑、無 log、無 metrics；
  `LOCAL_LLM_REFINEMENT_NO_REGRESSION=false` ⇒ 不得有任何守衛 log（P7-A 契約）。兩個新增 C2 開關關閉時各自不得留下
  fact-level issue/metrics 或 adherence prompt bytes；開啟只能影響 local path。

### CORE-3｜確定性專名正規化（零模型呼叫；安全網齊備）

- **開關**：`LOCAL_LLM_PROPER_NOUN_NORMALIZE`（**新，預設 False**）。
- **判定鏈（全部確定性，rev2 補齊 I10）**：
  1. **registry 優先**：`data/entities/entity_registry.json`（既有檔；既有消費者 `backend/core/fidelity_checks.py:313`）
     命中的官方名稱優先於任何近音推斷；衝突時採 registry 值。
  2. **候選定義**：以單位名詞尾綴（`股／科／室／處`）與 registry 既有專名為候選集合；
     僅處理「**交付文字中的專名不在逐字稿、而逐字稿存在唯一近音候選**」的情形。
  3. **唯一性判準**：沿用既有近音原語 `backend/services/correction.py:80-110`（`is_homophone_swap`）
     ＋`pypinyin`（`pyproject.toml:56`）⇒ 不新造重裝備；**候選數 ≠ 1 或無候選 ⇒ 保持原文**（不捏造）。
  4. **可稽核**：每次替換寫 log（`original → replaced`）＋累計計數；
     `skipped_reason` 覆蓋 `no_candidate`／`multiple_candidates`／`registry_conflict`。
- **評法（回應 I11）**：閘門 4 場（gemma×2、qwen×2）一律 **C3 關**（避免與 CORE-A/B/D 混雜歸因）；
  C3 開／關配對場列 **SUPPORTING S5**（資源允許才跑，1 場 gemma ≈40 分）。
- **反 gaming**：測試須斷言 C3 **不讀** `quality/fact_checklist.json`、提示詞不含 checklist token（沿用 P7-B 禁令）。
- 既有 `SECTION_MEETING_RECORD_TERM_FIXES`（`backend/core/prompt_templates/section_meeting.py:141`）**不動**，僅新增獨立階段。

## 4. rev11 SUPPORTING／BEST_EFFORT（歷史非阻斷項；rev13 不納入 parity 門檻）

- **S1｜E2E 投影補洞（零成本）**：把 `full_document_item_count`／`full_document_avg_item_chars`／
  `near_duplicate_items.count` 補進 `project_record_quality_metrics`（`scripts/e2e/run_owned_e2e.py:928-980`）
  **只補投影、不加門檻**（既有 5 條 `QUALITY_TAG_THRESHOLDS` 在 `:179-195`，不得新增／放寬）。
- **S2｜標註落點（R5）**：**只量測不改行為**。既有可動槓桿是模組常數
  `TAG_SNAP_TOLERANCE_SECONDS=180`／`TAG_SNAP_MAX_SHIFT_SECONDS=120`（`backend/core/text_postprocess.py:781,785`）
  與 `LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED`；**`LOCAL_LLM_TAG_SNAP_SIMILARITY` 並不存在**
  （rev1 誤引，已更正）。新增該旋鈕屬語意變更 ⇒ 本波不做，只登錄「不得放寬既有 5 項門檻」。
- **S3｜生成紀律歸因消融**：P7-B 三開關開／關各 1 場 qwen，檢驗「密度改善是否以覆蓋為代價」。成本 ≈30 分 ⇒ 排在 CORE 之後。
- **S4｜極小尾塊併回（需獨立測試）**：當最後一塊 est tokens <800 且併回前一塊後仍 ≤ 預算時併回；
  否則保持原狀（不得違反 `_validate_chunk_postcondition`）。
- **S5｜C3 開／關配對場（1 場 gemma）**：見 CORE-3 評法。
- **BEST_EFFORT｜跨場逐字稿差異**：各場 ASR／校正不同 ⇒ 跨場比對僅作觀察值。

## 5. rev13 品質 parity 量測與通過條件

**比較單位與固定輸入**：比較摘要服務本身，不把 ASR 差異當作模型品質差異。三路都必須逐位元讀取同一 canonical transcript `data/cache/e2e/p7b-qwen27b-e8/transcript.txt`（SHA-256 `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`）、`section_meeting`、同一產品 commit `a576b06fc93c4a9d057ae59cdb54f07426ce343d`；該 transcript 的來源音檔 SHA-256 為 `982151f4…012828`。開跑前 Stage 04 必須重新驗證檔案存在、hash 相符、輸入 bytes 相同、模型識別正確，否則 `BLOCKED`，不可換檔或猜補。checklist 使用 `.agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json`（67 條、core 28、SHA-256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`）；revision/hash 不同即停止並重規劃。兩份歷史 C5/本地全音檔輸出不是 parity 樣本，僅供根因參照。

**路徑、樣本與公平性**：以 `scripts/e2e/rerun_local_summarize.py` 呼叫正式摘要服務；`cloud` 的有效模型必須核對為 `gemini-3.5-flash-lite`，local 模型 key 必須分別為 `gemma-4-31b-it-mlx` 與 `qwen3.8-27b-splash`（Qwen 3.8 **27B**）。候選與最終 profile 完全相同：`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS=4500`、`LOCAL_LLM_EXTRACTION_CALL_BUDGET=4`、`LOCAL_LLM_RECORD_FACT_COVERAGE_ENABLED=true`、`LOCAL_LLM_RECORD_ADHERENCE_ENABLED=true`、`LOCAL_LLM_MAX_LOCAL_REFINEMENT_ROUNDS=3`、`LOCAL_LLM_REFINEMENT_CALL_BUDGET=3`、`LOCAL_LLM_PROPER_NOUN_NORMALIZE=false`，既有 coverage mode/categories 保持 `enforce`／`topic,decision,number,date`。其他不在此清單的設定沿用產品值並記錄。候選階段僅對 local invocation 明確設定這六個候選值；不得改雲端 invocation／共用 refinement default。

若候選盲評 PASS，Stage 04 的必要 profile-persistence wave 僅修改 `backend/core/config.py` 上述六個 local-only defaults 並同步 `.env.example` 說明值；不改使用者私有 `.env`、process environment、`config.macos.yaml`（該檔明確不供 backend runtime 載入）、模型預設／model key、`CLOUD_LLM_*`／`GEMINI_*` 或 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS`。`Settings` 的 effective precedence 是 process environment > `.env` > `config.py` defaults；persist wave 後每次正式 benchmark 必須在同一啟動 context 記錄六個**非敏感 effective values**。若 `.env`／process env 明確覆蓋任一候選值，不得覆寫它來假造 default PASS；該環境記為 `PROFILE-PERSISTENCE: BLOCKED`，先揭露具體鍵與非敏感目前值及差異，徵求使用者決定是否調整明示 override。只有六值實際相符，才能將最終執行宣稱為 profile parity。

三路各跑 3 次（共 9 份），使用唯一輸出檔與唯一、已被 `.gitignore` 忽略的執行資料目錄；記錄實際 provider/model/quantization、repo commit、模板、transcript/checklist hash、所有可取得的 generation 設定、run order、輸出 hash 與耗時。若 provider 支援 seed，固定 seed；不支援則記 `UNAVAILABLE`，不可假稱完全 deterministic。這是「同輸入、各自現行正式摘要路徑」品質比較，**不是**同 prompt／相同推理流程的裸模型 benchmark。使用固定 transcript 的比較刻意排除音檔轉錄與 `task_processor` 的逐字稿語意校正；完整 E2E 另驗本地交付鏈，但不混入這個摘要 parity 分數。

**凍結與逐份盲評的 CORE 維度**：須依 §0.13 在任何輸出生成前凍結 `quality/rubric-v1.md`；以匿名 aliases 提供給 Stage 04 blind scorer 與 Stage 05 fresh independent scorer。兩者不互看分數，且不知道 model/provider/run-order mapping；原始輸出與完整 score ledger 只在 gitignored raw cache。嚴重分歧依 §0.13 觸發第三位 blind scorer。不得把原始輸出或對照 mapping 複製到任務 artifact。

| CORE 維度 | 可重算定義 | 硬性錯誤／限制 |
|---|---|---|
| `COMPLETENESS` 核心事實完整性 | 28 條 core facts 逐條按凍結 rubric 對照 canonical transcript，分 `HIT=1`、`PARTIAL=0.5`、`MISS=0`、`FABRICATED=0`；分數＝加總／28×100。現有 `coverage-1.0.0` 字面命中只作旁證。 | checklist token 不得餵入生成模型；`FABRICATED` 依 rubric 評估並可觸發 fidelity hard fail。 |
| `FAITHFULNESS` 事實／語意保真 | 把輸出切成原子事實主張；分數＝grounded 原子主張數／所有實質原子主張數×100；按 §0.13 rubric 記錄否定、條件、數字、日期、主體／歸屬。 | 輸出發明或反轉核心決定、人員歸屬、行動、數額、日期或方向，且無逐字稿依據＝hard fail；不可由完整度或文筆抵銷。 |
| `TRACEABILITY` 來源可追溯 | 對相同原子事實主張，逐一核對可否定位至正確 canonical transcript 段落／時間標籤；分數＝正確 source anchor 主張數／全部實質事實主張數（含未 grounded／fabricated）×100。 | 缺失證據／hash 不符＝`BLOCKED`；錯誤來源／偽標籤不計成功。分母為 0 時 invalid/BLOCKED，不接受全標 `00:00:00` 虛高。 |
| `USABILITY` 結構與可用性 | 五面向為結構清楚、議題不混淆、決定／待辦／責任與期限可辨、可讀性、非冗贅；每面向依凍結的 0/25/50/75/100 錨點給分，五項算術平均。 | item count、平均字數、near-duplicate 不能替代此分數；不得事後增刪評分面向。 |

**嚴格 `<10%` 的操作定義**：只對持久化後的 final 3×3 作 PRIMARY_OUTCOME 結論。每維 `d` 先取 3 份有效 Gemini 分數中位數 `C_d`。對每份 local 輸出 `L_d` 計 `gap=max(0, 1 - L_d/C_d)`；保留未四捨五入值，僅 `gap < 0.10` 通過（等於 10% 即 FAIL）。`C_d <= 0`、baseline/model/config/rubric/score identity 無效即 scoped `BLOCKED`，不可以 P4 歷史數、epsilon 或換分母代替。Gemma 與 Qwen 分開算；每個模型 3/3 份且每份四個 CORE 維度都過才 CORE PASS。candidate 3×3 使用同公式作 profile go/no-go，但不算最終通過。不得以 local 中位數掩蓋單次退化或跨維度總平均。

**整合驗證（CORE 品質的 SUPPORTING 證據）**：通過同逐字稿評分後，Gemma 與 Qwen 各跑一場真正音檔→DOCX E2E 並驗 DOCX 可用性及模型／commit provenance。E2E 的逐字稿會經 ASR/逐字稿校正，與上述 canonical transcript 不同，因此 E2E 只證明目前交付整合，不得加入 parity 分母或以一場結果取代 3 次盲評。路徑碰撞修正只用新唯一 cache key；舊 attempt/cache 永遠不刪、不覆寫、不計分；傳給 runner 的 artifacts/runtime 路徑必須預先不存在，`runner-output-raw` 由 runner 自己建立。完整 raw transcript、輸出、log 只留 gitignored cache，Stage 04/05 任務 artifact 僅存固定 allowlist 指標、fact IDs、boolean 與 hash。

**Supporting（不單獨通過／否決品質 parity）**：現有字面 `coverage_all/core`、item count、平均字數、near-duplicate、耗時、provider 呼叫/chunk/refinement 數與 full audio-to-DOCX E2E 非品質細節。呼叫安全上限、逾時、raw/cache 隔離、模型身份、DOCX 交付及既有 local/cloud isolation / byte rollback 是具名的 MUST_NOT_BREAK 或決策有效性要求，不得為追品質而繞過。

**未達目標的路由**：有效分數中任一 local 模型／CORE 維度 gap `>=10%`，或出現 fidelity hard fail，即為真實品質 `FAIL`，不是 runner 環境 blocker；Stage 04 保留逐份分數與去識別 fact/claim IDs，依證據界定缺口後走 Stage 01 `ESCALATION_REPLAN` → fresh Stage 02 → Stage 03，聚焦失敗維度做最小產品修正並重新跑受影響 CORE 比較。不能調低 `<10%`、刪除失敗樣本、改 rubric/checklist、只選最佳輸出，或宣稱未完成 parity。外部／工具／模型 unavailable、hash 不符才是具名 `BLOCKED`；恢復後使用新的 cache key 重跑缺失的完整組別。

### rev11 歷史 P7-C 門檻（只供根因／趨勢參考；不是 rev13 acceptance）

**通則（回應 I2）**：所有阻斷條文採「**2 場皆 ≥地板** ＋ **至少 1 場 ≥目標**」的集合語意
（n=2 的「中位數」＝平均，會放行一場不達標的結果 ⇒ 不使用）。
容差下限＝本專案自訂噪聲帶 ±10pp（28 條制 ≈3 條、7 條制 ≈0.7 條）。
**明文限制**：n=2 且容差 ≥ 噪聲帶時，**小於 10pp 的變化不可宣稱是優化或回退造成的**，
一律以觀察值登錄。

| 目標 | 定義 | 儀器／命令 | 門檻（阻斷） |
|---|---|---|---|
| **CORE-A** gemma 交付層尾段 7 條 | F044／F054／F055／F056／F060／F065／F066 是否出現在交付 `.md`（附引文） | 人工＋`rg`（+ C1a 筆記層為觀察值） | 2 場**皆 ≥4/7**（1 條＝14.3pp＞噪聲帶）且**至少 1 場 ≥5/7**（＝預註冊預測值）且 **F044 至少命中 1 場** |
| **CORE-B** gemma 整體保真度地板（新，I5） | `coverage_core`（28 條核心） | `measure_coverage.py` | 2 場**皆 ≥22/28**（＝P7-B 25 −3 條 ≈10.7pp）且**至少 1 場 ≥25/28**（重現 P7-B 水準） |
| **CORE-C** qwen 整體保真度 | 同上 | 同上 | 2 場**皆 ≥24/28**（＝歷史最佳 27 −3 ≈10.7pp）且**至少 1 場 ≥27/28**（重現歷史最佳） |
| **CORE-D** qwen 密度地板（升為阻斷，I9） | `full_document_item_count`／`full_document_avg_item_chars` | `measure_record_quality.py` | 2 場**皆 ≤45 條且 ≥52 字**；且**至少 1 場 ≤40 條且 ≥58 字**（重現 P7-B 37／61.2，留 ~10% 餘裕） |
| **CORE-E** 成本（取代相對門檻） | ①**呼叫數**（確定性）：萃取呼叫數／補強輪／logical_generations；②**牆鐘**（`run_summary.json` `started_at`→`finished_at`，**非** pipeline total） | `backend.log` metrics＋`run_summary.json` | ①萃取呼叫 ≤ 實際完整塊數且 ≤ `CALL_BUDGET`(=4)；補強輪 ≤3；②牆鐘 **gemma ≤2,750 s**（＝P7-B 2,378.5＋340.6 整份萃取）、**qwen ≤2,650 s**（＝1,814.9 基線＋381 補強輪 allowance＋427.6 同路徑完整萃取 allowance，再留 26.5 s） |
| **CORE-F** DOCX | 存在且可開 | `ls`＋`unzip -t` | 阻斷（沿用 runner） |
| 反 gaming | 抽驗 2–3 條新命中事實的原文對照 | Stage 05 人工 | 阻斷（沿用 P7-B 禁令：不得把 checklist 關鍵詞寫進提示詞） |

**觀察值（不得單獨通過或否決；修掉 rev1 的規範／觀察混用）**：近似重複對（≥0.80）、
筆記層尾段 7 條、標註落點（`on_start_tag_ratio` 等 5 項既有門檻仍由 runner 判定）、
「不得再回退」清單（gemma F048 型；單條無法在噪聲帶下否決，故只登錄）。

**密度升為阻斷的理由（I9）**：本波新增兩條會直接影響密度的槓桿（多塊萃取＝素材碎片化、
第 3 輪補強＝整份紀錄重生成），密度有實質回吐風險；且密度是使用者最直接可感的維度（P7-B 已量測 −52.6% 條目）。

**Qwen 成本上限推導（RV-003；開跑前固定，不得看結果後調門檻）**：P7-B Qwen E8 的
`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-qwen27b-e8/run_summary.json`
實測同音檔、同本地路徑牆鐘 1,814.937858 s；`data/cache/e2e/p7b-qwen27b-e8/backend.log`
記錄兩塊萃取合計 427.6 s，且兩輪補強各約 381 s、360 s。新分塊的單一額外 Qwen 呼叫尚無直接實測；因此不假稱 150.5 s Gemma 尾段探針可外推，而用 Qwen 已量到的**完整兩塊萃取總時間 427.6 s**作保守增量 allowance，並用 Qwen 實測補強輪較慢值 381 s：
`1,814.937858 + 427.6 + 381 = 2,623.537858 s`，上取整至預註冊硬上限 **2,650 s**（含 26.462142 s 餘裕）。這是成本預算而非新 chunk 精確耗時預測；Stage 05 必須報告每場實際牆鐘／呼叫數，不得事後改門檻。若基線、日誌或計時失效，CORE-E 記 `BLOCKED`，不可估算代替。

**E2E 場次**：gemma 2 場（必）、qwen 2 場（必）＝4 場；資源允許再跑 S3／S5。
**預註冊**：每場開跑前寫下「塊數／各塊 tokens／尾段 7 條落點／預期命中集合」，跑完對帳。

## 6. P7-C 既有停損與回退（保留的安全不變式）

以下是已核准 P7-C local profile 的防止部分摘要／雲端耦合規則；rev12 固定 transcript 的九份摘要量測不以舊 CORE-E 牆鐘值判定品質。若後續修正產品行為，這些安全不變式仍適用，除非另經 Stage 01/02 明確重規劃。

- 停損以 **CORE-E（呼叫數＋由實測推導的絕對牆鐘上限）** 判定；**不再**用「相對對照場 +15%」（P7-B I14 教訓）。
- C1c 超限必須在任何萃取呼叫前拒絕該次本地摘要；禁止為滿足呼叫數上限而丟棄 transcript chunks。受影響任務沿用現有摘要失敗行為，只提供逐字稿與明顯警告，不得產出可驗收的部分會議紀錄；這是**單一會議摘要降級**，不得升級成全域服務 veto，亦不得改 `task_processor.py:259/262`。若固定 E2E 音檔實際需要超過預註冊 4 呼叫，該輸出不可計為會議紀錄或 E2E 品質 PASS；代表「3 塊預期」前提失效：Stage 04 停止後續 E2E、記 `PRIMARY_OUTCOME_STATUS: UNKNOWN`、`IMPLEMENTATION_STATUS: ESCALATED`、`CORE_ACCEPTANCE_STATUS: BLOCKED`、`TASK_CLOSURE_STATUS: REPLAN_REQUIRED`，不得暗中加大 budget。
- 任一槓桿可獨立關閉；全關（`CEILING=6000`、`CALL_BUDGET=0`、
  `LOCAL_LLM_RECORD_FACT_COVERAGE_ENABLED=false`、`LOCAL_LLM_RECORD_ADHERENCE_ENABLED=false`、
  `REFINEMENT_CALL_BUDGET=0`、`MAX_LOCAL_REFINEMENT_ROUNDS=0`（沿用既有 `MAX_REFINEMENT_ROUNDS=2`）、
  `PROPER_NOUN_NORMALIZE=false`，並保留 P7-B 原有 `LOCAL_LLM_RECORD_COVERAGE_MODE` 與 categories 預設值）
  ⇒ **local prompt／metrics／輸出 bytes 級回 `ab2528b` 行為**（`git show --stat ab2528b` ＝只新增 `.agent/` 證據檔，產品樹即 P7-B `5cff85f`）。
  `LOCAL_LLM_RECORD_COVERAGE_MODE=off` 仍是既有獨立契約，不可用來代替兩個新 C2 flags，因 P7-B 預設為 `enforce`。
- 觸發停損時：先關「本輪新增槓桿」，保留 P7-B 已知成果（分塊＋密度），並登錄 `escalation.md`；**不得**就地改語意。

## 7. P7-C 跨模型／跨 OS 的既有相容要求（本地目標以外的實機驗證仍 best-effort）

- 全部槓桿位於 `_summarize_with_local_pipeline`（引擎分派點之後）⇒ LM Studio／Ollama 同碼路徑。
- 不得出現 `platform.system`／`sys.platform`／`os.name`／`darwin`／`win32` 或模型名判斷
  （測試強制；既有函式清單式檢查在 `tests/test_t20260923_p7b_generation_discipline.py:183-193`，新函式須加入）。
- 新開關（含 `LOCAL_LLM_RECORD_FACT_COVERAGE_ENABLED`、`LOCAL_LLM_RECORD_ADHERENCE_ENABLED`）全部登錄 `.env.example`；一般 guard skip 路徑記 `skipped_reason`（observation-only）；C1c 超限依 §3/§6 是阻斷該次摘要的明確降級，不能當 observation-only 繼續生成。
- Windows／Ollama 實機仍 `[UNVERIFIED]`，Stage 05 對「守衛是否被評估／為何被跳過」做顯式斷言。

## 8. 驗證計畫（Stage 04 → Stage 05）

### rev13 原始執行波（由 rev14 唯一恢復條款補充；其他條件仍有效）

1. （已由 rev14 取代）Stage 01 更新同一任務 `PLAN_REVISION=13` → **Stage 02 fresh attempt-13** → Stage 03 編譯 rev13 handoff → fresh Stage 04；rev12 的 attempt-12 不可沿用。
2. Stage 04 在 `execution.md` append-only 補記 attempt-03 確切終態：helper build/probe 已過，但 wrapper 預建 runner-owned artifact directory、runner `exist_ok=False` 因而 exit 1；backend／upload／摘要推論均未開始，不是模型品質 FAIL。不得回寫舊 attempt、刪除或重用其 cache。
3. 在任何新摘要輸出生成前，依 §0.13 寫入 `quality/rubric-v1.md` 並記錄時間、核准 Plan hash、固定 input/checklist hashes、rubric hash；hash 完成以前不得產生／開啟摘要輸出。
4. 候選階段只讀核對 HEAD/工作樹、transcript/checklist/model identity、模式與 settings；候選 local invocation 明確使用 §5 profile，cloud 使用其現行值。目標 transcript 必須逐 byte SHA 相符；Gemini model/provider 錯、local key 不是 `gemma-4-31b-it-mlx`／`qwen3.8-27b-splash`、模板/settings 無法確定或資料缺失即 scoped BLOCKED，不可 fallback 到其他模型／舊輸出。
5. 按 §5 round-robin 進行候選 3×3（cloud/Gemma/Qwen 各 3 份）；輸出、stdout/stderr、service log 放入新的 gitignored raw cache，每個 `--out` 唯一，不預建工具自管目錄。Stage 04 controller 只管理生成與匿名 alias，不評分；兩個 fresh blind scorer 只見 `C-R01–C-R09`，score ledger／identity mapping 僅留 raw cache。候選任一模型未達各維度 3/3 `<10%` 或 hard fail，記 candidate gate `FAIL`，保留 evidence、轉 Stage 01 fresh replan；不得持久化該 profile或執行 supporting E2E。
6. 候選 gate 通過後，Stage 04 持久化 §5 的六個 local-only defaults 至 `backend/core/config.py`，同步 `.env.example`；修改前取得同 HEAD 的完整 `FULL-SUITE` baseline。不得碰使用者 `.env`／環境變數、`config.macos.yaml`、共享 refinement default、cloud/provider/model 設定或模型預設。更新／新增 focused config-precedence/local-vs-cloud contract tests；以乾淨 settings 證明六個 defaults 生效，以明確 override 證明使用者覆寫仍優先，再檢查 cloud 路徑／prompt/provider 完全不變、既有 off/rollback 行為維持。若需要變更更廣語意則停止並重新規劃，不在此波擴大。
7. 產品變更通過核准的 focused checks、`BYTE-ROLLBACK` 及 post-change `FULL-SUITE BASELINE_DELTA` 後，建立本機產品/test commit。於同一啟動 context 安全記錄六個 effective local settings；如任何 `.env`／process override 與 profile 不同，不改寫使用者設定，標 `PROFILE-PERSISTENCE: BLOCKED` 並提出精確、非敏感差異及需要 owner 決定的選項，停止 final benchmark。
8. 只有產品 commit、有效 settings、rubric/input/model provenance 全符合時，使用新 cache keys 做全新的 final cloud/Gemma/Qwen 3×3；final 輸出匿名為 `F-R01–F-R09`，由 Stage 04 blind scorer 評分。Candidate outputs/scores 不得併入或替代 final 組。最終任何 local gap `>=10%` 或 hard fail 皆 CORE=`FAIL`，按新 evidence 走 Stage 01 `ESCALATION_REPLAN`；不能調門檻、重抽樣或偷偷改 prompt／settings。
9. 僅當 final Gemma/Qwen 都達 §5 3/3×全維度條件後，才各執行一場 true audio→DOCX E2E。用全新 ignored cache keys；runner raw output/runtime 路徑須先不存在並由 runner 建立。它們只驗 supporting integration、不混 parity 分數；ASR/helper blocker 不抹除有效 final CORE 分數。
10. Stage 05 fresh read-only acceptance 以盲化 alias 獨立評分 final 9 份、依 §0.13 處理 scorer disagreement，核對 raw hashes、最終 effective config、兩場 E2E、狀態矩陣與隱私。只有 Stage 05 PASS 且 required checks closure-satisfied 後，才依授權規則決定 push；未過不發布。

### rev14 唯一恢復條款（優先於上述 rev13 已執行步驟）

1. Stage 01 rev14 → **Stage 02 fresh review attempt-15** → Stage 03 封存前一 handoff 並產生 rev14 handoff；fresh Stage 04 必須核對 Plan/handoff revision 與 hash 一致。
2. 保留 C-R01、C-R02、C-R03 舊 cache 和所有既有證據；不得開啟或評分它們的 raw output。確認更新後 LM Studio API reachable，記錄安全 allowlist 的 app/service version、唯一 loaded LLM、model key、quantization、loaded context。載入的模型必須恰為 Qwen 3.8 27B (`qwen3.8-27b-splash`)，context 必須是 65,536；不符即停，不自動換型號／調 window。
3. 只做一次新 recovery request，操作 run ID 為 `C-R03-recovery-01`，原始輸出/log 只放全新、gitignored、唯一 cache；其他模型、transcript SHA、template、profile、rubric 和 generation 設定須逐項沿用 §5。Stage 04 不計分、不讀原始輸出；只有 exit 0 且有效 output/hash 齊全，才在 blind mapping 中將其指定為 candidate alias `C-R03`（Qwen run 1/3）。舊失敗 C-R03 永不計入樣本。
4. Stage 04 controller 不設 30 分鐘總任務取消；持續等待 LM Studio 回覆並記錄實際時間。產品內每次請求既有 timeout 維持 1,800 秒；C-R03 已知 signature 是 `predict` error，並無 timeout 證據。若新請求確實以 timeout 結束，按下條文停，不自行提高 timeout 或改產品碼。
5. recovery 任何非零／無輸出／timeout、model/context/profile/hash 不符，立即停止候選波並回 Stage 01 evidence-backed replan；不再自行重試，不評分，不持久化，不進 E2E／Stage 05。只有 recovery 完整 exit 0 後，才按既有 round-robin 順序繼續 `C-R04–C-R09`；其餘任一候選 runner 非零仍依原 stop condition 立即停止。

### rev11 P7-C 實作波程序（歷史；已執行，不是 rev13 的當前 runbook）

以下 rev11 步驟記錄既有 P7-C controls 的開發／回退證據程序，留作 provenance 與將來修正時的參照；不得取代 rev13 §5 的品質目標，也不得因其中寫有「CORE-A–F」或四場就當成 parity PASS。rev13 若要改現行語意，必須先由 Stage 01 針對新證據重規劃。

1. ~~Stage 01 escalation-replan rev11 → Stage 02 attempt-11 → Stage 03 rev11 handoff → fresh Stage 04。~~（已完成之歷史步驟；核准與 handoff 不授權 rev12。）
2. **產品碼變更前取得完整全庫基線**：先查 `execution.md` 的 Stage04 rev6 baseline 證據是否在固定 HEAD `ab2528b`、且確實早於所有產品/test mutation；有效時可重用已記錄的 `DATA_DIR=/tmp/p7c-baseline-Z64k1x uv run --frozen pytest tests/ -q`（1129 passed, 2 skipped）。若該證據無效或需重跑，必須 `mktemp -d /tmp/p7c-baseline-XXXXXX` 建立新空目錄，明確記錄實際 `DATA_DIR`、完整命令、exit code 與摘要；**不得使用、覆寫或刪除**既存 `/tmp/test_scratch` 或舊 scratch。中斷的 pytest 不算基線。若仍無有效基線，依 §8.1 `FULL-SUITE` 標記，不得假設為乾淨。
3. 每個 CORE 切片先做**零模型呼叫驗證**（離線重播／單元與契約測試），再做 E2E；每個新開關需單元測試、`.env.example` 文件化及全關 byte 級回退證明。C2a flag 關閉時維持既有 categories、issue/prompt/metrics bytes；開啟時才新增 fact 類別。C2c flag 關閉時 refinement prompt bytes 等於 P7-B；開啟時只改 local refinement prompt，cloud prompt/output bytes 仍不變。兩個 flags 的開關路徑與回退測試分開驗證。

   **BYTE-ROLLBACK 固定零呼叫比較程序（不可用真實模型輸出代替）**：Stage 04 新增 `tests/test_t20260923_p7c_byte_rollback.py`，只用測試內固定合成 fixture（不得讀固定音檔、真實逐字稿、快取或使用者輸出），mock 所有 local/cloud provider 呼叫並回傳固定筆記／摘要；斷言沒有任何真實 provider/network 呼叫，且 local refinement 至少執行一次。基準來源固定為完整 commit `ab2528b718e8c91557fd72db174b0f9bb78d3a68`：以唯一暫存 detached worktree 執行同一 harness；將 harness 以 untracked 測試檔形式暫放至該 worktree，以 capture mode 執行 `P7C_BYTE_ROLLBACK_CAPTURE_BASELINE=1 uv run --frozen pytest tests/test_t20260923_p7c_byte_rollback.py -q`，只擷取預期欄位 SHA-256，確認該 worktree 的 tracked files 未變後移除本次暫放檔。capture mode 必須容許舊 commit 尚無兩個 C2 settings，將其視作關閉，不得改寫 baseline source。測試 checkout 亦以 `uv run --frozen pytest tests/test_t20260923_p7c_byte_rollback.py -q` 對同一固定輸入與 settings 執行並逐位元比較。測試 fixture `tests/fixtures/p7c_byte_rollback_ab2528b.json` 只保存基準 commit、fixture ID、設定值及各欄 UTF-8 SHA-256，不存任何 prompt／紀錄／逐字稿原文。回退配置明確為兩個 C2 flags `false`，其餘新旋鈕依 §6 全關值，舊 `LOCAL_LLM_RECORD_COVERAGE_MODE=enforce`、`LOCAL_LLM_RECORD_COVERAGE_CATEGORIES=topic,decision,number,date` 保持 P7-B 預設，不可改成 `off`。

   每個比較欄位以原始 UTF-8 bytes（不做 Unicode、空白或換行正規化）計 hash 並要求 expected hash 與 actual hash 完全相等：`coverage_issues` 的穩定 JSON bytes、`_record_coverage_metrics_fields()` bytes、完整 local initial/refinement system 與 user message bytes、local 最終 finalized record bytes、cloud 各提示訊息 bytes，以及 cloud finalization/output bytes。C2a 與 C2c 分別以只改動該 flag 的 case 驗證，另有兩者皆關閉的整條 local pipeline case；cloud 在 C2 flags false/true 組合及 local-only 設定變動下均須與固定基準相等。若 metrics/log 包含時鐘欄位，harness 必須固定時鐘；不得用遮罩非決定性位元的方式讓 prompt、metrics 或輸出 bytes 比對通過。Stage 04 將比較結果追加至 `.agent/tasks/T20260923-2050-01-local-extraction-adherence/verification/byte-rollback.json`，只記錄基準 SHA、測試命令／exit code、fixture ID、各欄 expected/actual SHA-256 與 equality boolean、實際 provider 呼叫數 0；不記錄原始字串。缺基準 checkout、固定 fixture、hash 或可比證據＝`BYTE-ROLLBACK: BLOCKED`；任一 byte/hash 不同＝`TASK_REGRESSION`。
   C2b 契約測試固定含：local max=`0` 繼承既有共享值 `2`；local max=`3` 且 shared=`2` 時地端可到第 3 輪；refinement budget=`1` 時只做一輪且保留該輪完整有效摘要；將 local max 改為 `3` 不改 Gemini 雲端 loop 的共享上限（仍為 `2`）、雲端提示詞 bytes 或輸出 bytes。全部用 stub/mock 確定性驗證，不作模型呼叫。
4. **E2E 前置（I12 保留）**：實作完成且 focused tests 綠 ⇒ 先 commit（只含產品碼＋測試），記錄該 commit SHA；主工作樹的任務計畫／Review／Stage 04 證據保持原位，不納入此 commit。
5. **E2E clean-worktree 執行（回應 rev4 escalation；決策性 preflight）**：
   - 用 `mktemp -d` 配置該執行 repo context 之外、無既有使用者內容的唯一暫存目錄；`git worktree add --detach <path> <產品測試 commit SHA>`。由同一執行 repo context 證明 `git -C <path> rev-parse HEAD` 等於固定 commit、runner script root 位於此 checkout，且每一場啟動前後 `git -C <path> status --porcelain` 為空。記錄 detached/head/root-match/clean booleans 與 commit/hash，不把絕對路徑寫入 task evidence。不可重用既存舊 detached worktree；無法在實際執行 context 驗證即停止並具名 BLOCKED，不以父 repo 看不到該路徑就臆測成功或失敗。
   - **Apple ASR helper preflight（rev11）**：在本次新建 detached worktree 內執行既有 `swift build -c release --package-path apple_speech_cli`；確認 `apple_speech_cli/.build/release/apple-speech-cli` 存在、`.build/` 被 package `.gitignore` 忽略、build 後 HEAD 不變且 porcelain 為空。不得使用 `--help` 作成功條件：CLI 不支援該選項，預期 input error 5 僅是診斷、不代表 helper runtime failure。以新且未存在、先經 `git check-ignore` 證實的 `data/cache/e2e/p7c-asr-helper-probe-r11/` 保存 `apple-speech-cli probe --locale zh-TW` 的 stdout/stderr raw JSON；不得印出 JSON。僅當 probe exit=0、`locale_supported=true`、`transcriber_is_available=true` 且 `locale_installed=true` 時，此 preflight 才 PASS。若 probe/平台/語系條件失敗，記具名環境 BLOCKED；若 locale 未安裝，記 AUTHORITY_REQUIRED、停止且先請使用者明示是否允許系統 asset installation；以上狀況均不得載入模型或啟動 runner。Package.swift 無外部 package dependencies。
   - 從 detached worktree 執行**原封不動的** `scripts/e2e/run_owned_e2e.py`，明確傳入 `--expected-revision <同一 SHA>`。Reviewer 已確認 runner `REPO_ROOT` 取自執行中腳本路徑，絕對 `--artifacts-dir`／`--runtime-dir` 不會被改寫；但 `artifacts_dir` 內含完整 health/model `raw_response`、TaskInfo（含 `original_filename`／自由文字 `user_prompt`／可能的 `error_message`）與失敗時 response body，故**整個 artifacts_dir 都視為 raw**，不採 runner docstring 的 redacted 宣稱。
   - 每場先確認全新的 attempt 路徑不存在，且主工作樹對 `data/cache/e2e/<唯一 attempt>/` 兩個子目錄均有 `git check-ignore` 命中；再令 `--artifacts-dir` 與 `--runtime-dir` 指向該 gitignored 目錄下不同絕對子目錄（`runner-output-raw/`、`runtime-raw/`）。不得指向 `.agent/tasks/`。這兩個路徑在 detached worktree 之外，保持 clean gate 為零 porcelain。**整個兩目錄均視為含敏感 raw 資料**：runner 的 `health_snapshot.json`／`model_snapshot*.json` 含原始 response，`task_final.json` 含 `original_filename`、自由文字 `user_prompt` 及可能的 `error_message`，錯誤路徑可存 response body；`runtime-raw` 含 backend.log／transcript／DOCX／DATA_DIR。所有原件只留本機 gitignored cache，不寫入或複製到 Review、execution、聊天或 task evidence。
   - 四個有效品質樣本 alias 固定為 `GEMMA-E1R`／`GEMMA-E2`／`QWEN-E1`／`QWEN-E2`，cache keys 相應為 repo-relative `data/cache/e2e/p7c-gemma-e1r`、`data/cache/e2e/p7c-gemma-e2`、`data/cache/e2e/p7c-qwen-e1`、`data/cache/e2e/p7c-qwen-e2`。舊 `data/cache/e2e/p7c-gemma-e1` 永久保留為 GEMMA-E1 失敗嘗試，嚴禁覆寫／清除／計分。每場 `runner-output-raw/` 與 `runtime-raw/` 均各自唯一且不存在。
   - Stage 04 在 `.agent/tasks/<TASK_ID>/e2e/<唯一 attempt>/result.md` 只追加固定 allowlist 的 redacted derivative：`RUN_ALIAS`、repo-relative `CACHE_KEY`（不含使用者絕對路徑）、產品測試 commit SHA、runner expected/actual build revision 與 match 布林值、模型家族標籤、PASS/FAIL/BLOCKED、牆鐘秒數、呼叫／chunk／輪數、核准 metric 數值與 fact IDs、固定 runner 檔案類別及各原件 SHA-256。不可加入 `raw_response`、response body、輸入音檔 basename／TaskInfo `original_filename`、自由文字 prompt、Task ID、絕對本機路徑／裝置資訊、transcript／DOCX 內容；錯誤僅留穩定分類，不附原始錯誤字串。Stage 05 在本機 read-only 依 `CACHE_KEY` 對照 cache 原件／hash，輸出同一 allowlist，另僅在 CORE-A／ANTI-GAMING 必需時附最短去識別來源引文；不得複製 raw payload。
   - 四場固定 Gemma 4 31B ×2、Qwen 3.8 27B ×2；每場明確設 `LOCAL_LLM_RECORD_FACT_COVERAGE_ENABLED=true` 與 `LOCAL_LLM_RECORD_ADHERENCE_ENABLED=true`，並沿用 C1/C2b 釘死值、C3 關閉。每場前後記錄 detached worktree HEAD／porcelain 和 SHA。產出若落入不合規路徑、task evidence 含未 redacted raw payload、HEAD 改變或 worktree 出現非空 status，該場不得計入 E2E PASS；立即停後續 E2E 並記錄 scoped blocker／replan，不修改 runner、ignore/exclude 或預註冊門檻。
   - 此隔離保持 runner 原本 clean-HEAD 決策性 gate 的效力，同時不提交或搬移主工作樹任務證據。Stage 05 在結果可用期間查驗 redacted derivative 與對應 gitignored cache 原件；所有必需驗收結束後，只可清理本任務建立且已核實無需保留資料的暫存 worktree，不得使用 `--force` 或刪除非任務資料。
6. Stage 05 獨立驗收：CORE-A／B／C／D／E／F 逐條、DOCX、反 gaming 抽驗、成本對帳、E2E commit provenance、狀態路由與殘餘風險。
7. 產出 `result.md`；誠實登錄未達項，不得以觀察值替代阻斷條文或把 `BLOCKED`／`NOT_RUN` 改寫成 `PASS`。
8. **完成後 commit + push（原始任務 brief 明確要求，非本輪即時動作）**：原始 user-supplied task brief（2026-09-23）要求完成 Stage 05 並驗收通過後才 commit + push；不從本輪 E2E 請求推導發布權限。只有 Stage 05 對目前產品／測試 commit 的獨立驗收為 `PASS`、所有 required checks 均 closure-satisfied，且沒有待修復、待複審或未解硬閘門後，才將該產品／測試 commit push 至 `origin/fix/qwen-local-quality-parity`；不 force-push。Stage 05 若判定 `FAIL`／`BLOCKED`，或 required verification 尚未閉合，保留本機 commit、不推送，按既定修復／replan 路由繼續。Push 前確認 remote 更新可 fast-forward；若遠端已前進或 push 被拒，停止並回報，不自行 rebase／改寫歷史。完成後驗證遠端分支指向預期 commit。不得將 gitignored raw E2E cache 納入任何 commit。

### 8.1 狀態感知驗證、基線與閉合（workflow-routing.md §7）

每個下列檢查在計畫時的初始值均為 `CHECK_RESULT: NOT_RUN`、`WAIVER_STATUS: NOT_ALLOWED`；Stage 04/05 依實證更新，永不回寫成推測的 PASS。所有列均為 `WAIVER_ALLOWED: NO`、`WAIVER_AUTHORITY: NONE`；代理不得自行豁免。`GOAL_CRITICALITY` 是對主要結果的貢獻，不等於是否為閉合閘門。

| CHECK_ID | 服務目標 | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_REQUIRED | FAILURE_CLASSIFICATION_RULE |
|---|---|---|---|---|---|---|
| `PARITY-COMPLETENESS` | REQ-品質：Gemma/Qwen final 組核心事實完整度相對 Gemini | CORE | OUTCOME | HARD_CLEAN | NO | 持久化後 final 組任一 local 3 份輸出 gap `>=10%`＝FAIL；候選只記候選 gate；輸入／評分無效＝BLOCKED；字面 coverage 不能取代人工語意評分。 |
| `PARITY-FAITHFULNESS` | REQ-品質：final 組主張有據、無重大捏造／矛盾 | CORE | OUTCOME | HARD_CLEAN | NO | final 組任一 local 重大捏造、關鍵數字／歸屬錯誤或語意反轉＝FAIL；其餘任一輸出 gap `>=10%` 亦 FAIL；證據缺失＝BLOCKED。 |
| `PARITY-TRACEABILITY` | REQ-品質：final 組重要主張能追溯到同一逐字稿來源 | CORE | OUTCOME | HARD_CLEAN | NO | final 組任一 local gap `>=10%` 或偽來源標記＝FAIL；候選不作 final acceptance；來源證據無效＝BLOCKED。 |
| `PARITY-USABILITY` | REQ-品質：final 組依凍結 blind rubric 的結構與可用性 | CORE | OUTCOME | HARD_CLEAN | NO | final 組任一 local gap `>=10%`＝FAIL；rubric 未於生成前凍結、評分／adjudication 缺失＝BLOCKED。 |
| `RUBRIC-FREEZE` | 決策有效性：生成前 rubric version/hash、盲化分派與 scorer protocol 固定 | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | 未於首份輸出生成／檢視前凍結，hash、Plan/input link、匿名 mapping 或 scorer protocol 缺失＝BLOCKED；凍結後改 rubric＝REPLAN_REQUIRED。 |
| `PARITY-PROVENANCE` | 決策有效性：final canonical input/checklist、產品 commit/effective settings、cloud/local model keys、匿名 output hash、rubric/scorer evidence 均符合 §0.13／§5 | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | 任一 hash/model/commit/config/rubric 不符或 raw evidence 無法 read-only 獨立重核＝BLOCKED；不得把候選組、舊 C5 或異 transcript 補入 final 組。 |
| `PROFILE-PERSISTENCE` | REQ-交付：通過候選 profile 已持久化到六個 local-only defaults，且 final 3×3 在產品 commit 的 effective values 全部相同 | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | 只有臨時 shell/.env 覆寫、設定 commit 未完成、effective override 不同或沒有全新 post-persistence 3×3＝NOT_RUN／FAIL／BLOCKED；不可聲稱產品目標達成。 |
| `ANTI-GAMING` | REQ-量測有效：模型提示未收到 28 條 checklist；所有事實評分可回 canonical transcript | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | checklist token 洩漏、故意選樣或輸出無來源 claim 被評為 grounded＝FAIL；prompt/原始輸出無法 read-only 核驗＝BLOCKED。 |
| `E2E-GEMMA-DOCX` | SUPPORTING 交付證據：Gemma 31B 真正音檔→DOCX journey | SUPPORTING | OUTCOME | HARD_CLEAN | NO | parity 全過後仍必須一場有效 E2E；DOCX 缺失／損壞或產品 journey failure＝FAIL，環境／ASR blocker＝具名 BLOCKED；不回寫 parity CORE。 |
| `E2E-QWEN-DOCX` | SUPPORTING 交付證據：Qwen 3.8 27B 真正音檔→DOCX journey | SUPPORTING | OUTCOME | HARD_CLEAN | NO | parity 全過後仍必須一場有效 E2E；DOCX 缺失／損壞或產品 journey failure＝FAIL，環境／ASR blocker＝具名 BLOCKED；不回寫 parity CORE。 |
| `LOCAL-CONTRACTS` | NFR-相容：六個 profile default／env precedence、local/cloud 隔離、逾限原子失敗、local-only 輪數與 budget、off/rollback、既有後處理與 fallback 語意 | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | default 未落地、明示 env override 不再優先、雲端受 local-only 設定影響、或既有安全／rollback 契約違反＝TASK_REGRESSION；使用者 override 與 profile 不同時只阻止該 profile acceptance，不得靜默改寫 override。 |
| `BYTE-ROLLBACK` | NFR-回退：兩個新 C2 flags 關閉時按固定 P7-B commit/fixture 比較 local/cloud prompts、metrics、輸出 UTF-8 bytes；僅在產品修改後需新證據時執行 | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | YES | 修改影響範圍內任一 byte/hash 不同＝TASK_REGRESSION；基準／fixture 無效＝BLOCKED；沿用上一個同 HEAD 有效 hash-only 證據時須明確核對。 |
| `PLATFORM-INDEPENDENCE` | NFR-跨平台：本波新邏輯不依 OS／模型名稱分支 | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | 只有本波有程式修改時核對；發現平台或模型分支＝TASK_REGRESSION。Windows/Ollama 實機未執行仍標 `[UNVERIFIED]`，不阻擋本機目標。 |
| `FULL-SUITE` | NFR-回歸：全庫測試 | SUPPORTING | REPOSITORY_HEALTH | BASELINE_DELTA | YES | 相同相關 failure signature 註記為 PRE_EXISTING_FAILURE；只有完整前置基線對照後無新增／惡化才可使 BASELINE_DELTA gate PASS，仍須揭露舊失敗且不得稱全庫全綠；新生／惡化且與改動相關＝TASK_REGRESSION；基線或同等環境不可得＝BLOCKED/INCOMPLETE。 |
| `STAGE05-INDEPENDENT` | REQ-獨立驗收：按凍結 rubric blind 重算 final 逐份 parity 分數並核對兩場 audio-to-DOCX integration | CORE | OUTCOME | HARD_CLEAN | NO | rubric/scorer protocol 有效才獨立驗收；分歧需第三者但無有效裁決、hash/輸入失效＝scoped BLOCKED；不得抹除 Stage 04 已證狀態。 |
| `STATUS-CONTRACT-FIXTURES` | NFR-誠實閉合：狀態、waiver、legacy 與 DONE 路由符合 v4.2 | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | Fixture 期望與 Stage 04/05 狀態不符、矛盾狀態被接受、或原 CHECK_RESULT 被 waiver/legacy 正規化改寫＝TASK_REGRESSION；fixture 無法判讀／證據缺失＝BLOCKED。這是避免錯誤宣稱 DONE 或抹除已證事實的具體正確性義務。 |
| `E2E-COMMIT-PROVENANCE` | 每場前後由實際執行 repo context 證明為新 detached worktree、`HEAD` 等於產品測試 commit、runner script root 與 checkout 相符、`git status --porcelain` 為空，health expected/actual revision 相符；完整 raw artifacts/runtime 僅存 gitignored cache；task evidence 僅 allowlist bool/hash/cache key | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | 缺 SHA/root-match/detached proof／dirty worktree／health revision mismatch／cache 分層錯誤／task evidence 含 raw payload 或無原件 hash＝對應 E2E check BLOCKED；不影響已有效的 parity CORE 分數。執行 context 必須能核實；不以父 repo 可見性臆測。 |
| `E2E-ASR-HELPER-PREFLIGHT` | 只在兩場 true E2E 前，固定 commit detached worktree build helper 並 `probe --locale zh-TW`；raw 只在 ignored cache | SUPPORTING | DIAGNOSTIC | HARD_CLEAN | NO | build/probe/locale 可用性失敗＝該 E2E `BLOCKED`，不載入模型或啟動 runner；locale 未安裝＝AUTHORITY_REQUIRED/BLOCKED；只阻斷交付 integration evidence，不抹除同 transcript parity CORE。 |

`FULL-SUITE` 雖為 SUPPORTING／REPOSITORY_HEALTH，不改變或 veto CORE 會議紀錄路徑；將它設為 `BASELINE_DELTA` 閉合閘門，是為了證明本波沒有新增／惡化回歸。相同且未惡化的前置失敗可揭露後繼續，不把全庫要求成 HARD_CLEAN；基線不可得只使 task closure pending，不阻止 Stage 04 完成實作或 CORE 驗收。

`E2E-COMMIT-PROVENANCE` 為 SUPPORTING／MUST_NOT_BREAK／HARD_CLEAN：它不評 parity 品質；但 E2E runner 本身將 clean HEAD 設為 decision-validity precondition，因此無法證明固定 commit、clean 狀態與 artifact/runtime 隔離時，該場只可記為 E2E BLOCKED，不能宣稱 integration PASS。它不抹除先前有效的同-transcript CORE 分數。Detached worktree 把失敗範圍限於 E2E 證據，不改 runner gate、產品語意或主工作樹任務證據。

所有摘要比較與 E2E 原始資料依 `security-privacy.md` 僅寫入本機 gitignored、task-scoped cache；`--artifacts-dir` 也按實際實作當 raw payload 處理，即使 CLI 文件稱之為 redacted。只有固定 allowlist 的 derivative、repo-relative `CACHE_KEY` 及雜湊留在 task evidence；不得出現絕對本機路徑、完整 request/response、自由文字 prompt、輸入音檔 basename、transcript 或 DOCX。Stage 05 必須 read-only 對照本機原件；只有為了核對 `PARITY-COMPLETENESS`／`PARITY-FAITHFULNESS`／`PARITY-TRACEABILITY` 確有必要時，才附最短去識別引文與 fact/claim ID，不複製 raw payload。

**狀態與路由**：Stage 04 的 `execution.md` 必須記錄六個正交欄位 `PRIMARY_OUTCOME_STATUS`、`IMPLEMENTATION_STATUS`、`CORE_ACCEPTANCE_STATUS`、`REQUIRED_VERIFICATION_STATUS`、`INDEPENDENT_ACCEPTANCE_STATUS`、`TASK_CLOSURE_STATUS`，以及每項檢查的上述完整欄位、阻斷範圍／證據／下一步、`PLAN_REVISION`、HANDOFF 身分／SHA-256、執行時間與可得的 artifact hash。四個 parity 維度 3/3 local 輸出皆有效且每項 gap `<10%`、無 hard fail 才可記 CORE `PASS`；有效 gap `>=10%`／重大錯誤為 `FAIL`，依 §5 replan；雲端、model identity、輸入或證據不能形成有效結論為具名 scope 的 `BLOCKED`；未執行為 `NOT_RUN`。E2E 環境／helper blocker 只阻斷對應 E2E supporting check，不回寫 parity CORE。若 full E2E 安全預算／呼叫預檢失敗而產生逐字稿-only，該場不可計為 integration PASS，按 §6 記錄且不可輸出不完整會議紀錄。

Stage 04 路由遵循 workflow-routing.md §7.7：語意／計畫前提失效 ⇒ `IMPLEMENTATION_STATUS: ESCALATED`、`TASK_CLOSURE_STATUS: REPLAN_REQUIRED`；核心 FAIL ⇒ 按政策設 implementation `IN_PROGRESS`、closure `FIX_REQUIRED`；核心 BLOCKED／NOT_RUN 分別進 `CORE_ACCEPTANCE_BLOCKED`／`PENDING_CORE_ACCEPTANCE` 並保留已證 implementation 狀態；核心通過但全庫基線差異未能結論 ⇒ `REQUIRED_VERIFICATION_STATUS: INCOMPLETE`、`PENDING_REQUIRED_VERIFICATION`，不得降格為 implementation blocker。只有 `FULL-SUITE` 基線差異已得結論，且所有其他 required checks closure-satisfied，aggregate `REQUIRED_VERIFICATION_STATUS` 才可 PASS；未結論的非迴歸驗證只能是 INCOMPLETE/BLOCKED，不能自動 waivable。

Stage 05 必須先讀取並記錄 Stage 04 `execution.md` 的 SHA-256 與不可變快照欄位 `STAGE_04_REPORTED_IMPLEMENTATION_STATUS`、`STAGE_04_REPORTED_CORE_ACCEPTANCE_STATUS`、`STAGE_04_REPORTED_REQUIRED_VERIFICATION_STATUS`；環境阻斷時保留這些快照，路由至 `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED`、`TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED`。若驗收推翻 load-bearing 計畫前提則改走 `REPLAN_REQUIRED`。只有主要結果已達、implementation complete、CORE 與 required verification 閉合、獨立驗收 PASS 且無未解硬閘門時，`TASK_CLOSURE_STATUS` 才可為 `DONE`（§7.10）。

### 8.2 Status-contract fixture inventory（Stage 04 留證；Stage 05 獨立複核）

這些是對 workflow-routing.md §7 的**確定性狀態案例**，不是產品功能或產品碼測試；每列指定輸入狀態與唯一預期路由。Stage 04 記錄結果前必須斷言 inventory 中 `FIXTURE_ID` 唯一（`len(ids) == len(set(ids))`），重複即 `STATUS-CONTRACT-FIXTURES: FAIL`，不得以 map overwrite 掩蓋。Stage 04 在 `execution.md` 的 `STATUS_CONTRACT_FIXTURE_RESULTS` 記錄每列 `FIXTURE_ID`、輸入、預期／實際狀態、`FIXTURE_RESULT` 及依據；Stage 05 逐列獨立重算／檢視並寫入新的驗收報告，**不可修改 Stage 04 execution.md 或其快照**。所有 fixture 均是 required verification；任一不符即不能宣告 DONE。

| FIXTURE_ID | 固定輸入情境 | 預期結果／斷言 |
|---|---|---|
| `SCF-01-CANONICAL-INCIDENT` | implementation 完成、CORE PASS、全庫 HARD_CLEAN/環境檢查仍有未解項、required verification INCOMPLETE | 保留已證實 implementation/CORE；closure=`PENDING_REQUIRED_VERIFICATION`；不可誤報 `IMPLEMENTATION_BLOCKED` 或 DONE。 |
| `SCF-02-IMPLEMENTATION-BLOCKED` | 產品實作未完成且在核准契約內不能安全繼續 | implementation=`BLOCKED`、closure=`IMPLEMENTATION_BLOCKED`，並具名 scope/subject/blocker/next action。 |
| `SCF-03-CORE-FAIL` | implementation 原先完成，CORE check 有效且低於核准門檻 | implementation=`IN_PROGRESS`、closure=`FIX_REQUIRED`；若 CORE 直接證明主要結果未達，primary outcome=`NOT_ACHIEVED`。 |
| `SCF-04-CORE-BLOCKED` | implementation 完成，但必要 CORE 證據受具名環境／輸入 blocker 阻斷 | implementation 保持 COMPLETE、CORE=`BLOCKED`、closure=`CORE_ACCEPTANCE_BLOCKED`。 |
| `SCF-05-CORE-NOT-RUN` | implementation 完成、必要 CORE 尚未執行 | CORE=`NOT_RUN`、closure=`PENDING_CORE_ACCEPTANCE`；不得當成 BLOCKED 或 PASS。 |
| `SCF-06-CORE-NOT-REQUIRED` | 無 CORE 的 Plan 未寫明理由／另以合理 rationale 明確標為非必要（兩個子案例） | 無 rationale ⇒ contract invalid、implementation=`ESCALATED`、closure=`REPLAN_REQUIRED`；有明確 rationale ⇒ 依其餘 closure 條件判定，不把 NOT_REQUIRED 當 NOT_RUN。 |
| `SCF-07-PLAN-PREMISE-INVALID` | 新證據推翻核准的 load-bearing 根因／語意／驗收前提 | implementation=`ESCALATED`、closure=`REPLAN_REQUIRED`；不准 Stage 04 當成機械修補。 |
| `SCF-08-BASELINE-UNAVAILABLE` | CORE PASS，但 `BASELINE_DELTA` 所需 mutation 前全庫基線缺失／不可比 | 該 check=`BLOCKED`，aggregate required verification=`INCOMPLETE`、closure=`PENDING_REQUIRED_VERIFICATION`；保留 implementation/CORE；不可猜測或自我 waiver。 |
| `SCF-09-BASELINE-DELTA` | 完整同條件前後基線顯示只有相同既有 failure、沒有新增／惡化 | 將該 failure 明列為 `PRE_EXISTING_FAILURE`；BASELINE_DELTA check 可 PASS，仍揭露舊失敗且不得稱全庫全綠。 |
| `SCF-10-HARD-CLEAN-DEBT` | HARD_CLEAN check 有已證據化的 pre-existing red，非本波 regression | check 不得標 clean/PASS；required verification=`INCOMPLETE`、closure=`PENDING_REQUIRED_VERIFICATION`；implementation/CORE 不被追溯降級。 |
| `SCF-11-FORMAL-WAIVER` | **僅合成通用案例**：fixture Plan 明示 WAIVER_ALLOWED=YES、authority=project owner；唯一未過的 required check 原 result=FAIL，owner 有完整授權證據 | waiver 可 APPROVED，但原 `CHECK_RESULT` 必須仍為 FAIL，不能改 PASS；aggregate 可按 §7.5 記 WAIVED，並繼續獨立驗收路由。此案例不授權豁免任何 P7-C gate。 |
| `SCF-12-UNAUTHORIZED-WAIVER` | 實際 P7-C check（本計畫全為 WAIVER_ALLOWED=NO）遭代理自行批准 waiver | `WAIVER_STATUS=NOT_ALLOWED`；保留原 check result；閉合仍由原 FAIL/BLOCKED/INCOMPLETE 決定。 |
| `SCF-13-INDEPENDENT-PENDING` | implementation、CORE、required verification 均 closure-satisfied，Stage 05 尚未執行且獨立驗收必需 | independent acceptance=`PENDING`、closure=`READY_FOR_INDEPENDENT_ACCEPTANCE`，不是 DONE。 |
| `SCF-14-INDEPENDENT-ENV-BLOCK` | Stage 05 因工具／輸入／環境 blocker 無法形成有效結論 | independent acceptance=`BLOCKED`、closure=`ACCEPTANCE_BLOCKED`；先保留 Stage 04 三個 snapshot 欄位與 execution SHA。 |
| `SCF-15-INDEPENDENT-PRODUCT-DEFECT` | Stage 05 有效證明核准契約內的機械產品缺陷 | independent acceptance=`FAIL`、implementation=`IN_PROGRESS`、closure=`FIX_REQUIRED`；Stage 04 snapshot 不回寫。 |
| `SCF-16-CONTRADICTIONS` | 輸入包括 `IMPLEMENTATION=BLOCKED + CLOSURE=DONE`、`IMPLEMENTATION=COMPLETE + CLOSURE=IMPLEMENTATION_BLOCKED`、CORE=`NOT_REQUIRED` 但無 Plan rationale | 三種組合均拒絕為非法終態；須依 §7 路由修正，不可擇一欄位覆蓋另一欄。 |
| `SCF-17-LEGACY-WITH-EVIDENCE` | 舊 `IMPLEMENTATION_BLOCKED` artifact 的證據可證明 implementation/CORE 已完成、blocker 僅屬 verification | 僅按證據正規化為 implementation=`COMPLETE`、closure=`PENDING_REQUIRED_VERIFICATION`，標 `EVIDENCE_BACKED`，保存原始舊值。 |
| `SCF-18-LEGACY-WITHOUT-EVIDENCE` | 舊單一狀態沒有足以判斷 blocker scope 的 artifact evidence | 不做字串替換／猜測；保留原值並標未知／需補證，不能宣稱 DONE。 |
| `SCF-19-DONE-PASS` | primary outcome ACHIEVED、implementation COMPLETE、CORE PASS、required verification PASS（或有效 NOT_REQUIRED/WAIVED）、independent acceptance PASS、無未解 hard blocker、diff in-scope 且 artifacts freshness/hash 全有效 | 全部 §7.10 條件成立時才允許 `TASK_CLOSURE_STATUS=DONE`；不能只因 implementation 或單一驗收 PASS 就結案。 |
| `SCF-DONE-01-PRIMARY` | primary outcome 為 NOT_ACHIEVED 或 UNKNOWN | 不得 DONE；保留相應 outcome 狀態與 next action。 |
| `SCF-DONE-02-IMPLEMENTATION` | implementation 非 COMPLETE（含 IN_PROGRESS／BLOCKED／ESCALATED） | 不得 DONE；closure 按具體 Stage 04 路由。 |
| `SCF-DONE-03-CORE` | CORE 為 FAIL／BLOCKED／NOT_RUN，或 NOT_REQUIRED 無明確 rationale | 不得 DONE；分別 FIX_REQUIRED／CORE_ACCEPTANCE_BLOCKED／PENDING_CORE_ACCEPTANCE／REPLAN_REQUIRED。 |
| `SCF-DONE-04-VERIFICATION` | required verification 為 FAIL／BLOCKED／NOT_RUN／INCOMPLETE，且無有效授權 waiver | 不得 DONE；依 §7.7 記 FIX_REQUIRED 或 PENDING_REQUIRED_VERIFICATION。 |
| `SCF-DONE-05-INDEPENDENT` | 必需 independent acceptance 非 PASS（PENDING／FAIL／BLOCKED） | 不得 DONE；依 §7.8 保持 READY、FIX_REQUIRED／REPLAN_REQUIRED 或 ACCEPTANCE_BLOCKED。 |
| `SCF-DONE-06-BLOCKER` | 任一 hard closure blocker 未解除 | 不得 DONE；保留具名 blocker scope、證據與 next action。 |
| `SCF-DONE-07-DIFF` | 最終 diff 超出核准範圍或未保留無關 user work | 不得 DONE；標明需修正的 diff/工作樹問題。 |
| `SCF-DONE-08-FRESHNESS` | 必需 artifact 缺失、rev/hash 過期或 Stage 05 未保留 Stage 04 snapshot | 不得 DONE；標明缺失／過期 artifact 與補救步驟。 |

fixture 結果欄位 schema 與實際驗證矩陣同樣包含 `CHECK_RESULT`、`WAIVER_STATUS`；合成 waiver 案例只驗證語意，不改本任務全列 `WAIVER_ALLOWED=NO` 的決定。若案例本身與 §7 路由不能一致，Stage 05 必須報 `STATUS-CONTRACT-FIXTURES: FAIL` 並提 replan，不得自行改 fixture 或閉合語意。

## 9. rev13 預算與切片

- 最多先跑候選 9 份固定 transcript 摘要（cloud/Gemma/Qwen 各 3 份）。只有候選盲評各維度均達標才進入 profile-persistence wave；候選不通過就保存失敗證據、replan，不先改 defaults 或花費 E2E 成本。
- 候選通過後，持久化六個 local-only defaults 並做 focused/rollback/full-suite delta 檢查；之後另跑全新的 final 9 份（不得重用候選輸出）。每次記錄實際 elapsed、呼叫數及非敏感 effective settings；遇正式 timeout 保留分類，不盲目重試或挑選最佳輸出。
- 只有 final 9 份達標後，才跑 2 場真正 local audio-to-DOCX integration。若 final parity 失敗，先 evidence-backed replan；修正後用新的 plan revision、raw cache keys 及獨立驗收 attempt。
- 暫不擴到第二個會議、Windows/Ollama、S3/S5、近似重複消融；這些不能替代本固定目標的核心品質證據，也不是 parity 不足的藉口。

## 10. rev13 未解風險／禁止猜測

- `[VERIFIED]` 歷史 C5 是雲端摘要並包含任務級本地逐字稿校正，且 runner 未收尾；它不是這個 rev12 的乾淨配對基準。新比較固定已校正 transcript 輸入，明確測摘要路徑。
- `[VERIFIED]` 本 revision 計畫將候選 profile 設成 defaults，但 `.env`／process environment 依 BaseSettings precedence 可覆蓋它。Stage 04 不讀取或修改使用者 `.env` secrets；若 effective local values 不符，須停在 scoped `PROFILE-PERSISTENCE: BLOCKED` 並提出需要 owner 決定的差異。
- `[VERIFIED]` 目前 repo 的 `.env` 檔不存在；這不排除 Stage 04 process environment 中有覆寫值，故必須在模型載入前核對實際 effective settings。
- `[VERIFIED]` 評分 rubric 在 Stage 01 Plan 中已逐條註冊，但其 task-scoped hash artifact 尚未建立；Stage 04 必須在摘要生成前寫出／hash 並凍結，否則不能開始模型生成。
- `[UNKNOWN]` P7-B 中 Gemma 尾段漏事實究竟由 extraction note 遺漏、分塊注意力或生成遵循造成；只有逐份 output/notes 與 transcript source-grounding 才能分辨。
- `[UNKNOWN]` LM Studio 是否能為這兩模型固定 seed；無 seed 時三次測量是最小操作樣本，不代表完整統計泛化。
- `[VERIFIED]` 單一會議／單一 transcript 只證明固定場景達標，不證明所有會議皆達標；跨會議泛化為本波外的 best-effort/non-goal，報告必須明講。

## 11. rev11 方案 A（尾段補萃取）vs C1b（全域細塊）— 歷史設計依據

| 面向 | 方案 A：尾段補萃取（rev1 前探針） | C1b：全域細塊（本波採用） |
|---|---|---|
| 證據 | 已量測：Gemma 尾半段單次呼叫 **6/7 命中（含 F044）**、**150.5 s** | 零呼叫重播（3 塊、F044 落 4,413 塊）＋P7-B 已證「分塊取代大呼叫」；Gemma／Qwen 成本分開估列 |
| 成本 | +1 次呼叫（+150.5 s，**僅 Gemma 探針實測**；不得外推 Qwen） | +1 次呼叫。Gemma 依其整份萃取實測增量；Qwen 依同路徑 E8 的 427.6 s 兩塊萃取總時間作保守 allowance（CORE-E 推導見 §5） |
| 覆蓋範圍 | **只有尾段**（中段漏寫無解） | **整份逐字稿**（每塊都有獨立呼叫） |
| 模型無關 | 是 | 是 |
| 風險 | 需決定「尾段」定義（時間／比例）＝新啟發式；單次視窗是**機率性**（兩次各 6/7 但命中集合不同） | 塊數隨逐字稿長度成長 ⇒ 成本需護欄（C1c） |
| 決策 | **備援**：若 C1b 之後尾段仍 <5/7（FALSIFIER 成立），依 Stage 01/02 重規劃；150.5 s 只可作 Gemma 探針依據，Qwen 須另有同路徑成本依據 | **主方案**（覆蓋範圍與模型無關性勝出） |

**成本證據邊界**：tail-half 的 150.5 s 僅為 Gemma 的單次探針時間，不用於 Qwen CORE-E 門檻。Qwen 的 2,650 s 是 P7-B Qwen E8 基線＋Qwen 自身實測補強 allowance＋完整兩塊萃取時間所推導的保守預算（§5）；額外 C1b chunk 的精確時間仍 `[UNVERIFIED]`，不得描述為已量測。
