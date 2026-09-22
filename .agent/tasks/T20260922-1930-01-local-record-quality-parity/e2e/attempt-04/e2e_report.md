# E2E 獨立驗收報告 — attempt-04（Stage 05）

- TASK_ID: `T20260922-1930-01-local-record-quality-parity`
- 判定對象：plan rev6（`bbfcd024…`）／handoff rev6（`PLAN_APPROVED`）
- 產出檔：`record.md`（＝runtime MD 複本）、`record_quality.json`、`baseline_record_quality.json`、
  `runner-console.txt`、`runner-times.txt`、`attempt.json`、`unit_tests_targeted.txt`、`unit_tests_full.txt`、
  `raw_model_output_*.md`（LM Studio server log 抽回的 raw 模型輸出）、`extract_raw_outputs.py`（抽回工具）

## 受測版本

| 項 | 值 |
|---|---|
| repo／branch | `/Users/hsiaojohnny/dev/convert`｜`fix/local-lmstudio-record-quality` |
| HEAD sha | `c611e6d58856c24f229a9637efd0d7ae0148cf5f`（開始前 `git status --porcelain` 為空＝乾淨） |
| `MEETINGSCRIBE_BUILD_REVISION` | `c611e6d58856c24f229a9637efd0d7ae0148cf5f`（runner 注入；`/api/health` 回報一致 → `build_revision_match=true`） |
| 模型 | `qwen3.6-35b-a3b-splash`（LM Studio、context 128000、唯一 loaded LLM instance；起訖 snapshot 一致） |
| 模式／模板 | `--processing-mode local`｜`--template section_meeting`（`template_applied=true`） |
| 音檔 | `/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…`，與上傳儲存位元組一致） |

## 執行指令與耗時

```
DATA_DIR="$PWD/data" uv run --no-sync python scripts/e2e/run_owned_e2e.py \
  --audio "/Users/hsiaojohnny/Downloads/0903-科務會議.m4a" \
  --processing-mode local --template section_meeting \
  --artifacts-dir .agent/tasks/T20260922-1930-01-local-record-quality-parity/e2e/attempt-04 \
  --runtime-dir data/cache/e2e/p1-fixed-01
```

- 牆鐘：`2026-09-22T20:19:53+08:00` → `20:27:13+08:00`，**總計 440 s（約 7 分 20 秒）**；exit code **0**。
- runner 自記：`20:19:54.023` → `20:27:13.490`＝**439.5 s**（與 attempt-03 基線 439.8 s 同級）。
- pipeline 分段：extraction 64.2 s／merge 0.0／final+refine 170.3 s／pipeline total 234.5 s；
  `logical_generations=4`（extraction＋final＋refinement×2）、`network_retries=0`。
- ASR：apple engine、音檔 2695.1 s、耗時 15.9 s、1340 segments、0 dropped。

## runner verdict 與全部 checks／failure_reasons

verdict＝**PASS**；`failure_reasons=[]`（attempt-03 的 4 條 general 章節誤判全部消失）。

| check | 值 | check | 值 |
|---|---|---|---|
| backend_started | true | task_completed | true |
| health_ok | true | task_summary_failed_false | true |
| build_revision_match | true | transcript_downloaded | true |
| model_snapshot_captured | true | docx_downloaded | true |
| model_inventory_unique | true | **formal_docx_valid** | **true** |
| upload_ok | true | metrics_valid | true |
| stored_upload_sha_match | true | model_snapshot_consistent | true |
| **template_applied** | **true** | child_terminated | true |

DOCX 模板感知路徑證據：`run_owned_e2e.py:921` 以 `meeting_template="section_meeting"` 呼叫
`validate_formal_docx_bytes(..., template_id)` → 走 `TEMPLATE_REQUIRED_SECTIONS["section_meeting"]`
（`一、科長轉知`／`二、科長指示及提醒事項`／`案由及承辦單位`／`散會`）；console 無「沿用 general」WARN。
獨立抽查 DOCX OOXML：4 章節字面各 1 次、無 fallback／逐字稿標記 → 非 transcript dump。

## CORE-1 判定 — **PASS**

儀器：`scripts/e2e/measure_record_quality.py --record <MD> --transcript <runtime 逐字稿> --template section_meeting`
（輸出：`record_quality.json`）。原始數字：

| 指標 | 實測 | 門檻 | 基線 |
|---|---|---|---|
| `table_source_tag_count` | **0** | =0 | 13 |
| `body_source_tag_count` | **27** | ≥1；退化線 <17 | 33 |
| `non_prefixed_tableish_source_tag_count` | 0（觀察值） | — | 0 |
| `tagged_item_ratio` | 1.0（27/27） | SUPPORTING-4 登記 | 0.9706（33/34） |

判定：表格 0 ✓、正文 27 ≥ 1 ✓、且 27 ≥ 17（未觸退化線）→ **PASS**。
獨立重算（grep 同 pattern）：新紀錄全檔 27 標註＝表格 0＋正文 27；基線 46＝13＋33。
`instruction_item_count`＝2（「二、科長指示及提醒事項」節內；基線 9）——登記，不閘門。

## CORE-2 判定 — **PASS（含鑑別力說明）**

- `known_term_fix_hits`（紀錄）：left=0 ✓（逐字稿 left=3：征收股1／增收股1／瑞裏1）；
  right：徵收股 2、瑞里 3、人事總處 0。
