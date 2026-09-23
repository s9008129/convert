# attempt-03 附錄：原始證據輸出（evidence.md）

> 對應受審檔：`$T/plan.md`（`PLAN_REVISION 4`）；本檔為 `$T/review/attempt-03/review.md` 的原始輸出佐證。
> `$T`＝`.agent/tasks/T20260923-1810-01-local-record-fidelity-density`（除特別註明外，指令皆自 repo 根執行）。
> 產出時間窗：2026-09-23 19:18–19:35（台北）。全部輸出皆於本機實跑、可原文重現；
> **0 次模型呼叫、0 次 E2E、未跑 pytest 全 suite、未呼叫外部服務**。
> 本 attempt 僅**新增** `review.md` 與本檔；未修改 `plan.md`、產品程式碼或任何既有 `review/**`；未 commit；
> 亦未動 `$T/e2e/`（另一個工作階段的 E2E 執行中產物，未讀取）。

---

## 0. 受審快照、commit 基準與環境

### 0.1 受審快照（plan.md）

```console
$ shasum -a 256 $T/plan.md
dc11dd1167418ab9fbad8325b723566cd9e3df4d2db1cf8e1c3272c2994e08fc  $T/plan.md
$ stat -f '%Sm %N' $T/plan.md
Sep 23 19:03:58 2026 $T/plan.md
$ wc -l $T/plan.md
     221 $T/plan.md
$ rg -n 'PLAN_REVISION' $T/plan.md
4:- `PLAN_REVISION`: 4
16:## 0. rev1 → rev2 變更摘要（來源：`review/attempt-01/review.md`，gate `PLAN_REVISION_REQUIRED`）
46:### 0c. rev3 → rev4（來源：`review/attempt-02/review.md`，gate `PLAN_REVISION_REQUIRED`）
```

- 量測時點：審查開始（19:17 前）與本附錄完成前各一次，**同值**，且與指定預期值一致；mtime 19:03:58（審查期間未再改寫）。
- 檔頭 `# …— rev4`。該 sha256 亦等於後續 commit `5cff85f` 內之 plan.md：

```console
$ git show 5cff85f:$T/plan.md | shasum -a 256
dc11dd1167418ab9fbad8325b723566cd9e3df4d2db1cf8e1c3272c2994e08fc  -
```

### 0.2 review.md 本身（本 attempt 產物，雜湊對帳）

```console
$ shasum -a 256 $T/review/attempt-03/review.md
7a3e095e3e81eed29c62e8c77262370fccf45295522a0dac2ddd31781b13065e  $T/review/attempt-03/review.md
$ git show 5cff85f:$T/review/attempt-03/review.md | shasum -a 256
7a3e095e3e81eed29c62e8c77262370fccf45295522a0dac2ddd31781b13065e  -
$ tail -1 $T/review/attempt-03/review.md
GATE: PLAN_APPROVED
```

（review.md 於 19:17 定稿、19:20:49 隨 commit `5cff85f` 進版控；本附錄未改動它一個位元組。）

### 0.3 commit 基準（重要：HEAD 於審查後前進）

```console
$ git log -1 --format='%H %cI %s' ac181be
ac181be510ce1e95882936bb7391d3c2ce8b940f 2026-09-23T18:55:37+08:00 feat(quality,p7b): 量測儀器擴充（全文條目／近似重複）＋P7-B 校準與成本實測證據；規劃 rev3
$ git log -1 --format='%H %cI %s' 5cff85f
5cff85f6372fc69b541f1d7b30b0b229d5fb6006 2026-09-23T19:20:49+08:00 feat(quality,p7b): 地端會議紀錄保真度修復（結構性分塊／生成紀律／佔位符正規化）＋Stage 02 審查通過
```

- **review.md 所述的「HEAD」一律指審查當時的 HEAD＝`ac181be`**（例：§2.1 的 `:300` 串接行、§2.2 的 `:2439`／`:2449`／`:2500`，見 §2）。審查進行中（19:05–19:17）工作樹仍有未 commit 實作且持續變動（review.md 載：`summarization.py` sha `461e78db…` → `480f04b0…`）。
- 19:20:49 另一工作階段將本波實作＋plan rev4＋attempt-02／03＋handoff 一併 commit（`5cff85f`），故**現在** `git show HEAD:` ≠ `ac181be`；複核 review.md 的 HEAD 行號請用 `git show ac181be:backend/services/summarization.py`。
- 重播所依據的工作樹內容可回溯：`a077dc94…` 即 `5cff85f` 內之 blob（下 §4.2 的函式級比對亦在同兩份內容上完成）：

