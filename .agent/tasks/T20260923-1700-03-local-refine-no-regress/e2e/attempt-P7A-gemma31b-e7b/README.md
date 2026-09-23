# Preflight FAIL（非產品 verdict）— attempt-P7A-gemma31b-e7b

- `verdict: FAIL`、`child_pid: null`、`backend_started: false`
- 唯一 failure reason：`repo worktree 不是 clean（E2E decision-validity gate）：1 個未提交變更`
  ——當時 `e2e/attempt-P7A-gemma31b-e7/`（前一次被 session 回收的中止場）尚未 commit。
- 語意：這是 **harness 前置條件的 fail-closed**（decision-validity gate 正常運作），
  **不是**產品品質或 E2E 驗收結論。正式場為 `attempt-P7A-gemma31b-e7c`。
