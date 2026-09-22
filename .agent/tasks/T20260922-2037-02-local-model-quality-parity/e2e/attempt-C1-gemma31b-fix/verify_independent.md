# attempt-C1-gemma31b-fix 獨立驗收報告（verify_independent.md）

- 查核者：獨立驗收者（fresh context；未參與本場 E2E 執行）
- 查核時間：2026-09-22 23:45 ～ 2026-09-23 00:05（Asia/Taipei）
- Repo：`/Users/hsiaojohnny/dev/convert`，branch `fix/qwen-local-quality-parity`，HEAD `e90040b`
- 驗收對象：`e2e/attempt-C1-gemma31b-fix/`（Gemma 4 31B／LM Studio `gemma-4-31b-it-mlx`／
  音檔 `0903-科務會議.m4a`／模板 `section_meeting`／模式 `local`）
- 寫入限制遵守聲明：本檔是查核者在 repo 內**唯一**寫入的檔案；所有重跑輸出與中間產物皆寫 `/tmp`；
  **未** commit、未修改任何其他檔案。（`attempt.json` 與 `run_notes.md` 為他人平行寫入，非本人產物。）
- 判準來源：`plan.md`（rev6）§4 第 3 點＋§7 N-1（門檻值一字未動）。

---

## 1. 重跑量測 vs tracked 值（PASS，0 差異）

以 tracked 交付 md ＋ 交付逐字稿＋`--template section_meeting` 自行重跑（輸出寫 `/tmp`）：

```
cd /Users/hsiaojohnny/dev/convert
uv run python scripts/e2e/measure_record_quality.py \
  --record     "data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md" \
  --transcript "data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec_逐字稿.txt" \
  --template section_meeting \
  --out /tmp/gemma31b-remeasure.json
```

- exit code 0；`/tmp/gemma31b-remeasure.json` 與 tracked `record_quality.json` 逐欄比對：
  **57 個 leaf 值（含 `notes` 巢狀）全數相同、0 diff**；stdout 擷取檔
  （`/tmp/gemma31b-remeasure-stdout.json`）與 tracked 檔逐位元相同（`diff` rc=0）。
- 額外重跑（更強）：把 LM Studio server log 於 23:43:36 的模型原始輸出
  （`Generated prediction`，`model=gemma-4-31b-it-mlx`；與 `/tmp/pred_2026-09-22_234336.txt`
  byte-identical，sha256 `facbcfc4…`）餵入產品後處理鏈
  `SummarizationService._finalize_record_text(mode="local")`，除交付 md 的標題列
  `# 科務會議紀錄`（由後續格式化步驟加入）外**byte-identical**；且重跑日誌的吸附統計
  （17 處／跨發言者 17／不可回溯 0／表格移除 0／跨節移除 0）與原場 23:43:36 日誌一致。

## 2. 驗收閘門逐項判定（plan rev6 §4-3；門檻未更動）

| 閘門 | 門檻 | tracked 值 | 我重跑值 | 判定 |
|---|---|---|---|---|
| `on_start_tag_ratio` | ≥ 0.95 | 1.0（20/20） | 1.0（20/20） | **PASS** |
| `on_start_tag_ratio_excluding_zero` | ≥ 0.9 | 1.0（17/17） | 1.0（17/17） | **PASS** |
| `traceable_tag_ratio` | ≥ 0.95 | 1.0（20/20） | 1.0（20/20） | **PASS** |
| `body_source_tag_count` | ≥ 17 | 20 | 20 | **PASS** |
| `table_source_tag_count` | == 0 | 0 | 0 | **PASS** |

五項全 PASS。判準文字與 plan.md:54-58、108-110 逐字相符（`exact_tag_ratio` 為觀察值，非閘門）。

## 3. Hash 自力驗證（PASS）

對 `sha256_manifest.json` 對應實體檔自行 `shasum -a 256` 重算：