```console
$ git show 5cff85f:backend/services/summarization.py | shasum -a 256
a077dc944cc7bc06071b5dfaa560d62f3b9b58e492ab4b722042f9b88dd84acb  -
$ git show 5cff85f:backend/core/config.py | shasum -a 256
01390909a786ae5cb69c4595094d168f2682ee544d2de623997c5c5f6d4ef6de  -
```

### 0.4 工作樹狀態快照

審查開始（19:18）：

```console
$ git status --porcelain
 M .agent/tasks/T20260923-1810-01-local-record-fidelity-density/plan.md
 M .env.example
 M backend/core/config.py
 M backend/core/text_postprocess.py
 M backend/services/summarization.py
 M tests/test_t20260922_2037_p4b_fidelity_tripwires.py
 M tests/test_t20260922_record_quality.py
 M tests/test_t20260923_p7a_refine_no_regression.py
?? .agent/tasks/T20260923-1810-01-local-record-fidelity-density/evidence/p7b-chunk-replay/
?? .agent/tasks/T20260923-1810-01-local-record-fidelity-density/evidence/p7b-placeholder-replay/
?? .agent/tasks/T20260923-1810-01-local-record-fidelity-density/review/attempt-02/
?? .agent/tasks/T20260923-1810-01-local-record-fidelity-density/review/attempt-03/
?? tests/test_t20260923_p7b_generation_discipline.py
?? tests/test_t20260923_p7b_placeholder_normalize.py
?? tests/test_t20260923_p7b_tail_coverage.py
```

本附錄完成時（19:2x；commit 後）：

```console
$ git status --porcelain
?? .agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/
```

（`e2e/` 未追蹤目錄屬另一工作階段，非本審查產物。）

### 0.5 重播工具（皆純字串、0 模型呼叫）

- `uv run --frozen python`（既有 venv；`--frozen` 不更動 lockfile）。
- 審查當時留在 `/tmp` 的離線腳本（本附錄原文照登）：`/tmp/byte_check.py`、`/tmp/replay3.py`、`/tmp/replay_split2.py`。
- 既有儀器 `scripts/e2e/measure_record_quality.py`（deterministic、無 LLM 判定）。

---

## 1. I9 證據：§7 停損時鐘四數字與算式

### 1.1 對照場牆鐘／pipeline 數字（逐一實查）

```console
$ sed -n '42p' .agent/tasks/T20260923-1700-03-local-refine-no-regress/e2e/attempt-P7A-gemma31b-e7c/README.md
- runner 全程 wall：`16:42:14 → 17:17:39` = **2,125.5 s（35 分 25 秒）**

$ sed -n '18p' .agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-P6A-qwen27b-e6b/README.md
- 時間：2026-09-23 14:45:32 → 15:02:35（台北）＝**1,023.2 s**（runner wall；**task 1,015.4 s**）
```

```console
$ sed -n '177p;249p;527p' data/cache/e2e/p7a-gemma31b-e7c/backend.log
（下列輸出已去除 ANSI 色碼；`INFO …` 之後省略 logger 欄位（模組名／行號），其餘文字與數字逐字保留）
16:51:25 INFO … 本地摘要上下文規劃：context_window=71936(lmstudio_instance), estimated_tokens=11711, chunk_budget=65999, merge_input_budget=68459, merge_visible_target=4096, merge_feasible_input=62794, merge_provider_output=3072, needs_chunking=False
16:57:05 INFO … 萃取筆記零損串接（略過有損整併）：1 份、1669 tokens ≤ 下游可承接上限 62794 tokens，context window 71936 tokens
17:17:35 INFO … 本地摘要 pipeline metrics：chunk_count=1, logical_generations=4, semantic_attempts=0, network_retries=0, merge_rounds=0, merge_groups_last_round=0, duration_seconds={'extraction': 340.6, 'merge': 0.0, 'final_and_refine': 1229.6, 'total': 1570.2}cov_expected_topic=10 cov_missing_topic=1 cov_expected_decision=11 cov_missing_decision=1 cov_expected_number=9 cov_missing_number=0 cov_expected_date=4 cov_missing_date=0 cov_issues_added=2

$ sed -n '155p;287p' data/cache/e2e/p6a-qwen27b-e6b/backend.log
（同上：去除色碼、`INFO …` 後省略 logger 欄位）
14:52:30 INFO … 萃取筆記零損串接（略過有損整併）：1 份、3967 tokens ≤ 下游可承接上限 118858 tokens，context window 128000 tokens
15:02:33 INFO … 本地摘要 pipeline metrics：chunk_count=1, logical_generations=3, semantic_attempts=0, network_retries=0, merge_rounds=0, merge_groups_last_round=0, duration_seconds={'extraction': 166.8, 'merge': 0.0, 'final_and_refine': 602.7, 'total': 769.6}cov_expected_topic=14 cov_missing_topic=0 cov_expected_decision=27 cov_missing_decision=0 cov_expected_number=9 cov_missing_number=0 cov_expected_date=4 cov_missing_date=0 cov_issues_added=0
```

