# 出處標註吸附—區間變體校準（P3／R24）

**閉區間＋段首命中優先（v1.1，本次修正）vs 閉區間＋取第一個命中段落（v1.0，修正前對照）**

- TASK_ID：`T20260922-2037-02-local-model-quality-parity`（P3 波、CORE-5／R24 校準）
- 日期：2026-09-23｜執行：Codex 子代理｜**未修改 repo 任何程式碼／測試**（探針腳本置於 `/tmp/p3_probe/`）
- 受測程式：工作樹 P3 版 `backend/core/text_postprocess.py` 之 `snap_source_tags_to_transcript`（真函式，未重寫）。

## 1. 方法

- v1.1：直接呼叫 repo 真函式 `snap_source_tags_to_transcript(紀錄, 逐字稿, get_template("section_meeting"))`。
- v1.0 對照：**只把 `_pick_containing_segment` 換成「閉區間＋清單中第一個命中的段落」**
  （＝ P3 前的 inline 行為 `[seg for seg in segs if seg[0] <= s <= seg[1]][0]`），
  其餘規則（同發言者容忍 180 s、位移上限 120 s、speaker_mismatch 路徑）完全不動。
  置換後之 `snapped_across_segment` 觀察值定義不變（落點段落是否含原時間戳）。
- 判讀腳本：`/tmp/p3_probe/snap_probe2.py`（本次執行；附錄 §9 為等價的可重現指令）。

## 2. 受測物（真實既有紀錄；逐字稿為各自目錄的 `.txt`）

| 紀錄 | 路徑（相對 repo） | md sha256 前 16 | 逐字稿 | 逐字稿 md5 | 段落數 |
|---|---|---|---|---|---|
| Qwen 27B dense | `data/cache/e2e/p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md` | `b0ac8563c190e0c6` | 同目錄 `..._逐字稿.txt` | `1f15658303d84075c7a19c9d1fe2e325` | 183 |
| Gemma 4 31B | `data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md` | `7d2de68463ada245` | 同目錄 `..._逐字稿.txt` | `07ba4e3f7afd257a551288cb204fb15a` | 183 |
| Qwen 35B-A3B MoE | `data/cache/e2e/p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md` | `94d2f96d1c0960c2` | 同目錄 `..._逐字稿.txt` | `864a0325fdd175e0697f93528a582a6c` | 183 |

**如實標註**：三份逐字稿**不是 byte 相同**（同一場會議、三次不同 ASR 產物，md5 各異），
每份紀錄搭配其自身目錄的逐字稿；三份皆 183 段。各目錄頂層 `transcript.txt` 與該目錄
`..._逐字稿.txt` 的 md5 一致（已核對）。

## 3. 吸附統計（v1.1，修正後）

| 紀錄 | segments | tags | snapped | changed | snapped_exact | snapped_nearest | snapped_speaker_mismatch | **snapped_across_segment** | kept_far | untraceable |
|---|---|---|---|---|---|---|---|---|---|---|
| 27B | 183 | 52 | 52 | **0** | 1 | 0 | 51 | **0** | 0 | 0 |
| Gemma | 183 | 20 | 20 | **0** | 0 | 0 | 20 | **0** | 0 | 0 |
| MoE | 183 | 14 | 14 | **0** | 0 | 0 | 14 | **0** | 0 | 0 |

- 標註數不變（52→52、20→20、14→14；吸附不增刪標註）。
- **`snapped_across_segment`（落點段落不含原時間戳）三份皆 0**，符合閘門要求。
- 事實背景：三份檔案的標註**全部**已落在真實段落起點上（52/52、20/20、14/14
  的時間戳＝某段落 `start`）——因為它們本來就是「生成時已由 v1.0 吸附過」的產物。
  因此 v1.1 對它們是 **fixpoint（0 改動）**；這是預期結果，不是「吸附無作用」。
- 標籤多為「科長」等角色名，逐字稿是「發言者N」→ 幾乎全走 speaker_mismatch 路徑
  （51/52、20/20、14/14）；`snapped_exact` 僅 27B 1 筆。exact 路徑在本批無代表性。

## 4. 冪等性 `f(f(x)) == f(x)`

