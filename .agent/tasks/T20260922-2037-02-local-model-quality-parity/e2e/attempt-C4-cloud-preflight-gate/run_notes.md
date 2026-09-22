# attempt-C4-cloud-preflight-gate（gate 自證：worktree 不乾淨 → preflight FAIL closed）

> 這不是一次失敗的驗收，而是 **gate 依設計發揮作用** 的證據：runner 在啟動 backend **之前**
> 就以「E2E decision-validity gate：repo worktree 必須 clean」擋下本次執行。

- 觸發條件：`attempt-C3-cloud-baseline` 尚未 commit（1 個未提交變更）。
- 結果：`verdict=FAIL`、`backend_started=false`、`child_pid=null`、無任何 upload（`run_summary.json` 原文保留）。
- 意義：E2E 的「待測物」是可追溯的 commit；髒工作樹會讓 evidence 對不上 revision，因此必須 fail closed。
- 處置：先 commit 證據目錄形成 clean HEAD，再以新 attempt（`attempt-C5-cloud-baseline`）重跑。