### 1.2 算式複核（`python3`）

```console
$ python3 - <<'PY'
print(150.5/1023.2, 150.5/2125.5)
print(340.6+150.5, (491.1/340.6-1)*100)
print(301/340.6, (301-340.6)/1570.2*100)
print(62/78-1, 48/42.5-1)
PY
0.1470875684128225 0.07080686897200658
491.1 44.18672930123311
0.8837345860246623 -2.5219717233473453
-0.20512820512820518 0.12941176470588234
```

### 1.3 plan §7 停損時鐘原文（節錄）

```
- **停損時鐘釘死＝runner 牆鐘**（審查 I9）。對照場：gemma＝P7-A **E7C 2,125.5 s**、
  qwen＝P6-A **E6b 1,023.2 s**。pipeline `duration_seconds.total`（1,570.2／769.6 s）**僅作交叉核對**，
  不與牆鐘混算（混鐘會讓「+15%」在不同模型上等於不同嚴格度）。
…
- 備援①（尾段補萃取）成本 **+150.5 s** ⇒ 對 qwen 牆鐘 **+14.7%**、對 gemma **+7.1%**；
  若與 CORE-1b 同時開啟使牆鐘增幅 ≥15%，須回 Planner 決策（執行者不得自行放行）。
```

plan §0b:37-39 對照表（「+44%」為萃取階段比例之出處）：

```
| 現況（E7C 實測） | 1 次（整份 11,711 est tokens） | **340.6 s** | — |
| rev2 的 CORE-1b（整份 ＋ 尾半段） | 2 次 | 340.6 ＋ **150.5** ＝ **491 s** | **+44%**（撞 §7 停損） |
| **rev3 的 CORE-1b（結構性分塊，每塊 ~6,000 tokens ⇒ 2 塊）** | 2 次（各約半份） | 150.5 × 2 ≈ **301 s** | **−12%**（推估） |
```

**判定**：`+14.7%`（150.5/1023.2）、`+7.1%`（150.5/2125.5）算術正確；`+44%` 僅為萃取階段（340.6→491.1）換算，非牆鐘。

---

## 2. I10 證據：雲端提示詞凍結（串接結構、掛載點、byte 比對）

### 2.1 `:300` 確實串接共用常數（以審查時 HEAD＝`ac181be` 複核）

```console
$ git show ac181be:backend/services/summarization.py | rg -n 'LOCAL_EXTRACTION_PROMPT = |CLOUD_EXTRACTION_PROMPT = |待辦清單要盡量拆細'
262:    LOCAL_EXTRACTION_PROMPT = """你是會議逐字稿資訊萃取助理。你的任務只有一個：盡量完整抽取事實，不要直接寫成最終會議記錄。
291:- 待辦清單要盡量拆細；設備、人力、場勘、新聞稿、餐盒、飲料、拍照流程等可獨立追蹤的工作請分列，不要合併成籠統大項。
300:    CLOUD_EXTRACTION_PROMPT = LOCAL_EXTRACTION_PROMPT + """
```

→ 就地改 `LOCAL_EXTRACTION_PROMPT` 一字即 byte 級改動雲端 ⇒ 契約（共用常數一字不改＋地端專屬區塊追加）是**必要**的。
工作樹（＝`5cff85f`）同構：`:289`（常數起點）／`:318`（拆細行）／`:327`（`CLOUD… = LOCAL… + """`）。

