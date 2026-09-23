# Pre-push 唯讀獨立程式碼審查（T20260922-2037-02；pre-push-review-01）

> 審查者角色：唯讀獨立程式碼審查員（push 前最後一道）。**不修改產品碼／測試／plan／handoff／CHANGELOG**，
> 不做 `git add/commit/push/checkout/stash`，不跑全套 pytest、不呼叫 LM Studio、不寫入 E4 產物目錄。
> 唯一寫入＝本檔。
> 產生時間：2026-09-23 11:18（Asia/Taipei）｜HEAD：`818b71e`

## 結論

**`PUSH_SAFE_WITH_NOTES`**

- 5 筆未 push commit（`d00d778`、`849e934`、`d562691`、`eb9dfeb`、`818b71e`）**沒有發現 push-blocking 的程式碼缺陷**：
  門檻常數未動、`off` 開關仍 byte 級短路、雲端提示詞與雲端路徑未觸及、`task_processor.py:259/262` 未被 diff 觸及。
- 有 4 項**必須知情**的註記（§5）：blast radius 聲明不精確、CHANGELOG 同波自相矛盾、fidelity 註解不精確、
  兩套段落語意並存；另有 3 類**殘留漏檢／新誤報**路徑（§2.4–2.6）已在下方以可重現輸入列出。
- 任務書說「6 筆未 push（含最新一筆）」與實況不符：實際為 **5 筆**（`git log --oneline origin/fix/qwen-local-quality-parity..HEAD` 共 5 行）。

## 0. 審查方法與證據來源

- `git show <sha>`、`git diff 76b904e..HEAD`、`rg`、5 支離線探針（`/tmp/prepush_review/probe{1..5}_*.py`，純文字／純函式）。
- 焦點測試（非全套）：`DATA_DIR=/tmp/probe_scratch_review uv run --frozen python -m pytest tests/test_t20260923_fidelity_boundary_fix.py tests/test_t20260923_p4a_number_boundary_fix.py tests/test_t20260923_p4a_paren_fix.py -q` → `24 passed in 0.44s`。
- 未觸及 `data/cache/e2e/p4-qwen27b-e4/` 與 `attempt-E4-*/`（見 §6 的揭露）。

---

## 1. 「只加嚴、不放寬」逐項檢查

### 1.1 閘門門檻常數／補強輪數：未動 `[VERIFIED]`

```
$ git diff --name-status 76b904e..HEAD
A  .agent/.../e2e/attempt-E3-qwen27b-p4a-fix/run_notes_addendum.md
A  .agent/.../e2e/attempt-E3-qwen27b-p4a-fix/verify_independent.md
M  .agent/.../escalation.md
M  CHANGELOG.md
M  backend/core/fidelity_checks.py
M  backend/services/summarization.py
A  tests/test_t20260923_fidelity_boundary_fix.py
A  tests/test_t20260923_p4a_number_boundary_fix.py
A  tests/test_t20260923_p4a_paren_fix.py
```

- `backend/core/config.py`（`LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2`（:280）、`LOCAL_LLM_RECORD_COVERAGE_MODE=enforce`（:287）、
  `LOCAL_FIDELITY_TRIPWIRES=True`（:304））**不在 diff**；`scripts/e2e/run_owned_e2e.py`（16 checks／quality gate）**不在 diff**。
- 本輪新增常數只有 2 個：`_TOPIC_TERM_SEPARATOR_CHARS="、"`（`backend/services/summarization.py:1206`）、
  `_RECORD_COVERAGE_ORDINAL_MARKER_PATTERN`（`backend/services/summarization.py:209`）。
- 門檻掃描：`git diff -U0 76b904e..HEAD -- backend/ | rg '0\.[0-9]|_MAX|= *[0-9]|cap|THRESH|round'`
  → 唯一命中是新 regex 行 `rf"(?<!\d)(?<!\d\.){re.escape(folded_literal)}(?!\d)(?!\.\d)"`；無任何門檻值變更。

### 1.2 `off` 模式：仍 byte 級短路 `[VERIFIED]`

- 覆蓋率：`backend/services/summarization.py:1783-1789` `mode == "off"` → `self._record_coverage_stats = {}` ＋ `return []`；
  本輪新增的折疊（`:1796 folded_number_record = ...`）與判定（`:1890`）都在早退之後 → 不可能影響 off。
- 忠實度：`backend/services/summarization.py:1985-1986` `LOCAL_FIDELITY_TRIPWIRES=False` → `return []`（連 lazy import 都不執行）
  → B1 修補不可能影響該開關。
- 實測（probe4，in-process）：