| 角色 | 實體檔 | 重算值 | 對 manifest | 判定 |
|---|---|---|---|---|
| 來源音檔 | `/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（45,107,503 B） | `982151f4…012828` | 同 `source_audio_sha256` | PASS |
| 儲存上傳 | `backend_data/uploads/6ae91fab3add.m4a` | `982151f4…012828` | 同 `stored_upload_sha256` | PASS |
| 逐字稿 | `outputs/0903-科務會議_ac1edcec_逐字稿.txt` | `199d37b5…08060a` | 同 `transcript_sha256` | PASS |
| DOCX | `outputs/0903-科務會議_ac1edcec.docx` | `9c23eb99…24c212` | 同 `meeting_record_docx_sha256` | PASS |

- DOCX zip 結構（`zipfile`）：17 entries、`testzip() = None`、`word/document.xml` 存在
  （20,528 B，未壓縮大小）。**僅驗結構，未驗視覺版面**（見 §8）。
- 註：`backend_data/` 內沒有名為 `transcript.txt` 的檔；manifest 的逐字稿 hash 對應的是
  交付的 `…_逐字稿.txt`（語意校正後版本）。另有 `cache/982151f4…_55f6458f….txt`（sha
  `809d6a0c…`）為**校正前** ASR＋diarization 快取，與 manifest 無涉。

## 4. 人工抽樣（10 筆，10/10 為真實段落起點）

方法：以 seeded RNG（seed 20260923）從交付 md 的 20 個標註 occurrence 中抽 10 筆
（index #1/#4/#7/#8/#10/#11/#12/#16/#19/#20），逐一回到逐字稿（段落列格式
`[HH:MM:SS - HH:MM:SS] 發言者N：`）確認「該時間戳＝某個真實段落的起點」：

| # | 標註 | 落點段落（逐字稿） | 判定 |
|---|---|---|---|
| 1 | （科長，00:00:00） | `[00:00:00-00:05:36] 發言者1` | PASS |
| 4 | （科長，00:19:39） | `[00:19:39-00:19:49] 發言者2` | PASS |
| 7 | （科長，00:29:10） | `[00:29:10-00:29:13] 發言者2` | PASS |
| 8 | （科長，00:05:57） | `[00:05:57-00:06:14] 發言者3` | PASS |
| 10 | （科長，00:05:57） | 同上（第 3 個 occurrence） | PASS |
| 11 | （科長，00:08:15） | `[00:08:15-00:10:04] 發言者1` | PASS |
| 12 | （科長，00:08:15） | 同上 | PASS |
| 16 | （科長，00:31:34） | `[00:31:34-00:31:34] 發言者4`（0 秒段） | PASS（見 §5.3 備註） |
| 19 | （科長，00:25:23） | `[00:25:23-00:26:08] 發言者1` | PASS |
| 20 | （科長，00:25:23） | 同上 | PASS |

**結論 10/10。** 抽樣與全量指標（20/20）一致。惟 #4 與 #16 雖是「真實起點」，
其語意精度有折扣（見 §5.2、§5.3），指標看不到。

## 5. 自查發現（含與既有敘述不符之處）

### 5.1 吸附**不是** no-op（更正：changed=8，非 0；kept_far=3，非 0）

以模型最終原始輸出（`/tmp/pred_2026-09-22_234336.txt`，見 §1 之來源驗證）重跑
`snap_source_tags_to_transcript`：

```
{"segments": 183, "tags": 20, "snapped": 17, "changed": 8,
 "snapped_exact": 0, "snapped_nearest": 0, "snapped_speaker_mismatch": 17,
 "kept_far": 3, "untraceable": 0}