### 2.2 三個掛載點存在、可承載 local-only 追加

```console
$ rg -n 'def _local_extraction_prompt|def _local_tag_placement_rule|def _build_record_generation_message|def _build_record_refinement_message' /tmp/ac181be_summ.py
562:    def _local_extraction_prompt(self, template: Optional[MeetingTemplate] = None) -> str:
2439:    def _local_tag_placement_rule(cls, mode: str, speaker_rule: str) -> str:
2449:    def _build_record_generation_message(
2500:    def _build_record_refinement_message(
# （`:2439` 即 `_local_tag_placement_rule`＝「mode 非 local 回空字串」的既有模式，見其 docstring；
#  `/tmp/ac181be_summ.py` 為審查時留存之 ac181be 版快照，供複核。）

$ rg -n 'def _local_extraction_prompt|def _local_extraction_discipline_rule|def _cloud_extraction_prompt|def _local_tag_placement_rule|def _local_record_discipline_rule|def _build_record_generation_message|def _build_record_refinement_message|def _build_refinement_message|def _build_cloud_summary_message|def _build_cloud_refinement_message' backend/services/summarization.py
589:    def _local_extraction_prompt(self, template: Optional[MeetingTemplate] = None) -> str:
599:    def _local_extraction_discipline_rule(cls) -> str:
605:    def _cloud_extraction_prompt(self, template: Optional[MeetingTemplate] = None) -> str:
2514:    def _local_tag_placement_rule(cls, mode: str, speaker_rule: str) -> str:
2525:    def _local_record_discipline_rule(cls, mode: str) -> str:
2545:    def _build_record_generation_message(
2597:    def _build_record_refinement_message(
2642:    def _build_refinement_message(
2654:    def _build_cloud_summary_message(
2663:    def _build_cloud_refinement_message(
```

（工作樹行號為 `a077dc94` 當時；review.md 內載之工作樹行號為 `480f04b0` 當時——未 commit 實作仍在演進，兩者有 ±6 行位移。）

### 2.3 byte 比對（原腳本與原始輸出）

`/tmp/byte_check.py`（全文；審查當時建立、本次重播沿用）：

```python
import sys, os, hashlib
sys.path.insert(0, '/Users/hsiaojohnny/dev/convert')
os.environ.setdefault('DATA_DIR', '/tmp/byte_check_data')
from backend.services.summarization import SummarizationService
from backend.core.config import settings

svc = SummarizationService()
notes, transcript, cur, issues = "筆記內容X", "逐字稿Y", "目前版本Z", ["問題1"]

def snapshot():
    return {
        'cloud_extraction': svc._cloud_extraction_prompt(None),
        'local_extraction': svc._local_extraction_prompt(None),
        'cloud_gen': svc._build_cloud_summary_message(notes, transcript, template=None),
        'local_gen': svc._build_record_generation_message(notes, transcript, template=None, mode="local"),
        'cloud_refine': svc._build_cloud_refinement_message(cur, notes, issues, transcript, template=None),
        'local_refine': svc._build_record_refinement_message(cur, notes, issues, transcript, template=None, mode="local"),
        'legacy_refine': svc._build_refinement_message(cur, notes, issues, template=None),
    }

def set_rules(v):
    object.__setattr__(settings, 'LOCAL_LLM_ONEPERITEM_RULE', v)
    object.__setattr__(settings, 'LOCAL_LLM_SPEAKER_DISCIPLINE_RULE', v)
    object.__setattr__(settings, 'LOCAL_LLM_ANTI_DUPLICATE_RULE', v)

set_rules(True); on = snapshot()
set_rules(False); off = snapshot()
for k in on:
    same = on[k] == off[k]
    print(f"{k}: identical_on_off={same} len_on={len(on[k])} len_off={len(off[k])} sha_on={hashlib.sha256(on[k].encode()).hexdigest()[:12]} sha_off={hashlib.sha256(off[k].encode()).hexdigest()[:12]}")
```

