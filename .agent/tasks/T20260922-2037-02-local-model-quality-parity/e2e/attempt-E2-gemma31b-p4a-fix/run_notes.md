# attempt-E2-gemma31b-p4a-fix 執行紀錄（`gemma-4-31B-it-MLX-4bit` @ 受測 HEAD `0054db4`，P4-A 假陽性修補後真實音檔 E2E）

> 本檔由 **E2 證據打包員**撰寫（繁體中文）。文內數字一律由打包者以 `git rev-parse`／`git status`、
> `shasum -a 256`、**重跑量尺**、**以受測版（`0054db4`）程式碼等價重實作比對器**、直接讀 runtime log 逐項查核；
> 與任務簡報不一致處，以我的查核為準並明確標註。寫入範圍僅本目錄（未動產品碼／測試／runner／plan／handoff）。
> 本場是 **P4-A 假陽性根因修補（commit `0054db4`）後第一次真實音檔 E2E**；目的＝驗證補強輪數是否收斂、
> 牆鐘是否改善、coverage 是否維持／上升。一句話結論：**輪數未收斂（2 輪跑滿）；牆鐘較 E1 −7.50%（2278.77→2107.87 s），
> 但較 D1 仍 +71.76%；coverage 持平（all／core 與 E1 數值完全相同，missing 集合 3 進 3 出）；且本場暴露
> P4-A 比對器殘餘假陽性 8/8 全為假陽性（§六）——該批已於本場後修補（`f374c27`），未回溯套用本場數字。**

## 0. 打包者自核結果

| 查核項 | 方法 | 結果 |
|---|---|---|
| 受測 HEAD | `run_summary.expected_build_revision`／`actual_build_revision`／`health_snapshot.build_revision`（三來源一致） | `0054db4485a0a07fde982494c85601d5e26dae42`（commit `0054db4`，09:21:40 提交；run 09:21:52 起跑） |
| 撰寫當下 HEAD／工作樹 | `git rev-parse HEAD`＋`git status --porcelain`（2026-09-23 10:24:42+08:00 快照） | HEAD＝`0d34fa1ca2d2537866b0e8b46ce310979ea1160f`；tracked 樹乾淨；untracked 皆他場並行產物（撰寫期間陸續出現：`…/e2e/attempt-E1-gemma31b-p4/verify_independent.md`、`…/e2e/attempt-E2-gemma31b-p4a-fix/verify_independent.md`、`…/e2e/attempt-E3-qwen27b-p4a-fix/`），非本場產物 |
| 受測後落地之 commit | `git log --format='%h %ci %s'` | `a412884`（10:10:03，runner 跨 OS tz 修補）／`f374c27`（10:10:20，P4-A 剩餘假陽性修補）／`0d34fa1`（10:13:44，本 attempt 目錄證據入庫＋四份稽核報告）。**皆未回溯套用於本場數字** |
| 來源音檔 | `shasum -a 256 ~/Downloads/0903-科務會議.m4a` | `982151f4…012828`（45,107,503 bytes）＝`source_audio_sha256`＝`stored_upload_sha256`（與 E1／D1／D2／C5 同一支） |
| 逐字稿 | `shasum -a 256` | `199d37b5…08060`（全文 `199d37b5a2ecdfd2bcac283e94d830a4357e5599836539cd1230b8ae5408060a`）＝`coverage.transcript.transcript_sha256`＝`sha256_manifest.transcript_sha256`；與 D1／D2／C5 相同，與 E1（`cc5b1d54…`）差 4 行 |
| DOCX | `shasum -a 256` | `f7e51573…530ec`＝`sha256_manifest.meeting_record_docx_sha256` |
| 紀錄 md | `shasum -a 256` | `6b7e8fc1…2a60`＝`run_summary.quality.record_markdown.sha256`＝`coverage.record_sha256`＝`record_quality.record_markdown.sha256` |
| 清單（checklist） | `shasum -a 256 quality/fact_checklist.json` | `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`（與 E1／D1／D2／C5 同尺） |
| 量尺重跑 | §八 兩條指令（`DATA_DIR=/tmp/probe_scratch`，輸出 `/tmp/e2_pack_verify/`） | `measure_coverage.py`：**byte-identical**（`cmp` 通過）；`measure_record_quality.py`：25 個共同欄位**零差異**；runner 投影 `unsupported_entities_count=2`／`sha=8b1039bd…` 可由 raw 清單重現（`len()`＋`sha256(json.dumps(sorted(...), ensure_ascii=False))`，實測相符） |
| runner 閘門 | 讀 `run_summary.json` | `verdict=PASS`、`failure_reasons=[]`、**16/16 checks 全 `true`**（15 項 required＋1 個非 required 鍵 `model_snapshot_captured`）；`quality.checks` 5/5 `true` |

