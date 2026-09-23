# 尾段萃取探針：gemma 4 31B 尾段事實漏失的「階段歸因」

- 任務：`T20260923-1810-01-local-record-fidelity-density`（P7-B）
- 產出：2026-09-23（Asia/Taipei）；分支 `fix/qwen-local-quality-parity`
- 型態：**唯讀診斷**。不改產品程式、不改既有 `review/**`、`e2e/**`；只新增本目錄。

## 1. 要回答的問題（單一）

P7-A 正式場 `attempt-P7A-gemma31b-e7c` 缺 7 條核心事實
（F044／F054／F055／F056／F060／F065／F066），逐字稿時間戳全部落在 **00:25–00:43**（後段）。
在決定「槓桿要打在哪一階段」之前，必須先分辨是哪一種：

- **(A) 萃取階段被稀釋**：長逐字稿一次呼叫（`chunk_count=1`）→ 尾段自然被忽略；
  尾段若單獨萃取救得回來 ⇒ 尾段補萃取／分塊有效。
- **(B) 生成階段寫不進去**：尾段單獨萃取也救不回 ⇒ 槓桿要打在生成／補強。

判別方式：**把尾段切出來，單獨餵同一顆模型跑「同一份產品萃取提示詞」**。

## 2. 方法（與產品同源，避免提示詞漂移）

- 探針：`probe_tail_extraction.py`（本目錄）
  - 直接呼叫 LM Studio OpenAI 相容端點 `http://localhost:1234/v1/chat/completions`，
    模型 `gemma-4-31b-it-mlx`（與 P7-A 受測同一顆）。
  - 提示詞**不自己寫**：呼叫產品自身的
    `SummarizationService._local_extraction_prompt()` 與 `_build_chunk_extraction_message(chunk, 1, 1)`
    ⇒ 與正式流程逐字相同。
  - 逐字稿來源＝P7-A 場的產物（同一份 ASR 輸出，非重跑 ASR）：
    `data/cache/e2e/p7a-gemma31b-e7c/backend_data/outputs/0903-科務會議_bb492356_逐字稿.txt`
  - 切片：`--start 00:33:00`（該場逐字稿總長 2,695.06 s ≈ 44:55）
  - 探針詞：7 條核心缺失事實的字面 token（`PROBES`），單獨看「這一輪萃取有沒有把它們寫進筆記」。

指令（實跑）：

```bash
DATA_DIR=/tmp/probe_scratch_p7b uv run --frozen python \
  .agent/tasks/T20260923-1810-01-local-record-fidelity-density/evidence/tail-extraction-probe/probe_tail_extraction.py \
  --start 00:33:00 --out .agent/tasks/T20260923-1810-01-local-record-fidelity-density/evidence/tail-extraction-probe/run-01
```

## 3. 結果（`run-01/result.json`；`[VERIFIED]`）

| 項目 | 值 |
|---|---|
| 切片段落數 / 字元數 | 31 段 / 3,796 字（`run-01/tail_slice.txt`） |
| 產出萃取筆記 | 1,022 字（`run-01/tail_notes.md`） |
| usage | prompt 3,741 tok / completion 789 tok |
| `finish_reason` | `stop`（非截斷） |
| **探針命中** | **6 / 7** |

命中明細（`result.json:probe_hits`）：

- ✅ F054 搬遷時程（`兩階段`、`搬遷`）、F055 三樓淹水（`禮堂`、`淹水`）、
  F056 防水刨除／排水管（`排水管`、`防水`）、F060 空辦公室霉味（`黴味`）、
  F065 分兩階段／工產科財管科（`工產科`、`財管科`）、F066 移交新聞行銷處（`新聞行銷處`）
- ❌ F044（`選舉`）未命中——**但該發言在 00:25:23，落在本次切片（00:33:00 起）之外**
  ⇒ 這是切片界線造成的未命中，**不是**萃取失敗，不可計入失敗率。

## 4. 產品流程端的對照證據（同一場，`data/cache/e2e/p7a-gemma31b-e7c/backend.log`）

1. `context_window=71936(lmstudio_instance), estimated_tokens=11711, needs_chunking=False`
2. `萃取筆記零損串接（略過有損整併）：1 份、1669 tokens`
   （同一支音檔的 qwen 場 `attempt-P6A-qwen27b-e6b` 是 3,967 tokens）
3. `chunk_count=1, logical_generations=4, duration_seconds={'extraction': 340.6, 'final_and_refine': 1229.6, 'total': 1570.2}`
4. **補強輪的問題清單從未出現這 7 條尾段事實**：兩輪清單只有
   `待辦 1／議題 2（其他行政裁示、辦公室搬遷與環境問題）／決議 2／數字 6／日期 1／專名 1`，
   收尾 warning 仍停在「議題遺漏 1 項」。

## 5. 判讀（收斂）

- 尾段單獨萃取 → 7 條中（切片內）6 條**立刻寫得進筆記**，且產出僅 1,022 字、`finish_reason=stop`
  ⇒ 屬 **(A) 萃取階段稀釋**，不是生成階段寫不進去。
- 第 4 點的兩層缺口：①萃取階段就沒抓到尾段 → ②補強清單的期望集合又來自萃取筆記
  ⇒ 尾段缺漏**在流程中沒有任何一層看得到**，補強輪再怎麼跑也不會去補它。
- 因此「**尾段覆蓋守衛**」（CORE-1：偵測到尾段命中率不足時，只對該區間補一次萃取）
  打在**正確的階段**；生成階段的「一案一條／去重」（CORE-2）解的是另一個問題（逐條化與重複）。

## 6. 限制（不可外推的部分）

- 單場、單次、單一模型（gemma 4 31B）；`temperature` 與產品一致但未做多次重跑 ⇒ 探針數字**不是**覆蓋率保證。
- 探針是**字面**命中（token 出現即算），不判語意正確性、不判否定、不判數字正確性。
- F044 因切片界線未受測，7 條中實際只有 6 條可測。
- 本探針只證明「萃取階段救得回來」；**尚未**證明「尾段補萃取後最終紀錄的 `coverage_core` 會提升」
  ——那要由 P7-B 的 CORE-1 實作＋E2E 驗收來證明。
