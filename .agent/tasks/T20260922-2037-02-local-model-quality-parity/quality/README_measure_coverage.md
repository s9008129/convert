# 事實涵蓋率量尺（measure_coverage.py）

`metric_version: coverage-1.0.0`（確定性字面量尺；**不呼叫** LLM／網路／LM Studio）

補上 `scripts/e2e/measure_record_quality.py` 量不到的維度：那把尺量的是「出處標註
可查核性」（`tag_traceability`），這把尺量的是「**會議真正講過的事實，有多少被寫進
紀錄**」——雲端（Gemini）與地端（Qwen／Gemma）模型用完全相同的規則比。

## 用法

```bash
uv run python scripts/e2e/measure_coverage.py \
    --record  <受測會議紀錄.md> \
    --checklist <事實清單.json> \
    [--json-out <out.json>] [--md-out <out.md>] \
    [--label <顯示名稱>] [--transcript <逐字稿.txt>] \
    [--fuzzy-homophone] [--timestamp|--no-timestamp]
```

- 預設把 JSON（單一物件、`ensure_ascii=False, indent=2`）印到 **stdout**；
  `--json-out`／`--md-out` 另外寫檔（`--md-out` 是人類可讀版）。
- 退出碼：`0` 成功；`2` 參數或環境錯誤（檔案不存在、JSON 無法解析、紀錄是 `.docx` 等）。
- 確定性：同一組輸入 → **byte 相同**輸出；預設**不寫**時間戳，`--timestamp` 才會加
  `generated_at`（`--no-timestamp` 為顯式化的預設值）。
- `--transcript` 提供時多一段 `transcript` **觀察值**（同一組 probes 對逐字稿的涵蓋率），
  用來分辨「模型漏寫」與「清單事實根本沒出現在逐字稿（ASR 變體／清單瑕疵）」；永不當閘門。

## 事實清單 schema

```json
{
  "checklist_version": "1.0.0",
  "meeting": "0903-科務會議",
  "facts": [
    {"id": "F001", "category": "decision|action_item|number|date|name|topic|constraint",
     "tier": "core|supporting",
     "statement": "一句話事實",
     "evidence": "逐字稿時間戳＋講者＋原文片段",
     "probes": [["關鍵詞A", "關鍵詞B"], ["替代說法C"]]}
  ]
}
```

`probes` 語意：**任一 group 內的全部 token 都出現在受測紀錄 → 該事實算被涵蓋**
（group 內 AND、group 間 OR）；命中第一個 group 即停，報告記
`matched_group_index`（命中的 group index，0 起算）與 `matched_positions`
（該 group 各 token 在**正規化後紀錄**的首次出現起始索引，依 token 宣告順序，
最多前 3 個）。未涵蓋者 `reason: "no_probe_group_matched"`。

## 正規化（雙向對稱；受測紀錄與 checklist token 套同一條管線）

1. **Unicode NFKC**：全形／半形、相容字（`ＡＩ`→`AI`、全形空白→空白）。
2. **casefold**：英數大小寫折疊（`Qwen`／`QWEN` 等價）。
3. **OpenCC `s2twp`**：簡繁＋台灣用語折疊到台灣正體（`组织规程`↔`組織規程`）。
   不可用時兩側套同一 identity fallback，報告標記 `opencc_available: false` 並發警告
   （**不假裝**能折疊）。選 `s2twp` 且「兩側都轉」是刻意的：它對已是正體的文本
   冪等，避免只轉單側造成簡繁混寫 token 的假漏寫。
4. **去空白／換行**（含 Windows `\r\n`）。
5. **去標點與符號**：只保留中日韓漢字（基本區／擴充 A＋B 以上／相容表意文字）
   與 ASCII 英數字；中英文標點、括號、破折號、`、：，.-_|`、Markdown 表格管線與
   `# * >`、全形空白全數去除。

`--fuzzy-homophone`（**預設關**）：字面未命中時，改用逐字拼音近音比對
（聲母/韻母混淆組沿用 `backend.services.correction` 的台灣口音分組；依賴既有的
`pypinyin`，**未新增任何第三方依賴**）。關閉時報告 `normalization.fuzzy=false`；
開啟且可用時為 `true`、`fuzzy_mode: "pinyin_per_char_near_syllable"`；要求了但
pypinyin 不可用時會發警告並誠實停用。

## 指標定義（報告 `notes.definitions` 同文）

