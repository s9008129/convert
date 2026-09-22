# Track D — 契約稽核（唯讀）

- 任務：`T20260922-1930-01-local-record-quality-parity`｜分支 `fix/local-lmstudio-record-quality`
- 稽核時間：2026-09-22 20:10（Asia/Taipei）
- 稽核修訂（working tree，**尚未 commit**；以下 sha256 為本報告綁定版本）：
  - `backend/core/text_postprocess.py` `5b4e6d3c70c914255809e106c66b1fee83de70dd904537e6b0fa4db10fea2298`
  - `backend/core/templates.py` `209cffbbfa493f0e3a92c15b9fea8ed580fc18bbcf702730ea91b27ec53f0077`
  - `backend/core/prompt_templates/section_meeting.py` `17bc5c23eeaad9a75e2ce2fafaf92c6abf0ea17825b6e4f201b55e2f7b7d0d52`
  - `backend/services/summarization.py` `a23330a117adac371c2f5eda43587e7a0f734306f65007e3e9521b2aaedac079`
  - `scripts/e2e/run_owned_e2e.py` `c79da56a469abcd08eebf88a9d0c40919c2dba8d8942f1910159bc44fc8f5ace`
  - `scripts/e2e/measure_record_quality.py` `3705d8e1aa6bc132c39140f361f743a01fe0ba22e1f27af76ad9f4877441143a`
- 稽核方式：只讀 `rg`／`sed`／`git diff`／`git status`；另以 `PYTHONDONTWRITEBYTECODE=1` 執行 (a) W6 量測腳本（stdout，未用 `--out`）、(b) runner 的 `validate_formal_docx_bytes`、(c) 模板列舉／strip／attachment 的記憶體內驗證（未寫任何受稽核檔）。未跑測試套。
- **全域注意（會直接讓 E2E 無法啟動，非程式缺陷）**：`git status --porcelain` 有 **19 筆**變更（含 9 筆 `??` 未追蹤）；runner 的 clean-HEAD preflight 以 porcelain 條目數判定（`scripts/e2e/run_owned_e2e.py:366-373`、`:1151`），**未 commit 前 `run_owned_e2e.py` 必定在啟動 backend 前 FAIL**。Stage 05 必須先形成 commit。

---

## 1. 雲端路徑未受影響 — `[PASS]`

呼叫點與 mode（唯一產品檔 `backend/services/summarization.py`；`--glob '!tests/**'` 全 repo 掃描只有這 7 處）：

| file:line | 角色 | 傳入 mode |
|---|---|---|
| `summarization.py:2138` | 地端最終生成後（local pipeline） | `mode="local"`（:2139） |
| `summarization.py:2177` | 地端每一輪補強後（:2151 loop 內） | `mode="local"`（:2178） |
| `summarization.py:2208` | `_finalize_record_text` 定義 | `mode: str = "cloud"`（:2212，keyword-only） |
| `summarization.py:2275` | `_finalize_cloud_record_text` → `_finalize_record_text` | **未傳 → 預設 "cloud"** |
| `summarization.py:3253` | Gemini 雲端最終生成 | 走 `_finalize_cloud_record_text` → cloud |
| `summarization.py:3283` | Gemini 雲端補強輪 | 走 `_finalize_cloud_record_text` → cloud |

雲端訊息 builder 也不帶 mode：`_build_cloud_summary_message`（:1400-1407）與 `_build_cloud_refinement_message`（:1409-1419）都只傳 template；地端導引列只在 `mode=="local"` 注入（`_local_tag_placement_rule`，:1283-1292）。`mode != "local"` 分支逐字回傳 `normalize_unfilled_placeholders(finalize_record(...))`（:2240-2241），與 v4.8.0 同序同參。

```console
$ rg -n "_finalize_record_text|_finalize_cloud_record_text" --glob '!*.pyc' --glob '!tests/**' .
./backend/services/summarization.py:2138:        summary = self._finalize_record_text(
./backend/services/summarization.py:2177:            summary = self._finalize_record_text(
./backend/services/summarization.py:2208:    def _finalize_record_text(
./backend/services/summarization.py:2266:    def _finalize_cloud_record_text(
./backend/services/summarization.py:2275:        return self._finalize_record_text(summary, template=template)
./backend/services/summarization.py:3253:        summary = self._finalize_cloud_record_text(
./backend/services/summarization.py:3283:            summary = self._finalize_cloud_record_text(
```
```console
$ sed -n 2138,2140p backend/services/summarization.py
        summary = self._finalize_record_text(
            self._clean_ollama_output(summary), template=template, mode="local"
        )
$ sed -n 2275p backend/services/summarization.py
        return self._finalize_record_text(summary, template=template)
```

