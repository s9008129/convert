# Stage 05 獨立驗收報告 — D1 E2E（Gemma 4 31B，P3 修復後）

- 任務：`T20260922-2037-02-local-model-quality-parity`
- 受驗 attempt：`e2e/attempt-D1-gemma31b-p3`（執行時間 2026-09-23 01:35:25 → 01:55:53，Asia/Taipei）
- 受驗實作：分支 `fix/qwen-local-quality-parity`、HEAD `c298cc81a12beae4d83d00def07cda73bb56d0a9`（rev 9 已 commit；健康檢查實測 `actual_build_revision` 與 expected 相同）。工作樹另有**未提交 rev 10**（`backend/core/text_postprocess.py`、`backend/services/summarization.py`、`tests/test_t20260922_2037_p3_parity.py`；mtime 01:59:33–02:00:14，晚於本場 E2E 結束時間 → 本場跑的是 rev 9 版本）；第 6 項宣稱獨立判定 rev 10 對 D1 證據的影響。
- 驗收者聲明：fresh context、唯讀產品碼／測試／`plan.md`／既有證據；未觸碰 port 9527、未重啟 LM Studio、未重跑 E2E。所有 Python 一律 `DATA_DIR=/tmp/probe_scratch LOG_LEVEL=CRITICAL uv run --frozen python ...`；臨時腳本置 `/tmp/probe_d1/`。本檔為唯一寫入（建立時不存在，append-only）。
- 受驗快照（本次實測 sha256）：record md `010a5224969e…`、逐字稿 `199d37b5a2ec…`、docx `eea4bf8c971b…`、fact_checklist `cf012d1f6983…`、source audio `982151f4629a…`。
- 方法：先讀 `plan.md` §8.4／§8.6、`backend/core/text_postprocess.py`（量尺與吸附實作）、`scripts/e2e/measure_coverage.py`；再以**自寫字串解析**重算全部指標（不 import 產品碼），並以產品函式再算一次交叉比對；涵蓋率走「官方工具＋自寫正規化/匹配」雙軌。

## 宣稱 1｜verdict=PASS、16/16 checks 全綠 — **一致**

宣稱：`verdict=PASS`、16/16 checks 全綠（對照 `run_summary.json`／`task_final.json`／`sha256_manifest.json`）。

實測（命令節錄）：
```
$ uv run --frozen python - <<'PY'   # 讀三個 json 重算
[run_summary] checks_total: 16 all_true: True verdict: PASS failure_reasons: []
[task_final] status=completed summary_failed=False processing_mode=local template_id=section_meeting error_message=None
16 checks：backend_started, health_ok, build_revision_match, model_snapshot_captured, model_inventory_unique,
upload_ok, stored_upload_sha_match, template_applied, task_completed, task_summary_failed_false,
transcript_downloaded, docx_downloaded, formal_docx_valid, metrics_valid, model_snapshot_consistent, child_terminated
$ shasum -a 256 <檔案>
982151f4…  /Users/hsiaojohnny/Downloads/0903-科務會議.m4a          # = manifest.source_audio / stored upload
199d37b5…  …0903-科務會議_ab5571ea_逐字稿.txt                        # = manifest.transcript（runtime 版同 hash）
eea4bf8c…  …0903-科務會議_ab5571ea.docx（runtime meeting_record.docx 同 hash） # = manifest.docx
```
判定：**一致**。16 個 check 全 true、`failure_reasons=[]`；manifest 四組 hash 全部與實體檔案相符；`expected_build_revision == actual_build_revision == HEAD`。另獨立複驗：`health_snapshot` 的 `selected_model=gemma-4-31b-it-mlx`、`model_snapshot` 的 `unique_loaded_llm_count=1`；`model_snapshot_end.json` 與起點快照差異僅 `captured_at` 與 `remaining_ttl_seconds`（模型集合一致）。DOCX 另以 `python-docx`＋E2E runner 同一組函式複驗：OOZIP header ✓、formal title「會議紀錄」✓、無 fallback 標記 ✓、`section_meeting` 四個必要章節全數命中（一、科長轉知／二、科長指示及提醒事項／案由及承辦單位／散會）✓、段落內 24 筆標註、表格 0 筆。

## 宣稱 2｜閘門指標 — **一致**

