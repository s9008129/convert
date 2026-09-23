# escalation.md — T20260922-2037-02（Stage 04 升級登錄）

> 撰寫者：Stage 04 實作者（P4 波）｜時間：2026-09-23T10:30+08:00
> 觸發：P4-A 落地後的兩場真實音檔 E2E（E1／E2）＋兩份獨立驗收稽核，出現**與計畫門檻語意相關**的事實。
> 依 handoff §8 STOP 條件與 AGENTS.md「語意變更＝規劃變更」，**不得由實作者自行放寬** → 升級回 Planner／使用者決定。

## STOP-1：§9.4「牆鐘退步 >25%」在 gemma-4-31B 上不可能達成（門檻自相矛盾）

- 事實：gemma 單輪補強生成 ≈485 s；D1 基準牆鐘 1227.2 s → **即使只跑 1 輪，牆鐘已 ≥ +39.5% > +25%**
  （E1 2 輪＝ +85.7%、E2 2 輪＝ +71.8%；E2 兩輪補強合計 858.881 s＝牆鐘 40.7%）。
- 推論：§9.4 的「輪數 >1 **或** wall >25% ＝未達」對 gemma 構成**必然未達**，與同節「落地後預期 1 輪」的設計意圖衝突。
- 需決策（planner／使用者）：(a) 改以「補強輪數」單獨判定、牆鐘降為觀察值；或 (b) 重訂分母基準（同模型 0 補強場）；
  或 (c) 維持門檻並接受「gemma 場在時間面必然未達」的既有結論並如實記錄。
- 實作者未做：**未**放寬門檻、**未**改 runner、**未**改量尺版本。

## STOP-2：聚合門檻 `coverage_all ≥0.65` 在 gemma n=2 仍不成立

- 事實：E1／E2 兩場 `coverage_all` 皆 0.6119（41/67）＝中位數 0.6119 < 0.65；`coverage_core` 0.8214 ≥ 0.80（已達）。
- 附註：兩場 build 不同（`da37407` vs `0054db4`），非嚴格同條件重複；若要求「同 build ≥2 次取中位數」，gemma 尚缺一次。
- 需決策：接受「core 達標／all 未達」為 P4-A 的最終結論，或加測（成本 ≈35 分／場）。

## STOP-3：P4-B 忠實度觀測值未進 stored 證據（無法自證）

- 事實：`rg fidelity scripts/e2e/run_owned_e2e.py` ＝ 0 命中；`run_summary.json`／`record_quality.json` 皆無 tripwire 欄位。
- 影響：tripwire 生效性目前只能由 **in-run log** 舉證，跨場比較與第三方複核缺可攜證據。
- 需決策：是否在 runner 增列 fidelity 投影（**新語意欄位**，屬規劃變更）。

## STOP-4：preflight 證據完整性缺口（乾淨工作樹 gate 對空目錄無效；無 `attempt.json`）

- 事實：clean-worktree gate 於 attempt 目錄建立後立即執行，空目錄對 git 不可見；E2 場亦無 `attempt.json`。
- 影響：gate 只攔「當下已存在的變更」，不保證整場執行期間工作樹乾淨。
- 需決策：是否新增 `attempt.json`（開始時間／HEAD／gate 結果）與「收尾再檢」語意。

## 不在本次升級範圍（已判定為實作者可自行處理並完成）

- P4-A 對帳器假陽性（議題／複合決議／斜線日期）：已於 `0054db4`／`f374c27` 修補，附離線重播＋負向對照。
- 跨 OS `tzdata` import-time BLOCKER（Windows 無 IANA tz database）：已於 `a412884` 修補並補回歸測試。

## 目前狀態

- 本波未變更任何門檻、量尺版本、`off` 模式行為、雲端提示詞與 `task_processor.py:259/262`。
- E3（`Qwen3.8-27B-Splash`、P4-A 修補後）真實音檔 E2E 進行中；收尾後比照同尺量測並補獨立驗收。