無任何雲端／`_build_cloud_*`／`generate_cloud` 路徑可新收到 `mode="local"`。**[PASS]**

---

## 2. 地端全部呼叫點（含每一輪補強寫回） — `[PASS]`

- `summarize()` 分派：`summarization.py:442-443`（cloud→`_summarize_with_gemini`；其餘→`_summarize_with_local_pipeline`）。
- 地端紀錄只有一條產出管線 `_summarize_with_local_pipeline`（:2019）；最終生成後立刻 `mode="local"` 收尾（:2138-2140）。
- 補強迴圈 `while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS`（:2151）；**迴圈內每一輪**生成後都走同一 `mode="local"` 收尾（:2177-2179）；迴圈結束後只記 warning 與 metrics，**沒有任何後續改寫**。
- 全 repo 只有兩個 refinement loop（local `:2151`、cloud `:3270`）；cloud loop 走 cloud 收尾（:3283）。
- 下游不改寫：`task_processor.py:396`（「不再改寫紀錄本文」）、`:407`（`body = summary`）。
- 其他地端產生紀錄的入口（`scripts/e2e/rerun_local_summarize.py:16,174`）走同一 `SummarizationService.summarize` 生產路徑，因此同樣受 `mode="local"` 覆蓋。

```console
$ rg -n 'mode="local"' backend/services/summarization.py
1674:            notes, None, template=template, mode="local"
1679:            notes, transcript, template=template, mode="local"
1706:            current_summary, notes, issues, None, template=template, mode="local"
1711:            current_summary, notes, issues, transcript, template=template, mode="local"
2139:            self._clean_ollama_output(summary), template=template, mode="local"
2178:                self._clean_ollama_output(summary), template=template, mode="local"
```
（1674/1679/1706/1711 為地端 `_resolve_final_*` 訊息組裝；2139/2178 為最終生成與每輪補強後的收尾。）

**無「補強輪以 cloud 預設收尾」的洞。** `[PASS]`

---

## 3. Term-fix 可達性與模板覆蓋 — `[PASS]`

`backend/core/templates.py` 內共有 4 個 `MeetingTemplate(...)` 建構（無任何 dict／runtime 動態建構；註冊表為靜態 dict comprehension）：

| template id | 建構行 | `record_term_fixes` 值 | 依據 |
|---|---|---|---|
| `general` | `templates.py:195` | `()`（dataclass 預設） | `templates.py:175` 預設 `()`；該建構未覆寫 |
| `procurement_evaluation` | `templates.py:303` | `()` | 未覆寫 |
| `section_meeting` | `templates.py:385` | `SECTION_MEETING_RECORD_TERM_FIXES`（4 條） | `templates.py:474`；定義於 `section_meeting.py:141-146` |
| `isms_monthly` | `templates.py:600` | `()` | `templates.py:618` `forbidden_patterns=()`，未覆寫 |

`_TEMPLATES`（`templates.py:687`）由上述 4 個實例組成；`get_template`（:698）`None`／空字串→`general`，未知 id→`ValueError`。地端接線 `summarization.py:2251` 以 `getattr(template, "record_term_fixes", ())` 取值（`section_meeting` 必得 4 條；其餘 0 條）。

```console
$ PYTHONDONTWRITEBYTECODE=1 DATA_DIR="$PWD/data" uv run --no-sync python - <<'PY'
from backend.core import templates as t
for tpl in t.list_templates(): print(tpl.id, "->", len(tpl.record_term_fixes), tpl.record_term_fixes)
PY
general -> 0 ()
procurement_evaluation -> 0 ()
section_meeting -> 4 (('征收股', '徵收股'), ('增收股', '徵收股'), ('人事總數(?=\\s*(?:Email|E-mail|電子郵件|郵件|寄|偽造|釣魚))', '人事總處'), ('瑞裏', '瑞里'))
isms_monthly -> 0 ()
get_template(None).id = general
unknown id -> ValueError 未知的會議類型: nope
```

非空僅 `section_meeting`、其餘模板空集合。`[PASS]`

---

## 4. 表格標註清除的爆炸半徑 — `[PASS]`（附 2 個殘餘風險）

