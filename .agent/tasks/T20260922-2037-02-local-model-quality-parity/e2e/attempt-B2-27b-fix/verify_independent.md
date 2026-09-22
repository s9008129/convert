# 獨立驗收報告 — attempt-B2-27b-fix（Stage 05，read-only）

- 受驗對象：`qwen3.8-27b-splash`（dense 27B，LM Studio，ctx 128000）＋ `section_meeting` ＋ `local`
  ＋ 真實音檔 `/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（2,695 s）
- 受驗 build revision：`3fec08f1f13b655bf3d69549b8207735b854ad17`（＝當時 HEAD；health snapshot 與 run_summary 雙向確認）
- 驗收者：獨立 Stage 05（read-only；未載入／卸載任何 LM Studio 模型、未修改任何產品程式碼或既有證據檔）
- 驗收時間：2026-09-22 21:48–21:53（Asia/Taipei）
- 範圍界定：**僅驗 27B**（依使用者指示不測 MoE；`attempt-B1-moe-fix` 不在本次判定範圍）
- 環境備註（影響可重現性，必須揭露）：驗收期間主 session 仍在同一 worktree 工作——
  `backend/core/text_postprocess.py`、`scripts/e2e/measure_record_quality.py`、`tests/test_t20260922_record_quality.py`
  有未提交變更，且 `record_quality.json` 於 21:50:52 被就地覆寫（見 §4.3）。本報告的判定以
  **執行時產物（21:46 以前、mtime 未變）＋ pinned rev `3fec08f` 的獨立重跑**為準。

---

## 0. 判定

| 層級 | 判定 | 依據 |
|---|---|---|
| **使用者目標**（能在真實音檔上正常產出會議紀錄檔） | **PASS** | task `dc3c8f7a` 完成、`summary_failed=false`、DOCX 有效且含 52 個出處標註 |
| **E2E runner**（16 項 required checks） | **PASS** | `verdict=PASS`、`failure_reasons=[]`、16/16 全 true |
| **plan rev2 字面閘門**（`exact_tag_ratio ≥ 0.8` 等 4 條） | **FAIL（1/4 條未達）** | `exact_tag_ratio = 0.0192`（閘門 0.8）——結構性不可達，見 §3 |

**綜合判定：`FAIL（字面閘門）` / `PLANNER_REPLAN_REQUIRED`。**

理由：CORE-1 在 plan rev2 寫的是「`exact_tag_ratio ≥ 0.8` **且** `traceable_tag_ratio ≥ 0.95`」，
另含條文「**優先落在該標註指名發言者的段落內**」（量測 `tags_inside_same_speaker_segment / tags_total`）。
本場實測 `tags_inside_same_speaker_segment = 1/52`（1.9%），且 51/52 的標註用角色名（「科長」），
逐字稿的發言者標籤是「發言者 N」——**這條閘門在本場的標籤詞彙下不可能通過**。
實作端在 `3fec08f` 已單方面把主指標改成 speaker-agnostic 的 `on_start_tag_ratio`（plan §5 風險條已預期此情形），
但 **plan 文字與閘門值未隨之修訂**；依 Harness v4.2 §11，改變驗收語意屬 PLANNER_REPLAN，驗收者不得自行 waive。

同時必須明講：**機械面沒有缺陷**。吸附機制在正式管線的行為與設計一致（100% 落在真實段落起點、
0 筆不可回溯、0 筆捏造嫌疑），本場失敗的唯一原因是「閘門定義 vs 模型標籤詞彙」不一致，不是功能壞掉。

---

## 1. 來源真實性（獨立重算，不引用既有 json）

| 項目 | 獨立重算值 | 與 manifest | 判定 |
|---|---|---|---|
| 使用者音檔 sha256 | `982151f4…012828` | `982151f4…012828` | [VERIFIED] 同一支音檔 |
| 逐字稿 sha256 | `bd6b52d7…4eb3fa` | `bd6b52d7…4eb3fa` | [VERIFIED] |
| 會議紀錄 DOCX sha256 | `9a511396…e3a66b` | `9a511396…e3a66b` | [VERIFIED] |

DOCX 結構獨立檢查：84 段落／1 表格／含標題「科務會議紀錄」／段落層出處標註 **52** 個 [VERIFIED]。
模型快照：開始與結束都是 `['qwen3.8-27b-splash']`（`context_length=128000`），`model_inventory_unique=true` [VERIFIED]。

---

## 2. Runner required checks（16/16）

`backend_started`、`health_ok`、`build_revision_match`、`model_snapshot_captured`、`model_inventory_unique`、
`upload_ok`、`stored_upload_sha_match`、`template_applied`、`task_completed`、`task_summary_failed_false`、
`transcript_downloaded`、`docx_downloaded`、`formal_docx_valid`、`metrics_valid`、`model_snapshot_consistent`、
`child_terminated` → **全為 true**；`failure_reasons=[]`；`verdict=PASS`；exit code 0 [VERIFIED]。

---

## 3. 逐條驗收對照（plan rev2）

| # | 驗收條目 | 門檻 | 實測（獨立重跑） | 判定 |
|---|---|---|---|---|
| 1 | `exact_tag_ratio` | ≥ 0.8 | **0.0192**（1/52） | **FAIL（結構性）** |
| 2 | `traceable_tag_ratio` | ≥ 0.95 | **1.000** | PASS |
| 3 | `body_source_tag_count`（退化防線） | ≥ 17 | **52** | PASS |
| 4 | `table_source_tag_count` | = 0 | **0** | PASS |
| 5 | `tagged_item_ratio` | （基線 33/34≈97.1%） | **1.000** | PASS |
| 6 | 字元數 | （A1 對照 4,338） | **4,062** | 同級（觀察） |
| 7 | `unsupported_entities` | 觀察值、非閘門 | 3（徵收股／煙酒文神股／稽查股） | 不判定 |
| 8 | runner 16 checks | 全過 | 16/16 | PASS |
| 9 | E2E verdict | PASS | PASS | PASS |
| 10 | 雲端不變性 | byte 級不變 | 不在本場 E2E 範圍（由單元測試釘住） | 未於本場驗證 |

補充獨立指標（本場額外計算，非 plan 閘門）：

| 指標 | 值 | 意義 |
|---|---|---|
| `on_start_tag_ratio` | **1.000**（52/52） | 每個標註時間戳都真的是某段落的起點 |
| `on_start_tag_ratio_excluding_zero` | **1.000**（45/45） | 排除 7 筆 `00:00:00` 後仍全中 |
| `tags_inside_same_speaker_segment` | **1/52 = 0.019** | 標籤指名發言者與段落發言者一致者僅 1（即唯一用「發言者3」的那筆） |
| `zero_time_tag_count` | 7（13.5%） | 7 筆標註都指向會議起點 00:00:00（辨別力低） |
| `distinct_tag_time_count` | 15（28.8%） | 52 筆標註只用了 15 個不同時間戳 |
| 吸附處置（log） | 40 處（段落內 1／最近段落 0／跨發言者 39／不可回溯保留 0） | 39 筆跨發言者吸附＝只改時間、不改歸屬（fail-soft 設計） |
| 其他後處理 | 術語修正 0、表格標註移除 0、跨節重複移除 0 | 無退化訊號 |

---

## 4. 獨立重跑與一致性

### 4.1 方法
1. 以 `git archive HEAD`（`3fec08f`）匯出**釘住版本**的原始碼到 `/tmp/b2-verify/repo-HEAD2`，用 repo 的 venv 執行同一支量測儀。
2. 另在一次在目前 worktree（含未提交的量測增補）執行，觀察指標定義漂移。

### 4.2 結果
- **pinned rev `3fec08f` 重跑 vs 執行時 `record_quality.json`：逐欄完全一致（無任何值差異）** [VERIFIED]。
- 三種實作版本（pinned／21:48 worktree／21:50 覆寫版）在**共用欄位**上值完全相同：
  `segments=183`、`tags_total=52`、`tags_inside_any_segment=52`、`traceable=1.0`、`tags_exact_segment_start=1`、
  `exact_tag_ratio=0.0192`、`tags_on_real_segment_start=52`、`on_start=1.0`、`tags_inside_same_speaker_segment=1`、
  `body=52`、`table=0`、`char_count=4062`、`instruction_item_count=25`、`tagged_item_ratio=1.0`、
  `cross_section_duplicate_pairs=0` [VERIFIED]。

### 4.3 證據完整性觀察（必須記錄）
- `record_quality.json` 的 mtime 由 21:47 → **21:50:52（被就地覆寫，未保留舊版）**；
  新增 `attempt.json`（21:51:08）、`run_notes.md`（21:51:19）。
- 量測定義在驗收期間被改了兩次：`on_start_tag_ratio_excluding_zero` 在 21:48 版為 **0.865**（分母＝全部 52），
  21:50 版為 **1.000**（分母＝非 00:00:00 的 45）——同名指標、不同分母 [VERIFIED]。語意上 1.000 才符合指標名稱，
  但**同名指標在一小時內出現兩種數值**是可重現性風險；E2E 證據應 append-only（`.recheck` 檔已在 A1 目錄出現，B2 則覆寫）。

---

## 5. 人工抽樣：8 筆正文出處標註（逐字稿段落時間表為 ground truth）

| # | 紀錄標註 | 該時間戳的逐字稿段落 | 是段落起點？ | 發言者一致？ | 內容相符？ |
|---|---|---|---|---|---|
| 1 | （科長，00:00:00） | [00:00:00-00:05:36] 發言者1：…11 月組織規程變動… | ✅ | ❌（角色名 vs 發言者1） | ✅ 相符 |
| 2 | （科長，00:05:45） | [00:05:45-00:05:56] 發言者1：局長說…詐騙…地震 | ✅ | ❌ | ✅ 相符 |
| 3 | （發言者3，00:05:57） | [00:05:57-00:06:14] 發言者3：佩魯科長昨天來訪談… | ✅ | ✅（全場唯一嚴格命中） | ✅ 相符 |
| 4 | （科長，00:22:44） | [00:22:44-00:23:00] 發言者1：局長提到增加省員／小秘書 | ✅ | ❌ | ✅ 相符 |
| 5 | （科長，00:17:52） | [00:17:52-00:17:53] 發言者4：「個全年都」 | ✅ | ❌ | ⚠️ 薄弱（實質內容在 00:18:09 發言者1） |
| 6 | （科長，00:27:03） | [00:27:03-00:29:10] 發言者1：資安／Email 純文字 | ✅ | ❌ | ✅ 相符 |
| 7 | （科長，00:39:44） | [00:39:44-00:39:47] 發言者5：「味。」 | ✅ | ❌ | ⚠️ 薄弱（實質內容在 00:39:47 發言者1） |
| 8 | （科長，00:39:44）（待辦節重複張貼） | 同上 | ✅ | ❌ | ⚠️ 薄弱且與 #7 同時間戳 |

**抽樣結論**：8/8 時間戳真的是逐字稿某段落起點、無任何一筆落在會議時間軸之外（無造假時間）；
1/8 發言者標籤與段落發言者一致；6/8 內容語意相符；2/8（+1 重複）落在 3 秒鐘的 ASR 斷句碎片上
（真實但閱讀體驗薄弱）。不符者清單：**無「時間戳不存在」的不符者**；不符合者集中在
**發言者歸屬不可驗證**（角色名 vs 發言者N），以及 **落在碎片段落**。

---

## 6. 耗時分解（1703 s；回答「為什麼這麼久」）

| 階段 | 秒數 | 備註 |
|---|---|---|
| ASR | 16.7 | RTF 0.0062，2695 s 音檔 |
| diarization | 153.7 | 682 段、8 位發言者、RTF 0.057 |
| 摘要管線（合計 1404.7） | extraction 360.9 ＋ final_and_refine 1043.9 | `logical_generations=4` |
| └ 4 次大呼叫 | 360 / 334 / 359 / 351 | 每次約 8.7–11.5 tok/s（dense 27B 4-bit 正常水位） |
| 後處理＋DOCX | < 2 | 吸附成本毫秒級 |
| 任務總計 | **1703.0** | run 全流程 1709.7 |

**主因不是 M4 Pro 不夠力**：ASR＋diarization 只花 170 s；1,400 s 全在 LLM，其中 **710 s（約 42%）來自 2 輪「品質補強」重生成**。
補強輪的觸發源是 `_quality_issues` 的「待辦事項遺漏」判準（見 §7.1），兩輪都無法收斂。

---

## 7. 非閘門觀察（不影響本次判定，但值得排入後續波）

### 7.1 品質閘門誤判：「待辦事項遺漏 6 項」為字面變體造成的假陽性 [VERIFIED]
最終紀錄**其實都寫了**那 6 項，只是文字變體讓 `_normalize_action_key` 的「包含」比對落空：

| 閘門判定遺漏 | 紀錄實際文字 | 差異 |
|---|---|---|
| 了解…土地增值稅科**的**配合事項 | …土地增值稅科**之**配合事項 | 的／之 |
| 了解房屋稅系統業務調整（稽查股/**征收**股） | （稽查股/**徵收**股） | ASR 誤辨變體 |
| 嚴禁轉傳科內群組訊息至外部 | 嚴禁將科內群組訊息（含照片）外流至任何外部渠道 | 改寫 |
| 盤點多元支付現狀並思考AI創新方案 | 盤點多元支付現狀，並思考**結合**AI**的**創新方案 | 增字 |
| 追蹤辦公室黴味處理進度與廠商報價 | 關注黴味處理進度**與費用** | 改寫 |
| 預備組織改名相關系統權限**、**設備調整 | …系統權限**及**設備調整 | 、／及 |

→ 成本：2 輪各約 355 s 的無效重生成（≈ 710 s、占總時長 42%），最終仍以 WARNING 收場（非阻斷）。
→ 且補強訊息要求「逐列補進**待辦事項表格**」，但 `section_meeting` 模板本身沒有待辦表格章節（只有決議事項＋一／二／三節）
   〔`record` 內無「待辦」章節，已獨立確認〕。

### 7.2 標註辨別力偏低
52 筆標註只用 15 個不同時間戳、其中 7 筆集中 `00:00:00`（13.5%）——同一時間戳重複張貼會讓讀者難以逐條回溯。

### 7.3 吸附的語意邊界
「跨發言者」吸附 39/40 是設計允許的規則 3（只改時間、不改歸屬）；但從 §5 抽樣可見，
它會把標註推到**别人的、且可能是 3 秒碎片**的段落上。對「逐條可查核」是進步（時間確實存在），
對「發言者歸屬」則沒有保證——這正是 §0 所述 CORE-1 第二條無法通過的直接原因。

---

## 8. 這次驗收**無法證明**什麼（必須與 PASS 項分開看）

1. **發言者歸屬正確性**：51/52 用角色名，逐字稿無對應標籤 → 無法用字面驗證；`tags_inside_same_speaker_segment=1/52` 不可解讀為「98% 歸屬錯誤」。
2. **捏造率／忠實度**：`unsupported_entities` 是高精確低召回的字面觀察，且明文「永不作為閘門」。
3. **覆蓋率**：本場沒有逐條覆蓋檢查表（plan 已排除 P1-4）；「25 條指示 vs 183 段逐字稿」的完整性未驗。
4. **跨場穩定性**：單次抽樣（temperature 0.7；含 2 輪 refine 亦為 0.7），不得外推為「27B 的品質水位」。
5. **與雲端 Gemini 的相對差距**：本場沒有重跑雲端對照（前波基準數字不在本場驗證範圍）。
6. **模型無關性（CORE-2）的實機證據**：本場只跑 LM Studio；Ollama／其他模型僅由共用管線與單元測試推論。
7. **DOCX 版面品質**：只通過結構檢查（`formal_docx_valid`＋段落/表格計數），未做視覺渲染驗收。
8. **27B vs MoE 高下**：本輪依指示未測 MoE，不做任何比較結論。

---

## 9. 建議（僅回報，未動任何程式碼或門檻）

1. **[PLANNER_REPLAN，阻斷]** 修訂 plan rev2 CORE-1 閘門文字：明訂主指標為 `on_start_tag_ratio ≥ 0.95`（speaker-agnostic）、
   把 `exact_tag_ratio` 降為「觀察值」，並對「指名發言者一致性」改用可實作的定義
   （例如：以角色名→發言者對照表，或改量「落在同一議題段內」）。否則此閘門永久不可通過。
2. **[P0 成本]** 修 `_normalize_action_key` 的召回判準（的/之、及/、 等變體、或改用詞彙集合覆蓋比對），
   並讓補強訊息只要求模板真的有的章節；可省下 2 輪、約 700 s 的無效生成。
3. **[P1]** 標註辨別力：抑制 `00:00:00` 重複張貼、要求同一段落內不同條目指向不同時間戳（P1-16）。
4. **[P1]** 吸附規則 3 的品質上限：跨發言者吸附時，若最近段落 ≤ 5 s 或為碎片，考慮改吸附到**前一個同發言者的實質段落**（需先由 Planner 決定語意）。
5. **[流程]** E2E 證據檔一律 append-only（`record_quality.json.recheck-2` 之類），量測定義改版需在檔內記 `metric_version`。

---

## 附錄：本次獨立驗收指令

```bash
# 1) 釘住版本的獨立重跑（結論欄位與執行時完全一致）
mkdir -p /tmp/b2-verify/repo-HEAD2 && git archive HEAD | tar -x -C /tmp/b2-verify/repo-HEAD2
cd /tmp/b2-verify/repo-HEAD2 && DATA_DIR="/Users/hsiaojohnny/dev/convert/data" \
  /Users/hsiaojohnny/dev/convert/.venv/bin/python scripts/e2e/measure_record_quality.py \
  --record "…/0903-科務會議_dc3c8f7a.md" --transcript "…/0903-科務會議_dc3c8f7a_逐字稿.txt" \
  --template section_meeting --out /tmp/b2-verify/recheck-pinned.json
# 2) 抽樣（段落時間表比對）與來源雜湊
DATA_DIR="$PWD/data" uv run --no-sync python /tmp/b2-verify/sample_check.py
shasum -a 256 "/Users/hsiaojohnny/Downloads/0903-科務會議.m4a"
```
