# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02，attempt-07）

- 受審對象：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md`（自稱 `PLAN_REVISION 8`，`plan.md:4`）。
- `REVIEWED_PLAN_REVISION`: **8**
- `REVIEWED_PLAN_SHA256`: **`168c5c8e74ddff1554bca635afa3d3e8ac8fc34d4aee85017313235e190a08f2`**（開審量測；收審複量見文末「收尾」）。
- 審查時間：2026-09-23 00:55–01:20（Asia/Taipei）。
- 審查者：獨立 Stage 02（fresh context；read-only）。未參與本計畫修訂；未修改 `plan.md`、產品碼、測試、`review/attempt-01`–`06`、`e2e/*`、`quality/*`、研究文件。
- 唯一寫入：本檔（＋同目錄 `snapshot_plan.sha256`）。所有重現實驗寫 `/tmp/rev07/`，未在 repo 留暫存檔。
- 受審範圍：rev 8 的變更落在 header 修訂紀錄與 §8（§8.2 回填、§8.3、§8.4、§8.5 W13、§8.6、§8.7）。工作樹未留 rev 7 副本，無法逐字 diff rev7→rev8；本次以「§8 全節 ⇄ 工作樹實作 ⇄ 實測」全面複核，並以 `review/attempt-06/snapshot_plan.sha256`（`59cf852a…`）確認受審版本已遞增。
- 環境事實（如實記錄）：審查期間工作樹存在平行未提交變更（`plan.md` rev 8；`backend/core/text_postprocess.py`；`backend/services/summarization.py`；`doc/*` 兩份；`scripts/e2e/measure_coverage.py`；`tests/test_measure_coverage.py`；`tests/test_t20260922_2037_p3_parity.py`；`.agent/.../quality/`；`e2e/attempt-C2-cloud-baseline/`）。本結論只綁定下列 hash；`plan.md` 之後若再被修改，本審查不自動沿用。
- 受測實作 hash（本次審查所用）：`backend/core/text_postprocess.py` `60713fffedfe8cba3732bc692d460ac23405026e08d2f5e396466706c0cb7566`；`backend/services/summarization.py` `e6dd85ad31dfe7c96ef1ca9e8dca2056d22b6e6ffb0b81fa6902ae9153656db4`。
- 已讀（依角色契約）：`~/.codex/prompts/02_plan_review_prompt.md`；`policies/plan-review-gate.md`、`goal-alignment-design-economy.md`；`plan.md` rev 8（重點 §7／§8 全節）；`review/attempt-06/review.md`＋`snapshot_plan.sha256`；`git diff -- backend/core/text_postprocess.py backend/services/summarization.py`；`tests/*`；`quality/`（`fact_checklist.json`、notes、`coverage/`、`README_measure_coverage.md`、`snap_interval_variant_check.md`、`guard_calibration.md`）；`e2e/attempt-C2-cloud-baseline/`；C1 模型原始輸出 `/tmp/pred_2026-09-22_234336.txt`。

## Goal Baseline（先於計畫框架、從權威來源重建）

1. 第一性結果（N-4）：人工看地端紀錄「品質非常不夠理想，跟雲端 Gemini 差很多」→ 要**接近雲端的品質，且可被證明**；機制模型無關、macOS／Windows 一體適用。
2. rev 6 已證「標註可查核」；rev 7/8 定位：先造能量「內容涵蓋缺口」的尺（CORE-3）→ 修「補強假陽性／不收斂」（CORE-4）與「吸附倒退／非冪等」（CORE-5）→ D1（Gemma）＋C2（雲端）同尺對照、公開缺口；明示不宣稱對齊。
3. 本波成功標準＝「尺可信、缺陷真的修好（且有量尺證明）、缺口被量到且公開」。CORE-5 的關鍵是**缺陷類必須被一個有鑑別力的量尺量到**。
4. 非目標：關掉品質缺口（後續波）；Windows 實機（`[UNVERIFIED]`，計畫已明示）。

## Top-down（目標對齊／必要性／關鍵路徑／閘門比例／失效圍堵／耦合／設計經濟）

- 目標對齊：rev 8 的三項修訂都在「讓修復可被證明」的路徑上；§8.6-7 不把「地端 vs 雲端缺口」設為閘門的決策，維持前輪「合理（有條件）」判定。
- **關鍵路徑**：CORE-5 的關鍵路徑是「缺陷類可量測 → 歸零」。rev 8 把觀察值換成**恆 0** 的定義（見 R1），等於在關鍵路徑上撤掉量尺；同時「不倒退」實際仍有活體缺陷（見 R3）＝priority inversion：驗收欄位「有」了，量測目的落空。
- **閘門比例**：§8.6-4 的 `D1 E2E snapped_across_segment == 0`（`plan.md:384`）是**恆真閘門**，不提供決策資訊，卻對外提供「不倒退已驗證」的錯誤保證。（同段 `on_start ≥0.95` 與冪等測試本身有效；問題只在這一條。）
- **失效圍堵**：R2「往更嚴＋不收斂保護」的圍堵設計存在且成本有上限（下方查核）；R1／R3 的失效**無**圍堵——量尺看不到、D1 全綠。
- 設計經濟：三個阻斷項的最小修正皆為局部、無新依賴（見各節）；反例皆為 2 段合成或既有真實素材，成本極低。

## Bottom-up（repo 接地、契約、安全、序列、驗證）

- 接地：`_pick_containing_segment`（`text_postprocess.py:791-808`）的「段首優先」只作用在**傳入清單**；規則 1 傳入 `same_speaker` 子清單（`:927-929`）、規則 3 傳入全集（`:937`）。此結構是一切反例的根源。
- 契約：`_pick_containing_segment` docstring（`:796`「再套用一次只能命中該段自己」）與 §8.4（`plan.md:348`「保證 `f(f(x)) == f(x)`」）皆為**無條件保證**，已被最小反例否證（R3）。
- 量尺：`measure_tag_traceability` 與吸附共用 `_segment_contains`（閉區間；`:970`）；R3④ 成立。
- 安全：本次未見新的隱私／安全面變更；C2 失敗屬外部（Gemini 503），如實。
- 驗證：本審查實跑完整測試 `928 passed／2 skipped`；覆蓋率儀器重跑（除 `--label` 外與 repo 報告 byte 相同）；自寫探針見附錄。

## 逐項判定

### R1（阻斷｜類型：閘門效度／如實性）`snapped_across_segment` 定義已一致，但恆 0、無鑑別力，**不可當回歸絆索**

判定：**部分收斂**（定義層面收斂；意義層面不收斂）。

- 收斂部分：定義已無自相矛盾、與實作一致——「落點段落不含原時間戳」、`snapped_nearest` 不計入（程式對應 `text_postprocess.py:954-961`）。前輪「`target < 原值` 必然包含合法吸附 → 偽 FAIL」的矛盾確實解了。
- **未收斂部分（結構證明）**：`status != "nearest"` 僅可能來自 `exact`／`speaker_mismatch`，兩者都保證「存在含原時間戳的段落」；計數條件再以 `_pick_containing_segment(segments, seconds)` 取段——此函式對任何含該秒的段落都回傳**含該秒**的段落（含段首命中），故只要 pick 仍回傳「含該秒的段落」，`not _segment_contains(...)` **恆 False**：此值不可能非 0。
- **實測**（`/tmp/rev07/probe.py` Part 3；A1＝`data/cache/e2e/p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c.md`）：
  - 把 `_pick_containing_segment` 換回 v1.0「閉區間取第一個命中」→ `changed=14`（全部後退）、`snapped_across_segment` **仍 = 0**；
  - v1.1 → `changed=12`、亦 = 0；A1 全 61 個 tag 上 across 條件可達筆數 = **0**。
- → `plan.md:352-353`（「哪天順序被改壞，E2E 立刻非 0」）與 `text_postprocess.py:959` 同句註解**不實**，且與同句前半「由建構保證為 0」互相矛盾。§8.6-4 的 D1 閘門恆真＝無鑑別力。
- 最小充分修正：把觀察值改為對缺陷類有鑑別力的計數（建議沿用前輪 R1 建議：「原時間戳 ∈ 任一真實段 `start` 且被移早」筆數），或如實降級為「恆 0 的結構性觀察值」並**移除其閘門地位**；同步修 `plan.md:352-353`、§8.6-4、程式註解與 E2E 欄位語意。
- 不修會發生什麼：CORE-5「不倒退」的驗收永遠綠燈，R24 類缺陷（R3 證明仍在）被閘門宣告為 0——重演本波要消滅的「指標盲區」，且這次是**自我認證**（由實作自身定義保證為 0）。

### R2（阻斷（範圍較窄）｜類型：設計不足＋驗收偽陰性）守衛部分收斂：否定詞僅攔「全域缺席」；日期類仍可被洗白

判定：**部分收斂**。

- 忠實落地（成立）：`ACTION_MATCH_MIN_LCS_RATIO = 0.6`（`summarization.py:148`）、視窗長度＝`len(key)+4`（`:996`）、候選視窗由標籤 bigram 位置反推（`:990-995`）——與 §8.3 文字一致。
- ≥3 位數字守衛（成立）：`13600` 對「約一萬三千六百」→ `ratio=0.7619`、守衛判**遺漏**；`13,600` 千分位折疊→不誤判。
- **否定詞守衛（未收斂）**：實作為 `term not in normalized_summary`（`:1045-1048`，**整份紀錄**）。可重現反例（真實 27B 紀錄 `p2-27b-fix-01/…_dc3c8f7a.md`）：
  - 把目標句改寫成語意反轉（「嚴禁將科內群組訊息（含照片）外流至任何外部渠道」→「…**得**外流至任何外部渠道」），他處仍有 5 次「嚴禁」→ `ratio=0.8571`、`missing=∅`（洗白）。
  - 全域移除「嚴禁」後才判遺漏（守衛只對「全域缺席」有效）。
  - → 與 §8.3 自述「不會把失真當成已涵蓋」不符；前輪「語意反轉、高字面重疊被洗白」的核心指控仍有一條可重現路徑。
- **日期類（未收斂）**：`9月30日→9月20日` → `ratio=0.9333`、仍判涵蓋（`\d{3,}` 不涵蓋 1–2 位數）；前輪 R2 明列的日期數字段落未處理，計畫也未給出「日期不設守衛」的理由（只舉 `17 台` 為 2 位數範例）。
- 最小充分修正：①否定詞守衛限定在**最佳匹配視窗內**（或要求否定詞出現在命中視窗／候選 bigram 區段）才放行；②數字守衛加日期樣式（如 `\d{1,2}月\d{1,2}日`）或「標籤含日期 token → 要求原樣出現」；③補上述兩條回歸測試；④修 §8.7「人工複核缺失清單」措辭——被洗白項不會出現在缺失清單，該緩解對本風險類無效（需定義另一種抽查）。
- 不修會發生什麼：補強迴圈對這兩類失真持續靜默放行（真遺漏不再觸發補強）；缺口在 final 覆蓋率尺上可能仍被看到（部分緩解），但「修復迴圈」自身喪失對這兩類的偵測。

### R3（阻斷｜類型：語意契約＋驗證）①不倒退／②冪等皆有可重現反例；③④成立

判定：**①未達成、②未達成、③成立、④成立**。

- **②冪等最小反例**（無重疊、純交界的 2 段逐字稿；`/tmp/rev07/probe.py` Part 1）：
  - 逐字稿：`[00:14:40-00:16:40] 發言者2` ／ `[00:16:40-00:23:20] 發言者1`
  - `（發言者2，00:18:40）` → `f(x)=00:16:40`（speaker_mismatch）→ `f(f(x))=00:14:40`（exact）→ **`f(f(x)) ≠ f(x)`**。
  - 根因：第一次落點（別的發言者的段 `start`）恰好是標籤發言者前一段的 `end`（純交界）；第二輪規則 1 用閉區間命中該 `end` → 再退一格。§8.4 的無條件保證與 docstring（`:796`）為假；`test_snap_是冪等的…`（`tests/test_t20260922_2037_p3_parity.py:67`）未涵蓋此類。
- **①不倒退（實體反例）**：
  - 合成：`（發言者2，00:16:40）` → `f(x)=00:14:40`——`00:16:40` 是逐字稿中 `發言者1` 段的真實 `start`（也是 `發言者2` 前段的 `end`），仍被吸回前一段起點。
  - 真實（A1＝`p2-27b-01` 的 27B 輸出）：61 tags／58 snapped／**changed=12、12/12 全為後退、12/12 皆交界類**（原時間戳＝同發言者段落 `end`）；其中 9 筆原時間戳 ∈ 全域真實段 `start`。例：`00:13:37`：同發言者段 `(792,817,發言者1)`、下一段 `(817,825,發言者2)` → v1.1 落點 `792`（`00:13:12`）＝**被吸回前一段起點**；`00:15:14`、`00:21:01` 同型（跨發言者交界）。
  - 測試盲區：`tests/test_t20260922_2037_p3_parity.py:46-64、118-131` 只覆蓋「同發言者相鄰」與「標籤屬起始段」兩種交界；「標籤屬**前段**、起點段是他發言者」未被覆蓋——正是規則 1（`same_speaker` 子清單）看不到段首優先的類。
  - 冪等性在 A1 上恰為 0 改動（材料性質），不能替代保證——最小反例已否證。
- **③成立**（良性吸附保留）：`test_…空隙邊界仍可回溯`（`:98`）；C1 模型原始輸出實測 `changed=1`（唯一改動＝`00:10:04→00:08:15`；`00:10:04` ∈ 段 `end`、∉ 任何段 `start`，段 `(495,604,發言者1)`）、冪等。
- **④成立**（量尺與產品共用語意）：皆用 `_segment_contains` 閉區間；`:118` 測試釘住。
- 最小充分修正：①把「原時間戳＝任一真實段 `start` → 不動（no-op）」提升為**全域規則**（在規則 1 之前短路），或 ②吸附後強制不動點（`f(target) != target` → 保留原值）；補 (a) 上述 2 段合成反例 fixture、(b) 「段首不得被移早」計數回歸（A1 型素材）。此修同時讓 R1 的鑑別型量尺可能歸零。
- 不修會發生什麼：27B 型輸出（標籤為「發言者N」）的交界時間戳持續被吸回前一段起點（A1：12 筆，最高約 25 s 精度損失）；重複套用可能再退（反例）；而 `on_start`／across 全綠——R24「指標盲區」原樣重演。

## 前輪三阻斷項收斂查核（attempt-06 → 本輪）

- attempt-06 **R1**（`snapped_backward` 定義矛盾＋鑑別力）：**部分收斂**——定義矛盾解除；「可達且有意義」未達成（本輪 R1：恆 0、閘門地位不當）。
- attempt-06 **R2**（bigram 0.75 洗白真遺漏）：**部分收斂**——LCS 0.6 忠實落地、≥3 位數字守衛有效；否定詞僅全域、日期類未收斂（本輪 R2）。
- attempt-06 **R3**（半開區間代價）：**主要關切已解**——回退為閉區間＋段首優先、良性吸附保留（③）、量尺共用語意（④）；但「不倒退＋冪等」的無條件宣稱有反例（本輪 R3①②）。

## 本輪驗證成立的正面事實（本次查核）

- `pytest tests/ -q --ignore=tests/test_end_to_end.py` → **928 passed／2 skipped**（與 §8.6-1 相符）；`tests/test_t20260922_2037_p3_parity.py`＋`tests/test_measure_coverage.py` → 29 passed。
- 三份既有紀錄（27B-B2／MoE-B1／Gemma-C1）v1.1 實測：`changed=0`、冪等、`snapped_across_segment=0`、`on_start=1.0`、`metric_version=tag_traceability-1.1.0`——§8.4 該句為真（但屬 fixpoint 材料，不得外推為一般輸入不倒退）。
- C1 模型原始輸出：`changed=1`（良性）＋冪等＋`untraceable=0`；與 `snap_interval_variant_check.md` §7 相符（該報告數字本審查複核可信；惟其結論 3「消除倒退與非冪等」宜加界線：未涵蓋規則 1 交界類）。
- R2 閘門決策（§8.6-7）維持前輪「合理（有條件）」判定。
- 不收斂保護：實作存在（`summarization.py:2330`／`:3483`）、雙向測試成立（`:263`／`:296`）；誤判代價硬上限＝`LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2`（`config.py:270`）。措辭註記：§8.7「不收斂保護（最多 1 輪）」不精確——保護只擋「問題集合相同」，2 輪上限來自 config，建議如實改寫（不影響圍堵有效性）。
- 覆蓋率儀器：重跑 Gemma 報告除 `--label` 外 byte 相同；`coverage_core=0.7500`／`coverage_all=0.5672`、逐字稿 `0.9851`／`1.0` 與 §8.2 相符；`quality/fact_checklist.json` 與 `data/cache/staging/quality/fact_checklist.json` sha256 相同（`cf012d1f…6c001`）。
- C2 `attempt-C2-cloud-baseline`：`task_final.json` `summary_failed=true`、stage「完成（⚠️ 僅逐字稿，會議紀錄生成失敗）」、`run_summary.json` mode `cloud`——FAIL 如實（外部 503）。
- `quality/guard_calibration.md`：本審查抽驗其 tamper（否定詞自紀錄移除）方向一致；該報告自陳「主探針結構性 0、守衛未執行」等限制，屬如實。

## 如實註記（非阻斷）

- `plan.md:398` §8.7 稱 `guard_calibration.md`「已有」量測：rev 8 定稿時該檔尚未落地，屬時序措辭不精確；該檔已於本輪審查期間存在，建議下一修訂順修。
- 本審查未取得 rev 7 舊文副本，無法逐字 diff rev7→rev8；已採「§8 全節 ⇄ 實作 ⇄ 實測」複核替代。
- A1（`p2-27b-01`）為舊執行產物；本審查以「現行 v1.1 對一般模型輸出」的語意檢驗之。其 12 筆交界倒退不是本波新引入，而是「未修好」的 R24 類。

## 收尾

- 開審量測：`168c5c8e…a08f2`（2026-09-23 00:55 CST）；收審複量（本檔寫入後）：同值（見同目錄 `snapshot_plan.sha256`）。
- 本審查未修改任何其他檔案；`review/attempt-07/` 僅含本檔與 `snapshot_plan.sha256`。

## 附錄：可重現指令（節錄）

（1）R3①②最小反例：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python - <<'PY'
import sys; sys.path.insert(0,".")
import backend.core.text_postprocess as tp
from backend.core.templates import get_template
tmpl=get_template("section_meeting")
SYN="[00:14:40-00:16:40] 發言者2：甲。\n[00:16:40-00:23:20] 發言者1：乙。\n"
for text in ("1.乙（發言者2，00:16:40）。","1.乙（發言者2，00:18:40）。"):
    fx,_=tp.snap_source_tags_to_transcript(text,SYN,tmpl)
    ffx,_=tp.snap_source_tags_to_transcript(fx,SYN,tmpl)
    print(text,"->",fx.strip(),"->",ffx.strip())
PY
```

（2）R1 絆索失效（A1＋v1.0 順序模擬）與 R3① 真實反例逐筆診斷：`/tmp/rev07/probe.py`（Part 2／Part 3）；逐筆交界結構：`/tmp/rev07/probe2.py`。

（3）R2 反例（局部否定詞消失／全域移除／日期／數字）：`/tmp/rev07/probe.py`（Part 4）。

## 判決

PLAN_REVISION_REQUIRED