宣稱：`on_start_tag_ratio=0.9583`（≥0.95）、`excluding_zero=0.9474`（≥0.90）、`body_source_tag_count=24`（≥17）、`table_source_tag_count=0`、`tagged_item_ratio=1.0`。

實測（自寫解析 `/tmp/probe_d1/independent_parse.py`，純字串、不 import 產品碼）：
```
"segments": 183, "tags_total": 24, "tags_inside_any_segment": 24, "traceable_tag_ratio": 1.0,
"tags_on_real_segment_start": 23, "on_start_tag_ratio": 0.9583,
"excluding_zero": 18, "on_start_tag_ratio_excluding_zero": 0.9474,
"zero_time_tag_count": 5, "distinct_tag_time_count": 16,
"body_source_tag_count": 24, "table_source_tag_count": 0, "excluded_header_field_tag_count": 0,
"leaf_items": 24, "tagged_items": 24, "tagged_item_ratio": 1.0
```
產品儀器交叉比對（`measure_tag_traceability`，metric_version `tag_traceability-1.1.0`）：`on_start_tag_ratio: 0.958333…`、`on_start_tag_ratio_excluding_zero: 0.947368…`、`tags_total: 24`、`traceable_tag_ratio: 1.0` — 與自寫解析同值。`measure_record_quality.py --template section_meeting`：`body_source_tag_count=24`、`table_source_tag_count=0`、`tagged_item_ratio=1.0`。

判定：**一致**（23/24、18/19、24、0、1.0 全部重算命中；門檻 ≥0.95／≥0.90／≥17 皆通過）。註：`on_start` margin 薄（差 1 筆即 22/24＝0.9167 < 0.95）；`00:00:00` 標註 5 筆（佔 0.2083）具結構性加成。

## 宣稱 3｜涵蓋率量尺 — **一致**

宣稱：`coverage_core=0.6786`、`coverage_all=0.5075`；missing core＝`F001,F019,F021,F025,F044,F060,F061,F065,F066`。

實測 A（官方工具，`coverage-1.0.0`）：
```
uv run python scripts/e2e/measure_coverage.py --record …/0903-科務會議_ab5571ea.md \
  --checklist …/quality/fact_checklist.json --transcript …_逐字稿.txt --label d1-gemma31b-p3
=> coverage_all 0.5075（34/67）、coverage_core 0.6786（19/28）、coverage_supporting 0.3846（15/39）
=> missing_core_ids = [F001, F019, F021, F025, F044, F060, F061, F065, F066]（9 筆）
=> warnings []；OpenCC s2twp 可用；逐字稿自檢 coverage_all 0.9851（66/67）/ core 1.0
=> 同輸入二跑 byte 相同（cmp 無差異）→ 確定性成立
```
實測 B（自寫獨立重算 `/tmp/probe_d1/coverage_independent.py`：自寫 NFKC→casefold→OpenCC s2twp→去空白→保留 CJK/英數 正規化＋自寫 group-AND/OR 匹配）：
```
fact_total 67, core 28, covered_total 34, covered_core 19,
coverage_all 0.5075, coverage_core 0.6786,
missing_core_ids 同上 9 筆
```
判定：**一致**（雙軌同值；缺口清單逐字元相同）。補記：本次複核期間（02:07:28）`quality/coverage/coverage_gemma31b_d1.{md,json}` 已落地，其 `record_sha256`、`checklist_sha256` 與我的重算來源相同、數值亦相同（此檔為平行流程產出，非本報告依據）。

## 宣稱 4｜耗時分解 — **一致（逐條）**

| 項目 | 宣稱 | 實測 | 一致 |
|---|---|---|---|
| wall | 20.5 分 | `run_summary` 01:35:25.863960→01:55:53.081220＝**1227.2 s＝20.45 分** | ✓（四捨五入） |
| ASR | 15.6 s | backend.log:43 `elapsed_seconds: 15.595`（01:35:31→01:35:47） | ✓ |
| diarization | 151.7 s | backend.log:44「diarization 完成：682 段、8 位發言者…耗時 **151.7s**（RTF 0.056）」 | ✓ |
| logical_generations | 2 | backend.log:320 `logical_generations=2`；程式碼：每次 `_generate_with_local_engine` 呼叫 `+1`（`summarization.py:2927`） | ✓ |
| extraction＋final | 346.4＋392.4＝738.8 | backend.log:320 `duration_seconds={'extraction': 346.4, 'merge': 0.0, 'final_and_refine': 392.4, 'total': 738.8}` | ✓ |
| 補強輪數 | 0 | log 無任何「本地摘要品質補強（第 N 輪）」／「補強未收斂」行；grep `補強` 僅命中 0 筆（backend.log／app log／structured jsonl）；2 次生成＝萃取＋最終 → 補強 0 輪 | ✓ |

