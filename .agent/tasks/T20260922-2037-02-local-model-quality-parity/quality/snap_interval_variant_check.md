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
## rev 10 增補量測（2026-09-23）：規則 4 精度保護

> **版本對照（必讀）**：本節全部數字對應 **rev 10 實作（工作樹未提交變更）**——`snap_source_tags_to_transcript`
> 於「採用 replacement 之前」新增**規則 4 精度保護**：原標註是 **`HH:MM`（無秒）**且吸附目標段首
> **不是整分鐘**（`target % 60 != 0`）→ **原樣保留**並計入新 stats 欄位 `kept_precision`；
> 僅在 render/parse 可逆（含秒，或目標為整分鐘）時才採用 replacement。
> 根因＝審查 `review/attempt-08` R1：無秒標註吸附後**非冪等**（`00:03 → 00:02 → 00:00` 鏈式後退）。
> **上方所有節（§1–§9、§rev 9）的數字對應 rev 8／rev 9 實作，勿與本節混用。本節為檔尾追加，未改動任何既有內容。**

- 量測基準：HEAD `c298cc81a12beae4d83d00def07cda73bb56d0a9`；受測實作＝**工作樹** `backend/core/text_postprocess.py`
  （rev 10；sha256 `44a5de3cd00f07a128ac7181bb78cee9c735f950fda8af2aef6920f8d480bd4b`）。
  規則 4 現址：`text_postprocess.py:987-989`（`with_seconds` 判定之後；其後 990 行才是 `replacement` 指派）：

  ```python
  if not with_seconds and target % 60 != 0:
      stats["kept_precision"] += 1
      return tag
  ```

- 全數以 repo 真函式 `tp.snap_source_tags_to_transcript(紀錄, 逐字稿, get_template("section_meeting"))` 執行；
  探針腳本置於 `/tmp/p3_probe/`（**未進 repo**）；命令一律 `DATA_DIR=/tmp/probe_scratch uv run --frozen python ...`。
- 工作樹另有 `backend/services/summarization.py`／`tests/test_t20260922_2037_p3_parity.py` 未提交變更；
  本節只呼叫吸附函式，與它們無關。
- **[VERIFIED]**：以下所有數字（五素材 stats、二次套用 byte 比較、合成探針、最小反例複現）均由 §rev10.E 腳本
  實際執行輸出，非轉抄。

### rev10.A 受測物（三既有＋A1＋D1 新素材）

| 紀錄 | 路徑（相對 repo） | md sha256 前 16 | 逐字稿 | 逐字稿 md5 | 段落數 |
|---|---|---|---|---|---|
| 27B | `data/cache/e2e/p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md` | `b0ac8563c190e0c6` | 同目錄 `..._逐字稿.txt` | `1f15658303d84075c7a19c9d1fe2e325` | 183 |
| Gemma | `data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md` | `7d2de68463ada245` | 同目錄 `..._逐字稿.txt` | `07ba4e3f7afd257a551288cb204fb15a` | 183 |
| MoE | `data/cache/e2e/p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md` | `94d2f96d1c0960c2` | 同目錄 `..._逐字稿.txt` | `864a0325fdd175e0697f93528a582a6c` | 183 |
| A1（p2 舊執行產物） | `data/cache/e2e/p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c.md` | `d48913472857df0c` | 同目錄 `..._逐字稿.txt` | `1f15658303d84075c7a19c9d1fe2e325` | 183 |
| **D1（本波 P3 D1 E2E 產物）** | `data/cache/e2e/p3-gemma31b-d1/backend_data/outputs/0903-科務會議_ab5571ea.md` | `010a5224969efe4e` | 同目錄 `..._逐字稿.txt` | `07ba4e3f7afd257a551288cb204fb15a` | 183 |

- D1 md 由 `e2e/attempt-D1-gemma31b-p3/`（`run_summary.json`：Gemma 4 31B、HEAD `c298cc8`、`task_completed=true`）產出；
  md mtime `01:55:49` 早於 rev 10 工作樹變更（`text_postprocess.py` mtime `01:59:33`）→ **D1 輸出由 rev 9 build 產生**（吸附後標註已是 rev 9 fixpoint）。
- A1 逐字稿 md5 與 27B 相同、D1 與 Gemma 相同：同模型同場次之 ASR 逐字稿檔重用（byte 相同，非筆誤）。

### rev10.B 五素材吸附統計（rev 10 真函式）

| 素材 | segments | tags | snapped | changed | kept_on_start | **kept_precision** | kept_far | backward_moves | max_backward_seconds | forward_moves | untraceable | 二次套用 byte 相同 | 二次 changed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 27B | 183 | 52 | 0 | **0** | 52 | **0** | 0 | 0 | 0 | 0 | 0 | True | 0 |
| Gemma | 183 | 20 | 0 | **0** | 20 | **0** | 0 | 0 | 0 | 0 | 0 | True | 0 |
| MoE | 183 | 14 | 0 | **0** | 14 | **0** | 0 | 0 | 0 | 0 | 0 | True | 0 |
| A1 | 183 | 61 | 3 | **3** | 58 | **0** | 0 | 3 | 70 | 0 | 0 | True | 0 |
| D1 | 183 | 24 | 0 | **0** | 23 | **0** | 1 | 0 | 0 | 0 | 0 | True | 0 |