實作（`backend/core/text_postprocess.py`）：
- `SOURCE_TAG_PATTERN`（:479）與 `SummarizationService._SOURCE_TAG_PATTERN`（`summarization.py:142`）逐字相同。
- 只認表格列：`_TABLE_ROW_PATTERN = re.compile(r"^\s*\|")`（:482）；逐行 `match`，非表格列直接跳過。
- 啟用閘門：`template_forbids_table_source_tags`（:491-502）掃 `forbidden_patterns` **標籤**是否含「發言來源標註」；`template=None`／缺屬性一律 False。
- 移除樣式（:484-486）會一併吃掉標註前的空白／頓號／逗號／分號。

`section_meeting` 的 forbidden label 為「彙整表內出現發言來源標註」（`templates.py:406-414`）→ 啟用；`general`（dataclass 預設 `()`，`templates.py:145`，未覆寫）、`procurement_evaluation`（:323-333 兩個標籤皆不含）、`isms_monthly`（:618 空 tuple）→ 停用。

記憶體內實測（真實基線檔）：

```console
$ ... strip_source_tags_from_table_rows(md, get_template("section_meeting"))
templates: [('general', 0), ('procurement_evaluation', 0), ('section_meeting', 4), ('isms_monthly', 0)]
forbids: {'general': False, 'procurement_evaluation': False, 'section_meeting': True, 'isms_monthly': False}
removed: 13 | table tags after: 0 | body tags after: 33
changed lines: 13 | all table rows: True
general no-op: True 0
attachment raw tags: 13 | after strip: 0
```

- 非表格行：**0 行被動**（changed 13 行全為 `^\s*\|` 表格列；正文 33 個標註逐字保留）。
- `general` 模板：byte 級 no-op（`out == md`，removed=0）。
- 雲端：`mode` 預設 cloud 使 strip 根本不會被呼叫（見 §1）。
- 列管資料附件讀同一份文字：附件由 **最終紀錄 md** 建構——`backend/api/routes.py:405-407` 讀 `result_path`，該檔由 `file_manager.save_result`（`file_manager.py:227-233`）寫入（內容＝ `task_processor.py:407` 的 finalized summary）；模擬結果 **raw 13 → strip 後 0**。修復後標註無法再流入附件。

殘餘風險（不阻擋本項 PASS，但與 §6/§7 相關）：
1. 只認 ASCII `|`：全形 `｜` 或非行首 `|` 的「表格」既不被清除、也不被 forbidden 樣式（`templates.py:406-414`，以 `^\|` 開頭）攔阻。
2. 清除範圍是「表格列內任何符合 `SOURCE_TAG_PATTERN` 的括號時間字串」，不限語意上的來源標註（例如表格內合法的 `（10:30 …）` 也會被移除）；此為 plan W2b 已明訂的形式判準。

---

## 5. Runner 模板感知 — `[PASS]`（附 1 個 false-FAIL 風險）

- 常數與推導：`run_owned_e2e.py:104-131`（`TEMPLATE_REQUIRED_SECTIONS` 僅 `section_meeting`；`TEMPLATE_REQUIRED_SECTION_PATTERNS` 由字面推導容忍空白樣式）。
- 簽名：`:560-562` `validate_formal_docx_bytes(docx_bytes, content_disposition, template_id=None)`。
- 分支：`:602-620`：`template_id in TEMPLATE_REQUIRED_SECTIONS` → 模板章節；否則（`general`／`None`／未列表）→ `GENERAL_REQUIRED_SECTIONS`＋`REQUIRED_SECTION_PATTERNS`，且未列表時僅多印一行 **stderr** `[WARN]`，失敗字串與修正前逐字相同。
- 呼叫點：**全檔唯一** `:921` `validate_formal_docx_bytes(docx_bytes, docx_disposition, meeting_template)`；`meeting_template` 的唯一來源是 `:1263` `meeting_template=args.template`（`run_full_e2e` 全 repo 僅一個呼叫點 `:1257-1263`，API／browser 共用）。
- `--template` 有值時才加 required check `template_applied`（`:1307-1308`；`template_applied` 由 `:884-892` 的 `task.template_id` 比對產生）。

以真實 attempt-03 DOCX 實測（修正前必 FAIL 的情境）：

```console
$ ... runner.validate_formal_docx_bytes(baseline_docx, formal_disposition, tid)
section_meeting -> []
None -> ['DOCX OOXML 的 general 模板 section「一、報告事項」缺少非空後續內容', '...「二、討論事項」...', '...「三、主席裁示事項」...']
general -> （與 None 完全相同 3 條）
isms_monthly -> （與 None 完全相同 3 條；stderr 多一行 [WARN] 未列表）
procurement_evaluation -> （與 None 完全相同 3 條；stderr 多一行 [WARN] 未列表）
```