**與任務簡報之差異（如實登錄）**：簡報所述「本場之後另有**未提交**變更（`run_owned_e2e.py`／`test_owned_e2e_acceptance.py` 的跨 OS tz 修補，以及 P4-A 修補）」——打包時點實查，
這些變更**已於 10:10 提交**（`a412884`、`f374c27`；前者 2 檔 +92 行、後者 2 檔 +304 行），其後 `0d34fa1` 又把本 attempt 目錄整批入庫；撰寫當下 tracked 樹乾淨。
本檔全部數字仍以**受測 HEAD `0054db4`** 的行為為準，兩者不得混淆（§九-7）。

## 一、受測設定

| 項目 | 值 | 來源 |
|---|---|---|
| 模型 | `gemma-4-31B-it-MLX-4bit`；LM Studio key `gemma-4-31b-it-mlx`（publisher `lmstudio-community`、arch `gemma4`、`mlx`、4bit、31B、18,444,440,967 bytes） | `model_snapshot(.end).json` |
| 已載入 LLM | `unique_loaded_llm_count=1`；instance `gemma-4-31b-it-mlx`、`context_length=71936`、`parallel=4` | `model_snapshot.json` |
| Provider | 請求 `auto` → effective `lmstudio`；probe `reachable=true`；`lmstudio_inventory_gate=true` | `provider_info.json`＋`run_summary.engine` |
| 處理模式 | `processing_mode=local`（`mode_used=local`、`mode_used_match=true`） | `task_final.json`＋`run_summary.engine` |
| 模板 | `section_meeting` | `task_final.template_id` |
| task_id | `7bf495fe` | `task_final.json` |
| 執行窗 | 2026-09-23T09:21:52.672510+08:00 → 09:57:00.540682+08:00；**牆鐘 2107.868 s（35:07.87）** | 我以 datetime 相減（`run_summary`） |
| 任務端到端 | 09:21:57.927500 → 09:56:57.133239；**2099.206 s**；backend log「耗時: 2099.2秒」 | `task_final.json`＋log |
| 觀測模式（runner） | `--quality-mode observe`＋`--coverage-checklist quality/fact_checklist.json`（coverage `observation_only=true`、`gate_effect=none`） | `run_summary.quality.observations.coverage` |
| 對帳模式（產品） | `LOCAL_LLM_RECORD_COVERAGE_MODE=enforce`（預設；證據＝`cov_*` 有值且對帳問題字串實際進入補強 prompt） | log 09:42:38.051／09:49:49.597 |
| 忠實度絆索 | `LOCAL_FIDELITY_TRIPWIRES` **未設 false**（預設 True；證據＝重跑量尺 raw `fidelity.attribution_flags=1` 且「來源標註歸屬」問題進入補強清單） | raw `fidelity` 區塊＋log |
| 健康快照 | version 4.9.0、Apple Silicon、asr backend `apple`、device `apple-neural`、`lmstudio_available=true`、`gemini_available=true`（本場未走雲端） | `health_snapshot.json` |
| 上傳 | `queue_position=1`、`file_size=45107503`、`original_filename=0903-科務會議.m4a` | `upload_response.json` |

## 二、閘門結果

- `verdict=PASS`、`failure_reasons=[]`；任務終態 `status=completed`／`progress=100.0`／`summary_failed=false`／`error_message=null`。
- `run_summary.checks` **16/16 全 `true`**：`backend_started`／`health_ok`／`build_revision_match`／`model_snapshot_captured`／`model_inventory_unique`／`upload_ok`／`stored_upload_sha_match`／`template_applied`／`task_completed`／`task_summary_failed_false`／`transcript_downloaded`／`docx_downloaded`／`formal_docx_valid`／`metrics_valid`／`model_snapshot_consistent`／`child_terminated`。
- required 判定（`run_owned_e2e.py`）：full 模式 15 項＝`backend_started`／`health_ok`／`build_revision_match`／`child_terminated`＋`model_inventory_unique`／`upload_ok`／`stored_upload_sha_match`／`task_completed`／`task_summary_failed_false`／`transcript_downloaded`／`docx_downloaded`／`formal_docx_valid`／`metrics_valid`／`model_snapshot_consistent`＋`template_applied`（有 `--template`）；`model_snapshot_captured` 為**非 required**（歷史「16/16」與 plan「實測 15 項」不衝突）。
- **品質觀測（observe 模式不列 verdict，亦不列 required）**：`quality.checks` 5/5 全 `true`——`quality_table_tag_count_zero`（table 標註 0）、`quality_body_tag_count_ok`（27 ≥ 17）、`quality_traceable_tag_ratio_ok`（1.0 ≥ 0.95）、**`quality_on_start_tag_ratio_ok`（1.0 ≥ 0.95；E1 為 0.9310＝false，本場已消失）**、`quality_on_start_excluding_zero_ok`（1.0 ≥ 0.9）。門檻值來源：`run_owned_e2e.py` 的 `QUALITY_TAG_THRESHOLDS`（既有門檻，不得放寬）。
- coverage 觀測：`coverage_all=0.6119`、`coverage_core=0.8214`；`observation_only=true`、`gate_effect=none`、`errors=[]`、`warnings_count=0`。

