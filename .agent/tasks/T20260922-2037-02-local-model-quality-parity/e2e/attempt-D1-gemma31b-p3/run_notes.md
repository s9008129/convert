# attempt-D1-gemma31b-p3（Gemma 4 31B P3 修復後複驗）執行紀錄

> 本檔為**執行紀錄**；獨立驗收判決見同目錄 `verify_independent.md`（本檔不重複其判決）。
> 本紀錄亦不改動任何受測物：未觸碰 port 9527（使用者 App）、未重啟 LM Studio、未重跑完整 E2E。

- 目的（plan rev 7 §8.0 N-3／§8.5 W11）：以**新量尺**（`measure_coverage.py`＋`fact_checklist.json`）
  複驗 P3 修復後的 Gemma 4 31B 基線——讓同一條 Gemma 基線同時具備「可查核性」與「涵蓋率」兩個維度。
- 模型：`gemma-4-31B-it-MLX-4bit`（LM Studio key `gemma-4-31b-it-mlx`、`lmstudio-community`、
  `arch=gemma4`、`format=mlx`、`quantization=4bit`、`loaded_context_length=71936`）。
- HEAD：`c298cc8`（`run_summary.expected_build_revision`＝`actual_build_revision`＝`health_snapshot.build_revision`
  三者一致；P3 的 **rev 9** 已 commit，rev 10 為工作樹未提交變更——見 §六③）。
- 音檔：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…012828`，與 A1／B1／B2／C1 同一支）。
- 模板／模式／上傳：`section_meeting`／`local`／`api`（runner `mode=full`）。
- 唯一載入模型：`model_snapshot.json` 與 `model_snapshot_end.json` 皆 `unique_loaded_llm_count=1`（＝gemma）；
  `backend.log` 本場 14 次生成呼叫全為 `model=gemma-4-31b-it-mlx`（12 次語意校正 temp 0.3＋抽取 0.6＋最終 0.7），
  無任何其他模型名。
- verdict：**PASS**（16/16 required checks、`failure_reasons=[]`；`task_final.summary_failed=false`、
  `error_message=null`）。
- 執行窗：2026-09-23 01:35:25 → 01:55:53（runner wall ≈1,227.2 s；任務端到端 1,218.6 s）。

## 一、執行環境與指令

可重現指令（依 `run_summary.json` 的 `artifacts_dir`／`runtime_dir`／`mode=full`／`upload_mode=api`
與 `task_final` 的 `template_id`／`processing_mode` 逐值重建；port 64459、`child_pid=88307` 為 runner 自動選取）：

```
uv run python scripts/e2e/run_owned_e2e.py \
  --audio "/Users/hsiaojohnny/Downloads/0903-科務會議.m4a" \
  --template section_meeting \
  --processing-mode local \
  --artifacts-dir .agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-D1-gemma31b-p3 \
  --runtime-dir data/cache/e2e/p3-gemma31b-d1
```

本紀錄的**量測指令**（我重跑，一律 `DATA_DIR=/tmp/probe_scratch uv run --frozen python …`）：

```
scripts/e2e/measure_record_quality.py --record  <runtime>/backend_data/outputs/0903-科務會議_ab5571ea.md \
  --transcript <runtime>/backend_data/outputs/0903-科務會議_ab5571ea_逐字稿.txt --template section_meeting
scripts/e2e/measure_coverage.py --record <同上 md> \
  --checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json \
  --label D1-gemma31b --transcript <同上 逐字稿>