```console
$ uv run --frozen python /tmp/byte_check.py
（logger 初始化行省略）
cloud_extraction: identical_on_off=True len_on=730 len_off=730 sha_on=437f3c9c44df sha_off=437f3c9c44df
local_extraction: identical_on_off=False len_on=616 len_off=562 sha_on=7715937522ea sha_off=3ce50305427d
cloud_gen: identical_on_off=True len_on=610 len_off=610 sha_on=1fc472614ae2 sha_off=1fc472614ae2
local_gen: identical_on_off=False len_on=836 len_off=610 sha_on=3c0788d38dbd sha_off=1fc472614ae2
cloud_refine: identical_on_off=True len_on=537 len_off=537 sha_on=f5f0a8926c40 sha_off=f5f0a8926c40
local_refine: identical_on_off=False len_on=763 len_off=537 sha_on=37354fdc29a5 sha_off=f5f0a8926c40
legacy_refine: identical_on_off=True len_on=514 len_off=514 sha_on=dc597dbac214 sha_off=dc597dbac214
```

**判讀**：
- 雲端三支（extraction／gen／refine）在開關 on/off 下 **byte 完全相同**（sha12 與 review.md 所載逐字元一致：`437f3c9c44df`／`1fc472614ae2`／`f5f0a8926c40`）。
- 地端三支隨開關改變；**全關時 `local_gen==cloud_gen`、`local_refine==cloud_refine`（sha 相同）** ⇒「地端全關＝byte 級回本波前」可達成。
- 本重播於工作樹 `a077dc94`（＝commit `5cff85f`）執行；輸出與審查時（`461e78db`／`480f04b0`）所載 sha12 **完全相同** ⇒ 契約跨工作樹演進維持。

---

## 3. I13 證據：qwen 驗收可證偽（儀器複算與門檻）

### 3.1 儀器複算（命令與結果）

```console
$ uv run --frozen python scripts/e2e/measure_record_quality.py \
    --record "data/cache/e2e/p6a-qwen27b-e6b/backend_data/outputs/0903-科務會議_c605df1a.md" \
    --template section_meeting
（stdout 為固定 schema JSON；exit 0。下列為關鍵欄位摘要）

$ uv run --frozen python scripts/e2e/measure_record_quality.py \
    --record "data/cache/e2e/p3-cloud-baseline-05/backend_data/outputs/0903-科務會議_ce67d0dc.md" \
    --template section_meeting
```

摘要（以 `python3 json` 自 stdout 擷取）：

```
E6b char_count= 4853  item_count= 78  avg= 42.5
E6b near_duplicate: {'count': 3, 'exact_count': 2, 'item_count': 78, 'threshold': 0.8}
E6b example pair: 40 98 1.0 | 4. 確認各單位皆報3人（科長，00:06:50）。 || 2. 確認各單位皆報3人（科長，00:06:50）。
C5  char_count= 2593  item_count= 28  avg= 65.1
C5  near_duplicate: {'count': 0, 'exact_count': 0, 'item_count': 28, 'threshold': 0.8}
```

獨立交叉核對（不經儀器）：

```console
$ rg -c '^\s*\d+\.' "data/cache/e2e/p6a-qwen27b-e6b/backend_data/outputs/0903-科務會議_c605df1a.md"
78
$ python3 - <<'PY'   # 同口徑自算（行首編號條目、去編號後平均字元）
import re
text = open("…/0903-科務會議_c605df1a.md", encoding='utf-8').read()
items = [re.sub(r'^\s*\d+\.', '', line).strip() for line in text.splitlines() if re.match(r'^\s*\d+\.', line)]
print(len(items), round(sum(len(i) for i in items)/len(items), 2))
PY
78 42.46
```

### 3.2 基線出處與 schema 釘死