## 三、耗時分解（證據：`data/cache/e2e/p4-gemma31b-e2/backend_data/logs/app_2026-09-23.log`）

| 階段 | 秒數 | 起訖／關鍵數字（log 行） |
|---|---|---|
| ASR（apple，fail-closed） | **15.701** | 子程序 09:21:57.947→09:22:14.164；引擎自報 `elapsed_seconds=15.701`、`audio_duration_seconds=2695.061`、`real_time_factor=0.0058`、`segment_count=1340`、`segments_dropped=0`（L36） |
| diarization | **152.4** | 09:22:14.16x→09:24:46.526（L37）；682 段、8 位發言者、`RTF 0.057`；標註後 183 段發言（L38） |
| 語意校正（LLM，12 次呼叫） | **355.665** | 首呼叫 09:24:46.889 →「語意校正完成」09:30:42.554（L43→L91）；45 段中 8 段有修正、1 段放棄、採納 27 處替換 |
| extraction（生成呼叫 1） | **332.019** | 09:30:42.563 → 09:36:14.582；`temperature=0.6`、prompt 12,583 tok、completion 1,816 tok |
| final（生成呼叫 2） | **383.360** | 09:36:14.586 → 09:42:37.946；`temperature=0.7`、prompt 16,290 tok、completion 1,721 tok |
| 補強第 1 輪（生成呼叫 3） | **431.454** | 09:42:38.054 → 09:49:49.508；prompt 18,363 tok、completion 1,848 tok |
| 補強第 2 輪（生成呼叫 4） | **427.427** | 09:49:49.599 → 09:56:57.026；prompt 18,092 tok、completion 1,859 tok |
| DOCX 轉換 | **2.558** | 09:56:57.133（結果已儲存）→ 09:56:59.691（`[DOCX] 轉換完成`） |
| 其餘（runner 啟停／上傳／下載／收尾） | **≈7.044** | 2107.868 −（固定 523.766＋生成 1574.5＋DOCX 2.558） |

**語意校正 12 次呼叫逐次（起→訖／秒）**：09:24:46.889→09:25:25.125／38.236；09:25:25.392→09:25:53.216／27.824；09:25:53.443→09:26:25.132／31.689；09:26:25.325→09:26:48.848／23.523；09:26:48.917→09:27:21.070／32.153；09:27:21.269→09:27:46.537／25.268；09:27:46.589→09:28:10.713／24.124；09:28:11.271→09:28:41.402／30.131；09:28:42.100→09:29:15.081／32.981；09:29:15.972→09:29:44.543／28.571；09:29:44.908→09:30:12.934／28.026；09:30:15.161→09:30:41.994／26.833。呼叫合計 **349.4 s**（其餘 6.3 s＝段間處理）。

**`pipeline metrics` 原樣引用（log 09:56:57.132／`structured_2026-09-23.jsonl` L123）**：
`chunk_count=1, logical_generations=4, semantic_attempts=0, network_retries=0, merge_rounds=0, merge_groups_last_round=0, duration_seconds={'extraction': 332.0, 'merge': 0.0, 'final_and_refine': 1242.5, 'total': 1574.5}`＋`cov_*`（§六）。

**固定成本 vs 模型生成**：固定＝ASR 15.701＋diarization 152.4＋語意校正 355.665＝**523.766 s（24.8% 牆鐘）**；模型生成＝metrics `total` **1574.5 s（74.7%）**；兩者合計 2098.266 s，對比任務端到端 2099.206 s（差 0.94 s＝收尾存檔），對比牆鐘 2107.868 s（差 9.602 s＝runner 啟停／下載／清理）。

## 四、量測結果

### coverage（`coverage.json`；`coverage-1.0.0`；label `E2-gemma31b-p4a-fix`；checklist `cf012d1f…`）

- `coverage_all=0.6119`（41/67）、`coverage_core=0.8214`（23/28）、`coverage_supporting=0.4615`（18/39）。
- `missing_core_ids=[F044, F048, F060, F065, F066]`（5 筆；E1 為 `[F019, F044, F054, F056, F066]`——**3 進 3 出、總數持平**）。
- `by_category`：decision 7/9=0.7778、name 3/3=1.0、action_item 7/9=0.7778、number 3/4=0.75、constraint 9/13=0.6923、**topic 8/25=0.32**、date 4/4=1.0。
- `record_char_count=2318`、`record_normalized_char_count=1638`；`warnings=[]`；正規化＝NFKC→casefold→OpenCC `s2twp`→去空白換行→去標點符號（`fuzzy=false`）。
- **逐字稿觀察值**：`coverage_all=0.9851`（66/67）、`coverage_core=1.0`（28/28）、僅缺 supporting `F058`；`transcript_char_count=15667`。
- **逐筆命中矩陣（同清單 `facts[].covered`）**：