| 紀錄 | 第二次套用後文字 byte 相同 | 第二次 `changed` | 第二次 `snapped` |
|---|---|---|---|
| 27B | True | **0** | 52 |
| Gemma | True | **0** | 20 |
| MoE | True | **0** | 14 |

## 5. 被改動的時間戳逐筆清單（v1.1）

- **三份紀錄：0 筆改動**（逐筆清單為空）；「新值 > 原值（前進）」筆數 **0**；
  落點段落不含原時間戳的案例 **0**。
- 唯一實際被 v1.1 改寫的樣本出現在 §7 的「Gemma 原始輸出重建」：
  `00:10:04 → 00:08:15`（tag#10）。人工檢視：原值**不是任何段落起點**、
  落點段落 `[00:08:15-00:10:04] 發言者1` **含**原時間戳（604 為該段 `end`）、
  方向為後退但屬**良性吸附**（C1 已記載之真修正），非「倒退一格」缺陷型。

## 6. v1.0 對照（同一批紀錄、只換 pick 策略）

### 6.1 統計

| 紀錄 | snapped | changed | exact | nearest | mismatch | kept_far | untraceable | **倒退筆數（新值<原值）** | **第二輪再套用後 changed** |
|---|---|---|---|---|---|---|---|---|---|
| 27B | 37 | 4 | 1 | 0 | 36 | 15 | 0 | **4** | **4（非冪等）** |
| Gemma | 15 | 4 | 0 | 0 | 15 | 5 | 0 | **4** | **4（非冪等）** |
| MoE | 14 | 3 | 0 | 0 | 14 | 0 | 0 | **3** | 0 |

（v1.0 的 `snapped_across_segment` 亦為 0：v1.0 的落點仍是「含原時間戳」的段落，
缺陷形式是**方向倒退**而非落到別段——這正是它當年無觀察值可看、主指標無感的原因。）

### 6.2 逐筆改動（11 筆；全部是「原值本身即段落起點、被往回搬」＝倒退一格；0 筆前進）

| 紀錄 | tag# | 原值 | v1.0 新值 | 原值是段落起點 | v1.0 命中段落（第一命中） |
|---|---|---|---|---|---|
| 27B | 10 | 00:19:35 | 00:19:34 | 是 | [00:19:34-00:19:35] 發言者3 |
| 27B | 36 | 00:11:53 | 00:11:46 | 是 | [00:11:46-00:11:53] 發言者1 |
| 27B | 37 | 00:17:52 | 00:17:47 | 是 | [00:17:47-00:17:52] 發言者2 |
| 27B | 40 | 00:19:35 | 00:19:34 | 是 | [00:19:34-00:19:35] 發言者3 |
| Gemma | 3 | 00:19:39 | 00:19:35 | 是 | [00:19:35-00:19:39] 發言者1 |
| Gemma | 4 | 00:19:39 | 00:19:35 | 是 | [00:19:35-00:19:39] 發言者1 |
| Gemma | 12 | 00:14:34 | 00:14:32 | 是 | [00:14:32-00:14:34] 發言者3 |
| Gemma | 13 | 00:18:06 | 00:17:53 | 是 | [00:17:53-00:18:06] 發言者1 |
| MoE | 7 | 00:19:06 | 00:18:57 | 是 | [00:18:57-00:19:06] 發言者1 |
| MoE | 12 | 00:29:13 | 00:29:10 | 是 | [00:29:10-00:29:13] 發言者2 |
| MoE | 13 | 00:32:33 | 00:31:34 | 是 | [00:31:34-00:32:33] 發言者1 |

**第二輪再套用 v1.0（非冪等實證）**：
27B `00:19:34→00:19:31`、`00:11:46→00:11:42`、`00:17:47→00:17:36`、`00:19:34→00:19:31`；
Gemma `00:19:35→00:19:34`×2、`00:14:32→00:14:29`、`00:17:53→00:17:52`；MoE 無。
→ 同一批紀錄：**舊行為倒退 11 筆、新行為 0 筆**；且舊行為再跑會繼續退（27B／Gemma 各再 4 筆）。

## 7. Gemma 原始輸出重建（交叉驗證既有 C1 證據）