```console
$ awk 'NR>=40 && NR<=46' $T/evidence/quality-instrument-p7b/README.md
40: | 紀錄 | `char_count` | `instruction_item_count` | `full_document_item_count` | `avg_item_chars` | `near_duplicate_items.count` | `exact_count` | `cross_section_duplicate_pairs` |
42: | qwen 3.8 27B（E6b） | 4,853 | 22 | **78** | **42.5** | **3** | 2 | 0（恆 0，量不到） |
44: | 雲端 gemini-3.5-flash-lite（C5） | 2,593 | 15 | 28 | **65.1** | 0 | 0 | 0 |

$ awk 'NR>=48 && NR<=54 {print NR": "$0}' tests/test_record_quality_metrics.py
48:     # 理由：cross_section_duplicate_pairs 依賴 general 模板章節語意，對 section_meeting
49:     # 結構性恆 0（量不到可見重複），因此另立全文條目與近似重複兩組觀測值。
50:     "full_document_item_count",
51:     "full_document_avg_item_chars",
52:     "near_duplicate_items",
53:     "known_term_fix_hits",
54:     "tag_traceability",

$ awk 'NR>=229 && NR<=238 {print NR": "$0}' tests/test_record_quality_metrics.py
229:     # P7-B：新觀測值同樣必須在 notes 明訂「永不作為閘門」，且說明與 instruction_item_count 的定義差異。
230:     assert "永不作為閘門" in payload["notes"]["definitions"]["full_document_item_stats"], (
231:         "full_document_item_stats 必須在 notes 明訂為觀察值（永不作為閘門）"
232:     )
233:     assert "不得混用" in payload["notes"]["definitions"]["full_document_item_stats"], (
234:         "notes 必須說明 full_document_item_count 與 instruction_item_count 定義不同、不得混用"
235:     )
236:     assert "永不作為閘門" in payload["notes"]["definitions"]["near_duplicate_items"], (
237:         "near_duplicate_items 必須在 notes 明訂為觀察值（永不作為閘門）"
238:     )
```

### 3.3 門檻算術與非阻斷語意（plan §5 原文節錄）

```
§5:172-175：qwen 分兩層：①`coverage_core` 不回退（≥27/28）＝**阻斷**；②**密度目標（可證偽、非阻斷）**：
全文 leaf item 數 **≤ 62**（自 E6b 基線 78 下降 ≥20%）且平均條目字元 **≥ 48**（自 42.5 上升 ≥12%），
朝雲端密度（28 條／65.1 字）移動；未達 ⇒ 如實登錄為「未達」，列為下一波槓桿（確定性去重等）的
決策輸入，**不阻斷**本波收尾。
§5:176：**反 gaming 禁令**：不得把 checklist／探針關鍵詞寫進任何提示詞；Stage 05 抽驗 2–3 條新命中事實的原文對照。
```

算式：`62/78−1＝−20.51%`（達 ≥20% ✓）、`48/42.5−1＝+12.94%`（達 ≥12% ✓）。

---

## 4. §3 CORE-1b 預註冊預測：產品 splitter 離線重播（0 呼叫）

### 4.1 腳本與輸出

`/tmp/replay3.py`（全文）：

```python
import sys, os
sys.path.insert(0, '/Users/hsiaojohnny/dev/convert')
os.environ.setdefault('DATA_DIR', '/tmp/replay_split_data')
from backend.services.summarization import SummarizationService
svc = SummarizationService()
text = open('/Users/hsiaojohnny/dev/convert/data/cache/e2e/p7a-gemma31b-e7c/transcript.txt', encoding='utf-8').read()
print('est total:', svc._estimate_tokens(text))
for ceiling in (6000, 5860, 5500):
    chunks = svc._split_transcript_into_chunks(text, ceiling)
    print(f'ceiling {ceiling}: {len(chunks)} chunks {[svc._estimate_tokens(c) for c in chunks]}')
c2 = svc._split_transcript_into_chunks(text, 6000)[1]
print('chunk2 starts:', c2.splitlines()[0][:30], '| has F044 ts:', '[00:25:23' in c2, '| F054:', '[00:32:33' in c2, '| F066:', '[00:43:03' in c2)
```

```console
$ uv run --frozen python /tmp/replay3.py
（logger 初始化行省略）
est total: 11711
ceiling 6000: 2 chunks [5960, 5918]
ceiling 5860: 3 chunks [5801, 5541, 682]
ceiling 5500: 3 chunks [5459, 5379, 1397]
chunk2 starts: [00:22:09-00:22:30] 發言者1：。對那個都 | has F044 ts: True | F054: True | F066: True
```

`/tmp/replay_split2.py`（逐時間戳；全文）：

```python
import sys, os
sys.path.insert(0, '/Users/hsiaojohnny/dev/convert')
os.environ.setdefault('DATA_DIR', '/tmp/replay_split_data')
from backend.services.summarization import SummarizationService
svc = SummarizationService()
text = open('/Users/hsiaojohnny/dev/convert/data/cache/e2e/p7a-gemma31b-e7c/transcript.txt', encoding='utf-8').read()
chunks = svc._split_transcript_into_chunks(text, 6000)
c2 = chunks[1]
for ts in ['00:22:09', '00:25:23', '00:32:33', '00:34:38', '00:35:21', '00:39:47', '00:43:03', '00:44:15']:
    print(ts, 'in chunk1(idx0)?', ts in chunks[0], '| in chunk2(idx1)?', ts in c2)
```