```

- `snapped=17／untraceable=0` 與 backend.log 23:43:36 之紀錄一致（log 不記錄 `changed`／`kept_far`）。
- **8 處 changed（7 個唯一值）**：`00:19:49→00:19:39`×2、`00:29:13→00:29:10`、`00:06:14→00:05:57`、
  `00:10:04→00:08:15`、`00:14:36→00:14:34`、`00:18:09→00:18:06`、`00:43:03→00:42:51`。
- 若任何敘述把本場吸附描述成「全部 no-op」，**不成立**。`run_notes.md` 稱
  「`kept_far`／不可回溯皆為 0」——`untraceable=0` 正確，但 **`kept_far=3` 與實測不符**
  （3 筆＝`00:31:34`×2 與 `00:42:51`，落在長段落、位移 > 120 s 而依精度保護保留原時間戳）。

**吸附的邊際貢獻（吸附前後對照）**：同一份原始輸出、同一支儀器：

| 指標 | 吸附前（模型原始輸出） | 吸附後（交付 md） |
|---|---|---|
| `on_start_tag_ratio` | 0.95（19/20，**恰在門檻線上**） | 1.0（20/20） |
| `on_start_tag_ratio_excluding_zero` | 0.9412（16/17） | 1.0（17/17） |
| `traceable_tag_ratio` | 1.0 | 1.0 |
| `body_source_tag_count` | 20 | 20 |
| `distinct_tag_time_ratio` | 0.7（14 種） | 0.55（11 種） |

→ 本場唯一真正 off-start 的標註（`00:10:04`）確實由吸附救回（→`00:08:15`）；
主指標 +0.05。但**即使完全不吸附，五閘門在本樣本也會全數通過**（主指標 0.95 恰好壓線）。
因此「本場達標」的主要來源是 Gemma 自己寫對了絕大多數段首，吸附提供的是保險與邊際改善，
不是「靠吸附救回一群爛標註」；反之也不是「吸附無作用」。

### 5.2 「倒退一格」精度損失（指標盲區；6/7 個改變是倒退）

7 個唯一改變值中，6 個是把模型**本來就寫對的段首**拉回**上一段的起點**：
`00:19:49→00:19:39`、`00:29:13→00:29:10`、`00:06:14→00:05:57`、`00:14:36→00:14:34`、
`00:18:09→00:18:06`、`00:43:03→00:42:51`（另 1 個 `00:10:04→00:08:15` 是真修正）。

成因（讀碼＋實測）：吸附規則 3 以 `containing_any[0]`＝「逐字稿順序中第一個含此秒數的段落」
且段落 end 為**閉區間**；當模型的時間戳恰為**下一段的起點**、而**上一段的 end 同秒**時，
會選到上一段的 start。逐字稿大量存在「上段結尾＝下段起點」的相鄰鏈，故觸發此效應。

具體案例（交付 md 內容 vs 逐字稿）：

- md「由發言者3負責詢問現金發放之行政程序是否可行（科長，00:18:06）」：逐字稿此指派是
  **發言者1 於 `[00:18:09-00:18:19]`**（「以你們要離居然現金先去問一下…」）。模型原寫
  `00:18:09`（正確段首），吸附倒退到 `[00:18:06-00:18:09]`（發言者2 的 3 秒段）起點。
- md「差勤管理／採購管理（科長，00:19:39）」：內容出自 **發言者1 `[00:19:49-00:21:01]`**；
  模型原寫 `00:19:49`（正確段首），吸附倒退到 `[00:19:39-00:19:49]`（發言者2）起點。

兩者落點仍是「真實段落起點」，`on_start_tag_ratio` 仍計為命中 → **1.0 無感**。
這是「可查核性達標」與「標註指向正確語句」之間的已知縫隙（plan 已將發言者歸屬除役為觀察值，
但這裡退化的是**時間精度**，不在既有觀察值清單內）。

### 5.3 吸附非冪等（候選缺陷）

對**已交付的 md** 再套一次吸附：`changed=4`（`00:19:39→00:19:35`、`00:14:34→00:14:32`、
`00:18:06→00:17:53`×2）；連續套用持續**單向後退**且不收斂（實測 4 輪：
`00:19:39→35→34→31→08`、`00:14:34→32→29→21→18`、`00:18:06→17:53→52→47→36`）。
每一步落點仍是真實起點（指標不變），但同一份文件重複後處理會得到不同時間戳。
成因同 §5.2 的相鄰鏈。建議（僅建議，不由我改）：規則 3 優先選 `start == t` 的段落，
或 end 改開區間。分級：P2 候選（不影響本波閘門判定，但屬確定性層的語意瑕疵）。

### 5.4 內容涵蓋不足的實證（反例；char_count 1,927 的解讀）

逐字稿有、交付 md **完全沒有**的內容（我逐字 grep 驗證）：

| 關鍵字 | 逐字稿 | md | 說明 |
|---|---|---|---|
| 省員（審核員） | 1 | 0 | 局長構想（00:22:44、00:23:05 段） |
| 小秘書 | 1 | 0 | 同上段 |
| 嘉義 | 1 | 0 | 參考嘉義市八等審核員 |
| 選舉 | 1 | 0 | 年底選舉謹慎（00:25:23 段的後半；該段的權限申請有進 md） |
| 視察 | 1 | 0 | 00:24:11 段 |
| 排水管／露臺／藤蔓 | 2／3／1 | 0／0／0 | 三樓淹水成因與處理（00:35:21 段） |
| 李飛 | 2 | 0 | 人事動態（00:19:31 段） |

- 其中「省員／小秘書／嘉義／李飛」等**出現在萃取階段筆記**（LM Studio log 內最終生成
  prompt 的上下文可見，窗內 5 處命中）→ 屬**最終生成涵蓋不足**，不是檢索失敗。
- `char_count` 1,927（27B＝4,062、MoE＝2,124，我由各場 tracked 值核對）：
  md **不是空殼**（11 個指示條目、`tagged_item_ratio` 1.0、0 跨節重複、19 個「（待確認）」），
  但涵蓋廣度是三個模型最低，且上述逐條缺口坐實「涵蓋不足」不只是字數幻覺。
  **結論：不影響五閘門（涵蓋率不在閘門內），但必須把它讀成「本場達標＝標註可查核性達標」，
  不能讀成「紀錄品質整體達到 27B 水準」。**
- 幻覺檢查：未發現憑空捏造的條目。最接近風險者為 md 的「**消耗稅科**」——逐字稿 ASR 作
  「校費稅科」（正確名稱依領域應為「消費稅科」），未被 term-fix 命中；
  以及 `unsupported_entities`（徵收股／稽查股）——逐字稿有「征收股」變體，屬已知低召回觀察值
  （plan 明定永不作為閘門）。

### 5.5 其餘觀察（誠實列出）

- 「（待確認）」共 **19** 處：標頭年/月/次 6、時間欄 4、地點 1、列管 1、彙整表辦理情形 6、散會 1。
- `zero_time_tag_count=3`（0.15）會膨脹主指標（`00:00:00` 結構上必為起點）；輔助指標已排除之。
- `exact_tag_ratio=0.0`：本場全部標註用角色名「科長」，逐字稿只有「發言者N」→ 結構性，
  plan rev3 已除役為觀察值。
- 歸屬殘餘：`（科長，00:05:57）`「由發言者3建議以發放宣導單替代」——該段是發言者3，
  00:05:45 段才是發言者1 引述局長；混合歸屬。同類：現金發放項的「發言者3」與 tag「科長」。
  （plan 已知 P1-1 殘餘風險，非本波閘門。）
- `known_term_fix_hits`：md 右形 4（徵收股 1、瑞里 3）、左形 0；逐字稿左形 3。
- `distinct_tag_time_ratio` 由 0.7 降至 0.55 是**吸附整併**造成（多筆收斂到同一起點），非模型退化。

### 5.6 clean-worktree gate 與平行寫入（不可完全重建項）

- runner 於啟動前做 clean worktree preflight，失敗會 abort 並寫 FAIL summary
  （`scripts/e2e/run_owned_e2e.py:1145-1170`）。本場 `run_summary.json` 為 PASS（16 checks 全 true、
  `failure_reasons=[]`）→ **推得**啟動時（23:15:52）gate 通過；但 gate 不會把 porcelain 內容寫入工件，
  我**無法直接重建**當時輸出。
- 現況：`doc/操作手冊/部署更新手冊_v4.1.md` 目前是修改狀態（+15 行；mtime `2026-09-22 23:23:04`，
  **落在本場執行窗 23:15:52–23:43:41 內**）。內容是 Windows／Ollama 部署前提（文件），
  **非執行路徑程式碼**，對本場判讀（LLM 管線與標註機制）影響評估為極小；但「全程 clean」不可證。
- 我於 23:44–23:45 查核期間觀察到 `attempt.json`、`run_notes.md` 由**他人平行寫入**（與任務說明
  「尚未有 attempt.json」不同）。本報告把它們當「主張」對待：其中 `kept_far=0` 之主張已被我
  重跑數據否證（§5.1），其餘未逐一背書。

## 6. 耗時重建（由 backend.log＋LM Studio server log 自行推導）

| 階段 | 起訖 | 耗時 | 證據 |
|---|---|---|---|
| 任務開始 | 23:15:57 | — | queue_manager 開始處理 `ac1edcec` |
| ASR | 23:15:57 → 23:16:13 | 15.8 s | `elapsed_seconds=15.824`；apple；音檔 2695.1 s；1,340 段 |
| Diarization | → 23:18:47 | 153.3 s | 682 段、8 位發言者、RTF 0.057；標註為 183 段發言 |
| 逐字稿語意校正 | 23:18:47 → 23:24:47 | 360 s | 45 段中 8 段修正、1 段放棄、採納 27 處；LM Studio 端 12 次呼叫（temp 0.3） |
| 抽取 | 23:24:47 → 23:30:22 | 335.0 s | pipeline metrics `extraction=335.0`（temp 0.6） |
| 最終生成 | 23:30:22 → 23:36:44 | 382 s | 生成請求至 prediction（temp 0.7） |
| 補強第 1 輪 | 23:36:44 → 23:43:36 | 412 s | 補強日誌至最終 finalize（temp 0.7） |
| pipeline 小計 | — | 1,129.3 s | `extraction 335.0／merge 0.0／final_and_refine 794.4／total 1129.3`；`chunk_count=1`、`logical_generations=3`、`merge_rounds=0` |
| 任務總計 | 23:15:57 → 23:43:36 | 1,659.6 s | `耗時: 1659.6秒` |
| runner 總計 | 23:15:52 → 23:43:41 | ≈ 1,669.8 s | `run_summary.json` started/finished |

- **補強輪數＝1，且收斂**：log 僅一筆「補強（第 1 輪）」（23:36:44，問題＝待辦遺漏 1 項），
  之後**無**「本地摘要仍有待補強問題」warning（`summarization.py:2193`；grep 命中數 0）。
- 成本結構：ASR＋diarization 僅 169 s（10%）；語意校正＋LLM pipeline（360＋1129.3）約占 90%。
- 註：`run_notes.md` 的耗時表與本重建一致（我逐項對過 log）；本報告以 log 為準。

## 7. 模型證據（PASS；grep 反證失敗＝無反例）

- `model_snapshot.json`（23:15:57）與 `model_snapshot_end.json`（23:43:41）：唯一
  `loaded_instances` 非空者＝`gemma-4-31b-it-mlx`（lmstudio-community／`gemma4`／4bit／31B／
  ctx 71,936）；`unique_loaded_llm_count=1`；3 個 qwen 模型 `loaded_instances: []`；
  兩 snapshot 除 `captured_at` 與 TTL 外完全相同。
- `backend.log`：所有生成呼叫均 `model=gemma-4-31b-it-mlx`（43 處）；其他 `model=` 僅
  `model=Apple`（ASR 引擎）與設定行 `model=LM Studio（依已載入模型）`；
  「gemini」全 log 僅 1 處設定字樣（`cloud_provider=gemini`，**未呼叫**）。**無非 gemma 模型呼叫。**
- LM Studio server log（`~/.lmstudio/server-logs/2026-09/2026-09-22.1.log`）23:15–23:44 窗：
  `POST /v1/chat/completions` 15 次＝`Generated prediction` 15 次，全部 `[gemma-4-31b-it-mlx]`；
  請求 body `"model"` 30 處全為 gemma；窗內無 embeddings／其他端點；
  窗內溫度：校正 0.3×12、抽取 0.6×1、最終＋補強 0.7×2。
  （窗外：23:09:35 有 1 筆 gemma、早於 backend 啟動，非本場 window，不列入。）
- `run_summary.json`：16 checks 全 true、`verdict=PASS`、`failure_reasons=[]`、
  `build_revision` 前後皆 `e90040b`。

## 8. 本場無法證明的事

1. **模型本質優劣**：單次抽樣（抽取 temp 0.6、最終/補強 temp 0.7）＋單一音檔單一模板；
   run-to-run 變異未量化。本場只證明「此家族此顆模型在此條件下可達標」，不得外推。
2. **涵蓋率／忠實度的絕對水準**：無 ground truth、無事實探針；§5.4 是「有缺口的實證」，
   不是完整的涵蓋率量化。
3. **與雲端 Gemini 的差距**：未跑雲端對照。
4. **Windows 11＋RTX 4090＋Ollama 實機**：本場仍是 macOS＋LM Studio；跨平台僅程式碼/文件層主張。
5. **DOCX 視覺版面**：僅驗 zip 結構與 `word/document.xml` 存在，未渲染比對。
6. **clean worktree 全程成立**：見 §5.6（gate 啟動時通過為「推得」；執行期間有非執行路徑變更）。
7. **「模型無關」的普遍性**：機制在共用管線＋本次第三方家族實測達標；但單一模型無法排除
   其他家族在別的樣本失敗的可能。

## 9. 最終 Verdict

**通過（PASS）。**

- 依據門檻：plan rev6 §4 第 3 點五閘門——`on_start_tag_ratio ≥ 0.95`、`on_start_tag_ratio_excluding_zero ≥ 0.9`、
  `traceable_tag_ratio ≥ 0.95`、`body_source_tag_count ≥ 17`、`table_source_tag_count == 0`；
  實測 1.0／1.0／1.0／20／0，**五項全過**。
- 支撐證據：重跑量測 0 diff（§1）；hash／zip 自力驗證全對（§3）；抽樣 10/10（§4）；
  模型證據唯一 gemma、無反例（§7）；E2E `verdict=PASS`（16 checks）。
- 判讀限縮（必讀）：
  1. 吸附在本場**不是** no-op（8 處改變、救回唯一 off-start），但它同樣製造了
     6 個唯一值的「倒退一格」精度損失與非冪等漂移（§5.2、§5.3）；這些不影響閘門，
     因為落點仍是真實起點——本波「模型無關性」的證明有效，但吸附機制本身有一個
     尚未被閘門捕捉的精度缺口。
  2. 即使不吸附，本樣本的五閘門也會過（主指標恰 0.95）→ 本場「達標」不能解讀成
     「吸附救了很多錯」；它是「模型自達標＋吸附提供邊際保險」。
  3. 本場紀錄的**涵蓋廣度**明顯低於 27B（char 1,927 vs 4,062，且有多項逐字稿內容缺口）：
     通過的是「出處標註可查核性」閘門，不是「紀錄整體品質與 27B 等價」。
  4. clean worktree 全程與 Windows／Ollama 實機未能證明（§5.6、§8）。

## 附錄 A：重跑產物清單（皆在 /tmp，未入 repo）

`/tmp/gemma31b-remeasure.json`、`/tmp/gemma31b-remeasure-stdout.json`、
`/tmp/pred_2026-09-22_234336.txt`（§1 已驗來源）、
`/tmp/c1-snap-check.py`、`/tmp/c1-snap-check2.py`、`/tmp/c1-metrics-pre.py`、
`/tmp/c1-measure-pre-full.py`、`/tmp/c1-sample.py`、`/tmp/c1-chain-repro.py`、`/tmp/c1-snap-prev.py`。

## 附錄 B：與既有敘述之差異對照

| 既有敘述（run_notes.md 等） | 我的實測 | 判定 |
|---|---|---|
| 「`kept_far`／不可回溯皆為 0」 | `untraceable=0` 正確；**`kept_far=3`** | 敘述部分錯誤 |
| （未提及吸附改變量；易被讀成 no-op） | `changed=8`（7 唯一值），其中 1 個是真修正、6 個是倒退 | 需更正/補充 |
| 「17 筆標註全部成功落在真實段落起點」 | 正確（含 3 筆 00:00:00；全量 20/20 起點） | 正確但未揭示 §5.2 精度損失 |
| 「最終生成 382 s」 | 正確（23:30:22→23:36:44） | 一致 |
| 「補強 1 輪收斂」 | 正確（無 warning） | 一致 |

（本報告僅代表我實際跑過、看到的證據；未跑過的數字一律不背書。日期：2026-09-23。）