```
== off-switch equivalence (coverage) ==
  mode=off -> issues: []  stats: {}
```

- 既有測試已覆蓋 off：`tests/test_t20260923_p4a_record_coverage.py:379/500/627`、`tests/test_t20260923_p4b_fidelity_wiring.py:279/312`。

### 1.3 雲端提示詞／雲端路徑／`task_processor.py:259/262`：未動 `[VERIFIED]`

- 5 筆 commit 未動任何提示詞檔（`--name-status` 全清單見 §1.1）。
- `rg -n "_validate_record_source_coverage|_validate_record_fidelity" backend/services/summarization.py`
  → 定義 `:1767`／`:1970`；呼叫 `:3134`／`:3137`／`:3191`／`:3194`；四處都落在 `:2995 async def _summarize_with_local_pipeline`
  → **雲端流程不呼叫這兩支檢查**（本輪改動對雲端輸出無路徑可達）。
- `backend/services/task_processor.py:255-266`（本地校正層；任務書指的 `:259/262` 落在此段）檔案不在 diff。

### 1.4 方向分類：**兩筆是「偵測放寬」，必須點名** `[VERIFIED]`

| commit | 方向 | 說明 |
|---|---|---|
| `818b71e` | **加嚴** | 子字串 → 數字邊界；只會多報（附「不得過嚴」負向案例） |
| `849e934` | **放寬（減少誤報）** | `_topic_terms_cover` 新增「可略過分隔符」路徑（`summarization.py:1261-1264`）→ 議題召回守衛接受更多、判缺更少 |
| `eb9dfeb` | **放寬（減少誤報）** | B1 由「檔序首命中」改集合語意（`fidelity_checks.py:539-545`）→ 歸屬絆索回報更少（commit 自述「寧可少報，不誤報」） |

- 兩筆放寬都有負向對照（真缺仍判缺／真錯仍報），但「本輪只加嚴」這句話**不成立於這 2 筆**；
  對外說明應寫「門檻未放寬；兩筆偵測器為減少假陽性而放寬偵測，方向已登錄殘餘風險」。

---

## 2. 新引入的假陰性（漏報）風險

### 2.1 B1 集合語意：與量尺同語意（一致性改善）`[VERIFIED]`

- 量尺 `backend/core/text_postprocess.py:1268-1276` 的 `tags_inside_same_speaker_segment` 本來就是
  `any(_segment_contains(seg, seconds) for seg in segments if speaker == label)`（any-match）；
  修後產品 B1（`fidelity_checks.py:539-545`）與量尺同語意 → 消除了「產品說 14 筆假陽性、量尺說 45/45」的矛盾。
- 獨立 replay（15 份快取 `.md` × `_逐字稿.txt`，舊實作 vs 新實作）：**5 對改變，全部是 old>0 → new=0（純移除）**：

```
  DIFF p1-fixed-01              old=2 new=0
  DIFF p2-27b-01                old=16 new=0
  DIFF p4-gemma31b-e1           old=1 new=0
  DIFF p4-gemma31b-e2           old=1 new=0
  DIFF p4-qwen27b-e3            old=14 new=0
  pairs=15  changed_pairs=5
```

### 2.2 B1 中段重疊：可構造的真漏報（目前語料未觸發）`[VERIFIED]`

反例輸入（段落真正重疊，非只有交界）：

```
[00:00:00-00:00:20] 發言者3：甲案說明。
[00:00:10-00:00:30] 發言者2：乙案說明。
紀錄：1. 乙案（發言者2，00:00:15）。
```

實測輸出：

```
  old: ['tag_owner|（發言者2，00:00:15）落在 發言者3 的逐字稿段落內']
  new: []
```

- 掃 15 份快取逐字稿：**中段重疊 0/15** → 目前為理論風險（邊界重疊才是常態，而邊界抑制是本次設計意圖）。
- 若日後 ASR 來源產生真正重疊語音區間，該區間內 B1 會完全靜音 `[UNVERIFIED 實機]`。

### 2.3 B1 混用命名：新增判定（反方向；目前語料未觸發）`[VERIFIED]`

```
逐字稿：[00:00:00-00:00:20] 科長：甲案說明。 / [00:00:10-00:00:30] 發言者2：乙案說明。
紀錄：  1. 甲案（發言者1，00:00:15）。
  old: []   new: ['tag_owner|（發言者1，00:00:15）落在 發言者2 的逐字稿段落內']
```

