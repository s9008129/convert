# 早期場次事實涵蓋率補算（coverage baseline backfill）

## 為什麼有這個目錄

`p1-*`／`p2-*`／`p3-gemma31b-d*` 這 7 場 E2E 是「優化開始之前」的早期場次，當時
`scripts/e2e/measure_coverage.py` 還沒被引入流程，因此**沒有留下 coverage JSON**。
要回答「Gemma 4 31B 與 Qwen 3.8 27B 各自改善了多少」，就必須先把它們補算出來，
否則只能拿「優化後」的數字自我比較，會得到誤導性的結論。

本目錄是**唯讀事後補算**：不改任何既有 `review/**`、`e2e/**` 證據，只新增報告 JSON。

## 可重現指令（逐場）

```bash
cd /Users/hsiaojohnny/dev/convert
CH=.agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json
for n in p1-baseline-01 p1-fixed-01 p2-27b-01 p2-27b-fix-01 \
         p2-gemma31b-fix-01 p3-gemma31b-d1 p3-gemma31b-d2; do
  rec=$(ls data/cache/e2e/$n/backend_data/outputs/*.md | head -1)
  uv run --frozen python scripts/e2e/measure_coverage.py \
    --record "$rec" --checklist "$CH" --label "$n" --no-timestamp \
    --json-out ".agent/tasks/T20260923-1810-01-local-record-fidelity-density/evidence/coverage-baseline-backfill/$n.json"
done
```

## 歸因（模型別由 backend.log 實查，非推測）

`grep -a "使用 LM Studio 本地模式 (model=" data/cache/e2e/<場次>/backend.log`

| 場次 | 模型 | 場次性質 |
|---|---|---|
| `p1-baseline-01`／`p1-fixed-01` | `qwen3.6-35b-a3b-splash` | **使用者已明令不再受測**；僅作歷史參考，不得再跑 |
| `p2-27b-01`／`p2-27b-fix-01` | `qwen3.8-27b-splash` | Qwen 27B 的**最早 baseline** |
| `p2-gemma31b-fix-01` | `gemma-4-31b-it-mlx` | Gemma 4 31B 的**最早 baseline** |
| `p3-gemma31b-d1`／`d2` | `gemma-4-31b-it-mlx` | 同模型重跑，用於估計**單場變異** |

全部 7 場的 `backend.log` 皆為 `Gemini 摘要生成成功` 出現次數 **0** ⇒ 確認是**地端**生成，
不是雲端產物。

## 讀取注意

- 量尺為**字面比對**（`metric_version=coverage-1.0.0`，checklist sha256 `cf012d1f…`）；
  同義改寫可能被計為漏寫，關鍵詞堆砌可能造成假陽性。
- 本目錄僅 7 場早期場次。優化後的場次 JSON 已存在於各自的 `e2e/attempt-*/` 目錄。
- `p3-cloud-baseline-01` 的產物是**逐字稿檔**（雲端 503 失敗的 fallback），不是會議紀錄，
  故**不列入**覆蓋率比較。