三份交付檔案都已吸附過，無法直接看到「模型原值」。C1 獨立驗收文件
（`e2e/attempt-C1-gemma31b-fix/verify_independent.md` §5.1）記載了 Gemma 原始輸出
8 處 changed（7 唯一值）的完整映射；依該映射把交付檔 8 個 tag 的值還原回模型原值：

| tag# | 交付檔現值 | 還原（模型原值） |
|---|---|---|
| 3, 4 | 00:19:39 | 00:19:49 |
| 6 | 00:29:10 | 00:29:13 |
| 7 | 00:05:57 | 00:06:14 |
| 10 | 00:08:15 | 00:10:04 |
| 12 | 00:14:34 | 00:14:36 |
| 13 | 00:18:06 | 00:18:09 |
| 16 | 00:42:51 | 00:43:03 |

- **v1.0 重跑此還原文字**：`snapped=17, changed=8（7 唯一值）, kept_far=3,
  speaker_mismatch=17, untraceable=0`——與 C1 文件記載的數字**逐項一致**
  （該文件：snapped 17／changed 8／kept_far 3）。→ 本次 v1.0 對照實作可信。
  8 筆改動中：7 筆的唯一值**原值皆為段落起點**（倒退缺陷型，例 `00:18:09→00:18:06`），
  1 筆 `00:10:04` 原值非起點（良性吸附）。
- **v1.1 重跑同一份還原文字**：`changed=1`——只有 `00:10:04→00:08:15`（良性）；
  6 個倒退值（00:19:49、00:29:13、00:06:14、00:14:36、00:18:09、00:43:03）全數保留原值。
  再套用一次 `changed=0`（冪等）。

## 8. 結論與限制

**結論**
1. v1.1 在三份真實紀錄上：`changed=0`、`snapped_across_segment=0`、`kept_far=0`、
   `untraceable=0`，且冪等（第二次 byte 相同、`changed=0`）。
2. v1.0 在同一批紀錄上倒退 11 筆（4／4／3），再套用仍會繼續退（27B／Gemma 各 4 筆）→
   修正確實修到東西，且與 C1 獨立驗收「6/7 個改變是倒退」一致（在原始輸出重建樣本上重現）。
3. 就本批材料，修正的邊際貢獻＝**消除倒退與非冪等**；對「已吸附過」的檔案則維持原值（fixpoint）。

**限制（不得外推）**
- 單一會議（0903 科務會議）、樣本 3 份；逐字稿是 ASR 產物且三份非 byte 相同
  （同一次會議的逐字稿內容略有差異，本報告以「各紀錄配自身逐字稿」為準）。
- 本批幾乎全走 speaker_mismatch 路徑（角色名 vs 發言者N）；exact／nearest 路徑樣本過少。
- 「0 changed」是 fixpoint 的結構性結果；`[UNKNOWN]`：其他會議、零長度段落、
  位移落在 120 s 邊界、發言者標籤可對上名等情境的行為。
- v1.0 對照以 monkeypatch 重現 P3 前的 pick 策略（其餘參數相同）；未跑 `git` 取舊版檔案比對
  （依任務硬約束），其可信度由 §7 與 C1 記載完全吻合佐證。

## 9. 附錄：可重現指令

一鍵重跑（本次實際執行之等價指令；輸出即為本報告 §3、§4、§6、§7 的數字）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python - <<'PY'
import sys; sys.path.insert(0, ".")
from pathlib import Path
from backend.core import text_postprocess as tp
from backend.core.templates import get_template