| fact | 陳述（節錄） | E2 | E1 | D2 | D1（離線檔） |
|---|---|---|---|---|---|
| F010（15%） | 委任比例 40%→25%，約 15% 可升稅務員 | ✅ | ✅ | ✅ | ✅ |
| F015（10/14） | 瑞里發放排定 10月14日 | ✅ | ✅ | ✅ | ❌ |
| F021（下週一內稽） | 下週一內稽、本科下午受檢 | ✅ | ✅ | ✅ | ❌ |
| F024（600 元） | 便當＋飲料、每人 600 元禮券 | ✅ | ✅ | ❌ | ❌ |
| F025（800／17／13600） | 文康經費每人 800 元×17 人＝13600 元 | ✅ | ✅ | ❌ | ❌ |
| F061（10月底搬進） | 工產科與財管科 10月底搬進 | ✅ | ✅ | ❌ | ❌ |
| F019（組織規程） | 組織規程／編制表變動 | ✅ | ❌ | ✅ | ❌ |
| F054（檢舉業務移撥） | 檢舉業務移至煙酒及稅務管理科 | ✅ | ❌ | ❌ | ✅ |
| F056（公務車禁接送） | 公務車禁用私人接送 | ✅ | ❌ | ❌ | ✅ |
| F048（照片外流臉書） | 照片外流臉書、留言未撤 | ❌ | ✅ | ❌ | ✅ |
| F060（政風室霉味） | 政風室旁空辦公室霉味重（給工產科） | ❌ | ✅ | ❌ | ❌ |
| F065（兩階段搬遷） | 財政四科分兩階段搬遷 | ❌ | ✅ | ❌ | ❌ |
| F014（瑞里 100 多戶） | 分配瑞里發放、100 多戶 | ❌ | ❌ | ❌ | ❌ |
| F066（新聞行銷處） | 空間移交新聞行銷處 | ❌ | ❌ | ❌ | ❌ |

- **真缺口逐條（打包者獨立 grep，見 §六末）**：`F044`（選舉／政治／敏感＝0 命中）、`F048`（臉書／留言＝0）、`F060`（政風室＝0）、`F065`（兩階段／工產科／財管科＝0）、`F066`（新聞行銷處＝0）＝**本場真的沒寫進紀錄**；`F014`＝**量尺 probe 假陰性**（逐字稿是「瑞理」1 次＋「瑞裏」1 次，紀錄寫「瑞理」；probe 只認 瑞里／瑞裏）——與 §六 的比對器判缺（8 項）是**兩組不同的東西**，勿混用。
- 逐字稿觀察值僅缺 `F058`（supporting），意即 67 條清單中 66 條的字面線索都在逐字稿裡——缺的 5 條 core 屬**模型漏寫**而非清單瑕疵。

### record_quality（`record_quality.json`；`tag_traceability-1.1.0`）

- 字面統計：`char_count=2318`（E1 2552）、`body_source_tag_count=27`（E1 29）、`table_source_tag_count=0`、`non_prefixed_tableish=0`、`tagged_item_ratio=1.0`、`cross_section_duplicate_pairs=0`、`instruction_item_count=10`；`known_term_fix_hits` left 0／right 1（`徵收股` 修正 1 次）。
- `tag_traceability`：`segments=183`、`tags_total=27`、`tags_inside_any_segment=27`、`traceable_tag_ratio=1.0`、`tags_exact_segment_start=2`（`exact_tag_ratio=0.0741`）、`tags_on_real_segment_start=27`、**`on_start_tag_ratio=1.0`（E1 0.9310）**、`tags_on_real_segment_start_excluding_zero=18`、`on_start_tag_ratio_excluding_zero=1.0`（E1 0.9130）、`tags_inside_same_speaker_segment=3`、**`zero_time_tag_count=9`（E1 6；`zero_time_tag_ratio=0.3333`）**、`distinct_tag_time_count=16`、**`distinct_tag_time_ratio=0.5926`（E1 0.6552；D2 0.5217）**。
- 敏感投影：`unsupported_entities_count=2`、`unsupported_entities_sha256=8b1039bd…`；重跑量尺重現 raw＝`["徵收股", "稽查股"]`、`unsupported_entities_registry_aware=[]`——**這 2 筆是正確官名（逐字稿 ASR 誤寫），屬已登錄的量尺已知假陽性**（plan §9.4 校準即載明）。
- 忠實度絆索（P4-B，observe）：`fidelity.metric_version=fidelity-1.0.0`、`entity_flags=0`、`number_fabricated=0`、`number_missing=0`、**`attribution_flags=1`**（`attribution_kinds=["tag_owner"]`、`attribution_overlap_median=0.2424`，問題字串＝「來源標註歸屬待確認：（發言者2，00:11:13）落在 發言者1 的逐字稿段落內」）。
- `quality.checks` 5/5 `true`（§二）；`check_failures=[]`。

## 五、與 E1／D1／D2／B2（27B）／C5（雲端）的同尺對照表

同尺判定：coverage 一律 `coverage-1.0.0`＋checklist `cf012d1f…`；`tag_traceability-1.1.0`（B2 為 v1.1 原生）。**但逐字稿版本與量測性質不全同**（見表下註），不同尺欄位不得直接比。