- **[VERIFIED] 與事先預期逐項一致**：`kept_precision` 五素材全 0（輸入域掃描 171 個標註中 **0 個無秒**）；
  `changed` 依序 0／0／0／3／0；D1 `kept_on_start=23`、`kept_far=1`；五個二次套用皆 **byte 相同、`changed=0`**（冪等）。
- A1 的 3 筆 changed（[VERIFIED] 逐筆診斷）：tag#24／#25／#53，`（發言者1，00:25:21）→（發言者1，00:24:11）`（Δ=-70 s、snapped_exact）；
  原值＝段落 `(1451,1521,發言者1)` 的 **end** 且非任何段 start（閉區間邊界吸附，rev 9 已記載）。三筆皆**含秒**標註，
  規則 4 不涉入 → **與 rev 9 輸出完全一致；rev 10 未對既有素材新增任何改寫**。
- D1 唯一 `kept_far`（[VERIFIED] 逐筆診斷）：tag#10 `（科長，00:04:53）`（orig=293 s），落點段首 0 s、位移 293 s > `TAG_SNAP_MAX_SHIFT_SECONDS=120`
  → 依既有位移上限原樣保留（先於規則 4 判定，屬 rev 9 既有保護，非規則 4 之功）。
- 三份既有 P2 檔（27B／Gemma／MoE）標註 100% 已落在真實段首 → 規則 0 全數接住、`changed=0`（fixpoint 結構性結果，同 rev 9）。

### rev10.C 合成探針：規則 4 生效證據與最小反例

fixture 自建於 `/tmp`（合成逐字稿＋合成紀錄；`/tmp/p3_probe/rev10_minute_probe.py`，見 §rev10.E）。
「rev9sim」＝以現行函式原始碼**機械移除規則 4 區塊**重建（`assert src.count(BLOCK) == 1` 防定位錯誤；非人為改寫）。

| 案例 | 逐字稿（段首；目標＝落點候選段） | 紀錄標註 | rev10 `f(x)` | rev10 `f(f(x))` | rev10 changed 1→2 | rev10 `kept_precision` | rev9sim `f(x)` → `f(f(x))` | 判讀 |
|---|---|---|---|---|---|---|---|---|
| A｜attempt-08 R1 原 fixture（5 段；目標段首 `00:02:42` 非整分鐘） | `00:00:12／00:00:42／00:02:42／00:03:18／00:04:48` | `（科長，00:03）` | `（科長，00:03）`（原樣） | 同左 | 0→0 | **1** | `00:02` → `00:00`（1→1；**f(f(x))≠f(x)**） | 規則 4 擋下；審查反例鏈完整複現 |
| B｜自建最小反例（2 段；目標段首 `00:02:42`） | `00:00:42／00:02:42` | `（科長，00:03）` | `（科長，00:03）` | 同左 | 0→0 | **1** | `00:02` → `00:00`（1→1；**非冪等**） | 最小型反例（兩段即可）；即 `00:03→00:02→00:00` |
| C｜合成②：目標段首**整分鐘** | `00:02:00` | `（科長，00:03）` | `（科長，00:02）`（snapped=1） | `（科長，00:02）`（第二輪由規則 0 接住） | 1→0 | 0 | `00:02` → `00:02`（1→0） | 整分鐘目標可吸附且冪等（`parse(render(120s))==120s`） |
| D｜合成①單段版：目標段首非整分鐘 | `00:02:42` | `（科長，00:03）` | `（科長，00:03）` | 同左 | 0→0 | **1** | `00:02` → `00:02`（1→0） | 規則 4 原樣保留；rev9 會做一次「值失真」後退（120 s 非任何段首）後靜止 |

- **[VERIFIED] ①（非整分鐘 → 原樣保留）**：A／B／D 三案例 `kept_precision=1`、標註原樣、`changed=0`、二次套用 byte 相同。
- **[VERIFIED] ②（整分鐘 → 可吸附）**：C 案例 `snapped=1`、`kept_precision=0`、`changed=1`，`00:03→00:02` 落點＝目標段首；二次套用 byte 相同（規則 0 接手）。
- **[VERIFIED] ③（冪等）**：A～D 四案例二次套用皆 byte 相同（A／B／D 靠規則 4，C 靠規則 0）。
- **[VERIFIED] 最小反例（無規則 4 時 non-idempotent；本節自行複現）**：B（自建，僅 2 段）rev9sim `f(x)=（科長，00:02）`
  → `f(f(x))=（科長，00:00）`、`changed1=1／changed2=1`；與 `review/attempt-08` R1 記載之 `00:03 → 00:02 → 00:00` 鏈一致，
  A 則為該審查原 fixture 之逐字複現（同鏈）。機理：`00:03`（180 s）被吸到段首 162 s → `with_seconds=False` 渲染捨秒成
  `00:02`（120 s）→ 第二輪 120 s 落回更前段 `[42,162]` → 段首 42 s → `00:00`（0 s 不在任何段內才停）。