| 欄位 | 定義 |
| --- | --- |
| `coverage_all` | 已涵蓋事實數／事實總數（0~1） |
| `coverage_core` | core 事實涵蓋率（分母 `fact_core_total`；0 筆時 0.0） |
| `coverage_supporting` | supporting 事實涵蓋率（分母 `fact_supporting_total`；0 筆時 0.0） |
| `covered_total` / `covered_core` / `covered_supporting` | 對應的計數（避免 0 分母誤讀） |
| `missing_core_ids` / `missing_core_statements` | 未涵蓋 core 的 id／statement（清單順序、同序） |
| `missing_supporting_ids` | 未涵蓋 supporting 的 id |
| `by_category` | 每類 `total`／`covered`／`coverage`（順序＝清單首次出現順序） |
| `record_char_count` | 紀錄 Markdown 全文 `len(text)`（含換行；與 `measure_record_quality.py` 的 `char_count` 同定義） |
| `record_normalized_char_count` | 正規化後字元數（`matched_positions` 的索引基準） |
| `record_sha256` / `checklist_sha256` | 輸入原始 bytes 的 SHA-256（可追溯量的是哪一版） |
| `normalization` | 實際套用步驟、OpenCC 可用性與來源、fuzzy 狀態 |
| `warnings` | 空清單、token < 2 字、正規化後為空、tier 未知、重複 id、OpenCC／pypinyin 不可用… |
| `transcript` | 觀察值（逐字稿的涵蓋率）；未提供時 `null` |
| `facts[]` | 每條事實的 id／tier／category／statement／`covered`／`matched_group_index`／`matched_positions`／`reason` |

## 已知限制（誠實揭露）

1. **字面 ≠ 語意**：換句話說、語序重排、同義改寫可能被計為漏寫。實例：清單
   `F001` 的 probe 含「11月1」，而紀錄寫「（11/1 生效）」——事實有寫到，但
   正規化後 `111` ≠ `11月1`，會被判漏寫。**漏寫清單必須人工抽查再定案。**
2. **反向風險**：紀錄零散出現關鍵詞即算涵蓋（keyword stuffing、表格殘留可能
   造成 false positive），本尺沒有「是否成句、是否正確」的判定。
3. **不判否定與數值正確性**：「同意」與「不同意」在 token 層面同分；probe 只要求
   數字 token 出現，不檢查數值／單位是否正確。
4. `--fuzzy-homophone` 只處理同音近音錯字，不處理 ASR 漏字／斷詞錯誤。
5. **清單品質不由本尺保證**：fact 是否真的出自逐字稿、probe 是否選得準，都是清單
   產生端的責任；`--transcript` 觀察值可做第一層交叉檢查（逐字稿也對不上 → 先懷疑清單）。
6. **單次抽樣**（生成 temperature 0.7）：跨模型差異的解讀仍需搭配重跑次數。

## 實測結果（2026-09-23；清單 sha256 `cf012d1f…6ec001`，67 條＝core 28＋supporting 39）

| 受測紀錄 | `coverage_all` | `coverage_core` | `coverage_supporting` | 漏寫 core |
| --- | --- | --- | --- | --- |
| Gemma 4 31B `0903-科務會議_ac1edcec.md`（1,927 字） | 0.5672（38/67） | 0.7500（21/28） | 0.4359（17/39） | 7 條 |
| Qwen 27B `0903-科務會議_dc3c8f7a.md`（4,062 字） | 0.8209（55/67） | 0.8929（25/28） | 0.7692（30/39） | 3 條 |
| Qwen 35B-A3B（MoE）`0903-科務會議_0cc199da.md`（2,124 字） | 0.6269（42/67） | 0.8214（23/28） | 0.4872（19/39） | 5 條 |
| 逐字稿（觀察值，同一組 probes） | 0.9701–0.9851 | 0.9643–1.0000 | — | — |

三個模型共同漏掉的 core：`F025`（文康活動 800 元 × 17 人＝13600 元，三份皆無）；
`F066`（原空間移交新聞行銷處）、`F021`（下週一內稽、本科下午受檢）各漏 2/3。
人工抽查已知**偽陰性** 2 例（Gemma：`F001` 寫「11/1」而 probe 是「11月1」；
`F054` 以「處理時間未知／長期抗戰」表達「拖很久」）——故漏寫清單是**待抽查線索**，
不是定罪名單。

## 檔案位置

- `measure_coverage.py`：量尺本體（正式位置預定 `scripts/e2e/measure_coverage.py`）。
- `test_measure_coverage.py`：pytest 單元測試（正式位置預定 `tests/`）。
- `fixture_checklist.json`：8 條自建 fixture（僅自我測試用，非權威清單）。
- `coverage_*.md` / `coverage_*.json`：實測報告（`checklist` 用
  `data/cache/staging/quality/fact_checklist.json`）。

執行測試（在 repo 內跑，不落地任何追蹤檔案；`data/cache/*` 已 gitignore）：

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest data/cache/staging/coverage/test_measure_coverage.py -q -p no:cacheprovider
```