P = Path("data/cache/e2e")
PAIRS = [
    ("27B",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a_逐字稿.txt"),
    ("Gemma", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec_逐字稿.txt"),
    ("MoE",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da_逐字稿.txt"),
]

def old_pick(segments, seconds):  # v1.0：閉區間＋清單第一個命中段落
    for seg in segments:
        if tp._segment_contains(seg, seconds):
            return seg
    return None

def tag_seconds(text):
    out = []
    for m in tp.SOURCE_TAG_PATTERN.finditer(text):
        tm = tp.SOURCE_TAG_TIME_PATTERN.search(m.group()[1:-1])
        out.append(tp._hms_to_seconds(tm.group(1), tm.group(2), tm.group(3) or "0") if tm else None)
    return out

RAWS = {3: "00:19:49", 4: "00:19:49", 6: "00:29:13", 7: "00:06:14",
        10: "00:10:04", 12: "00:14:36", 13: "00:18:09", 16: "00:43:03"}  # C1 記載的 Gemma 模型原值

tpl = get_template("section_meeting")
for name, rp, tpth in PAIRS:
    rec, tr = rp.read_text(encoding="utf-8"), tpth.read_text(encoding="utf-8")
    new, st = tp.snap_source_tags_to_transcript(rec, tr, tpl)
    new2, st2 = tp.snap_source_tags_to_transcript(new, tr, tpl)
    saved = tp._pick_containing_segment; tp._pick_containing_segment = old_pick
    old, ost = tp.snap_source_tags_to_transcript(rec, tr, tpl)
    old2, ost2 = tp.snap_source_tags_to_transcript(old, tr, tpl)
    tp._pick_containing_segment = saved
    back = sum(1 for a, b in zip(tag_seconds(rec), tag_seconds(old)) if a is not None and b is not None and b < a)
    print(name, "| v1.1", st, "| idem", new2 == new, st2["changed"],
          "| v1.0", ost, "| v1.0 backward", back, "| v1.0 re-apply changed", ost2["changed"])

rp = P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md"
tpth = P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec_逐字稿.txt"
rec, tr = rp.read_text(encoding="utf-8"), tpth.read_text(encoding="utf-8")
text = rec
for idx in sorted(RAWS, reverse=True):
    m = list(tp.SOURCE_TAG_PATTERN.finditer(text))[idx]
    tm = tp.SOURCE_TAG_TIME_PATTERN.search(m.group()[1:-1])
    s, e = m.start() + 1 + tm.start(), m.start() + 1 + tm.end()
    text = text[:s] + RAWS[idx] + text[e:]
new, st = tp.snap_source_tags_to_transcript(text, tr, tpl)
saved = tp._pick_containing_segment; tp._pick_containing_segment = old_pick
old, ost = tp.snap_source_tags_to_transcript(text, tr, tpl)
tp._pick_containing_segment = saved
print("Gemma raw-restore | v1.0", ost, "| v1.1", st)
PY
```

輔助探針：`/tmp/p3_probe/snap_probe.py`（輸出 JSON 版）、`/tmp/p3_probe/snap_probe2.py`（本報告主腳本，含逐筆改動清單與第二輪套用）。判讀以 `python3` 讀 JSON 完成。

## rev 9 修訂版量測（2026-09-23）

> **版本對照（必讀）**：本節全部數字對應 **rev 9 實作**——`snap_source_tags_to_transcript` 新增
> **規則 0 全域段首保護**（`kept_on_start`）、移除 `snapped_across_segment`（恆 0 無鑑別力）、
> 新增 `backward_moves`／`forward_moves`／`max_backward_seconds`。
> **上方 §1–§9 的數字對應 rev 8 實作（舊版），勿與本節混用**：rev 8 的 `snapped_across_segment`
> 在 rev 9 已不存在；rev 8 的 `changed` 統計語意也不同（rev 9 多了規則 0）。
> 本節為**追加**，未改動任何舊數字。

### rev9.0 實作核對（以 `git diff backend/core/text_postprocess.py` 實際核對，非只信描述）

- 規則 0 位於 `replace_tag` 內、發言者判定**之前**：

  ```python
  if any(seg[0] == seconds for seg in segments):
      stats["kept_on_start"] += 1
      return tag
  ```

- stats 鍵＝`segments/tags/snapped/changed/snapped_exact/snapped_nearest/snapped_speaker_mismatch/kept_on_start/backward_moves/forward_moves/max_backward_seconds/kept_far/untraceable`；**已無** `snapped_across_segment`。
- `_pick_containing_segment`：段首命中（`seg[0] == seconds`）優先，否則取**第一個**含此秒數的段落（閉區間）；三條吸附路徑的落點仍一律是某段 `start`。
- `backward_moves`／`forward_moves`／`max_backward_seconds` 為**觀察值（非閘門）**；`backward_moves` 非零是正常（段落內吸附本來就往段首收）。

### rev9.A 新實作統計（五個素材；全用 repo 真函式）

呼叫：`tp.snap_source_tags_to_transcript(紀錄, 逐字稿, get_template("section_meeting"))`。

| 素材 | segments | tags | snapped | changed | kept_on_start | backward_moves | forward_moves | max_backward_seconds | kept_far | untraceable | 二次套用 byte 相同 | 二次 changed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 27B | 183 | 52 | 0 | **0** | 52 | 0 | 0 | 0 | 0 | 0 | True | 0 |
| Gemma | 183 | 20 | 0 | **0** | 20 | 0 | 0 | 0 | 0 | 0 | True | 0 |
| MoE | 183 | 14 | 0 | **0** | 14 | 0 | 0 | 0 | 0 | 0 | True | 0 |
| **A1**（`p2-27b-01/.../0903-科務會議_f012e80c.md`） | 183 | 61 | 3 | **3** | 58 | 3 | 0 | 70 | 0 | 0 | True | 0 |
| fixture（合成跨發言者最小反例） | 2 | 1 | 0 | **0** | 1 | 0 | 0 | 0 | 0 | 0 | True | 0 |

- 三份既有紀錄：**changed=0**（52/52、20/20、14/14 個時間戳本來就是全域真實段首 → 規則 0 全數原樣保留）；`backward_moves=0`、`forward_moves=0`。此為 fixpoint 的結構性結果，非「吸附無作用」。
- **A1**：changed=3，全部是同一個時間戳 `00:25:21`（tag#24/#25/#53）→ `00:24:11`（Δ=-70 s）。診斷（`rev9_a1_diag.py`）：`00:25:21`＝段落 `(1451,1521,發言者1)` 的 **end**、且不是任何段落的 start → 規則 0 不保護；`_pick_containing_segment` 段首優先不命中 → 回退到該段（閉區間）吸到段首。屬「閉區間邊界吸附」的既定取捨（與 rev 8 §7 的 C1 良性案例 `00:10:04 → 00:08:15` 同型），非跨段倒退；位移 70 s ≤ 120 s 故不觸發 `kept_far`。
- fixture（跨發言者交界最小反例，可重現）：
  - 逐字稿：`[00:13:12-00:13:37] 發言者1：前面這段話內容。`／`[00:13:37-00:13:45] 發言者2：後面這段話內容。`
  - 紀錄：`會議紀錄（發言者1 00:13:37）此為跨發言者交界最小反例。`
  - 新實作：`kept_on_start=1、changed=0`（v1.0 會改寫成 00:13:12，見 rev9.B）。

### rev9.B 鑑別力證明：v1.0 全行為 vs 新實作

**v1.0 對照＝`git show HEAD:backend/core/text_postprocess.py` 取出的舊版函式**（P3 前的
「閉區間＋清單第一個命中」、**無**規則 0），以 AST 取出該函式原文後 `exec` 執行（**未重寫**；見 `rev9_snap.py`）。
其結果與 rev 8 §6.1 的 monkeypatch 對照一致（27B=4／Gemma=4／MoE=3）→ 兩條獨立重建路徑互相印證。

「**原時間戳已是全域真實段首，卻仍被改寫**」的筆數：

| 素材 | v1.0 changed | **v1.0：原值∈全域段首仍被改寫** | v1.0 backward／forward | **新實作：原值∈全域段首仍被改寫** | 新實作 changed |
|---|---|---|---|---|---|
| 27B | 4 | **4** | 4／0 | **0** | 0 |
| Gemma | 4 | **4** | 4／0 | **0** | 0 |
| MoE | 3 | **3** | 3／0 | **0** | 0 |
| A1 | 14 | **11** | 14／0 | **0** | 3 |
| fixture | 1 | **1** | 1／0 | **0** | 0 |

→ 閘門結論：新實作 **0/5 素材**（合計 0 筆）；v1.0 **5/5 素材皆 > 0**（合計 23 筆）。

A1 的 11 筆（v1.0 逐筆；tag# 原值→新值）：
`#16 00:13:37→00:13:12`、`#17 00:15:14→00:14:36`、`#34 00:32:33→00:31:34`、`#35 00:33:07→00:32:34`、
`#36 00:33:56→00:33:55`、`#38 00:44:15→00:43:03`、`#48 00:15:14→00:14:36`、`#52 00:21:01→00:19:49`、
`#57 00:32:33→00:31:34`、`#58 00:32:33→00:31:34`、`#59 00:44:15→00:43:03`。
（v1.0 另 3 筆原值非全域段首：tag#24/#25/#53＝`00:25:21→00:24:11`。）

**與審查者數字的交叉核對（rev 8 重建）**：把現行函式原始碼**機械移除規則 0 區塊**（`rev9_rev8sim.py`，
`assert src.count(BLOCK) == 1` 防定位錯誤）→ 得 rev 8 行為：
- A1：rev 8 changed=**12**，其中「原值∈全域段首」=**9**（tag#16,17,34,35,36,48,52,57,58）——與
  `review/attempt-07/review.md` 記載的「changed=12、12/12 後退、9 筆 ∈ 全域段 start」**一致**；
- rev 8 的 12 筆＝新實作仍改的 3 筆（#24/#25/#53，段 end 邊界）＋ 規則 0 擋下的 9 筆；
- fixture：rev 8 仍改寫（changed=1，`00:13:37→00:13:12`）→ **證實「段首優先」單獨不足、規則 0 是必要條件**（審查 R3①）。

### rev9.C 冪等 `f(f(x)) == f(x)`

五個素材二次套用皆 **byte 完全相同、`changed=0`**（表末兩欄）。A1 首輪 3 改動的落點都是段首 → 第二輪被規則 0 保護 → fixpoint。

### rev9.D 反例與限制（誠實標註）

- **未發現 A/B 型反例**：五個素材上，新實作沒有改寫任何「原值∈全域段首」的時間戳；`forward_moves` 全 0；冪等成立。
- A1 仍有 3 筆 changed（同一個段 end 時間戳、70 s，見 rev9.A）：以「段首不得被移早」為基準是 0；以「任何非原樣保留」為基準則非 0，已知且可解釋。
- 限制：單一會議（0903）＋A1 為**舊執行產物**（非本波輸出）＋fixture 為合成；exact/nearest 路徑樣本仍少。
- `[UNKNOWN]`：其他會議、逐字稿含零長度段落、位移剛好落在 120 s 邊界、標籤時間戳晚於逐字稿結尾等情境。
- v1.0 對照以 HEAD 原文函式重現；rev 8 對照以「機械移除規則 0 區塊」重建（兩者皆非人為改寫）。

### rev9.E 可重現指令（本次實際執行）

`rev9_snap.py`（§rev9.A／B 主腳本；v1.0＝HEAD 原文函式 exec）：

```bash
cd /Users/hsiaojohnny/dev/convert && git show HEAD:backend/core/text_postprocess.py > /tmp/p3_probe/rev9_head_text_postprocess.py
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev9_snap.py
```

<details><summary>rev9_snap.py 全文</summary>

```python
"""rev9：吸附（規則0 全域段首保護）校準。v1.0 對照＝HEAD 原文函式（exec，不重寫）。"""
import ast, json, sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from pathlib import Path
from backend.core import text_postprocess as tp
from backend.core.templates import get_template

# ---- v1.0：直接從 HEAD 檔案取出舊函式原始碼（未改寫）並 exec ----
src = open("/tmp/p3_probe/rev9_head_text_postprocess.py", encoding="utf-8").read()
tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
          and n.name == "snap_source_tags_to_transcript")
mod = ast.Module(body=[fn], type_ignores=[])
ast.fix_missing_locations(mod)
_ns = dict(vars(tp))
exec(compile(mod, "<v10-src>", "exec"), _ns)
snap_v10 = _ns["snap_source_tags_to_transcript"]

def tag_seconds(text):
    out = []
    for m in tp.SOURCE_TAG_PATTERN.finditer(text):
        tm = tp.SOURCE_TAG_TIME_PATTERN.search(m.group()[1:-1])
        out.append(tp._hms_to_seconds(tm.group(1), tm.group(2), tm.group(3) or "0") if tm else None)
    return out

P = Path("/Users/hsiaojohnny/dev/convert/data/cache/e2e")
MATS = [
    ("27B",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a_逐字稿.txt"),
    ("Gemma", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec_逐字稿.txt"),
    ("MoE",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da_逐字稿.txt"),
    ("A1",    P/"p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c.md",       P/"p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c_逐字稿.txt"),
]
FIXT_TR = "[00:13:12-00:13:37] 發言者1：前面這段話內容。\n[00:13:37-00:13:45] 發言者2：後面這段話內容。\n"
FIXT_REC = "會議紀錄（發言者1 00:13:37）此為跨發言者交界最小反例。"

tpl = get_template("section_meeting")
out = {}
for name, rp, tpth in (MATS + [("fixture", None, None)]):
    if name == "fixture":
        rec, tr = FIXT_REC, FIXT_TR
    else:
        rec, tr = rp.read_text(encoding="utf-8"), tpth.read_text(encoding="utf-8")
    segs = tp.iter_transcript_segments(tr)
    starts = {s for s, _, _ in segs}
    new, st = tp.snap_source_tags_to_transcript(rec, tr, tpl)
    new2, st2 = tp.snap_source_tags_to_transcript(new, tr, tpl)
    old, ost = snap_v10(rec, tr, tpl)
    olds = tag_seconds(rec); news = tag_seconds(new); olds2 = tag_seconds(old)
    def rewritten_on_start(orig, after):
        return [i for i, (a, b) in enumerate(zip(orig, after))
                if a is not None and b is not None and a in starts and a != b]
    v10_on_start = rewritten_on_start(olds, olds2)
    new_on_start = rewritten_on_start(olds, news)
    v10_back = [i for i, (a, b) in enumerate(zip(olds, olds2)) if a is not None and b is not None and b < a]
    v10_fwd  = [i for i, (a, b) in enumerate(zip(olds, olds2)) if a is not None and b is not None and b > a]
    out[name] = {
        "segments": len(segs),
        "new": st, "new_idem_byte_equal": new2 == new, "new_changed2": st2["changed"],
        "v10": ost,
        "v10_rewritten_on_start_n": len(v10_on_start),
        "v10_rewritten_on_start_tags": [(i, olds[i], olds2[i], tp._seconds_to_hms(olds[i], with_seconds=True), tp._seconds_to_hms(olds2[i], with_seconds=True)) for i in v10_on_start],
        "new_rewritten_on_start_n": len(new_on_start),
        "v10_backward_n": len(v10_back), "v10_forward_n": len(v10_fwd),
        "new_backward_from_orig": sum(1 for a, b in zip(olds, news) if a is not None and b is not None and b < a),
        "new_forward_from_orig": sum(1 for a, b in zip(olds, news) if a is not None and b is not None and b > a),
    }
print(json.dumps(out, ensure_ascii=False, indent=1))
```

</details>

`rev9_rev8sim.py`（rev9.B 交叉核對）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev9_rev8sim.py
```

<details><summary>rev9_rev8sim.py 全文</summary>

```python
"""rev9 交叉驗證：以「現行函式原始碼機械移除規則0區塊」重建 rev8 行為（非人為改寫）。"""
import inspect, json, sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from pathlib import Path
from backend.core import text_postprocess as tp
from backend.core.templates import get_template

src = inspect.getsource(tp.snap_source_tags_to_transcript)
BLOCK = (
    '        if any(seg[0] == seconds for seg in segments):\n'
    '            stats["kept_on_start"] += 1\n'
    '            return tag\n'
)
assert src.count(BLOCK) == 1, "規則0區塊定位失敗，中止"
src2 = src.replace(BLOCK, "")
ns = dict(vars(tp))
exec(compile(src2, "<rev8-sim>", "exec"), ns)
snap_rev8 = ns["snap_source_tags_to_transcript"]

def tag_seconds(text):
    out = []
    for m in tp.SOURCE_TAG_PATTERN.finditer(text):
        tm = tp.SOURCE_TAG_TIME_PATTERN.search(m.group()[1:-1])
        out.append(tp._hms_to_seconds(tm.group(1), tm.group(2), tm.group(3) or "0") if tm else None)
    return out

P = Path("/Users/hsiaojohnny/dev/convert/data/cache/e2e")
MATS = [
    ("27B",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a_逐字稿.txt"),
    ("Gemma", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec_逐字稿.txt"),
    ("MoE",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da_逐字稿.txt"),
    ("A1",    P/"p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c.md",       P/"p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c_逐字稿.txt"),
]
FIXT_TR = "[00:13:12-00:13:37] 發言者1：前面這段話內容。\n[00:13:37-00:13:45] 發言者2：後面這段話內容。\n"
FIXT_REC = "會議紀錄（發言者1 00:13:37）此為跨發言者交界最小反例。"
tpl = get_template("section_meeting")
out = {}
for name, rp, tpth in (MATS + [("fixture", None, None)]):
    rec, tr = (FIXT_REC, FIXT_TR) if name == "fixture" else (rp.read_text(encoding="utf-8"), tpth.read_text(encoding="utf-8"))
    segs = tp.iter_transcript_segments(tr); starts = {s for s, _, _ in segs}
    rev8, st8 = snap_rev8(rec, tr, tpl)
    orig = tag_seconds(rec); after = tag_seconds(rev8)
    on_start = [i for i, (a, b) in enumerate(zip(orig, after)) if a is not None and b is not None and a in starts and a != b]
    changed = [i for i, (a, b) in enumerate(zip(orig, after)) if a is not None and b is not None and a != b]
    out[name] = {"rev8_stats": st8, "rev8_rewritten_on_start_n": len(on_start),
                 "rev8_rewritten_on_start_tags": [i for i in on_start],
                 "rev8_changed_tags": changed,
                 "rev8_changed_pairs": [(i, tp._seconds_to_hms(orig[i], with_seconds=True), tp._seconds_to_hms(after[i], with_seconds=True)) for i in changed]}
print(json.dumps(out, ensure_ascii=False, indent=1))
```

</details>

`rev9_a1_diag.py`（A1 三筆 changed 的逐筆診斷）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev9_a1_diag.py
```

<details><summary>rev9_a1_diag.py 全文</summary>

```python
import sys; sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from pathlib import Path
from backend.core import text_postprocess as tp
from backend.core.templates import get_template
P = Path("/Users/hsiaojohnny/dev/convert/data/cache/e2e")
rp = P/"p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c.md"
tpth = P/"p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c_逐字稿.txt"
rec, tr = rp.read_text(encoding="utf-8"), tpth.read_text(encoding="utf-8")
tpl = get_template("section_meeting")
segs = tp.iter_transcript_segments(tr)
starts = {s for s, _, _ in segs}
def tag_list(text):
    out = []
    for m in tp.SOURCE_TAG_PATTERN.finditer(text):
        tm = tp.SOURCE_TAG_TIME_PATTERN.search(m.group()[1:-1])
        if tm:
            secs = tp._hms_to_seconds(tm.group(1), tm.group(2), tm.group(3) or "0")
            out.append((m.group(), tm.group(), secs, m.start()))
        else:
            out.append((m.group(), None, None, m.start()))
    return out
before = tag_list(rec)
new, st = tp.snap_source_tags_to_transcript(rec, tr, tpl)
after = tag_list(new)
for i, (tb, ta) in enumerate(zip(before, after)):
    if tb[2] is not None and ta[2] is not None and tb[2] != ta[2]:
        orig, tgt = tb[2], ta[2]
        containing = [(s, e, sp) for s, e, sp in segs if tp._segment_contains((s, e, sp), orig)]
        on_start = orig in starts
        # same-speaker segments containing orig
        speaker = tp._normalize_speaker_label(tb[0][1:-1][:tb[0][1:-1].find("00")].strip(tp._SPEAKER_LABEL_STRIP_CHARS)) if False else None
        print(f"tag#{i} {tb[1]} -> {ta[1]} ({orig}->{tgt}, Δ={tgt-orig}s) on_start={on_start} containing={containing}")
print("stats:", st)
```

</details>