附帶：任務完成耗時 log:344 `1218.6秒`（< wall，上傳與開機時差合理）。

## 宣稱 5｜冪等性 — **一致**

宣稱：對 D1 紀錄重跑吸附 → `changed=0`、`kept_on_start=23`、`kept_far=1`，且二次套用後 byte 完全相同。

實測（`/tmp/probe_d1/snap_checks.py`；rev10 工作樹函式＋rev9 HEAD 來源函式各跑兩次）：
```
rev10_first : changed=0, kept_on_start=23, kept_far=1, kept_precision=0, snapped=0, untraceable=0
rev10_second: 同值；first 輸出 == 原 .md（byte 相同）；second == first（byte 相同）
rev9_first  : changed=0, kept_on_start=23, kept_far=1（同值）；輸出 == 原 .md
rev10_output == rev9_output（byte 相同）
獨立絆索（自寫解析）: 原值為全域真實段首卻被改寫 = 0 筆；changed = 0 筆
```
另與生產期統計對帳（backend.log:319）：生產吸附 7 處（段內 0／最近 0／跨發言者 7；全域段首保護 16 筆不動；往前收 7 筆／最大 75 s；不可回溯 0）→ 16＋7＝23 筆成為段首；唯一未落段首者 `（科長，00:04:53）`（第 38 行）＝位移 293 s > 120 s 的 `kept_far` 精度保護，符號一致。

判定：**一致**。②「已是全域段首未被搬動」以獨立解析重數＝0 筆；③後退幅度可觀測（生產 log：7 筆／最大 75 s，且全為段內落點吸附）。

## 宣稱 6｜rev 10 對 D1 證據的有效性 — **一致（D1 證據在 rev 10 下仍有效）**

- D1 紀錄中**無秒（HH:MM）來源標註筆數＝0**（自寫解析 `no_seconds_tag_count: 0`；24 筆標註全為 `HH:MM:SS`）。
- rev 10 唯一行為差異＝**規則 4 精度保護**：`if not with_seconds and target % 60 != 0: stats["kept_precision"] += 1; return tag`（`backend/core/text_postprocess.py` diff，作用域僅無秒標註；含秒路徑與 rev 9 相同）；其餘 diff 為 docstring／log 欄位（`kept_precision` 加入 `[品質]` log）與 2 個新測試。
- 行為探針（唯讀、synthetic）：A 無秒＋目標非整分鐘 → 原樣保留（`kept_precision=1, changed=0`）；B 無秒＋目標為整分鐘 → 吸附且冪等；C 含秒＋同一輸入 → 照常吸附（rev 10 無影響）。
- 實測套用於 D1 紀錄：`kept_precision=0`、輸出與 rev 9 byte 相同（見宣稱 5）。

判定：**一致**。D1 的 24 筆標註皆含秒 → 規則 4 不可能觸發；rev 10 對 D1 產物與量尺結果零影響，D1 證據在 rev 10 下仍然有效。（唯一非語意差異：rev 9 的生產 log 無「精度保護」欄位，屬格式差異。）

## `plan.md` §8.6 逐條評分

