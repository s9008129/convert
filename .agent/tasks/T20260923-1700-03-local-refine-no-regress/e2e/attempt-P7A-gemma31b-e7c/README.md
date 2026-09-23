# attempt-P7A-gemma31b-e7c — P7-A 正式 E2E（**verdict = PASS**）

## 受測設定

| 項目 | 值 |
|---|---|
| 模型 | `gemma-4-31b-it-mlx`（LM Studio；**整場唯一 loaded LLM**，start／end 快照一致） |
| 素材 | `/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…2828`，與 P6-A 各場同一支） |
| 模板 | `section_meeting`（科務會議） |
| 品質儀器 | `--quality-mode observe`（**只觀測、不進 verdict**） |
| 受測修訂 | `b2f11cafae2bb5ba0a0ff3713f78c579a7ac2199`（含 `3e9311a` 的守衛程式；該 commit 本身只登錄證據） |
| runner | `scripts/e2e/run_owned_e2e.py`（owned child、隔離 DATA_DIR、health 修訂比對） |

> 後續 `53de4e4` 為**文件與審查登錄**（無程式變更），不影響本場對程式修訂 `b2f11ca` 的效力。

## 驗收結果

- `verdict = PASS`、`checks = 16/16`、`failure_reasons = []`
- `task_final`：`status=completed`、`summary_failed=false`、`error_message=null`
- DOCX：`data/cache/e2e/p7a-gemma31b-e7c/backend_data/outputs/0903-科務會議_bb492356.docx`
  （40,026 bytes；sha256 `df00ae0b…26cc`；manifest 一致）
- 逐字稿 sha256 `fd40a201…72bf`；音檔上傳位元組 sha256 與來源一致

## 守衛實況（`backend.log`）

```
17:03:21  紀錄覆蓋率比對（議題）未涵蓋 2 項／（決議）未涵蓋 2 項／（數字）未涵蓋 6 項／（日期）未涵蓋 1 項
17:03:21  本地摘要品質補強（第 1 輪）…
17:10:27  地端補強不回退守衛：第 1 輪核心未涵蓋 11 → 4 項（期望 34 項）（更好，取本輪）
17:10:27  本地摘要品質補強（第 2 輪）…
17:17:35  地端補強不回退守衛：第 2 輪核心未涵蓋 4 → 2 項（期望 34 項）（更好，取本輪）
```

- 本場**兩輪都更好**（11 → 4 → 2，期望 34 項），因此**沒有**出現
  `地端補強第 N 輪造成事實回退` warning ⇒ **回退分支未被實戰觸發**（如實登記，不記 FAIL）。
  回退分支的證據來源＝`tests/test_t20260923_p7a_refine_no_regression.py`（T01–T12）＋
  `e2e/attempt-P7A-offline-replay/`（用真實失敗場的逐字稿／筆記重播，判定 `guard_would_revert: true`）。
- 交付版本＝本次執行最佳版本（核心未涵蓋 2 項）。

## 耗時（同場兩種基準，勿混用）

- runner 全程 wall：`16:42:14 → 17:17:39` = **2,125.5 s（35 分 25 秒）**
- 任務本身：`16:42:19.68 → 17:17:35.75` = **2,116.1 s（35 分 16 秒）**
  （`backend.log`「耗時: 2116.1秒」同值；此數字於 Stage 05 獨立複驗時發現原本誤植為 1,916.1 s，已勘誤）
- `logical_generations=4`（草稿 1＋最終 1＋補強 2）；每輪生成約 340–430 秒，四次生成合計約 1,570 秒
  （≈ 任務時間的 74%）；ASR 15.8 s＋diarization 約 158 s ⇒ **慢的原因是模型推論吞吐＋呼叫次數，不是 M4 效能不足**

## 外部品質指標（**只觀測**，`gate_effect: none`）

- `coverage_all = 0.5821`、`coverage_core = 0.75`、`missing_core_ids` 7 項（`F044`／`F054`／`F055`／`F056`／`F060`／`F065`／`F066`）
- 同模板同素材的 P6-A gemma 場（`p6a-gemma31b-e6`）為 `coverage_all 0.6269`／`coverage_core 0.75`
  ⇒ **核心覆蓋相同、`all` 略低**；單場比較、不可當成機制成效。
- 雲端可比基線 `coverage_core = 0.8929` ⇒ **本波仍未達雲端水準**，不得宣稱已對齊。
- 支持性覆蓋（Stage 05 另量）：`coverage_supporting = 0.4615` ⇒ 主要落差仍在支持性事實與版面收斂，不在「核心事實有沒有被寫進去」。
- 已知的殘留品質問題（**非本波目標**）：交付紀錄大量 `（待確認）`（逐條化過度），見
  `data/cache/e2e/p7a-gemma31b-e7c/backend_data/outputs/0903-科務會議_bb492356.md`。

## 證據清單

`run_summary.json`／`task_final.json`／`sha256_manifest.json`／`health_snapshot.json`／
`model_snapshot.json`／`model_snapshot_end.json`／`provider_info.json`／`upload_response.json`／
`record_quality.json`／`coverage_observation.json`／`verification-report.md`（Stage 05 獨立複驗）。