### rev10.D 如實邊界（不得外推）

- **[VERIFIED] 規則 4 在五個真實素材上完全未觸發（`kept_precision=0`；輸入域掃描 171 個標註中 0 個無秒）**
  → 它**不是**既有素材品質改善的來源，只是把「無秒標註（`HH:MM`）」這個**可達輸入域**的冪等宣稱補齊；
  **不得宣稱它改善了既有素材**。既有素材輸出與 rev 9 逐項相同（27B／Gemma／MoE `changed=0`、A1 `changed=3`、
  D1 `kept_on_start=23／kept_far=1`）。
- 規則 4 的**生效證據全部來自合成 fixture**（A～D）；真實素材只有「未觸發（=0）」這一項證據。**不得外推**為
  「真實會議曾發生無秒標註鏈退」。
- rev9sim 為「機械移除規則 4 區塊」之行為重建，未以 `git stash`／checkout 舊版檔實跑；僅作「若無規則 4」對照。
- `[UNKNOWN]`：含秒＋無秒混雜之長紀錄、無秒標註的目標段首恰為整分鐘但原標註本身非段首之真實案例
  （C 為合成）、其他會議／多會議批次、規則 4 與 `kept_far` 同時成立時的行為（現行碼 `kept_far` 先判，未以 fixture 交叉驗證）。

### rev10.E 可重現指令（本次實際執行）

`rev10_snap.py`（§rev10.A／B 主腳本）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev10_snap.py
```

<details><summary>rev10_snap.py 全文</summary>

```python
"""rev 10 增補量測：五素材（27B／Gemma／MoE／A1／D1）真實素材吸附統計（工作樹 rev 10 實作）。

呼叫 repo 真函式 backend.core.text_postprocess.snap_source_tags_to_transcript；
輸出 JSON（含首輪 stats、二次套用 byte 相同、輸入域無秒標註計數）。"""
import hashlib, json, sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from pathlib import Path
from backend.core import text_postprocess as tp
from backend.core.templates import get_template