```console
$ uv run --frozen python /tmp/replay_split2.py
（logger 初始化行省略）
00:22:09 in chunk1(idx0)? True | in chunk2(idx1)? True
00:25:23 in chunk1(idx0)? False | in chunk2(idx1)? True
00:32:33 in chunk1(idx0)? False | in chunk2(idx1)? True
00:34:38 in chunk1(idx0)? False | in chunk2(idx1)? True
00:35:21 in chunk1(idx0)? False | in chunk2(idx1)? True
00:39:47 in chunk1(idx0)? False | in chunk2(idx1)? True
00:43:03 in chunk1(idx0)? False | in chunk2(idx1)? True
00:44:15 in chunk1(idx0)? False | in chunk2(idx1)? True
```

（`00:22:09` 同時在兩塊＝重疊行設計；`[00:22:09-00:22:30]` 為 chunk 2 首行。）

### 4.2 splitter 家族在 `ac181be`→`5cff85f` 間未變（ast 原始碼雜湊）

```console
（以 ast.get_source_segment 取函式原始碼、sha256[:16]；ac181be vs 工作樹 a077dc94）
_assemble_chunks_from_lines: ac181be=e42951792893c010 wt=e42951792893c010 same=True
_estimate_tokens: ac181be=1354bed7c32631e4 wt=1354bed7c32631e4 same=True
_insert_paragraph_breaks: ac181be=35a4f17af27b2a55 wt=35a4f17af27b2a55 same=True
_split_oversized_line: ac181be=52a6dbfa2bb6be12 wt=52a6dbfa2bb6be12 same=True
_split_transcript_into_chunks: ac181be=4046b505063c96ca wt=4046b505063c96ca same=True
_validate_chunk_postcondition: ac181be=82d2a68bd3574694 wt=82d2a68bd3574694 same=True
```

（比對腳本本體在 repo 外之 stdin 執行，未留下檔案。）

### 4.3 尾段事實 × chunk 歸屬（`quality/fact_checklist.json` 之 evidence 時間戳）

```
（逐 fact 讀 evidence 首個時間戳；ts ≥ 00:22 共 30 條，節錄關鍵列）
F038 00:22:02 in_c1=True  in_c2=False
F039 00:22:44 in_c1=True  in_c2=True      （重疊行）
F040 00:23:05 in_c1=False in_c2=True
F042 00:24:11 in_c1=False in_c2=True
F044 00:25:23 in_c1=False in_c2=True
F054 00:32:33 in_c1=False in_c2=True
F055 00:34:38 in_c1=False in_c2=True
F056 00:35:21 in_c1=False in_c2=True
F060 00:39:47 in_c1=False in_c2=True
F065 00:43:03 in_c1=False in_c2=True
F066 00:43:03 in_c1=False in_c2=True
F067 00:43:03 in_c1=False in_c2=True
```

→ 自 `00:25:23` 起（含 F044／F054／F055／F056／F060／F065／F066）**全部僅落在 chunk 2**，與預註冊預測（「涵蓋 F044／F054／F066」）一致。

### 4.4 估算 vs 實測（刀鋒邊界但書）

```console
$ python3 -c "print('step=', max(6000-220,1), 'ceil(11711/step)=', -(-11711//(6000-220)), 'actual=2')"
step= 5780 ceil(11711/step)= 3 actual=2
```

（工作樹 `_build_local_context_plan` `:707-709` 以公式估塊數＝**3**；實際切法＝**2**。plan §3:115 已明寫
「本上限是**刀鋒邊界**…⇒ 實測以 `chunk_count=` 為準並如實登錄」——但書正確且必要。）

plan §3:113-118 原文節錄：