- 15 份快取逐字稿的段落標籤**全部是 `發言者N`**（非 `發言者N` 標籤 = 0/15）→ 目前不觸發。
- `fidelity_checks.py:536-538` 的註解寫「（與舊版等效）…語意不變」**不精確**（此案例下語意確實改變）。
- 註：舊版在「首命中段落是 `科長`」時是整支跳過；新版把非 `發言者N` 段落濾掉後仍可能回報 → 這是**加嚴**方向，非放寬。

### 2.4 數字對帳器：殘留漏檢（同缺陷類別未收盡）`[VERIFIED]`

`_fold_record_for_number_coverage`（`summarization.py:1579-1595`）的序號剝除＝ASCII 標點集，且**先剝除、後 NFKC**。實測：

| 形式 | fold 後 | `covered('15')` |
|---|---|---|
| `15. 辦公室` | `' 辦公室'` | False（正確） |
| `15、辦公室`／`15) 辦公室`／`15）辦公室`／`- 15. 辦公室`／`* 15. 辦公室`／`１５）辦公室` | `' 辦公室'` | False（正確） |
| `１５．辦公室`（全形句點，無空白） | `'15.辦公室'` | **True（漏檢）** |
| `\u300015. 辦公室`（全形空白縮排） | `' 15. 辦公室'` | **True（漏檢）** |
| `• 15. 辦公室`／`> 15. 辦公室` | 未剝除 | **True（漏檢）** |
| `115. 09.03 開會` | `' 09.03 開會'` | 行首 `115.` 被當編號剝除（若 `115` 進期望集合 → 理論誤報） |

- 這些是**修正前就存在**的同類殘留（非回歸）；但 commit/測試都只 pin ASCII 形式，文件未登錄這些存活形式。

### 2.5 數字對帳器：新誤報（過嚴；方向可接受但需知情）`[VERIFIED]`

```
covered('600', fold('600、800、13600 元')) = False      # 行首數字列舉被當編號剝除
covered('600', fold('共600，15項'))          = False      # NFKC: ，→, → 千分位去除 → '共60015項'
covered('15',  fold('共600，15項'))          = False      # 兩數其實都在
```

- 15 份快取 replay 中，上述型態**未觸發**（見 §5-a 的兩份差異皆為真缺口）。
- 另外 `_number_literal_is_covered`（`:1599-1629`）只加嚴、無過度接受：`600` 不命中 `13,600`/`13600`/`6000`/`1600`，
  `15` 不命中 `150`/`12.15`/`15.5`，正常命中 `600元`/`15%`/`13600元`/`17個人` 全部保留。

### 2.6 議題詞級覆蓋：弱證據接受（真漏報方向）`[VERIFIED]`

```
label = 廉政宣導（拆勤、採購、公務車使用）
cover(label, haystack 內「使用」只出現在無關專名「使用牌照稅科」) = True
cover(label, 同一段移除「使用」)                              = False
cover(label, 同上；把分隔符規則停用＝pre-fix)                    = False
```

- 即：修補後可因**複合詞被 DP 拆出的碎片**在無關語境命中而接受（E3 實例正是靠 `使用牌照稅科` 的「使用」）。
- 文件只寫「子詞仍須全數命中」，未寫「子詞可來自無關專名碎片」→ 建議補進殘餘風險（非阻擋）。

### 2.7 例外／退化輸入：無 crash `[VERIFIED]`

- probe4 掃 `literal ∈ {"", "0", "、", "600"}` × `record ∈ {"", "、", None}`：無例外；`cover("、、","、、")=False`、`cover("、","")=False`
  （空／純分隔符不會被誤接受）。regex 皆為 escape 過的字面值＋固定寬度 lookbehind → 無災難性回溯風險。

---

## 3. 跨 OS／跨引擎

- `git diff 76b904e..HEAD -- backend/ tests/ | rg '^\+.*(os\.name|sys\.platform|platform\.|os\.sep|encoding=|PYTHONIOENCODING|pathlib)'` → **空**。`[VERIFIED]`
- CRLF（Windows 逐字稿格式）實測：`fold('# 紀錄\r\n\r\n15. 辦公室搬遷\r\n600元\r\n')` = `'# 紀錄 辦公室搬遷 600元 '`；
  `covered('15')=False`（序號正確剝除）、`covered('600')=True`、`covered('600', fold('...13,600...'))=False`。`[VERIFIED]`
- Unicode `\d` 為 Unicode-aware：`re.fullmatch(r'\d','１')→True` → 全形數字序號 `１５）` 仍被剝除；漏剝的是 `．`（全形句點）等非 ASCII 標點（§2.4）。`[VERIFIED]`
- 3 支新測試檔只用 `tempfile.mkdtemp` ＋ `os.environ`，無平台相依寫檔／路徑分隔。
- Ollama 與 LM Studio 共用同一條 local pipeline（`:2995 _summarize_with_local_pipeline`），本輪未新增任何引擎分支
  → Windows＋Ollama **無新增風險**；實機驗收仍為 `[UNVERIFIED]`（與既有登錄一致）。