1. **pytest 全綠** — ✓（我實跑目前工作樹 rev10：`935 passed, 2 skipped in 9.62s`；rev9 的 `933 passed／2 skipped` 由 `review/attempt-08` 獨立複跑佐證，且 933＋rev10 新増 2 測試＝935，算術自洽）。
2. **CORE-3 儀器** — ✓ 儀器存在、同輸入二跑 byte 相同（cmp 實測）；對稱正規化/全半形/簡繁/標點/CRLF 由單元測試釘住（本次全套測試綠）。
3. **CORE-4** — ✓ 三側單元測試（含 attempt-07 兩反例與「否定詞在別子句」）在 rev10 測試檔、pytest 綠；D1 補強輪數＝0 ≤ 1；log 無「連續兩輪問題集合相同仍繼續補強」；log 亦無「待辦召回守衛攔下」訊息 → 本場無被守衛攔下的項目（該條件式 log 要求未被觸發）。
4. **CORE-5** — ✓ ①二次套用 `changed==0`（且 byte 相同）；②「原值為全域段首卻被改寫」＝0（獨立重數；rev9 鑑別力對照 23 筆見 plan §8.4）；③`backward_moves` 僅出現在段內吸附落點（生產：7 筆全為規則 3 的跨發言者→段內落點），`max_backward_seconds=75` 可觀測；④`on_start_tag_ratio=0.9583 ≥ 0.95`。
5. **對照（DOCX＋公開 coverage）** — ✓ D1 正式 DOCX 有效（OOZIP／章節／標註一致）；同一把尺 `coverage-1.0.0` 的 D1 報告已落地且與我獨立重算相同；C2 雲端 503 失敗如實、未宣稱雲端基線。
6. **雲端不變性** — ✓（由既有測試套件釘住；本次全套測試通過。本報告未逐行重驗 cloud byte 差異，判定依賴測試覆蓋）。
7. **明示不宣稱** — ✓ §8.6-7 明文；D1 相關報告無「地端 ≥ 雲端−X」閘門宣稱；缺口（coverage_core 0.6786）有公開。

## `plan.md` §8.4 吸附語意評分

- rev 9 的「規則 0 全域段首保護＋段首命中優先」在 D1 輸入上成立：不跨段後退（重跑 0 筆改寫、0 筆段首被搬動）、冪等（byte 級）；`kept_on_start=23` 顯示規則 0 確有作用（生產期 16 筆＋吸附後 7 筆）。
- 落點一律為真實段首：D1 最終 23/24；唯一例外為 `kept_far`（位移 >120 s 的精度保護，規格明列），非跨段後退。
- rev 10 追加的第三層（精度保護）在 D1 不觸發（0 筆無秒），不改變上述結論。

## 已知限制與殘餘風險（不得外推）

1. **單次抽樣**：單一會議（0903）、單一模型、temperature 0.6/0.7；所有數字不得外推為模型或方法的本質優劣。
2. **閘門 margin 薄**：`on_start=0.9583` 距門檻 0.95 只差 1 筆（22/24＝0.9167 即 FAIL）；且 5/24 為 `00:00:00`（結構性加成），排除後 0.9474 亦有空間。
3. **覆蓋率低於前次 Gemma 執行**：本次 `coverage_core 0.6786` < C1 場 `0.7500`（單樣本變異）；量尺是「人工清單字面召回」，不判語意、否定、數值正確與歸屬正確。
4. **平台**：Windows 11＋Ollama 未實機驗證 `[UNVERIFIED]`；本場僅 macOS＋LM Studio。
5. **rev 10 狀態**：rev 10 為未提交工作樹變更，D1 證據綁定 rev 9；本報告已驗證 rev 10 對 D1 零行為差異，但 rev 10 本身未經實機 E2E 複驗（僅單元測試 935 綠＋本次探針）。
6. **規則 0 的語意界線**：保護的是「段首事實」而非「內容歸屬正確」；保留值仍可能歸屬有誤，現行量尺無感（plan §8.7 風險①已明示）。

**VERDICT: PASS**

## 給非技術讀者的白話摘要

這次驗收的是「用本機 AI 模型（Gemma 4 31B）重新生成會議紀錄」的最新一次完整實測。
我沒有採信報告上的數字，而是自己寫程式把會議紀錄與逐字稿重新比對、重新計算。
結果：16 項自動檢查全部通過；紀錄裡 24 個時間出處有 23 個精準落在逐字稿的發言起點（比率 0.9583，門檻 0.95）；表格內不該有出處標註，確實 0 筆。
涵蓋率（會議重點被寫進紀錄的比例）約 68% 的重點事項、整體 51%，有 9 條重要事實沒寫到，清單已公開。
時間方面：整場約 20.5 分鐘，語音辨識 15.6 秒、講者分群 151.7 秒、AI 生成約 739 秒，而且沒有發生「白燒時間」的額外補強輪。
另外我確認了後來追加的程式修正（rev 10）只影響「只寫到分鐘」的罕見標註格式，而本次紀錄完全沒有這種格式，所以本次驗收結果在新版本下仍然有效。
限制：這只是一場會議、一次抽樣；Windows 電腦與其他模型尚未實測，數字不能直接推廣。
