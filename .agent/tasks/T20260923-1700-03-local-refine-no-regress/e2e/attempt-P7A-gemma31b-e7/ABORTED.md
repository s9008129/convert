# 中止場 — attempt-P7A-gemma31b-e7（未產生 verdict）

- 模型：`gemma-4-31b-it-mlx`（LM Studio，唯一已載入 LLM）
- 素材／模板／模式：`0903-科務會議.m4a`／`section_meeting`／`--quality-mode observe`
- 修訂：`3e9311a5a611118abc81b13019ed05fe8b38b659`

## 中止原因（非產品缺陷）

本場以背景 shell（`nohup … &`）啟動，該 shell session 結束時 **runner 行程被連帶終止**，
但 backend 子行程（獨立 process group）存活成孤兒：任務 `3842fb58` 已開始 ASR
（16:40:46 完成，音檔時長 2,695.1 s），卻不會再有 poll／收尾／verdict。

處置：對孤兒 backend process group 送 `SIGTERM` 後 `SIGKILL`（已確認 port 釋放、無殘留
`uvicorn backend.main`），並改以 **持久 session** 重跑（`attempt-P7A-gemma31b-e7b`）。

## 本目錄內容（partial evidence，append-only 保留）

- `health_snapshot.json`／`provider_info.json`／`model_snapshot.json`：preflight 與 health gate
  已通過（revision 相符、唯一 loaded LLM）。
- `upload_response.json`：API upload 已成功、任務已入列。
- 缺件：`task_final.json`／`sha256_manifest.json`／`run_summary.json`／DOCX 正式性檢查
  ——因 runner 死亡而**不存在**（不得補造）。

> 教訓：E2E runner 必須跑在**不會被 session 回收的持久 session**；不得用 `nohup … &` 背景化。