| 指標 | E1（P4） | **E2（P4-A fix，本場）** | D1（P3 後） | D2 | B2（27B） | C5（雲端） |
|---|---|---|---|---|---|---|
| 模型 | gemma 31B | gemma 31B | gemma 31B | gemma 31B | qwen3.8-27B | gemini-3.5-flash-lite（生成） |
| 牆鐘（s） | 2278.77 | **2107.87** | 1227.2 | 1251.13 | 1709.73 | 任務 536.4（runner 未收尾） |
| 補強輪數 | 2 | **2** | 0 | 0 | 2（359＋351 s） | 1（Gemini） |
| `coverage_all` | 0.6119 | **0.6119** | 0.5075 | 0.5075 | 0.8209¹ | 0.8060 |
| `coverage_core` | 0.8214 | **0.8214** | 0.6786 | 0.6786 | 0.8929¹ | 0.8929 |
| `coverage_supporting` | 0.4615 | **0.4615** | 0.3846 | 0.3846 | 0.7692¹ | 0.7436 |
| `missing_core` 數／集合 | 5（F019,F044,F054,F056,F066） | **5（F044,F048,F060,F065,F066）** | 9 | 9 | 3（F021,F025,F055）¹ | 3（F025,F056,F066） |
| `record_char_count` | 2552 | **2318** | 1955 | 1951 | 4062 | 2593 |
| `body_source_tag_count` | 29 | **27** | 24 | 23 | 52 | 28 |
| `on_start_tag_ratio` | 0.9310 | **1.0** | 0.9583 | 1.0 | 1.0 | 1.0（全 `00:00:00`） |
| `distinct_tag_time_ratio` | 0.6552 | **0.5926** | 0.6667 | 0.5217 | 0.2885 | 0.0357 |
| 逐字稿 sha（前 8） | `cc5b1d54` | **`199d37b5`** | `199d37b5` | `199d37b5` | `bd6b52d7` | `199d37b5` |
| verdict | PASS | **PASS** | PASS | PASS | PASS（runner）／獨立驗收 FAIL | **無 verdict** |

¹ B2 的 coverage 為**事後離線量測**（`quality/coverage/coverage_qwen27b.md`，非 runner 當場量測），且其 `record_quality.json` 曾就地覆寫（v1.0→v1.1，證據完整性風險）；B2 逐字稿亦不同版（`bd6b52d7`）。
C5 runner 未收尾（無 verdict、無 runner DOCX）；C5 的 `on_start 1.0` 全部時間戳 `00:00:00`＝辨別力虛胖（`distinct 0.0357`）。
E1 逐字稿 `cc5b1d54` 與本場 `199d37b5` 差 4 行（語意校正階段字詞替換）→ E1↔E2 為**近同尺、非同尺**；D1／D2／C5 與 E2 逐字稿相同。
來源：各場 `run_summary.json`／`attempt.json`／`coverage.json`／`run_notes.md`／`timing-forensics-01/report.md`／`p4-comparison-table-01/baseline_table.md`（本表數字全部經打包者重讀實檔核對）。

**牆鐘差異（我自算）**：E2 vs E1 **−7.50%**（−170.9 s）；E2 vs D1 **+71.76%**；E2 vs D2 **+68.48%**；E2 vs B2 **+23.29%**。

## 六、本場最重要新發現：P4-A 比對器「剩餘假陽性」（**8/8 判缺皆為假陽性**）

最終輪 log（`structured_2026-09-23.jsonl` **L123**〔打包者實查；簡報所述 L122–123 中含 `cov_*` 者為 L123〕；`app_2026-09-23.log` L126）：
`cov_expected_topic=12 cov_missing_topic=5 cov_expected_decision=12 cov_missing_decision=3 cov_expected_number=9 cov_missing_number=0 cov_expected_date=4 cov_missing_date=0 cov_issues_added=2`

**機制（受測版 `0054db4` 的實際行為，我已等價重實作驗證）**：判缺＝(i) 最佳滑窗 LCS < 0.6，或 (ii) 通過 LCS 但「否定詞／≥2 位數字串」守衛在局部範圍（最佳視窗＋最相似單句）找不到。`_normalize_action_key` 會**刪掉 `/`**（'10/14'→'1014'、'11/1'→'111'），而紀錄把日期寫成「10月14日／11月1日」——連續子字串 '1014'／'111' 永不出現 → 守衛攔下。

**5 個議題判缺（逐項重驗）**：