`general`／`None`／未列表模板的 verdict 行為不變（僅未列表多一行 stderr 診斷）。`[PASS]`

false-FAIL 風險（供 Stage 05 注意）：runner 對 `section_meeting` 只驗 4 個「章節級」項目（`一、科長轉知`／`二、科長指示及提醒事項`／`案由及承辦單位`／`散會`），且每個項目要求「其後仍有非空內容」；若模型把 `散會` 寫成整份文件最後一行且其後無內容，模板感知檢查會判 FAIL（基線有「散會：（待確認）」故過關）。另此 4 項未涵蓋產品契約的 `時間`／`主持人`／`紀錄標題`（`templates.py:395-402`）——但產品自身的 `_validate_summary_quality` 會在生成階段攔這些缺漏。

---

## 6. 量測儀器正確性 — `[PASS]`（數字全對；定義漂移為缺陷）

定義（`scripts/e2e/measure_record_quality.py`）：
- `count_source_tag_regions`（:91-115）：逐行；`"|" in stripped` → table 計數（:109）；`^(?:時間|地點|主持人|出席人員|紀錄)`（:75）→ header 排除；其餘 → body。與 `summarization.py:1064-1066` 既有排除語意一致（plan W6 要求）。
- `extract_body_items`／ratio（:118-130、:210-212）：leaf item＝`^\s*(?:\d+\.|[（(]\d+[)）])`（:78），排除 `|` 行與開頭欄位；`tagged_item_ratio = 有標註 items / items`。
- 共用白名單：import 軌 A 的 `SOURCE_TAG_PATTERN`、`SECTION_MEETING_RECORD_TERM_FIXES`、`dedupe_cross_section_items`（:73-80），未複製第二份。
- plan §5（`plan.md:131-136`）對 `table_source_tag_count = 0`、`body_source_tag_count ≥ 1`（退化線 <17，`plan.md:32-33`）。

腳本實際輸出（真實基線 artefact）：

```console
$ PYTHONDONTWRITEBYTECODE=1 DATA_DIR="$PWD/data" uv run --no-sync python scripts/e2e/measure_record_quality.py --record data/cache/e2e/p1-baseline-01/backend_data/outputs/0903-科務會議_70a58030.md --transcript data/cache/e2e/p1-baseline-01/transcript.txt --template section_meeting
  "body_source_tag_count": 33,
  "table_source_tag_count": 13,
  "instruction_item_count": 9,
  "tagged_item_ratio": 0.9706,
  "cross_section_duplicate_pairs": 0,
  "known_term_fix_hits": {"left_hits": 0, "right_hits": 3, "transcript": {"left_hits": 3, ...}}
```

獨立重算（同一 artefact，`grep`/`rg`）：

```console
$ grep -o -E '（[^）]{0,24}?[0-9]{1,2}:[0-9]{2}(:[0-9]{2})?[^）]{0,12}?）' <md> | wc -l            # 全檔
46
$ grep -E '^[[:space:]]*\|' <md> | grep -o ... | wc -l                                          # 表格列標註
13
$ grep -vE '^[[:space:]]*\|' <md> | grep -vE '^(時間|地點|主持人|出席人員|紀錄)' | grep -o ... | wc -l  # 正文
33
$ ... | grep -cE '^[[:space:]]*([0-9]+\.|[（(][0-9]+[)）])'                                       # body leaf items
34
$ ... | grep -c -E '（...時間樣式...）'                                                          # 帶標註 items
33
```

46 = 33 + 13，leaf items 34、33 帶標註 → 33/34 = 0.9706，與腳本 JSON 完全一致（plan 說 46＝33＋13、97.1%）。**數字 PASS**。

**缺陷（定義漂移，可能讓驗收失效）**：`table_source_tag_count` 的表格判準是「行內任何位置含 `|`」（:109），但 (a) 清除器 `strip_source_tags_from_table_rows` 只處理「行首（可縮排）`|`」（`text_postprocess.py:482`），(b) 產品 forbidden 樣式要求行首即 `|`（`templates.py:406-414`）。後果：
- 正文行只要含一個 `|` 且帶標註 → 會被計為 table → CORE-1 的 `table = 0` 可能**永遠無法達成**（false FAIL，且無程式可清除它）。
- 反之，全形 `｜`／非行首 `|` 的真表格列標註 → 計為 body 且不被清除 → `table = 0`、`body ≥ 1` 可**通過**而使用者端表格仍帶標註（false PASS）。
基線 artefact 無此形狀（body 0 行含 `|`），故本次重算不受影響；新 E2E 紀錄若出現上述形狀，驗收即失真。