- **鑑別力說明（必讀）**：基線（修復前）紀錄的 left_hits **本來就是 0**（trackD §7.3），
  故本項 E2E 通過與否**不取決於 W3 是否生效**。且本次 run 的
  `[品質] 地端紀錄後處理` 從未出現 → `apply_record_term_fixes` 實際觸發 **0 處**；
  紀錄字形乾淨來自語意校正層（19 處替換）與模型自身，**不得**把本 E2E 當成 term-fix 生效證據。
- 真實證據＝單元測試：5 檔 targeted **84 passed**；全套（`--ignore=tests/test_end_to_end.py`）
  **881 passed, 2 skipped**（含「人事總數為 45 人」負案例）。

## SUPPORTING 登記（不阻斷）

- **SUPPORTING-1**：`template_applied` ＋ `formal_docx_valid` ＋ verdict PASS ✓。
- **SUPPORTING-2（W5 dedupe）**：本次場景 `cross_section_duplicate_pairs=0`、
  `[品質] 地端紀錄後處理` 的「跨節重複移除」未觸發；W5 證據在單元測試（fixture 10／0）。
- **W2b／W3 in-flight（實測）**：全 run `[品質] 地端紀錄後處理` **0 行** → 三項計數全為 0
  （final r0 @20:25:14、refinement#1 @20:26:08、refinement#2 @20:27:08 的 finalization 都沒有觸發）。
  唯一品質後處理 log＝`[品質] 修復範本骨架佔位符 3 行`（20:25:14，r0 finalization）。
- **forbidden issues**：兩輪 refinement 問題全是「待辦事項遺漏 N 項」（第1輪 2 項、第2輪 19 項、
  終態警告 1 項：確認文康活動形式…）；**任何一輪都沒有出現「彙整表內出現發言來源標註」**。
  refinement 輪數＝**2**（等於上限，燒完仍有 1 項覆蓋警告）。
  該終態警告項其實已列於彙整表（「確認文康活動形式（外出用餐或辦公室下午茶＋禮券）及現金發放程序」）
  → 屬驗證啟發式 vs 表格文字的登記缺口，非硬性缺漏。
- **SUPPORTING-3／4**：覆蓋率僅登記（見殘餘風險）；ratio 1.0 ≥ 50% ✓。

## 對基線差異表（attempt-03：`p1-baseline-01`，同音檔／同模型／同模板）

| 指標 | 基線 | attempt-04 | 差異 |
|---|---|---|---|
| verdict | FAIL（驗收器誤判） | **PASS** | failure_reasons 4→0 |
| `char_count` | 3238 | 3368 | **+130（+4.0%）** |
| `table_source_tag_count` | 13 | **0** | −13 |
| `body_source_tag_count` | 33 | **27** | −6（仍在 17 之上） |
| `tagged_item_ratio` | 0.9706（33/34） | 1.0（27/27） | +0.0294 |
| 彙整表資料列數 | 13 | 21 | +8（表格內容變多） |
| `instruction_item_count` | 9 | 2 | −7（登記） |
| `cross_section_duplicate_pairs` | 0 | 0 | 0 |
| 未落地專名（觀察） | 徵收股／煙酒業務股／稽徵股 | 徵收股／煙酒業務股／稽查股 | 觀察值 |
| 耗時 | 439.8 s | 439.5 s | 同級 |

**兩次都是單次抽樣（temperature 0.7）**；上述差異不得外推為分布結論。

## 已知限制與殘餘風險

1. **單次抽樣**：CORE 以本次樣本＋確定性指標為準，不得外推。
2. **正文標註 27 < 基線 33（−18.2%）**；「二、科長指示及提醒事項」節僅 2 條（基線 9），
   部分內容改落於彙整表（21 列）／第一章；結構密度差異已登記。
3. **覆蓋率**：refinement 2 輪燒完仍有 1 項「待辦事項遺漏」警告（登記；plan 明定不閘門）→
   使用端仍可能需要人工補列。
4. **ASR／錯字殘留**（使用者體感風險）：紀錄中可見「校費稅科」（逐字稿亦有）、「猜情風險」、
   「科原」、「審員」等；`unsupported_entities` 觀察值 3 筆（徵收股／煙酒業務股／稽查股，屬
   ASR 變體重建，字面比對無法判捏造）；**「瑞吉」在紀錄 2 次但逐字稿 0 次**（可能未落地，
   建議人工複核）。這些皆在 plan §6 已明示「本波不做」。
5. **儀器邊界**：table 判定已與清除器同定義（`^\s*\|`）；全形「｜」／非行首缺口以
   `non_prefixed_tableish_source_tag_count` 觀察（本次 0，未 materialize）。W6 工具永不 non-zero，
   CORE 判定為本次 Stage 05 手動套用（見上）。
6. **W2b stripper 本次完全未觸發**：raw 模型輸出（自 LM Studio server log 抽回）三次生成
   table_tags 皆 0 → 模型本身已不寫表格標註；確定性清除器在 E2E 未被實測（僅單元測試覆蓋）。
   正文未損失：raw r2 body=27＝最終 artifact body=27，且 diff 僅新增標題 2 行。
7. attempt-04 檔案為新增 untracked 證據（Stage 05 規則：不 commit、不 git add）。
8. **相鄰證據（非本人撰寫）**：`quality/attempt-01/quality_review.md`（Track E 品質評閱，20:31 產生，
   評閱同一份 `327a48e6` 紀錄）指出「27 個出處標註中 17 個時間戳在逐字稿不存在、多件歸屬存疑」。
   本人 spot-check 5 個標註：3 個時間戳可在逐字稿找到（00:03:45、00:05:57、00:16:55）、
   2 個找不到（00:44:00、00:28:00）→ 該殘餘風險方向成立，值得擁有者複核（本波不閘門）。

## 最終閘門

**ACCEPTED**