```
- **預註冊可證偽預測（E2E 開場先核對）**：以產品分塊器離線重播固定素材（est 11,711 tokens、ceiling 6,000）
⇒ **恰 2 塊，估 5,960／5,918 tokens**；chunk 2 起點 `[00:22:09]`，涵蓋 F044／F054／F066。
本上限是**刀鋒邊界**（5,500／5,860 ⇒ 3 塊）⇒ 實測以 `chunk_count=` 為準並如實登錄。
- **成本值域（非單點）**：整份 1 次＝340.6 s（E7C 實測）、半份 1 次＝150.5 s（run-02 實測）
⇒ 2 塊推估 **−12%～+5%（萃取階段）**，對 gemma 全場約 **−2.5%**；qwen 的單次萃取僅 166.8 s（E6b），
分塊相對成本方向 `[UNKNOWN]`，一律以 E2E 實測登錄。
```

---

## 5. 其他抽查（支撐 review.md §5 底層主張）

### 5.1 E7C `quality/record_quality.json`（R4）

```console
$ python3 - <<'PY'  # 遞迴走訪 JSON，找 tag_traceability 子物件
/tag_traceability/exact_tag_ratio = 0.038461538461538464
/tag_traceability/zero_time_tag_count = 6
PY
```

（plan :84 載「`exact_tag_ratio 0.038`、`zero_time_tag_count 6`」→ 一致；計畫標記為 BEST_EFFORT、本波不做。）

### 5.2 佔位符計數（R3）

```console
$ rg -o '（待確認）（待確認）' data/cache/e2e/p7a-gemma31b-e7c/backend_data/outputs/0903-科務會議_bb492356.md | wc -l
1
$ rg -o '（待確認）：' data/cache/e2e/p7a-gemma31b-e7c/backend_data/outputs/0903-科務會議_bb492356.md | wc -l
11
$ rg -o '（待確認）（待確認）' data/cache/e2e/p6a-qwen27b-e6b/backend_data/outputs/0903-科務會議_c605df1a.md | wc -l
2
```

### 5.3 R1c：期望集合由萃取筆記抽取（ac181be `:1988-2002` 呼叫點原文）

```
1988:         # 類別一／二：議題、決議（取萃取筆記；重用既有比對器與兩道守衛）
1989:         for category, label, extractor, tail in (
1990-1996:        ("topic", "議題", self._extract_notes_topic_items, "這些議題都出現在萃取筆記的「議題與決議」中…")
1997-2002:        ("decision", "決議", self._extract_notes_decision_items, "請把對應決議寫進紀錄正文並保留原文的單位、期限與數字…")
```

（抽取器定義：ac181be `:1710 _extract_notes_topic_items`、`:1724 _extract_notes_decision_items`。）

### 5.4 R2：格式密度研究（任務相對路徑 `$T/research/format-density-comparison.md`）

```
37: | 動詞開頭（無主詞指令句）比例 | 4%（1/28） | 0%（0/23） | 19%（15/78） |
46: | 近似重複對（≥0.60，見附錄定義） | 2（皆為表格列 vs 正文，屬結構性） | 2（同左，結構性） | **7（僅 1 對涉及表格、3 對 r=1.0 為正文自我重複）** |
96-100: （L40/L98、L42/L99、L66/L119 三對 r=1.0 實例；「土地卡重印」跨節重寫）
```

### 5.5 I17 佐證：ac181be `:2484` 為生成 builder 內「拆成多列」句

```console
$ git show ac181be:backend/services/summarization.py | rg -n '拆成多列'
2484:{detail_rule}- 所有明確待辦都必須出現在待辦事項中；不要把多個不同待辦合併成單一籠統項目，可分列追蹤者請拆成多列
```

（三個 mode-gated builder 起點：`:2439`／`:2449`／`:2500`；補強 builder 定義在 `:2500`，與 review.md I17 所述一致。）

---

## 6. 未執行清單與合規聲明

- **未執行**：任何模型呼叫（LM Studio／Ollama／Gemini）、E2E、`pytest` 全 suite、外部服務呼叫、任何 `git commit`／分支操作。
- **未修改**：`plan.md`、產品程式碼、attempt-01／attempt-02 既有 `review/**`；本 attempt 僅新增本檔與 `review.md`。
- 本附錄所有數字皆為本機實跑輸出（出處＝上方指令）或檔案行擷取（出處＝路徑＋行號）；未引用任何他人結論。
- 備註：`review.md` 內「HEAD」行號以審查時 HEAD＝`ac181be` 為基準；分支已於 19:20:49 前進至 `5cff85f`，複核請以 `git show ac181be:…` 取得同內容。