| # | 判缺標題（log） | 正規化 key | 我的等價重實作 LCS | 紀錄中的實質內容（grep 出處） | 判定 |
|---|---|---|---|---|---|
| T1 | 土地稅卡重新列印 | `土地稅卡重新列印` | **0.500**（best window `本科配合重新列印科長00`） | L19 表格列「整理並重新列印損毀之土地稅卡（本科/相關承辦）」；L52 正文「…待其整理出清單後，由本科配合重新列印」 | **假陽性**（紀錄語序「重新列印…土地稅卡」與標題相反，LCS 只到一半） |
| T2 | 局長專案與權限 | `局長專案與權限` | **0.571**（`局長關於市場端權限之需`） | L23 表格列「請示局長關於市場端權限之需求（科長）」；L56 正文「針對市場端請求權限之需求，由科長再行請示局長」 | **主要假陽性**；唯一 nuance：子詞「專案」在紀錄 `grep -c`＝**0**（逐字稿 1 次，L144「局長會交辦一些專案」）→ 標題級已涵蓋、子詞級未保留 |
| T3 | 資安宣導（社交工程） | `資安宣導社交工程` | **0.500**（`有逼真之社交工程釣魚郵件`） | L57「（二）資安與紀律」；L58「近期有逼真之社交工程釣魚郵件…（科長，00:27:03）」 | **假陽性**（「宣導」以「要求全員設定純文字模式」的指示改寫） |
| T4 | 科內資訊外流禁令 | `科內資訊外流禁令` | **0.500**（`科內公共訊息轉傳至外部群`） | L26 表格列＋L59「嚴禁將科內公共訊息（如群組照片）轉傳至外部群組，違者將予追究（科長，00:31:34）」 | **假陽性**（「外流」→「轉傳至外部群組」改寫） |
| T5 | 辦公室搬遷與環境問題 | `辦公室搬遷與環境問題` | **0.500**（`辦公室搬遷1.由於原搬遷地點`） | L62「（四）辦公室搬遷」；L63「…室內有濃厚黴味，除霉工程複雜且可能影響健康…（科長，00:32:33）」 | **假陽性**（「環境問題」→黴味／除霉改寫） |

**3 個決議判缺（逐項重驗）**：

| # | 判缺條目（final log） | 正規化 key | LCS | 守衛 | 紀錄中的實質內容 | 判定 |
|---|---|---|---|---|---|---|
| 決① | 將先公告預佈缺，避免 11/1 才找人過晚。 | `將先公告預佈缺避免111才找人過晚` | **1.000** | 缺數字 `['111']` | L36「將先公告預佈缺，避免 **11月1日**才找人過晚（科長，00:00:00）」 | **假陽性（日期格式）**；守衛 log：09:56:57.081（LCS 1.00、缺數字 ['111']） |
| 決② | 確認 10/14 排程，預計發放人數 100 多戶。 | `確認1014排程預計發放人數100多戶` | **1.000** | 缺數字 `['1014']` | L51「瑞理村發放活動確認於 **10月14日**排程，預計發放人數 100 多戶」 | **假陽性（日期格式）**；守衛 log：09:42:37.999（LCS 0.79）→09:56:57.078（LCS 1.00、缺數字 ['1014']） |
| 決③ | 費用報支應照實報，不可浮報；小額採購需避免與廠商利益交換。 | `費用報支應照實報不可浮報小額採購需避免與廠商利益交換` | **0.538** | 缺否定詞 `['不可']`（最相似單句無「不可」） | L42「費用報支應照實報，不可浮報」＋L45「小額採購需避免與廠商利益交換，嚴禁收受廠商贈品」＝**複合句被拆成兩句寫入** | **假陽性（複合句拆寫）**；`浮報`／`利益交換` 逐詞 grep 各 1 命中 |

**結論（真缺 vs 假陽性）**：比對器本場 8 項判缺——**5 議題＋3 決議，全數為假陽性**（實質內容皆已在紀錄；僅 T2 的「專案」一詞屬未保留的子概念）。
**真正沒寫進紀錄的是另一組**：coverage 的 5 筆 core（`F044`／`F048`／`F060`／`F065`／`F066`，§四逐項 grep＝0 命中）＋量尺 probe 假陰性 `F014`（瑞理 vs 瑞里）。
`_find_missing_action_keys` 的兩筆守衛 log（缺數字 `['1014']`／`['111']`）**確認為日期數字正規化造成**（等價重實作復現同一結果；`grep -c "1014"`＝0、`grep -c "111"`＝0）。

**可重跑指令與輸出（打包者實跑）**：

```
R="data/cache/e2e/p4-gemma31b-e2/backend_data/outputs/0903-科務會議_7bf495fe.md"
grep -c "土地稅卡重新列印" "$R"   # 0（literal 標題 0 次＝判缺直接原因）；grep -n "重新列印" → L19, L52
grep -c "專案"             "$R"   # 0（逐字稿 1 次）；grep -n "局長" → L23, L39, L41, L56
grep -n "社交工程\|資安"    "$R"   # L57, L58
grep -n "轉傳"             "$R"   # L26, L59
grep -n "搬遷\|黴味\|除霉"   "$R"   # L62, L63
grep -c "10/14"            "$R"   # 0；grep -n "10月14日" → L51
grep -c "11/1"             "$R"   # 0；grep -n "11月1日" → L29, L35, L36
grep -n "浮報\|利益交換"    "$R"   # L42, L45
grep -c "1014"             "$R"   # 0；grep -c "111" "$R" → 0
grep -c "選舉\|政治\|敏感"  "$R"   # 0（F044 真缺）；grep -c "臉書\|留言" → 0（F048 真缺）
grep -c "政風室"           "$R"   # 0（F060 真缺；注意「廉政風險」含跨詞「政風」字串，需用「政風室」精準查）
grep -c "兩階段\|工產科\|財管科" "$R"   # 0（F065 真缺）；grep -c "新聞行銷處" → 0（F066 真缺）
grep -o "瑞理\|瑞里\|瑞裏"  "$R" | sort | uniq -c   # 瑞理 3（紀錄；逐字稿為 瑞理 1＋瑞裏 1）＝F014 probe 假陰性的原因
```