REPO = Path("/Users/hsiaojohnny/dev/convert")
P = REPO / "data/cache/e2e"
MATS = [
    ("27B",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md"),
    ("Gemma", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md"),
    ("MoE",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md"),
    ("A1",    P/"p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c.md"),
    ("D1",    P/"p3-gemma31b-d1/backend_data/outputs/0903-科務會議_ab5571ea.md"),
]
tpl = get_template("section_meeting")
out = {}
for name, rp in MATS:
    raw = rp.read_bytes()
    rec = raw.decode("utf-8")
    trp = rp.with_name(rp.stem + "_逐字稿.txt")
    tr = trp.read_text(encoding="utf-8")
    # 輸入域掃描：無秒（HH:MM）標註筆數
    no_sec = 0
    for m in tp.SOURCE_TAG_PATTERN.finditer(rec):
        tm = tp.SOURCE_TAG_TIME_PATTERN.search(m.group()[1:-1])
        if tm and tm.group(3) is None:
            no_sec += 1
    new, st = tp.snap_source_tags_to_transcript(rec, tr, tpl)
    new2, st2 = tp.snap_source_tags_to_transcript(new, tr, tpl)
    out[name] = {
        "md": str(rp.relative_to(REPO)),
        "md_sha256": hashlib.sha256(raw).hexdigest(),
        "md_sha256_16": hashlib.sha256(raw).hexdigest()[:16],
        "transcript_md5": hashlib.md5(tr.encode("utf-8")).hexdigest(),
        "no_second_tags_in_input": no_sec,
        "stats1": st,
        "byte_identical_second": new2 == new,
        "stats2": st2,
    }
print(json.dumps(out, ensure_ascii=False, indent=1))
print()
for name, _ in MATS:
    r = out[name]
    s = r["stats1"]
    print(
        f"{name:5s} segs={s['segments']} tags={s['tags']} snapped={s['snapped']} changed={s['changed']} "
        f"kept_on_start={s['kept_on_start']} kept_precision={s['kept_precision']} kept_far={s['kept_far']} "
        f"backward={s['backward_moves']} max_back={s['max_backward_seconds']} forward={s['forward_moves']} "
        f"untraceable={s['untraceable']} | 2nd byte==1st: {r['byte_identical_second']} (changed2={r['stats2']['changed']}) "
        f"| no-sec in input: {r['no_second_tags_in_input']}"
    )
```

</details>

`rev10_minute_probe.py`（§rev10.C 合成探針，含 rev9sim 機械重建）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev10_minute_probe.py
```

<details><summary>rev10_minute_probe.py 全文</summary>

```python
"""rev 10 規則 4（精度保護）合成探針：無秒標註（HH:MM）的冪等。

(a) 工作樹 rev 10 實作（repo 真函式）；
(b) rev 9 模擬：以「現行函式原始碼機械移除規則 4 區塊」重建（非人為改寫），
    用於複現 review/attempt-08 R1 的鏈式後退（00:03 → 00:02 → 00:00）。

案例：
  A = attempt-08 R1 原 fixture（reviewer 的 5 段逐字稿）——本節自行複現一次。
  B = 自建最小非冪等反例（2 段：目標段首 00:02:42 非整分鐘 + 其前段）。
  C = 合成②：目標段首為整分鐘（00:02:00）→ 規則 4 不擋、可吸附，且冪等。
  D = 合成①單段版：目標段首非整分鐘 → rev10 原樣保留（kept_precision=1），
      對照 rev9 會先搬到 00:02（120s，非任何段首／非段落內 → 值失真後靜止）。
"""
import inspect, json, sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from backend.core import text_postprocess as tp
from backend.core.templates import get_template

src = inspect.getsource(tp.snap_source_tags_to_transcript)
BLOCK = (
    '        if not with_seconds and target % 60 != 0:\n'
    '            stats["kept_precision"] += 1\n'
    '            return tag\n'
)
assert src.count(BLOCK) == 1, "規則 4 區塊定位失敗，中止"
src2 = src.replace(BLOCK, "")
ns = dict(vars(tp))
exec(compile(src2, "<rev9-sim>", "exec"), ns)
snap_rev9 = ns["snap_source_tags_to_transcript"]

tpl = get_template("section_meeting")

CASES = {
    "A_attempt08_R1原fixture": {
        "tr": (
            "[00:00:12-00:00:42] 發言者1：話。\n"
            "[00:00:42-00:02:42] 發言者2：話。\n"
            "[00:02:42-00:04:42] 發言者2：話。\n"
            "[00:03:18-00:03:19] 發言者1：話。\n"
            "[00:04:48-00:04:49] 發言者2：話。\n"
        ),
        "rec": "會議紀錄。1.（科長，00:03）",
    },
    "B_自建最小反例_2段": {
        "tr": (
            "[00:00:42-00:02:42] 發言者2：話。\n"
            "[00:02:42-00:04:42] 發言者2：話。\n"
        ),
        "rec": "會議紀錄。1.（科長，00:03）",
    },
    "C_合成②目標段首整分鐘": {
        "tr": "[00:02:00-00:04:42] 發言者2：話。\n",
        "rec": "會議紀錄。1.（科長，00:03）",
    },
    "D_合成①單段非整分鐘": {
        "tr": "[00:02:42-00:04:42] 發言者2：話。\n",
        "rec": "會議紀錄。1.（科長，00:03）",
    },
}
KEYS = ("changed", "kept_precision", "kept_on_start", "kept_far",
        "snapped", "snapped_speaker_mismatch", "untraceable")
out = {}
for name, c in CASES.items():
    f1, s1 = tp.snap_source_tags_to_transcript(c["rec"], c["tr"], tpl)
    f2, s2 = tp.snap_source_tags_to_transcript(f1, c["tr"], tpl)
    f3, s3 = tp.snap_source_tags_to_transcript(f2, c["tr"], tpl)
    r1, r1s = snap_rev9(c["rec"], c["tr"], tpl)
    r2, r2s = snap_rev9(r1, c["tr"], tpl)
    r3, r3s = snap_rev9(r2, c["tr"], tpl)
    out[name] = {
        "transcript": c["tr"], "record": c["rec"],
        "rev10": {
            "f1": f1, "f2": f2, "f3": f3,
            "changed1": s1["changed"], "changed2": s2["changed"], "changed3": s3["changed"],
            **{k: s1[k] for k in KEYS},
            "idempotent": f2 == f1 and f3 == f2,
        },
        "rev9sim": {
            "f1": r1, "f2": r2, "f3": r3,
            "changed1": r1s["changed"], "changed2": r2s["changed"], "changed3": r3s["changed"],
            "idempotent": r2 == r1 and r3 == r2,
        },
    }
print(json.dumps(out, ensure_ascii=False, indent=1))
print()
for name in CASES:
    r = out[name]
    a, b = r["rev10"], r["rev9sim"]
    print(f"== {name}")
    print(f"   rev10  f1={a['f1']!r}")
    print(f"          f2={a['f2']!r}  changed1={a['changed1']} changed2={a['changed2']} "
          f"kept_precision={a['kept_precision']} kept_on_start={a['kept_on_start']} snapped={a['snapped']} "
          f"kept_far={a['kept_far']} idempotent={a['idempotent']}")
    print(f"   rev9sim f1={b['f1']!r}")
    print(f"          f2={b['f2']!r}  changed1={b['changed1']} changed2={b['changed2']} idempotent={b['idempotent']}")
```

</details>

`rev10_detail.py`（A1 changed／D1 kept_far 逐筆診斷）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev10_detail.py
```

<details><summary>rev10_detail.py 全文</summary>

```python
"""rev 10 補充診斷：A1 三筆 changed 與 D1 kept_far 的逐筆落點（真函式）。"""
import sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from pathlib import Path
from backend.core import text_postprocess as tp
from backend.core.templates import get_template
REPO = Path("/Users/hsiaojohnny/dev/convert")
P = REPO / "data/cache/e2e"
tpl = get_template("section_meeting")

def tag_list(text):
    out = []
    for m in tp.SOURCE_TAG_PATTERN.finditer(text):
        tm = tp.SOURCE_TAG_TIME_PATTERN.search(m.group()[1:-1])
        out.append((m.group(), tm.group() if tm else None,
                    tp._hms_to_seconds(tm.group(1), tm.group(2), tm.group(3) or "0") if tm else None))
    return out

for name, rel in [
    ("A1", "p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c"),
    ("D1", "p3-gemma31b-d1/backend_data/outputs/0903-科務會議_ab5571ea"),
]:
    rp = P / (rel + ".md"); tpth = P / (rel + "_逐字稿.txt")
    rec, tr = rp.read_text(encoding="utf-8"), tpth.read_text(encoding="utf-8")
    segs = tp.iter_transcript_segments(tr); starts = {s for s, _, _ in segs}
    new, st = tp.snap_source_tags_to_transcript(rec, tr, tpl)
    before, after = tag_list(rec), tag_list(new)
    print(f"### {name}  stats1={st}")
    print(f"    changed 逐筆:")
    for i, (tb, ta) in enumerate(zip(before, after)):
        if tb[2] is not None and ta[2] is not None and tb[2] != ta[2]:
            print(f"      tag#{i} {tb[0]} -> {ta[0]}  on_start_before={tb[2] in starts}")
    print(f"    kept_far 候選（規則 0 未命中、有 target、位移>120s）逐筆:")
    # 重新標定 kept_far 為哪一筆：以「規則 0 未命中且有落點但未改寫」逐一檢查
    for i, tb in enumerate(before):
        if tb[2] is None: continue
        if tb[2] in starts: continue
        inner = tb[0][1:-1]; tm = tp.SOURCE_TAG_TIME_PATTERN.search(inner)
        speaker = tp._normalize_speaker_label(inner[:tm.start()].strip(tp._SPEAKER_LABEL_STRIP_CHARS))
        by_spk = {}
        for s in segs: by_spk.setdefault(tp._normalize_speaker_label(s[2]), []).append(s)
        same = by_spk.get(speaker, ())
        target = None
        if same:
            c = tp._pick_containing_segment(same, tb[2])
            if c is not None: target = c[0]
            else:
                n = min(same, key=lambda s: abs(s[0]-tb[2]))
                if abs(n[0]-tb[2]) <= tp.TAG_SNAP_TOLERANCE_SECONDS: target = n[0]
        if target is None:
            c = tp._pick_containing_segment(segs, tb[2])
            if c is not None: target = c[0]
        if target is not None and abs(target-tb[2]) > tp.TAG_SNAP_MAX_SHIFT_SECONDS and after[i][2] == tb[2]:
            print(f"      tag#{i} {tb[0]}  orig={tb[2]}s target={target}s shift={abs(target-tb[2])}s")
```

</details>

**標註總表**：[VERIFIED] rev10.A／B／C 全部數字、規則 4 程式碼位置與 sha256 綁定、rev9sim 反例鏈複現；
[UNKNOWN] 見 §rev10.D 最後一條。本節未宣稱任何既有素材品質改善。
## rev 12 增補（2026-09-23）：規則 2 nearest 跨段後退的如實界定

> **版本對照（必讀）**：本節對應 **rev 12 工作樹**——`snap_source_tags_to_transcript` 在 rev 10（規則 4）之上，
> 於 docstring／行內註解新增「規則 2 nearest 容忍**仍可跨段後退**」的如實界定（**未改任何行為分支**）。
> **與 §rev 9／§rev 10 的關係＝只限縮宣稱、不改行為**：rev 9 起「一般輸入不跨段後退」的宣稱須限縮為
> 「**已是全域真實段首的值不被搬動**」＋「規則 1／3 的落點必在時間戳所屬段落內或其段首」；
> **規則 2（nearest，容差 180 s）例外**，仍可跨段後退（v1.0 即有）。rev 10 的冪等宣稱不受影響
> （本節反例輸出二次套用 byte 相同）。**本節未宣稱任何既有素材品質改善。** 本節為檔尾追加，未改動任何既有內容。

- 量測基準：HEAD `c298cc81a12beae4d83d00def07cda73bb56d0a9`；受測實作＝工作樹 `backend/core/text_postprocess.py`
  （rev 12；sha256 `f08a873cd2526328a963847a893a506c84213de0ac7231f1988f40b7b5bf4510`）。
  規則 2 分支現址：`text_postprocess.py:972-974`（`nearest = min(...)`／容差 `TAG_SNAP_TOLERANCE_SECONDS=180`）。
- 全數以 repo 真函式 `tp.snap_source_tags_to_transcript(紀錄, 逐字稿, get_template("section_meeting"))` 實跑；
  探針腳本：`/tmp/p3_probe/rev12_nearest_probe.py`（**未進 repo**）；一律 `DATA_DIR=/tmp/probe_scratch uv run --frozen python ...`。
- **[VERIFIED]**：以下數字（吸附結果、stats、Δ、冪等、HEAD／v1.0 重建對照、log 計數）皆為本節實跑輸出，非轉抄。

### rev12.A 最小反例（兩段）與 Δ 量測

fixture（合成；最小兩段，內建於探針腳本）：

```text
[00:00:02-00:00:32] 發言者2：話。
[00:00:32-00:01:02] 發言者1：話。
```

| 案例 | 紀錄標註 | 吸附後 `f(x)` | Δ（後退秒數） | stats1 關鍵欄位 | 二次套用 byte 相同 |
|---|---|---|---|---|---|
| N1（本節最小反例） | `（發言者2，00:00:34）` | `（發言者2，00:00:02）` | **32 s** | `snapped_nearest=1／changed=1／backward_moves=1／max_backward_seconds=32` | True |
| N2 | `（發言者2，00:00:47）` | `（發言者2，00:00:02）` | **45 s** | 同 N1，`max_backward_seconds=45` | True |
| N3 | `（發言者2，00:00:57）` | `（發言者2，00:00:02）` | **55 s** | 同 N1，`max_backward_seconds=55` | True |

N1 實際 `stats1`（原樣貼出）：

```python
{'segments': 2, 'tags': 1, 'snapped': 1, 'changed': 1, 'snapped_exact': 0, 'snapped_nearest': 1, 'snapped_speaker_mismatch': 0, 'kept_on_start': 0, 'kept_precision': 0, 'backward_moves': 1, 'forward_moves': 0, 'max_backward_seconds': 32, 'kept_far': 0, 'untraceable': 0}
```

- 機理：`00:00:34` 落在**別位**發言者（發言者1）的段落 `[32,62]` 內；同發言者清單僅 `[2,32]`、不含 34
  → 規則 1 不命中；nearest `|2-34|=32 ≤ 180` → 規則 2 吸到 `00:00:02`＝**跨越段落邊界（32 s）的後退**。
  N2／N3 同型（Δ=45／55；均 ≤ `TAG_SNAP_MAX_SHIFT_SECONDS=120`，故未被 `kept_far` 擋下）。

### rev12.B 冪等：二次套用 byte 相同

| 案例 | `f(f(x))` | 二次 stats（重點） | byte 相同 |
|---|---|---|---|
| N1／N2／N3 | `會議紀錄。1.（發言者2，00:00:02）`（與 `f(x)` 相同） | `kept_on_start=1、changed=0、snapped=0` | True（三例皆然） |

- 落點 `00:00:02` 是全域真實段首 → 第二輪由**規則 0** 接住；rev 10 的冪等宣稱在此類輸入仍成立（`f³(x)` 亦相同）。

### rev12.C 非本波引入：HEAD 對照（本 repo 無 `v1.0` tag）

- [VERIFIED] `git tag -l` 實跑：僅 `v0.1.0／v2.1.3／v2.2.0／v3.1.0／v3.5.4-stable`，**無 `v1.0` tag** →
  依任務指示改用 HEAD（`c298cc8`）對照並如實說明（此為 rev 9 基線，非 P3 前 v1.0 提交）。
- [VERIFIED] HEAD 對照（`git show HEAD:backend/core/text_postprocess.py` → AST 取出函式原文 `exec`，未重寫）：
  N1／N2／N3 輸出與工作樹**逐位元組相同**；stats 除 HEAD 無 `kept_precision` 鍵外**逐欄相同**。
  N1 的 HEAD `stats1`：

  ```python
  {'segments': 2, 'tags': 1, 'snapped': 1, 'changed': 1, 'snapped_exact': 0, 'snapped_nearest': 1, 'snapped_speaker_mismatch': 0, 'kept_on_start': 0, 'backward_moves': 1, 'forward_moves': 0, 'max_backward_seconds': 32, 'kept_far': 0, 'untraceable': 0}
  ```

- [VERIFIED] 規則 2 分支原文在 HEAD 與工作樹**逐字元相同**（探針內 `assert` 與
  `rule2_block_identical_head_vs_worktree=True`）→ rev 10／rev 12 未動此分支。
- 補充（標示為**重建**、非 checkout）：v1.0 重建＝HEAD 原文機械移除規則 0 區塊（`assert count==1`）
  ＋`_pick_containing_segment` 換回 P3 前 inline 行為（沿用本檔 §1／§rev9.B 既有手法）→ 三案例亦**同輸出**。

### rev12.D 實務未觸發：三次真實 E2E log `最近段落`=0

```bash
cd /Users/hsiaojohnny/dev/convert && grep -n "最近段落" data/cache/e2e/p2-27b-fix-01/backend.log data/cache/e2e/p2-gemma31b-fix-01/backend.log data/cache/e2e/p2-moe-fix-01/backend.log
```

| 真實 E2E log | 命中行（`最近段落` 值） |
|---|---|
| `data/cache/e2e/p2-27b-fix-01/backend.log` | L273（0）／L350（0）／L425（0） |
| `data/cache/e2e/p2-gemma31b-fix-01/backend.log` | L324（0）／L413（0） |
| `data/cache/e2e/p2-moe-fix-01/backend.log` | L137（0）／L157（0）／L174（0） |
| （補充）`data/cache/e2e/p3-gemma31b-d1/backend.log` | L319（0） |

- [VERIFIED] `grep -o "最近段落 [0-9]*" … | sort | uniq -c` 實跑：全部 9 個出現值皆 `0`（27B×3、Gemma×2、MoE×3、D1×1）
  → 三次（＋D1）真實 E2E 中規則 2 nearest **從未命中**；本節界定屬**可達輸入類**（合成 fixture 可達），
  非既有素材已發生之缺陷。

### rev12.E 如實邊界

- 本節**只限縮宣稱、不改行為**：五素材（27B／Gemma／MoE／A1／D1）以**現行工作樹**重跑 §rev 10 腳本，
  `stats1` 與二次套用 byte 結果與 §rev 10 節**逐欄相同**（`/tmp/p3_probe/rev12_resnap_out.json` 對
  `/tmp/p3_probe/rev10_snap_out.json` 實跑比對）；既有素材數字不重貼，亦**未宣稱任何品質改善**。
- **[UNKNOWN]**：其他會議／其他 ASR 之「標註發言者與時間戳錯位且距離 ≤ 180 s」實際出現率；
  規則 2 與 `kept_far`／規則 4 的先後組合窮舉；此跨段後退在真實輸出的可觀察品質影響
  （三次 E2E 未觸發，無樣本可量）。
- 規則 2 反例為合成 fixture；不得外推為「真實會議曾發生」。HEAD 對照為 rev 9（非 P3 前 v1.0 提交）；
  「非本波引入」的正面證據＝規則 2 分支原文 HEAD↔工作樹逐字元相同 ＋ v1.0 重建同輸出。

### rev12.F 可重現指令（本次實際執行）

`rev12_nearest_probe.py`（§rev12.A／B／C 主腳本；含 HEAD 原文 exec 與 v1.0 重建對照）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev12_nearest_probe.py
```

<details><summary>rev12_nearest_probe.py 全文</summary>

```python
"""rev 12 增補探針：規則 2（nearest 容忍）跨段後退的如實界定。

(a) 工作樹 rev 12 實作（repo 真函式，含 rule 4；rule 2 未改）；
(b) HEAD（c298cc8，rev 9）函式原文對照：以 AST 取出 `git show HEAD:backend/core/text_postprocess.py`
    的函式原文後 exec（未重寫），驗證同輸出（「非本波引入」）；
(c) v1.0 重建（補充，非 checkout）：HEAD 函式原文「機械移除規則 0 區塊」＋
    `_pick_containing_segment` 換回 P3 前 inline 行為（本檔 §1 既有手法），
    標示為重建值。

fixture（兩段，最小）：
  [00:00:02-00:00:32] 發言者2
  [00:00:32-00:01:02] 發言者1
標註（發言者2，00:00:34／00:00:47／00:00:57）：時間戳落在別的發言者段落內、
同發言者清單無命中 → 走規則 2 nearest → 吸回 00:00:02（Δ=32／45／55 s）。
"""
import ast, inspect, json, subprocess, sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from backend.core import text_postprocess as tp
from backend.core.templates import get_template

REPO = "/Users/hsiaojohnny/dev/convert"
TR = (
    "[00:00:02-00:00:32] 發言者2：話。\n"
    "[00:00:32-00:01:02] 發言者1：話。\n"
)
FIXTURES = [
    ("N1_最小反例_Δ32s", "會議紀錄。1.（發言者2，00:00:34）", 34),
    ("N2_Δ45s",         "會議紀錄。1.（發言者2，00:00:47）", 47),
    ("N3_Δ55s",         "會議紀錄。1.（發言者2，00:00:57）", 57),
]

# --- HEAD（c298cc8）函式原文 ---
head_src = subprocess.run(
    ["git", "show", "HEAD:backend/core/text_postprocess.py"],
    cwd=REPO, capture_output=True, text=True, check=True).stdout
open("/tmp/p3_probe/rev12_head_text_postprocess.py", "w", encoding="utf-8").write(head_src)
tree = ast.parse(head_src)
fn = next(n for n in tree.body
          if isinstance(n, ast.FunctionDef) and n.name == "snap_source_tags_to_transcript")
head_fn_src = ast.get_source_segment(head_src, fn)
ns_head = dict(vars(tp))
exec(compile(head_fn_src, "<head-c298cc8>", "exec"), ns_head)
snap_head = ns_head["snap_source_tags_to_transcript"]

# --- v1.0 重建（補充）：HEAD 原文 − 規則 0 區塊 ＋ 舊 pick 策略 ---
BLOCK0 = (
    '        if any(seg[0] == seconds for seg in segments):\n'
    '            stats["kept_on_start"] += 1\n'
    '            return tag\n'
)
assert head_fn_src.count(BLOCK0) == 1, "HEAD 規則 0 區塊定位失敗"
v1_src = head_fn_src.replace(BLOCK0, "")

def old_pick(segments, seconds):  # v1.0：閉區間＋清單第一個命中段落
    for seg in segments:
        if tp._segment_contains(seg, seconds):
            return seg
    return None

ns_v1 = dict(vars(tp))
ns_v1["_pick_containing_segment"] = old_pick
exec(compile(v1_src, "<v1.0-sim>", "exec"), ns_v1)
snap_v1 = ns_v1["snap_source_tags_to_transcript"]

# --- 規則 2 區塊：HEAD 原文 vs 工作樹現行原文，逐字比對 ---
NEAREST_BLOCK = (
    "                nearest = min(same_speaker, key=lambda seg: abs(seg[0] - seconds))\n"
    "                if abs(nearest[0] - seconds) <= TAG_SNAP_TOLERANCE_SECONDS:\n"
    '                    target, status = nearest[0], "nearest"\n'
)
cur_fn_src = inspect.getsource(tp.snap_source_tags_to_transcript)
assert head_fn_src.count(NEAREST_BLOCK) == 1, "HEAD 規則 2 區塊定位失敗"
assert cur_fn_src.count(NEAREST_BLOCK) == 1, "工作樹規則 2 區塊定位失敗"

tpl = get_template("section_meeting")

def tag_seconds(text):
    out = []
    for m in tp.SOURCE_TAG_PATTERN.finditer(text):
        tm = tp.SOURCE_TAG_TIME_PATTERN.search(m.group()[1:-1])
        out.append(tp._hms_to_seconds(tm.group(1), tm.group(2), tm.group(3) or "0") if tm else None)
    return out

out = {"rule2_block_identical_head_vs_worktree": True, "fixtures": {}}
for name, rec, orig_secs in FIXTURES:
    f1, s1 = tp.snap_source_tags_to_transcript(rec, TR, tpl)
    f2, s2 = tp.snap_source_tags_to_transcript(f1, TR, tpl)
    f3, s3 = tp.snap_source_tags_to_transcript(f2, TR, tpl)
    h1, hs1 = snap_head(rec, TR, tpl)
    v1, v1s = snap_v1(rec, TR, tpl)
    out["fixtures"][name] = {
        "record_in": rec, "orig_seconds": orig_secs,
        "worktree": {"f1": f1, "f2": f2, "f3": f3, "stats1": s1, "stats2": s2,
                     "idempotent_f2_eq_f1": f2 == f1, "idempotent_f3_eq_f2": f3 == f2,
                     "delta": orig_secs - tag_seconds(f1)[0] if tag_seconds(f1)[0] is not None else None},
        "head_c298cc8": {"f1": h1, "stats1": hs1, "same_output_as_worktree": h1 == f1},
        "v1.0_sim": {"f1": v1, "stats1": v1s, "same_output_as_worktree": v1 == f1},
    }
print(json.dumps(out, ensure_ascii=False, indent=1))
print()
for name, rec, orig in FIXTURES:
    r = out["fixtures"][name]
    w = r["worktree"]
    print(f"== {name}  標註原值 {orig}s")
    print(f"   worktree f1={w['f1']!r}  Δ={w['delta']}s  冪等={w['idempotent_f2_eq_f1']}")
    print(f"   stats1={w['stats1']}")
    print(f"   HEAD(c298cc8) 同輸出={r['head_c298cc8']['same_output_as_worktree']} | "
          f"HEAD stats1={r['head_c298cc8']['stats1']}")
    print(f"   v1.0重建 同輸出={r['v1.0_sim']['same_output_as_worktree']}")
```

</details>

log 計數（§rev12.D）：

```bash
cd /Users/hsiaojohnny/dev/convert && grep -n "最近段落" data/cache/e2e/p2-27b-fix-01/backend.log data/cache/e2e/p2-gemma31b-fix-01/backend.log data/cache/e2e/p2-moe-fix-01/backend.log data/cache/e2e/p3-gemma31b-d1/backend.log
cd /Users/hsiaojohnny/dev/convert && grep -o "最近段落 [0-9]*" data/cache/e2e/p2-27b-fix-01/backend.log data/cache/e2e/p2-gemma31b-fix-01/backend.log data/cache/e2e/p2-moe-fix-01/backend.log data/cache/e2e/p3-gemma31b-d1/backend.log | sort | uniq -c
```

五素材「不改行為」對照（§rev12.E；腳本見 §rev 10.E）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev10_snap.py > /tmp/p3_probe/rev12_resnap_out.json
```

**標註總表**：[VERIFIED] rev12.A／B／C／D 全部數字與程式碼原文比對；[UNKNOWN] 見 §rev12.E。
本節未宣稱任何既有素材品質改善；未修改 repo 任何程式碼／測試／文件。