---

## 4. 測試充分性

- 實跑結果：`24 passed in 0.44s`（3 檔：fidelity boundary 12、number boundary 7、paren 5）。`[VERIFIED]`
- 「測了但測不到根因」檢查：以**舊實作離線重播**同一 fixture，確認測試在 pre-fix 會 fail：

| 測試 | pre-fix 行為（舊實作） | 結論 |
|---|---|---|
| `test_B1_邊界時間戳引用段落起點_不報` | 舊回 `['tag_owner|（發言者3，00:00:10）落在 發言者1 …']` | 釘住根因 ✔ |
| `test_T34_括號複合標題…` | 把 `_TOPIC_TERM_SEPARATOR_CHARS` 設回 `""` → `cover=False` | 釘住根因 ✔ |
| `test_T35_數字邊界_600與15的兩個真實假命中` | 舊 `folded_literal in folded_record` → `missing=0` | 釘住根因 ✔ |

- 測試缺口（不阻擋，建議後續補）：
  1. §2.2／2.3 的 B1 對照案例（中段重疊、混用命名）。
  2. §2.4 的全形句點／全形空白縮排／`•`／`>` 序號形式。
  3. §2.5 的行首數字列舉與全形逗號黏合誤報型態。
  4. `off` 等價已有既有測試（§1.2），本輪未新增 → 可接受。
- 未跑整套 pytest（E4 進行中）→ 全套基準（1066 passed／2 skipped）**未由本審查重驗** `[UNVERIFIED 本次]`。

---

## 5. 其他 push 前必須知道的問題（皆非程式碼阻擋）

**a) blast radius 聲明不精確（`818b71e`）**
commit message 寫「唯一差異＝E3」。我對 15 份快取 replay：`p4-qwen27b-e3`（0→2）**與 `v480-attempt-01`（1→2）**都改變；
六份對照 fixture（E1／E2／D1／D2／C5／E3）內確實只有 E3。方向正確（v480 紀錄僅有 `13,600`、無獨立 `600`；逐字稿確有「發 600塊」）。
建議：在 E4 `run_notes`（append-only）補記此第六份差異，勿改寫已 commit 的訊息。

**b) CHANGELOG 同波自相矛盾**
`CHANGELOG.md:50` 仍列「補強輪數仍為 2 > 1」為未達、`:59-61` 把「修掉括號詞組假陽性」列為*下一步*，但該修補已在本 push 內（`849e934`）。
建議：下一次 CHANGELOG 更新時補記（依 append-only 精神，不回溯改寫 v4.10.0 條目）。

**c) fidelity 註解不精確**
`backend/core/fidelity_checks.py:536-538`「非『發言者N』的段落不參與判定（與舊版等效）…語意不變」與 §2.3 實測不符。

**d) 兩套段落語意並存**
`_tag_owner_issues`（集合語意）與 `backend/core/text_postprocess.py:799 _pick_containing_segment`（段首優先）對「時間戳屬哪一段」有兩套語意。
本輪刻意不統一（B1 要的是「是否可能正確」而非「最可能的段落」），但長期建議集中為單一來源。

---

## 6. 未驗證／揭露事項

- E4 E2E 進行中：本審查**未執行** pytest 全套、未呼叫 LM Studio（`127.0.0.1:1234`）、未寫入 `data/cache/e2e/p4-qwen27b-e4/`
  或 `attempt-E4-qwen27b-p4-final/`。
- 揭露：標籤掃描的第一次 glob（`data/cache/e2e/*/backend_data/outputs/*_逐字稿.txt`）曾命中 E4 的逐字稿檔並讀取其段落列標籤；
  該檔未被修改、未讀其輸出檔。統計已改以排除 E4 的 15 份重跑（`non_發言者N=0`、`mid_overlaps=0`）。
- 未驗證項：Windows 11＋Ollama（RTX 4090）實機、E4 收斂結果、全套 pytest 基準（見 §4）。

## 7. 審查判定

- 程式碼層面：**可 push**（無門檻放寬、無雲端路徑影響、無 off 破壞、無跨 OS 新增相依、測試釘得住根因）。
- 文件層面：4 項註記（§5）建議在 push 後、E4 證據落地時一併以 append-only 方式補記。
- 放行條件（若要求零註記）：修正 §5-c 註解與 §5-a／5-b 的文字登錄即可，但**均非 push-blocking**。