---

## 7. 驗收相關殘餘風險（Stage 05 可能 PASS 但使用者體感仍差） — `[FAIL]`

（本項非實作缺陷：1-7 為驗收流程／量尺覆蓋不足；現行程式碼在 §1-§6 契約面均為 PASS。）

依 `plan.md:131-136`（§5）、`handoff.md:73-75`（STOP/ESCALATION）逐條比對：

1. **Runner verdict 完全不含 CORE-1／CORE-2 指標**。`run_owned_e2e.py` 的 required checks（`:1291-1306`）沒有任何 `table_source_tag_count`／`body_source_tag_count`／`known_term_fix_hits`；全檔未引用 `measure_record_quality`（`rg` 無命中）。且 W6 工具永遠 `exit 0`（除檔案不存在等參數錯誤），**不會 FAIL**。→ `verdict=PASS` 可與「彙整表仍有標註」「正文退化到 1 個標註」並存，只要驗收者沒手動跑／沒如實解讀 W6。
2. **退化防線 `<17` 未機械化、`body ≥ 1` 過弱**：plan §1 明訂 body <17 即回 Stage 01（`plan.md:32-33`），但沒有任何程式檢查；`body=1`、甚至 `items=1/tagged=1`（ratio=100%）都能通過 plan 的字面門檻，單次抽樣（temperature 0.7）下可能以退化紀錄 PASS。
3. **CORE-2 的 E2E 閘門無鑑別力**：基線紀錄在**修復前**左側命中已是 **0**（錯誤形只存在逐字稿，transcript left=3），因此「左側命中=0」通過與 `apply_record_term_fixes` 是否真的生效無關；W6 也不驗證右側字是否經修正產生。CORE-2 只能靠單元測試（plan 亦如此設計），E2E 不得被當成修正生效證據。
4. **列管資料附件不在 E2E 路徑**：runner 只下載紀錄 DOCX／逐字稿（`run_owned_e2e.py` stage 4-5），附件端點（`routes.py:394-410`）未被驗收；本報告的附件 13→0 為記憶體模擬＋單元測試層級證據。
5. **`散會` 條款 false FAIL**（見 §5）：模型輸出若以裸 `散會` 收尾且其後無內容，verdict 會 FAIL 而使用者看到的紀錄其實正常。
6. **clean-HEAD preflight**：目前 19 筆 dirty/untracked（含 9 筆 `??`）→ 未 commit 前 E2E 必定 FAIL；反之，若為了跑 E2E 而臨時 commit，也必須確保 commit 內容＝本報告稽核的 sha 版本。
7. **W5 dedupe 作用域比 plan 描述寬**：`_finalize_record_text(mode="local")` 對「所有非 `section_meeting` 的本端模板」都會呼叫 dedupe（`summarization.py:2255`），而 plan/handoff 將 W5 描述為 general 專屬。實務上 `isms_monthly`／`procurement_evaluation` 無「決議」＋「主席裁示事項」標題對，函式會 early-return（`text_postprocess.py:667` 只排除 section_meeting），故目前 no-op；但這是超出書面範圍的潛在改寫面。

---

## 最可能讓 E2E 驗收失效的 3 件事

1. **Runner 的 PASS 與 CORE-1／CORE-2 無機械連結**：required checks 完全不含 W6 指標，W6 工具也永不 non-zero；「verdict PASS」在表格標註仍存在、或正文只剩 1 個標註時照樣可能出現。Stage 05 必須把 W6 JSON 當**閘門條件**人工（或補 runner check）執行並貼證據。
2. **表格判準定義漂移（metric `"|" in line` vs 清除 `^\s*\|` vs forbidden `^\|`）**：正文含 `|` 的標註會造成永遠綠不了的 false FAIL；全形／非行首 `|` 的真表格標註則可能被計成 body 而讓 `table=0` 假性通過——兩種方向都會讓驗收結論失真。
3. **退化與抽樣無防護**：`body < 17` 的退化防線未機械化、`tagged_item_ratio` 分母可小到 1，加上單次抽樣（temp 0.7），一個「表格 0、正文 1 個標註、內容單薄」的紀錄仍可通過字面門檻與 runner verdict。