**本場後落地的修補（`f374c27`，未回溯套用本場數字）**：`_SLASH_DATE_PATTERN`／`_fold_slash_date`（兩側折疊 `10/14≡10月14日`）、日期守衛 `_ACTION_DATE_TOKEN_PATTERN`＋`_date_token_present`、`_split_match_clauses`（複合決議子句 AND 判定）、`_topic_terms_cover`（議題詞級覆蓋）；該 commit 的 docstring 直接引用本場（E2）案例（「『10月14日』→已寫進紀錄被誤判遺漏」）。
〔如實邊界〕本節 LCS 為**等價重實作**（同一正規化、同一滑窗 LCS、同一守衛；notes 原文未落盤故以 log 標題為 key），非 byte 級 in-run 重播；判「內容已在紀錄」一律以 grep 字面為準（§八 可重跑）。

## 七、補強輪數與收斂

| 輪 | 起訖（log） | 生成秒數 | 問題集合（log 原文摘要） |
|---|---|---|---|
| 第 1 輪 | 09:42:38.054 → 09:49:49.508 | **431.454** | 議題 5（同 §六）；決議 2（確認 10/14…、費用報支…）；**數字 5（15、600、800、17、13600）**；**日期 1（10月底）**；彙整表欄位歸屬（表格列出現「發言者3」）；來源標註歸屬（（發言者2，00:11:13）落在發言者1 段）；金額／數量依據（800塊／600塊／13600／15%／17個） |
| 第 2 輪 | 09:49:49.599 → 09:56:57.026 | **427.427** | 議題 5（同）；決議 3（確認 10/14…、費用報支…、**由於除霉工程複雜且可能影響健康，預計搬遷時間將延後…**）；來源標註歸屬（同） |
| （輪後終態） | 09:56:57.131 warning | — | 議題 5（同）；決議 3（將先公告預佈缺避免 11/1…、確認 10/14…、費用報支…）；來源標註歸屬（同） |

- **差異解讀**：第 1 輪把**數字 5、日期 1、表格欄位、金額依據**補掉（第 2 輪清單已消失）＝**真缺口的有效補強**；第 2 輪清單只剩議題 5（全假陽性）＋決議 2（全假陽性）＋來源標註，且新增一項「除霉搬遷延後」（最終紀錄 L63 已涵蓋）。第 2 輪→終態之間，「11/1」條目由（未涵蓋清單外）翻為判缺——合理推測是模型把日期改寫成「11月1日」觸發 §六 的數字守衛；**中間輪紀錄未落盤，此因果標 [INFERRED]、無法 byte 級查核**。
- **為何「未收斂」**：本場跑滿 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2`（`backend/core/config.py:280` 預設）；「不收斂保護」（連續兩輪問題集合完全相同才停）因**每輪集合都在變**（I0≠I1≠I2）從未觸發 → 終態仍有 3 決議＋5 議題＋來源標註未消。依 plan 語意＝**未收斂**。
- **成本**：兩輪合計 **858.881 s＝牆鐘 40.7%**（431.454＋427.427）。反事實：只跑 1 輪＝2107.868−427.427＝**1680.441 s**（vs D1 +36.93%）；0 輪＝**1248.987 s**（vs D1 +1.78%、vs D2 −0.17%）。
- **與 E1 對照**：E1 的首輪判缺決議是 **11/11 全判缺**（引用標頭污染等根因，已修）；本場首輪決議只判缺 **2 項**＝修補有效；但剩餘假陽性仍讓兩輪白跑大部分——**輪數未收斂的直接原因是對帳器假陽性，不是模型沒補**（§六）。

## 八、可重現指令（打包者實際執行；`DATA_DIR=/tmp/probe_scratch`）

```
cd /Users/hsiaojohnny/dev/convert
R="data/cache/e2e/p4-gemma31b-e2/backend_data/outputs/0903-科務會議_7bf495fe.md"
T="data/cache/e2e/p4-gemma31b-e2/backend_data/outputs/0903-科務會議_7bf495fe_逐字稿.txt"

DATA_DIR=/tmp/probe_scratch uv run --frozen python scripts/e2e/measure_record_quality.py \
  --record "$R" --transcript "$T" --template section_meeting --out /tmp/e2_pack_verify/record_quality.json