```

- 環境快照（`health_snapshot.json`）：`version=4.9.0`、`gpu_available=true`、`lmstudio_available=true`、
  `selected_model=gemma-4-31b-it-mlx`、`context_length=71936`、`asr_backend=apple`、
  `current_device=apple-neural`；`gemini_available=true`（本場未使用雲端）。
- 上傳（`upload_response.json`）：`task_id=ab5571ea`、原始檔名 `0903-科務會議.m4a`、`file_size=45107503`；
  `stored_upload_sha_match=true`（存檔 hash 與來源相同）。

## 二、時序與耗時分解（backend.log 時間戳）

| 階段 | 時間 | 證據 |
|---|---|---|
| ASR | 15.595 s | `elapsed_seconds=15.595`、`audio_duration_seconds=2695.061`、`segment_count=1340`、`real_time_factor=0.0058`、`engine_chain=apple`（fail-closed、無 fallback） |
| diarization | 151.7 s（01:35:47→01:38:18） | `diarization 完成：682 段、8 位發言者、音檔 2695s、耗時 151.7s（RTF 0.056）` |
| 發言者標註 | ≈1 s（01:38:19） | `183 段發言（diarization 682 段、threshold=0.6）` |
| 逐字稿語意校正 | 311 s（01:38:19→01:43:30） | `語意校正完成：45 段中 8 段有修正、1 段放棄、採納 27 處替換`；12 次小呼叫（間隔約 21–31 s） |
| 抽取（單次大呼叫） | 346.4 s（01:43:30→01:49:17） | pipeline metrics `extraction: 346.4`；temp 0.6、prompt 12,583 tokens（回應診斷 completion 1,744 tokens） |
| 最終生成 | 392.4 s（01:49:17→01:55:49） | pipeline metrics `final_and_refine: 392.4`（**本場無補強輪**，即最終生成單獨）；temp 0.7、prompt 16,242 tokens（completion 1,551 tokens） |
| LLM pipeline 小計 | 738.8 s | `chunk_count=1, logical_generations=2, semantic_attempts=0, network_retries=0, merge_rounds=0, merge_groups_last_round=0` |
| 任務端到端 | **1,218.6 s** | log `任務 ab5571ea 處理完成，耗時: 1218.6秒`；`task_final` 01:35:31.100202→01:55:49.667113（差＝1,218.57 s） |
| runner wall | ≈1,227.2 s | `run_summary` 01:35:25.863960→01:55:53.081220（差＝1,227.217 s） |

- 分解占比：ASR＋diarization＋標註 ≈168 s（13.8%）；語意校正 311 s；LLM pipeline 738.8 s
  → 後兩者合計 ≈1,050 s（86.2%），為主要成本。
- 本場未另行分解 prefill／decode（未重跑 LM Studio server log 分析）。
- 備註：本場逐字稿 sha256 與 C1 逐字稿**完全相同**（皆 `199d37b5…`，`diff` 無差異）——
  ASR＋語意校正這一側兩場 byte 相同，兩場輸出差異全在 LLM 生成端。

## 三、閘門與觀察值

量測（儀器 v1.1.0；數字＝我重跑 §一兩支指令的輸出）：

| 閘門 | 門檻 | 本場實測 | 判定 |
|---|---|---|---|
| `on_start_tag_ratio` | ≥ 0.95 | **0.9583**（23/24） | PASS |
| `on_start_tag_ratio_excluding_zero` | ≥ 0.90 | **0.9474**（18/19） | PASS |
| `traceable_tag_ratio` | ≥ 0.95 | **1.0**（24/24） | PASS |
| `body_source_tag_count` | ≥ 17 | **24** | PASS |
| `table_source_tag_count` | == 0 | **0** | PASS |

觀察值（非閘門）：`tagged_item_ratio=1.0`、`instruction_item_count=19`、`char_count=1,955`、
`zero_time_tag_count=5`（0.2083）、`distinct_tag_time_count=16`（ratio 0.6667）、`exact_tag_ratio=0.0417`（1/24）、
`known_term_fix_hits`（紀錄側 left 0／right 1＝`徵收股`；逐字稿側 left 3＝`征收股`／`增收股`／`瑞裏`）、
`unsupported_entities=3`（`徵收股`／`煙酒分管股`／`稽查股`；觀察值、永不作為閘門）、
`cross_section_duplicate_pairs=0`。

- 複核：我另以自寫字串解析重數 183 段——`on_start=23/24=0.9583`、排除零 `18/19=0.9474`；
  唯一 off-start 標註＝`00:04:53`（落在段落 `[00:00:00-00:05:36]` 內、非段首）。
- `record_quality.json`（同目錄）與我重跑 `measure_record_quality.py` 的 stdout **byte 相同**（`diff` 無輸出）
  → 量測可重現。
- 生成期後處理（`[品質]`，01:55:49；全場僅此一行）：
  「術語修正 0 處、出處標註吸附 **7 處**（段落內 0／最近段落 0／**跨發言者 7**；**全域段首保護 16 筆不動**；
  往前收 7 筆／最大 75 s；不可回溯保留 0）、表格出處標註移除 0 處、跨節重複移除 0 條」；
  另有「修復範本骨架佔位符 3 行」。
  - 一致性核對：16（保護）＋7（吸附）＝23 筆落在段首＝量測 23/24；餘 1 筆＝`00:04:53`
    （rev 10 重跑診斷 `kept_far=1`：落點位移 293 s > 120 s 之精度保護；見
    `quality/snap_interval_variant_check.md` §rev 10）。
- **補強 0 輪**：pipeline `logical_generations=2`（抽取＋最終）；log 無「本地摘要品質補強」行、
  無「仍有待補強問題」警告、無「連續兩輪問題集合相同仍繼續補強」。

## 四、新量尺：事實涵蓋率（`coverage-1.0.0`，本波新增維度）

指令見 §一；數字（我重跑）：

| 指標 | 值 | 備註 |
|---|---|---|
| `coverage_core` | **0.6786**（19/28） | missing core 9 條：`F001,F019,F021,F025,F044,F060,F061,F065,F066` |
| `coverage_all` | **0.5075**（34/67） | |
| `coverage_supporting` | 0.3846（15/39） | |
| 逐字稿自檢（同一組 probes 對逐字稿） | core **1.0**／all **0.9851**（66/67） | 缺口方向＝模型漏寫，不是清單事實不存在或 ASR 失真 |
| `by_category`（covered/total） | decision 6/9、name 3/3、action_item 5/9、number 1/4、constraint 8/13、topic 10/25、date 1/4 | |

- checklist sha256 `cf012d1f…`（67 條／core 28）；`record_sha256=010a5224…`、`opencc_available=true`、
  `fuzzy=false`、`warnings=[]`。
- 同尺對照（單次抽樣；plan §8.9 表）：D1 **0.6786／0.5075**、C1（同模型）0.7500／0.5672、
  B2（Qwen3.8-27B）0.8929／0.8209、B1（Qwen3.6-35B-A3B）0.8214／0.6269。
- 質性抽查（grep 驗證）：逐字稿有、D1 交付 md **完全沒有**：`嘉義`、`選舉`、`視察`、`露臺`、`藤蔓`、`李飛`；
  C1 完全缺席的 9 詞中，`省員`、`小秘書`、`排水管` 本場已寫進 md；另有 20 處「（待確認）」。

## 五、產物清單與 hash

| 產物 | 路徑（runtime，gitignored） | sha256 |
|---|---|---|
| 會議紀錄 MD | `data/cache/e2e/p3-gemma31b-d1/backend_data/outputs/0903-科務會議_ab5571ea.md` | `010a5224…65ae51`（1,955 chars） |
| 逐字稿 | `…/outputs/0903-科務會議_ab5571ea_逐字稿.txt` | `199d37b5…08060a`＝`sha256_manifest.transcript_sha256`（實體重算相符） |
| DOCX | `…/outputs/0903-科務會議_ab5571ea.docx` | `eea4bf8c…a10e1d2`＝`sha256_manifest.meeting_record_docx_sha256`（實體重算相符） |
| runtime 根副本 | `…/meeting_record.docx`、`…/transcript.txt` | 與上列 docx／逐字稿**同 hash**（byte 相同副本） |

- DOCX 可開啟（結構檢查）：`unzip -t` **無錯誤**、17 個 entry、含 `word/document.xml`（20,475 bytes）；
  runner gate `formal_docx_valid=true`。**視覺版面未驗**（僅結構）。
- `sha256_manifest.json`：`source_audio_sha256`＝`stored_upload_sha256`＝`982151f4…012828`；
  `generated_at=2026-09-23T01:55:52`；tracked 證據僅存 hash／redacted metadata，raw payload 在 gitignored runtime dir。
- 本目錄 tracked 證據：`run_summary.json`、`task_final.json`、`sha256_manifest.json`、`health_snapshot.json`、
  `model_snapshot.json`／`model_snapshot_end.json`、`upload_response.json`、`record_quality.json`、
  `verify_independent.md`（獨立複核）、`run_notes.md`（本檔）、`attempt.json`。

## 六、如實界線

1. **單次抽樣**：本場為單次執行（抽取 temp 0.6／最終 temp 0.7），run-to-run 變異未量化；
   不得外推為模型本質優劣、也不得外推為「P3 修復的普遍效果」。
2. **D1 與 C1 覆蓋率差＝抽樣變異，不是品質退化**：同模型不同次執行，`coverage_core` 0.6786 vs C1 0.7500
   （−7.1 個百分點）、`coverage_all` 0.5075 vs 0.5672（−6.0 個百分點）→
   **不得**解讀為「修復造成品質退化」或「模型本質」。
3. **rev 9 執行、rev 10 有效性**：本場跑在 rev 9（`c298cc8`）上；rev 10 的規則 4 只影響**無秒 `HH:MM`
   標註**路徑，而本場 24 個標註**無一為無秒格式**（我逐筆檢查：全部 `HH:MM:SS`）→
   rev 10 對本場數字無影響、證據在 rev 10 下仍有效（獨立複核見同目錄 `verify_independent.md`；本檔不代為判決）。
4. **補強 0 輪是本波預期行為**：W10（R23 修復）的目標即消除補強假陽性／不收斂；本場守衛未誤攔、
   不收斂保護未觸發 → 0 輪（符合驗收「補強輪數 ≤ 1」）。此為單場觀測，非「一律 0 輪」的保證。

## 七、已知限制

- 覆蓋率量尺是**字面**量尺：不判否定與數值正確性（「同意」vs「不同意」同分；「13600」vs「一萬三千六百」），
  換句話說但意思有寫到的事實可能被計為漏寫；probe 品質會系統性影響分數。
- 雲端可比基線**仍未取得**：`attempt-C2-cloud-baseline` 為 FAIL（Gemini `503 high demand`，
  產品正確 fallback 成逐字稿 DOCX、`summary_failed=true`），「地端 vs 雲端」覆蓋率對照需另開
  `attempt-C3-cloud-baseline` 重跑（append-only）。
- 本場未分解 prefill／decode；Windows／Ollama 實機與 DOCX 視覺版面皆未驗。
