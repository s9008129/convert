# P7-B CORE-1b 預註冊可證偽預測：離線重播（0 次模型呼叫）

- 產生時間：2026-09-23（Asia/Taipei），分支 `fix/qwen-local-quality-parity`
- 素材：`data/cache/e2e/p7a-gemma31b-e7c/transcript.txt`（sha256 見 `replay.json`；
  est 11,711 tokens＝與 0903 場同量級）
- 儀器：**產品自身**的 `SummarizationService._build_local_context_plan` +
  `_split_transcript_into_chunks`（純字串函式；無網路、無模型）
- 原始輸出：`replay.json`（同目錄）

## 重播指令（可複製重跑）

```bash
DATA_DIR=/tmp/p7b_replay uv run --frozen python - <<'PY'
from backend.services.summarization import SummarizationService
from backend.core.config import settings
from backend.core.templates import get_template
s = SummarizationService(); tpl = get_template("section_meeting")
t = open("data/cache/e2e/p7a-gemma31b-e7c/transcript.txt", encoding="utf-8").read()
settings.LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS = 6000
plan = s._build_local_context_plan(t, settings.DEFAULT_SYSTEM_PROMPT, template=tpl, context_window_tokens=71936)
print(plan.chunk_input_budget_tokens, plan.needs_chunking)
print([s._estimate_tokens(c) for c in s._split_transcript_into_chunks(t, plan.chunk_input_budget_tokens)])
PY
```

## 結果（與計畫 §3 的預註冊預測逐條對照）

| 觀測 | 預註冊預測（rev4 §3） | 離線重播實測 | 判定 |
|---|---|---|---|
| 塊數（ceiling 6,000） | 恰 2 塊 | **2 塊** | 一致 |
| 各塊大小（est tokens） | 5,960／5,918 | **5,960／5,918** | 一致 |
| chunk 2 起點 | `[00:22:09]` | `[00:22:09-00:22:…]` | 一致 |
| chunk 2 涵蓋尾段事實 | F044／F054／F066 | 尾段字面探針命中 **6/7**：F044／F054／F055／F056／F065／F066；**F060（霉味）在第一塊** | 一致（F060 本來就不在尾段） |

**刀鋒邊界（實測）**：ceiling 5,500 ⇒ **3 塊**（5,459／5,379／1,397）；5,860 ⇒ **3 塊**
（5,801／5,541／682）；6,000／6,500 ⇒ **2 塊**。⇒ 預設 6,000 是刀鋒值，E2E 必須以
`chunk_count=` 實測值為準，不得直接採信「2 塊」。

**已知落差（誠實登錄）**：`LocalContextPlan.estimated_chunk_count` 在 ceiling 6,000 回 **3**，
實際 splitter 產出 **2** 塊——估算法（依 token 預算取整）比實際切法保守。E2E 對帳以
`chunk_count=`（pipeline metrics）為準，`estimated_chunk_count` 只作觀測。

**成本對照**：本重播**沒有**呼叫任何模型。成本值域仍以既有實測為依據：
整份 1 次＝340.6 s（E7C `backend.log` `duration_seconds.extraction`）、
半份 1 次＝150.5 s（`../tail-extraction-probe/run-02-tailhalf/result.json` `elapsed_seconds`）。