DATA_DIR=/tmp/probe_scratch uv run --frozen python scripts/e2e/measure_coverage.py --record "$R" \
  --checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json \
  --label E2-gemma31b-p4a-fix --transcript "$T" --json-out /tmp/e2_pack_verify/coverage.json

cmp .agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-E2-gemma31b-p4a-fix/coverage.json /tmp/e2_pack_verify/coverage.json   # 無輸出＝byte-identical
```

輸出摘要：`measure_coverage.py` 與 runner 產出 **byte-identical**；`measure_record_quality.py` 25 個共同欄位零差異（raw 另含 `unsupported_entities=["徵收股","稽查股"]`、`unsupported_entities_registry_aware=[]`、`fidelity` 區塊）；
`sha256(json.dumps(sorted(["徵收股","稽查股"]), ensure_ascii=False))`＝`8b1039bd9d49ec8fe484a7119ca5a8c52ac1188df43268a4c27d8705e6685365`＝runner 投影 sha（`run_owned_e2e.py:project_record_quality_metrics`）。
`sha256_manifest.json` **未修改**（原檔已含音檔／逐字稿／DOCX hash，內容經我逐項複核一致）。

## 九、如實邊界與未達項（不得美化）

1. **未達（plan §9.4 F2「輪數 >1（需第 2 輪）或 wall 時間退步 >25%＝未達」）**：本場**補強 2 輪**（>1）且牆鐘 2107.868 s vs D1 1227.2 s＝**+71.76%**、vs D2 1251.13 s＝**+68.48%**（皆 >+25%）→ **兩項準則都未達**。成本幾乎全在生成呼叫：D1 為 2 次生成（738.8 s）、本場為 4 次（1574.5 s）＋固定成本 523.8 s。**plan 的兩個準則在此模型下互斥**：單輪生成 ≈427–431 s≈D1 牆鐘的 +35%——即使收斂到 1 輪仍 >+25%；此成本接受是 **planner 決策**（plan §9.4 已載明，實作者不得自行放寬）。
2. **未達（plan §9.3 F1② 聚合觀察目標）**：`coverage_all 0.6119 < 0.65`（未達）；`coverage_core 0.8214 ≥ 0.80`（已達）。兩者皆「觀察值、須 ≥2 次取中位數才可宣稱支持」→ **單場不得定論**。逐條歸因閘門（同 F1②）本場命中：F024／F025／F015／F061／F021／F010 皆 True 且不退步；但 F048／F060／F065 由 E1 True 掉回 False（3 進 3 出）→ 本場僅能說 **coverage 維持、未上升**。
3. **共同歸因（plan §9.3 F1④ 隔離場未做）**：本場**未開** `LOCAL_FIDELITY_TRIPWIRES=false`（預設 True 運作之證據＝§四 fidelity 區塊）。P4-B(C) 的「數字漏寫」問題（800／600／13600／15%／17）與 P4-A 對同一批事實 F024／F025 重疊 → 本場召回功勞**不得獨歸 P4-A**，須標示 **P4-A＋P4-B 共同歸因**。
4. **單次抽樣**：生成 temperature 0.7（校正 0.3），跨 run 變異存在（D1 vs C1 曾差 6.0–7.1 pp）；且本場逐字稿（`199d37b5`）雖與 D1／D2 同版，與 E1（`cc5b1d54`）不同版 → 跨模型／跨場比較須以 ≥2 次中位數為準。
5. **`on_start_tag_ratio` 門檻**：本場 1.0（27/27）過 ≥0.95；E1 的 0.9310＝false 消失。但 **`zero_time_tag_count=9`（比率 0.3333，E1 為 6）與 `distinct_tag_time_ratio=0.5926`（E1 0.6552）較 E1 退**；嚴格版 `exact_tag_ratio=0.0741`（僅 2 筆）。`required` 升級決策本波不做（plan §9.9）——升級前這兩項須先處理。
6. **剩餘假陽性（§六）＝本場核心未達項**：比對器 8/8 判缺皆假陽性（含兩筆日期守衛誤攔）；以「對帳判缺」當收斂判準時本場**註定不收斂**。該批已於本場後修補（`f374c27`）。
7. **本場之後落地的修補未回溯套用**：`a412884`（tz）、`f374c27`（對帳修補）、`0d34fa1`（證據入庫）皆在本場 09:57 結束之後（10:10 起）→ 本場數字代表 `0054db4` 行為；**不得**用修補後行為為本場結果開脫或美化。
8. **同尺引用邊界**：B2 coverage 為事後離線量測且其 `record_quality.json` 曾就地覆寫（v1.0→v1.1，獨立驗收列為證據完整性風險）；C5 runner 未收尾、無 verdict；E1 逐字稿不同版（差 4 行）→ 表五可並列對照，**不可**當「模型高下」或「P4-A 因果」定論。E3（27B、P4-A fix）於撰寫當下尚未有產物（僅 untracked 目錄），未納入本節。
