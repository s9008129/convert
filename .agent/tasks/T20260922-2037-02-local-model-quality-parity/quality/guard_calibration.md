# 待辦召回守衛—假陽性校準（P3／R2：否定詞與 ≥3 位數字守衛）

- TASK_ID：`T20260922-2037-02-local-model-quality-parity`（P3 波、CORE-4／R23＋守衛校準）
- 日期：2026-09-23｜執行：Codex 子代理｜**未修改 repo 任何程式碼／測試**（探針置於 `/tmp/p3_probe/`）
- 受測程式：工作樹 P3 版 `backend/services/summarization.py` 之
  `_find_missing_action_keys`／`_action_key_best_lcs_ratio`／`_normalize_action_key`／
  `_extract_action_table_labels`（全部呼叫真函式；判定邏輯未重寫）。
- 守衛設定（工作樹值）：`ACTION_MATCH_MIN_LCS_RATIO=0.6`、
  `ACTION_NEGATION_TERMS=("嚴禁","禁止","不得","勿","避免","不可")`、`_ACTION_NUMBER_PATTERN=r"\d{3,}"`。

## 1. 受測物

| 紀錄 | 路徑（相對 repo） | 紀錄 md sha256 前 16 |
|---|---|---|
| Qwen 27B dense | `data/cache/e2e/p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md` | `b0ac8563c190e0c6` |
| Gemma 4 31B | `data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md` | `7d2de68463ada245` |
| Qwen 35B-A3B MoE | `data/cache/e2e/p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md` | `94d2f96d1c0960c2` |

## 2. 指定主量測：紀錄自身表格列標籤 vs 整份紀錄（假陽性＝應為 0）

呼叫：`S._find_missing_action_keys(keys, S._normalize_action_key(整份紀錄))`，
`keys = {S._normalize_action_key(label) for label in service._extract_action_table_labels(紀錄)}`。

| 紀錄 | 抽出的表格列標籤 | 其中「表頭偽標籤」`案由及承辦單位` | keys 總數 | 精確子字串命中（規則 1） | **假陽性（LCS＋守衛）** | 假陽性（僅 LCS，關兩守衛） | **守衛額外造成的假陽性** |
|---|---|---|---|---|---|---|---|
| 27B | 18 | 1 | 18 | 18 | **0** | 0 | 0 |
| Gemma | 8 | 1 | 8 | 8 | **0** | 0 | 0 |
| MoE | 11 | 1 | 11 | 11 | **0** | 0 | 0 |

判讀（重要，避免誤讀）：
- 三份紀錄的唯一表格是「決議事項辦理情形彙整表」（第一欄 `案由及承辦單位`）。
  `_extract_action_table_labels` 只排除表頭 `待辦事項`／`事項說明`，**不排除**這個表頭，
  因此每個檔案各多出 1 筆「表頭偽標籤」。此為「拿紀錄餵此函式」的儀器限制；
  真實管線餵的是萃取筆記（表頭為 `待辦事項`，會被排除）。
- **37/37 個 key 都是 haystack 的精確子字串 → 全部在「規則 1」短路**，
  守衛程式碼**根本沒被執行**。因此「守衛額外假陽性＝0」在本探針下是
  **結構性必然、不可作為守衛安全的證據**（見 §3、§5 的非空洞樣本）。

## 3. 補充探針：真實執行 log 的萃取筆記標籤（非空洞樣本）

把三場**真實 backend.log** 中被舊版判定「待辦事項遺漏」的萃取筆記標籤逐字轉錄為 keys
（這是當時真正觸發補強輪的 key 集合），餵給 P3 新判定：

| 紀錄 | log 證據（檔內行） | 舊版判遺漏 | 新判定遺漏（LCS＋守衛） | 僅 LCS | 走 LCS 路徑者之比例 |
|---|---|---|---|---|---|
| 27B | `logs/app_2026-09-22.log` 21:34:59「第 1 輪…遺漏 11 項」 | 11 | **0** | 0 | 6 筆：0.692／0.875／0.941／0.941／0.952／1.000（餘 5 筆規則 1） |
| Gemma | 同上 23:36:44「第 1 輪…遺漏 1 項」 | 1 | **0** | 0 | 規則 1 |
| MoE | 同上 21:12:57「第 1 輪…遺漏 2 項」 | 2 | **0** | 0 | 1 筆：0.720（餘 1 筆規則 1） |

- 14/14 個真實候選 key 全數判為涵蓋 → 舊版假陽性已被新判定消解（與 R23 敘述一致）。
- 其中 `了解房屋稅系統業務調整（稽查股/征收股）` 得 LCS **0.9412**，
  與程式註解記載的「實測 0.94」相符（`征收`≠`徵收` 由近似比對吸收）。
- 守衛在 1 筆被**實際評估後放行**：`嚴禁轉傳科內群組訊息至外部`（含否定詞「嚴禁」，
  ratio 0.692 ≥ 0.6，且紀錄中含「嚴禁」）→ 這是守衛「可被執行且未誤攔」的真實樣本。
- 偏差聲明：這 14 筆是**舊規則判遺漏的子集**（選擇偏差），不能用來估計新判定的整體假陽性率；
  它回答的是「舊假陽性是否消解」與「守衛是否誤攔真實候選」。

## 4. 敏感度：把標籤從紀錄逐條刪掉

「刪掉」＝把該標籤文字在紀錄中的所有原樣出現處移除（含表格列與正文若逐字相同），
再以 `_find_missing_action_keys({該 key}, normalize(刪除後紀錄))` 判定。
**逐筆結果（37 筆）**：

### 27B（18 筆）

| 標籤 | 刪除處數 | 刪除後判定 | ratio | 僅 LCS 判定 | 殘留最長重疊（診斷值） |
|---|---|---|---|---|---|
| 了解印花稅業務移轉至土地增值稅科之配合事項 | 1 | 涵蓋 | 0.6190 | 涵蓋 | 印花稅業務移轉 |
| 了解房屋稅系統業務調整（稽查股/徵收股） | 1 | **遺漏** | 0.5294 | 遺漏 | 房屋稅系統業務調整 |
| 分發文康活動禮券（扣除點心費後） | 1 | **遺漏** | 0.4286 | 遺漏 | 文康活動 |
| 嚴禁將科內群組訊息（含照片）外流至任何外部渠道 | 2 | **遺漏** | 0.4286 | 遺漏 | 科內群組訊息 |
| 抽籤決定今年文康活動主辦人 | 1 | **遺漏** | 0.5385 | 遺漏 | 文康活動主辦人 |
| 採購文康活動點心（含工程師份）並拍照佐證 | 1 | **遺漏** | 0.5556 | 遺漏 | 文康活動 |
| 關注辦公室黴味處理進度與廠商報價 | 1 | **遺漏** | 0.5625 | 遺漏 | 黴味處理進度與 |
| 預備組織改名相關系統權限及設備調整 | 1 | **遺漏** | 0.3529 | 遺漏 | 系統權限 |
| 案由及承辦單位（表頭偽標籤） | 1 | **遺漏** | 0.0000 | 遺漏 | 案 |
| 下次科務會議報告多元支付創新構想 | 1 | 涵蓋 | 0.7500 | 涵蓋 | 下次科務會議 |
| 年底選舉期間業務處理謹慎，避免捲入政治爭議 | 1 | 涵蓋 | 1.0000 | 涵蓋 | 年底選舉期間業務處理 |
| 所有同仁將Email設定為「純文字模式」 | 1 | 涵蓋 | 1.0000 | 涵蓋 | 將email設定為純文字模式 |
| 整理下週一內機檢查現場 | 1 | 涵蓋 | 0.6364 | 涵蓋 | 下週一內機檢查 |
| 盤點多元支付現狀並思考結合AI之創新方案 | 1 | 涵蓋 | 0.9500 | 涵蓋 | 盤點多元支付現狀並思考結合ai |
| 科內宣導廉政事項（拆勤、加班、採購、公務車使用） | 1 | 涵蓋 | 0.6364 | 涵蓋 | 事項拆勤、加班、採購、公務車使用 |
| 視察索取資料時配合提供 | 1 | 涵蓋 | 1.0000 | 涵蓋 | 視察索取資料時 |
| 詢問現金發放程序是否麻煩（決定發禮券或現金） | 1 | 涵蓋 | 0.7000 | 涵蓋 | 問現金發放程序是否麻煩 |
| 配合土地稅課重新列印損毀土地卡 | 1 | 涵蓋 | 0.6000 | 涵蓋 | 土地稅課 |

### Gemma（8 筆）

| 標籤 | 刪除處數 | 刪除後判定 | ratio | 僅 LCS 判定 | 殘留最長重疊（診斷值） |
|---|---|---|---|---|---|
| 思考資料庫 AI 運用創新方案（相關承辦人） | 1 | 涵蓋 | 0.7222 | 涵蓋 | 創新方案相關承辦人 |
| 瑞里發放活動之現場執行及宣導單發放（相關承辦人） | 1 | 涵蓋 | 0.9545 | 涵蓋 | 瑞里發放活動之現場執行 |
| 盤點多元支付現有題目並思考 AI 創新方案（相關承辦人） | 1 | 涵蓋 | 0.7083 | 涵蓋 | 創新方案相關承辦人 |
| 準備下週一（下午）內稽相關文件與現場環境（全體同仁） | 1 | **遺漏** | 0.5909 | 遺漏 | 下週一下午 |
| 詢問文康活動發放現金之行政程序是否可行（發言者3） | 1 | **遺漏** | 0.5652 | 遺漏 | 之行政程序是否可行 |
| 配合組織變更調整系統權限與名稱（資管股及相關同仁） | 1 | **遺漏** | 0.4783 | 遺漏 | 組織變更 |
| 配合重新列印損毀之土地稅卡（相關承辦人） | 1 | **遺漏** | 0.3889 | 遺漏 | 配合重新列印 |
| 案由及承辦單位（表頭偽標籤） | 1 | **遺漏** | 0.4286 | 遺漏 | 承辦 |

### MoE（11 筆）

| 標籤 | 刪除處數 | 刪除後判定 | ratio | 僅 LCS 判定 | 殘留最長重疊（診斷值） |
|---|---|---|---|---|---|
| 準備下週一下午之內機檢查，將物品歸位 | 1 | 涵蓋 | 0.8235 | 涵蓋 | 下週一下午 |
| 盤點目前多元支付服務現況，思考與AI相關之創新服務方案 | 1 | 涵蓋 | 0.6538 | 涵蓋 | 現況思考與ai相關 |
| 辦理詐騙防制宣導（排定10月14日），每人報3件，涵蓋瑞里、瑞吉等偏遠地區，注意老人行動不便問題 | 1 | 涵蓋 | 0.6512 | 涵蓋 | 瑞里、瑞吉等偏遠地區 |
| 嚴禁將科內群組訊息、照片外流至外部群組或平台（如LB），列為會議記錄並嚴懲 | 1 | **遺漏** | 0.5588 | 遺漏 | 列為會議記錄 |
| 查詢並確認文康活動發放「現金」之財務程序（是否需預借、簽收流程） | 1 | **遺漏** | 0.2857 | 遺漏 | 確認文康活動 |
| 確認文康活動形式（外出用餐或室內點心/便當+拍照），並確認現金發放之程序（若採現金） | 1 | **遺漏** | 0.4167 | 遺漏 | 並確認現金發放之程序 |
| 設定Email為「文字模式」，勿亂點假Email連結或檔案，防範社交工程攻擊 | 1 | **遺漏** | 0.5294 | 遺漏 | 為文字模式勿亂點 |
| 評估新辦公室搬遷時程，評估淹水處理進度及黴味對健康影響，做好長期在原辦公室工作準備 | 1 | **遺漏** | 0.3846 | 遺漏 | 做好長期在原辦公室 |
| 配合土地稅科整理出需重新列印之土地稅卡清單，並協助重新列印 | 1 | **遺漏** | 0.5714 | 遺漏 | 土地稅科整理出 |
| 配合組織規程與編制表調整（11月1日生效），注意系統權限、系統名稱變更（地價稅科、土地增值稅科、使用牌照稅科、煙酒及稅務管理科、稽徵股、徵收股等）及業務移撥（印花稅移土地增值稅科、檢舉業務移煙酒及稅管科） | 1 | **遺漏** | 0.5053 | 遺漏 | 注意系統權限、系統名稱 |
| 案由及承辦單位（表頭偽標籤） | 1 | **遺漏** | 0.2857 | 遺漏 | 承辦 |

**讀法與如實邊界**
- 21/37（真實標籤 18/34）在刪除後**立即**判遺漏；16/37 仍判「涵蓋」。
- 16 筆「仍判涵蓋」**不是守衛漏判**：每一筆的正文都還有改寫殘留
  （ratio 0.60–1.00，殘留重疊已列出；例：`年底選舉期間業務處理謹慎，避免捲入政治爭議`
  在正文另有 `年底選舉期間，業務處理需謹慎，避免捲入政治爭議`）→
  刪除並未真正移除資訊，判「涵蓋」與內容一致；
  且 **16/16 在「僅 LCS」下判定完全相同** → 與守衛無關。
- 反之，18 筆「刪除即判遺漏」是真遺漏／半遺漏的攔截，亦與守衛無關（ratio 已 <0.6）。
- 「保守方向的代價」確實存在但**不是守衛造成**：例 `嚴禁將科內群組訊息（含照片）外流至任何外部渠道`
  刪除兩處（表格＋正文逐字句）後 ratio 0.4286 判遺漏，但正文另有強改寫句
  （`科內群組訊息屬公共訊息，嚴禁轉傳至外部…`，第 59 行）→ 會多觸發一輪補強；
  此屬**字面量尺（LCS 0.6 門檻）**的取捨，與兩條守衛無關（僅 LCS 判決相同）。
- 表頭偽標籤 3 筆全數判遺漏（紀錄中不存在其正文）→ 對 FP 量測無影響，但提醒此儀器限制。

**強制刪除（嚴格版敏感度）**：反覆刪除「標籤中仍原樣出現在紀錄裡的最長子字串」直到判遺漏
（判定仍用真函式；刪除是診斷工具）：
| 紀錄 | 結果 | 輪數（min/max/mean） |
|---|---|---|
| 27B | **18/18 判遺漏** | 1/3/1.9 |
| Gemma | **8/8 判遺漏** | 1/3/1.6 |
| MoE | **11/11 判遺漏** | 1/3/1.8 |

→ 標籤與其內容確實從文件中消失時，**一律**觸發遺漏（守衛沒有讓真遺漏漏掉）。

## 5. 守衛攔截力的定向量測（tamper／微觀探針）

### 5.1 Tamper：把真實標籤內的否定詞從紀錄中抽掉（其餘文字原樣保留）

| 紀錄 | 標籤（截短） | 移除詞 | LCS 比例 | LCS＋守衛判遺漏 | 僅 LCS 判遺漏 |
|---|---|---|---|---|---|
| 27B | 嚴禁將科內群組訊息（含照片）外流至任何外部渠道 | 嚴禁 | 0.9048 | **是** | 否（誤判涵蓋） |
| 27B | 年底選舉期間業務處理謹慎，避免捲入政治爭議 | 避免 | 0.9000 | **是** | 否 |
| MoE | 嚴禁將科內群組訊息、照片外流至外部群組或平台（如LB）… | 嚴禁 | 0.9412 | **是** | 否 |
| MoE | 設定Email為「文字模式」，勿亂點假Email連結或檔案… | 勿 | 0.9706 | **是** | 否 |

→ 4/4：LCS 已達 0.90–0.97 會被舊近似判定誤判「涵蓋」，加入守衛後改判遺漏
（皆為**真語意缺失**，非假陽性）。Gemma 的真實標籤不含否定詞 → 無此情境。

### 5.2 微觀探針（合成案例；僅驗守衛機制與其字面性風險）

| 情境 | LCS | 規則 1 | LCS＋守衛 | 僅 LCS | 解讀 |
|---|---|---|---|---|---|
| 數字缺失：key 含 `13600`，紀錄寫成「約一萬多元」（依 plan §8.3 引用的真實缺口樣態） | 0.6316 | — | **遺漏** | 涵蓋 | 數字守衛攔截（預期方向） |
| 千分位等價：紀錄 `13,600` | — | 命中 | 涵蓋 | 涵蓋 | 對稱折疊（無假陽性） |
| 全形數字：紀錄 `１３６００` | — | 命中 | 涵蓋 | 涵蓋 | NFKC 折疊（無假陽性） |
| 數字原樣 `13600` | — | 命中 | 涵蓋 | 涵蓋 | — |
| 否定同義替換：key 含「嚴禁」，紀錄寫「禁止」 | 0.9375 | — | **遺漏** | 涵蓋 | **守衛的字面性假陽性風險**（語意未丟，但同義詞不匹配） |

## 6. 守衛額外造成的假陽性—總表

| 情境 | 樣本 | 「LCS＋守衛」vs「僅 LCS」判決差異筆數 | 其中真語意缺失（守衛正確攔截） | 其中假陽性風險（守衛誤攔） |
|---|---|---|---|---|
| 指定主探針（紀錄全檔當 haystack） | 37 keys | **0** | 0 | 0（但守衛未執行，屬結構性 0） |
| 真實 log 候選 keys | 14 keys | **0** | 0 | 0（1 筆經守衛評估後放行） |
| 逐條刪除 | 37 keys | **0** | 0 | 0（16 筆涵蓋判定與僅 LCS 相同） |
| tamper（抽掉否定詞） | 4 keys | **4**（涵蓋→遺漏） | 4 | 0 |
| 微觀探針（合成） | 5 案例 | **2** | 1（數字缺失） | 1（否定同義替換） |

**直接回答本項任務**：在三份真實紀錄上，兩條守衛額外造成的假陽性＝**0 筆**
（主探針為結構性 0；非空洞樣本＝14 個 log keys 與 16 個「刪除後仍判涵蓋」的比率 ≥0.6 案例，
守衛評估後全數放行）。守衛唯一被證實的誤攔風險是**字面性**：
否定詞同義替換（嚴禁→禁止 等）與數字改寫格式不在折疊範圍內（後者已由 NFKC／千分位折疊緩解，
前者無對策）。此風險在本批真實材料**未被觸發**（[UNKNOWN] 於其他語料）。

## 7. 結論與限制

**結論**
1. 指定主量測：三份紀錄的表格列標籤（34 筆真實＋3 筆表頭偽標籤）在「整份紀錄當 haystack」下，
   假陽性 0 筆；LCS 開／關兩情境差異 0 筆。**惟 37/37 走規則 1 短路，此 0 不代表守衛安全。**
2. 非空洞樣本：14 個真實 log 候選 key 全數判涵蓋（含 0.69–1.00 的 LCS 路徑），
   守衛在其中的 1 筆被評估且放行；守衛額外假陽性 0 筆 → **R23 收斂未被守衛破壞**。
3. 敏感度：逐條刪除→21/37 立即判遺漏；嚴格刪除→37/37 判遺漏 → 真遺漏必觸發。
4. 守衛攔截力：4 筆真實 tamper＋1 筆微觀數字缺失，在 LCS 0.63–0.97 下仍被判遺漏
   （僅 LCS 全部誤判涵蓋）→ 守衛不是死碼，方向「往更嚴」成立；代價是 §5.2 的字面性誤攔。

**限制（不得外推）**
- 單一會議、僅 3 份紀錄、真實標籤 34 筆；無統計效力。
- 紀錄自身表格當 keys 的設計使主探針幾乎只測到「規則 1」；真實管線的 keys 來自萃取筆記
  （本報告以 log 轉錄補上樣本，但該樣本有選擇偏差）。
- 真實標籤中含 ≥3 位數字者為 **0 筆** → 數字守衛在真實文件上的假陽性率
  **[UNKNOWN]**；僅能用合成微觀探針驗機制（1 攔截、3 無 FP）。
- 「殘留最長重疊」與「ratio」皆為字面量尺；同義改寫（例如以「外流」對「轉傳」）
  的涵蓋判定仍可能偏嚴或偏寬，需人工複核。
- 表頭偽標籤（`案由及承辦單位`）是「把紀錄餵給列標籤抽取函式」的儀器產物，
  非產品缺陷（真實管線的萃取筆記表頭為 `待辦事項`，會被排除）。

## 8. 附錄：可重現指令

### A. 主探針（假陽性＋僅 LCS 對照＋tamper）

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python - <<'PY'
import re, sys; sys.path.insert(0, ".")
from pathlib import Path
from backend.services.summarization import SummarizationService as S

P = Path("data/cache/e2e")
RECS = [
    ("27B",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md"),
    ("Gemma", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md"),
    ("MoE",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md"),
]
NEVER = re.compile(r"(?!x)x")

def guards_off(keys, haystack):
    t, p = S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN
    S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = (), NEVER
    try:
        return S._find_missing_action_keys(keys, haystack)
    finally:
        S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = t, p

svc = S()
for name, path in RECS:
    rec = path.read_text(encoding="utf-8")
    labels = svc._extract_action_table_labels(rec)
    keys = {S._normalize_action_key(l) for l in labels} - {""}
    hs = S._normalize_action_key(rec)
    missing_g, _ = S._find_missing_action_keys(keys, hs)
    missing_l, _ = guards_off(keys, hs)
    print(name, "| labels", len(labels), "| keys", len(keys),
          "| exact-substring", sum(1 for k in keys if k in hs),
          "| missing guards", len(missing_g), "| LCS-only", len(missing_l),
          "| guard-extra", sorted(missing_g - missing_l))
    for k in sorted(keys):
        for term in [t for t in S.ACTION_NEGATION_TERMS if t in k and t in hs]:
            hs2 = S._normalize_action_key(rec.replace(term, ""))
            mg, r2 = S._find_missing_action_keys({k}, hs2)
            ml, _ = guards_off({k}, hs2)
            print("   tamper", k[:20], "移除", term, "ratio %.4f" % r2.get(k, 0),
                  "守衛判遺漏", k in mg, "LCS-only", k in ml)
PY
```

### B. 刪除敏感度（逐條＋嚴格）＋ log 真實 keys

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python - <<'PY'
import sys; sys.path.insert(0, ".")
from pathlib import Path
from backend.services.summarization import SummarizationService as S

P = Path("data/cache/e2e")
RECS = [
    ("27B",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md"),
    ("Gemma", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md"),
    ("MoE",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md"),
]
LOG_KEYS = {
    "27B": ["了解印花稅業務移轉至土地增值稅科的配合事項", "了解房屋稅系統業務調整（稽查股/征收股）",
            "分發文康活動禮券（扣除點心費後）", "嚴禁轉傳科內群組訊息至外部", "抽籤決定今年文康活動主辦人",
            "採購文康活動點心（含工程師份）並拍照佐證", "整理下週一內機檢查現場",
            "盤點多元支付現狀並思考AI創新方案", "詢問現金發放程序是否麻煩（決定發禮券或現金）",
            "追蹤辦公室黴味處理進度與廠商報價", "預備組織改名相關系統權限、設備調整"],
    "Gemma": ["瑞里發放活動之現場執行（含宣導單發放）"],
    "MoE": ["注意組織調整後之系統權限、系統名稱變更（地價稅科、土地增值稅科、使用牌照稅科、煙酒及稅務管理科、稽徵股、徵收股等）及業務移撥（印花稅移土地增值稅科、檢舉業務移煙酒及稅管科）",
            "準備下週一下午之內機檢查，將物品歸位"],
}

def lcs_sub(a, b):
    best = ""
    for i in range(len(a)):
        for j in range(i + len(best) + 1, len(a) + 1):
            if a[i:j] in b: best = a[i:j]
            else: break
    return best

def strict_remove(record, key):
    text = record
    for round_index in range(1, 13):
        if key in S._find_missing_action_keys({key}, S._normalize_action_key(text))[0]:
            return True, round_index
        best = ""
        for i in range(len(key)):
            for j in range(i + len(best) + 1, len(key) + 1):
                if key[i:j] in text: best = key[i:j]
                else: break
        if len(best) < 3:
            return False, round_index
        text = text.replace(best, "")
    return False, 12

svc = S()
for name, path in RECS:
    rec = path.read_text(encoding="utf-8")
    labels = svc._extract_action_table_labels(rec)
    flagged = strict_ok = total = 0
    for label in labels:
        key = S._normalize_action_key(label)
        if not key: continue
        total += 1
        hs = S._normalize_action_key(rec.replace(label, ""))
        if key in S._find_missing_action_keys({key}, hs)[0]:
            flagged += 1
        else:
            print("   刪除後仍判涵蓋:", label[:34], "ratio",
                  round(S._find_missing_action_keys({key}, hs)[1].get(key, 0), 4),
                  "殘留重疊", lcs_sub(key, hs))
        strict_ok += bool(strict_remove(rec, key)[0])
    print(name, "| 刪除後立即判遺漏", flagged, "/", total, "| strict 判遺漏", strict_ok, "/", total)
    lk = {S._normalize_action_key(l) for l in LOG_KEYS[name]}
    mg, ratios = S._find_missing_action_keys(lk, S._normalize_action_key(rec))
    print("   log 真實 keys", len(lk), "→ 遺漏", sorted(mg) or 0, "| ratio", {k[:12]: round(v, 3) for k, v in ratios.items()})
PY
```

### C. 微觀探針（數字／否定守衛機制；合成案例）

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python - <<'PY'
import re, sys; sys.path.insert(0, ".")
from backend.services.summarization import SummarizationService as S
NEVER = re.compile(r"(?!x)x")

def guards_off(keys, hs):
    t, p = S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN
    S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = (), NEVER
    try: return S._find_missing_action_keys(keys, hs)
    finally: S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = t, p

for label, key_text, hay in [
    ("數字缺失", "查詢文康活動經費13600元之核銷程序", "請確認文康活動經費約一萬多元之核銷程序"),
    ("千分位",   "查詢文康活動經費13600元之核銷程序", "查詢文康活動經費13,600元之核銷程序"),
    ("全形",     "查詢文康活動經費13600元之核銷程序", "查詢文康活動經費１３６００元之核銷程序"),
    ("原樣",     "查詢文康活動經費13600元之核銷程序", "查詢文康活動經費13600元之核銷程序"),
    ("否定同義", "嚴禁將科內群組訊息外流至外部渠道",   "禁止將科內群組訊息外流至外部渠道"),
]:
    key = S._normalize_action_key(key_text); hs = S._normalize_action_key(hay)
    mg, ratios = S._find_missing_action_keys({key}, hs)
    ml, _ = guards_off({key}, hs)
    print(label, "| 規則1:", key in hs, "| LCS %.4f" % ratios.get(key, 0),
          "| 守衛判遺漏", key in mg, "| LCS-only", key in ml)
PY
```

輔助探針：`/tmp/p3_probe/guard_probe.py`（FP／刪除／tamper 的 JSON 版）、
`/tmp/p3_probe/guard_probe2.py`（嚴格刪除＋微觀）、`/tmp/p3_probe/logkeys_probe.py`（log keys）、
`/tmp/p3_probe/residual_check.py`（殘留重疊診斷）。

## rev 9 修訂版量測（2026-09-23）

> **版本對照（必讀）**：本節全部數字對應 **rev 9 實作**——`_action_key_best_window` 回傳（比例, 視窗文字）；
> 數字樣式由 `\d{3,}` 放寬為 **`\d{2,}`**；守衛改為**局部範圍**＝「最佳視窗 ∩ 最相近一句話
> （`_split_record_sentences`）」，**兩者都必須含 token 才放行**。
> **上方 §1–§8 的數字對應 rev 8 實作（全域檢查＋`\d{3,}`），勿與本節混用**；rev 8 的
> 「守衛額外假陽性＝0」需以本節的條件重述（rev 8 的 0 是「整份紀錄有沒有出現」的 0）。
> 本節為**追加**，未改動任何舊數字。

### rev9.0 實作核對（以 `git diff backend/services/summarization.py` 實際核對）

- `ACTION_NEGATION_TERMS = ("嚴禁", "禁止", "不得", "勿", "避免", "不可")`（未變）；`_ACTION_NUMBER_PATTERN = re.compile(r"\d{2,}")`（原 `\d{3,}`）。
- `_action_key_best_window(key, haystack, bigram_index)` 回傳 `(ratio, window)`；`window`＝以標籤 bigram 反推位置的連續區段（長度＝標籤長+4）。
- `_find_missing_action_keys(cls, expected_actions, normalized_summary, local_sentences=None)`：
  - `key in normalized_summary`（規則 1）→ 涵蓋（仍短路守衛）；
  - 否則取滑窗 ratio；`ratio < 0.6` → 遺漏；`>= 0.6` 時，對 `local_texts = [最佳視窗] + [最相近一句話（若提供）]`，**任一文字缺**標籤中的否定詞或 `\d{2,}` token → 判遺漏；
  - `local_sentences=None` 時退化為只檢查視窗。
- 管線端以 `self._split_record_sentences(cleaned)` 傳入（本節探針用同款呼叫）。

### rev9.1 主探針（37 keys）＋ log keys（14）重跑

呼叫：`S._find_missing_action_keys(keys, S._normalize_action_key(紀錄全文), local_sentences=S._split_record_sentences(紀錄全文))`。

| 紀錄 | 表格列標籤 | keys | 規則1子字串命中 | 假陽性（rev9 守衛） | 假陽性（僅視窗） | 假陽性（僅 LCS） | **守衛額外假陽性** |
|---|---|---|---|---|---|---|---|
| 27B | 18 | 18 | 18 | **0** | 0 | 0 | 0 |
| Gemma | 8 | 8 | 8 | **0** | 0 | 0 | 0 |
| MoE | 11 | 11 | 11 | **0** | 0 | 0 | 0 |

- **37/37 仍為 rule-1 精確子字串**（新正規化 NFKC／OpenCC 後）→ 守衛根本未執行；此 0 是**結構性 0**（同 rev 8 §2 的註記），不可當守衛安全的證據。
- 「若未命中規則 1 會進入守衛」的真實標籤：27B 2 筆（含否定詞）、MoE 4 筆（2 筆否定詞＋2 筆含 ≥2 位數字：`11月1日`／`10月14日`）；因 rule-1 短路，全數未經守衛。
- log keys（14 筆真實舊判遺漏候選，同 rev 8 §3）：重跑後 **14/14 判涵蓋**、**守衛額外假陽性 0**。
  其中唯一進入 LCS 路徑且含守衛 token 的是 `嚴禁轉傳科內群組訊息至外部`（ratio **0.6923**）：
  實測「嚴禁」在**最佳視窗**與**最相近句**皆存在（`term_in_window=True`、`term_in_nearest_sentence=True`）
  → 守衛**實際被執行且放行**（非假陽性）。其餘 5 筆 LCS 路徑 key 無守衛 token，與守衛無關。

### rev9.2 審查者反例（i）：否定詞在別處、目標子句反轉 → 判遺漏 ✅

構造（`rev9_guard2.py`）：27B 紀錄中**兩處**原樣句 `嚴禁將科內群組訊息（含照片）外流至任何外部渠道`
改成 `得將科內群組訊息（含照片）外流至任何外部渠道`（目標子句語意反轉；其餘「嚴禁」4 次仍在紀錄中）。

| 判讀路徑 | 結果 |
|---|---|
| LCS 比例 | **0.9048**（≥ 0.6，舊近似會放行） |
| **rev9 守衛（視窗 ∩ 最相近句）** | **判遺漏**（兩個局部文字皆缺「嚴禁」） |
| 退化版（只查視窗） | 判遺漏 |
| 僅 LCS（關兩守衛） | 判涵蓋（洗白） |
| 舊 round-1 守衛等價式（整份紀錄有沒有「嚴禁」） | 不判遺漏（洗白）→ rev9 修正有效 |

- 更難變體（同句前段 `嚴禁同仁遲到，` ＋反轉後子句）：實測**仍判遺漏**（最佳視窗落在反轉子句處、未含「嚴禁」）。
- **殘留邊界（誠實揭露）**：若「嚴禁」離反轉子句**極近**，會被最佳視窗（≈標籤長+4 字元）吸收 → 放行。
  adversarial 掃描（`rev9_adversarial.py`）：`嚴禁`＋`啊`×g＋反轉句 → g=0–11 判涵蓋、**g≥12 判遺漏**；
  `嚴禁遲到，`＋`啊`×g＋反轉句 → g=0–9 判涵蓋、**g≥10 判遺漏**。
  最小重現：`嚴禁遲到，得將科內群組訊息（含照片）外流至任何外部渠道。` → 判**涵蓋**（gap=0）。
  此殘留**嚴格小於**舊版（舊版：嚴禁出現在文件任何位置即放行）；方向仍是「往更嚴」，但「緊鄰而未約束」的否定詞仍可洗白 → 列為已知限制。

### rev9.3 審查者反例（ii）：`9月30日` → `9月20日` → 判遺漏 ✅

| 判讀 | 值 |
|---|---|
| 比例 | 0.9375；`rule1=False` |
| rev9 守衛 | **判遺漏**（缺數字 token `30`） |
| 僅 LCS | 判涵蓋 |
| 對照（日期原樣） | rule-1 命中、涵蓋 |

### rev9.4 tamper 4 例（沿用 rev 8 的四筆真實標籤）

全域移除標籤中的否定詞後：4/4 **判遺漏**（ratio 0.9000／0.9000／0.9412／0.9706）；僅 LCS 全部放行 → 守衛攔截力在新局部規則下保留。

### rev9.5 刪除敏感度（37 筆真實標籤；逐條刪除）

27B 8/18、Gemma 5/8、MoE 8/11 → **立即判遺漏 21/37**，與「僅 LCS」完全相同（無守衛差異）；
16 筆仍判涵蓋者皆有正文改寫殘留（ratio 0.60–1.00，清單同 rev 8 §4）。→ 守衛未讓真遺漏漏掉。

### rev9.6 額外假陽性總表（含真實材料）

| 場景 | 樣本數 | 「LCS↔rev9 守衛」判決差異 | 其中真缺失（正確攔截） | 其中**新增假陽性** |
|---|---|---|---|---|
| 主探針（紀錄全檔當 haystack） | 37 keys | 0 | 0 | **0（結構性）** |
| 真實 log 候選 keys | 14 keys | 0 | 0 | **0**（1 筆守衛實跑後放行） |
| 逐條刪除 | 37 keys | 0 | 0 | **0** |
| 審查者反例 (i)/(ii) | 2 | 2 | 2 | 0 |
| tamper | 4 | 4 | 4 | 0 |
| 微觀合成探針 | 6 | 3 | 2 | **1**（否定同義替換：`嚴禁`→`禁止`，ratio 0.9375 誤攔；字面性風險） |

**答案**：在三份真實紀錄＋14 個真實 log keys 上，rev 9 兩條守衛**額外造成的假陽性＝0 筆**。
已知代價與界線：
- 否定同義替換（嚴禁→禁止等）仍誤攔（字面量尺；同 rev 8 §5.2）；
- `\d{2,}` 放寬後，2 位數日期／數量也受守衛——本批真實 key 無此類進入守衛路徑者，真實 FP 率 **[UNKNOWN]**；
- 微觀 6 例中：數字缺失（`13600` vs「約一萬多元」，LCS 0.6316）與 2 位數日期缺失（LCS 0.9231）皆正確攔截；千分位／全形／原樣皆 rule-1 命中無 FP。

### rev9.7 與舊版（rev 8）差異摘要

1. 主探針與 log keys 的「假陽性＝0」不變，但 rev 9 的驗證**多了一條真實材料放行樣本**（`嚴禁轉傳…`，ratio 0.6923，守衛實跑後放行）。
2. 新增覆蓋：審查者兩反例（(i) 反轉＋別處否定詞、(ii) 2 位數日期）在 rev 9 皆**判遺漏**（rev 8 皆洗白）。
3. 新增已知殘留：緊鄰反轉子句的否定詞仍被窗∩句放行（gap ≤ ~標籤長+4）；舊版是任意距離皆放行。
4. 敏感度、tamper 結論不變。

### rev9.8 可重現指令（本次實際執行）

`rev9_guard.py`（主探針＋log keys＋僅 LCS／僅視窗對照）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev9_guard.py
```

<details><summary>rev9_guard.py 全文</summary>

```python
"""rev9：守衛（局部範圍＋\d{2,}）假陽性與鑑別力校準。判定全部呼叫真函式。"""
import json, re, sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from pathlib import Path
from backend.services.summarization import SummarizationService as S

P = Path("/Users/hsiaojohnny/dev/convert/data/cache/e2e")
RECS = [
    ("27B",   P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md"),
    ("Gemma", P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md"),
    ("MoE",   P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md"),
]
LOG_KEYS = {
    "27B": ["了解印花稅業務移轉至土地增值稅科的配合事項", "了解房屋稅系統業務調整（稽查股/征收股）",
            "分發文康活動禮券（扣除點心費後）", "嚴禁轉傳科內群組訊息至外部", "抽籤決定今年文康活動主辦人",
            "採購文康活動點心（含工程師份）並拍照佐證", "整理下週一內機檢查現場",
            "盤點多元支付現狀並思考AI創新方案", "詢問現金發放程序是否麻煩（決定發禮券或現金）",
            "追蹤辦公室黴味處理進度與廠商報價", "預備組織改名相關系統權限、設備調整"],
    "Gemma": ["瑞里發放活動之現場執行（含宣導單發放）"],
    "MoE": ["注意組織調整後之系統權限、系統名稱變更（地價稅科、土地增值稅科、使用牌照稅科、煙酒及稅務管理科、稽徵股、徵收股等）及業務移撥（印花稅移土地增值稅科、檢舉業務移煙酒及稅管科）",
            "準備下週一下午之內機檢查，將物品歸位"],
}
NEVER = re.compile(r"(?!x)x")
svc = S()

def guards_off(keys, hs, local_sentences=None):
    t, p = S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN
    S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = (), NEVER
    try:
        return S._find_missing_action_keys(keys, hs, local_sentences=local_sentences)
    finally:
        S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = t, p

out = {}
for name, path in RECS:
    rec = path.read_text(encoding="utf-8")
    labels = svc._extract_action_table_labels(rec)
    keys = {S._normalize_action_key(l) for l in labels} - {""}
    hs = S._normalize_action_key(rec)
    sents = S._split_record_sentences(rec)
    miss_new, ratios_new = S._find_missing_action_keys(keys, hs, local_sentences=sents)
    miss_win, _ = S._find_missing_action_keys(keys, hs)                      # 只檢查視窗（退化解）
    miss_off, ratios_off = guards_off(keys, hs, local_sentences=sents)       # 關兩守衛
    lk = {S._normalize_action_key(l) for l in LOG_KEYS[name]}
    miss_log, ratios_log = S._find_missing_action_keys(lk, hs, local_sentences=sents)
    miss_log_off, _ = guards_off(lk, hs, local_sentences=sents)
    out[name] = {
        "labels": len(labels), "keys": len(keys),
        "exact_substring_keys": sum(1 for k in keys if k in hs),
        "missing_new": sorted(miss_new), "missing_window_only": sorted(miss_win),
        "missing_lcs_only": sorted(miss_off),
        "guard_extra_fp": sorted(miss_new - miss_off),
        "log_keys": len(lk), "log_missing_new": sorted(miss_log),
        "log_missing_lcs_only": sorted(miss_log_off),
        "log_guard_extra_fp": sorted(miss_log - miss_log_off),
        "log_ratios": {k[:14]: round(v, 4) for k, v in ratios_log.items()},
        "keys_need_guard_eval": sorted(k for k in keys if k not in hs),
    }
print(json.dumps(out, ensure_ascii=False, indent=1))
```

</details>

`rev9_guard2.py`（審查者兩反例＋tamper＋刪除＋守衛執行診斷）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev9_guard2.py
```

<details><summary>rev9_guard2.py 全文</summary>

```python
"""rev9 守衛：審查者兩反例、tamper、刪除敏感度、守衛執行診斷（修訂版）。"""
import json, re, sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from pathlib import Path
from backend.services.summarization import SummarizationService as S

P = Path("/Users/hsiaojohnny/dev/convert/data/cache/e2e")
R27 = P/"p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md"
RGE = P/"p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md"
RMO = P/"p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da.md"
NEVER = re.compile(r"(?!x)x")
svc = S()

def guards_off(keys, hs, local_sentences=None):
    t, p = S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN
    S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = (), NEVER
    try:
        return S._find_missing_action_keys(keys, hs, local_sentences=local_sentences)
    finally:
        S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = t, p

def bigram_index_of(hs):
    idx = {}
    for i in range(len(hs) - 1):
        idx.setdefault(hs[i:i+2], []).append(i)
    return idx

def probe(label, key_text, hay_text, note=""):
    key = S._normalize_action_key(key_text); hs = S._normalize_action_key(hay_text)
    sents = S._split_record_sentences(hay_text)
    mg, ratios = S._find_missing_action_keys({key}, hs, local_sentences=sents)
    ml, _ = guards_off({key}, hs, local_sentences=sents)
    mgw, ratios_w = S._find_missing_action_keys({key}, hs)  # 只檢查視窗（退化解）
    ratio = ratios.get(key, ratios_w.get(key, 0.0))
    # 舊（round-1）守衛等價式：只查「整份紀錄有沒有出現」——僅作對照
    old_guard_missing = (ratio < S.ACTION_MATCH_MIN_LCS_RATIO) or any(
        t in key and t not in hs for t in S.ACTION_NEGATION_TERMS
    ) or any(tok in key and tok not in hs for tok in S._ACTION_NUMBER_PATTERN.findall(key))
    return {
        "case": label, "note": note, "ratio": round(ratio, 4),
        "rule1_substring": key in hs,
        "missing_new_local": key in mg, "missing_new_window_only": key in mgw,
        "missing_lcs_only": key in ml,
        "missing_old_round1_guard_equiv": old_guard_missing,
    }

out = {"micro": [], "tamper": [], "deletion": {}, "guard_eval_diag": []}

# ---- 審查者反例 (i)：目標句反轉（兩處原樣句都改），他處仍有「嚴禁」 ----
rec = R27.read_text(encoding="utf-8")
PHRASE = "嚴禁將科內群組訊息（含照片）外流至任何外部渠道"
assert rec.count(PHRASE) == 2, rec.count(PHRASE)
rec_rev = rec.replace(PHRASE, "得" + PHRASE[2:])
out["micro"].append({
    **probe("(i)反轉：目標句 嚴禁→得（兩處原樣句）", PHRASE, rec_rev,
            f"其餘嚴禁次數 {S._normalize_action_key(rec_rev).count('嚴禁')}（原 {S._normalize_action_key(rec).count('嚴禁')}）"),
})
# (i-c) 更難變體：同一句內他子句保留「嚴禁」（逗號分隔，切句器不切）
rec_rev2 = rec_rev.replace("1. 得將科內群組訊息", "1. 嚴禁同仁遲到，得將科內群組訊息", 1)
out["micro"].append({
    **probe("(i-c)同句他子句保留嚴禁（，分隔）", PHRASE, rec_rev2,
            "目標子句仍反轉；嚴禁僅在同句前段"),
})
# 對照：round-1 行為的極端（全域移除嚴禁）
out["micro"].append(probe("(i-d)對照：全域移除嚴禁", PHRASE, rec.replace("嚴禁", ""), "全域缺席"))

# ---- 審查者反例 (ii)：9月30日 → 9月20日 ----
out["micro"].append(probe("(ii)日期：9月30日→9月20日",
                          "辦理防詐騙宣導9月30日瑞里場次",
                          "辦理防詐騙宣導9月20日瑞里場次"))
out["micro"].append(probe("(ii-b)對照：日期原樣", "辦理防詐騙宣導9月30日瑞里場次",
                          "辦理防詐騙宣導9月30日瑞里場次"))

# ---- tamper 4 例（沿用 rev8 的四筆真實標籤；全域移除否定詞） ----
for name, path, key_text, term in [
    ("27B", R27, PHRASE, "嚴禁"),
    ("27B", R27, "年底選舉期間業務處理謹慎，避免捲入政治爭議", "避免"),
    ("MoE", RMO, "嚴禁將科內群組訊息、照片外流至外部群組或平台（如LB），列為會議記錄並嚴懲", "嚴禁"),
    ("MoE", RMO, "設定Email為「文字模式」，勿亂點假Email連結或檔案，防範社交工程攻擊", "勿"),
]:
    r = path.read_text(encoding="utf-8")
    out["tamper"].append(probe(f"tamper {name} 全域移除「{term}」", key_text, r.replace(term, "")))

# ---- 刪除敏感度（37 筆真實標籤；逐條刪除） ----
for name, path in [("27B", R27), ("Gemma", RGE), ("MoE", RMO)]:
    rec = path.read_text(encoding="utf-8")
    rows = []
    for label in svc._extract_action_table_labels(rec):
        key = S._normalize_action_key(label)
        if not key: continue
        hs = S._normalize_action_key(rec.replace(label, ""))
        sents = S._split_record_sentences(rec.replace(label, ""))
        mg, ratios = S._find_missing_action_keys({key}, hs, local_sentences=sents)
        ml, _ = guards_off({key}, hs, local_sentences=sents)
        rows.append({"label": label[:26], "missing_new": key in mg, "missing_lcs_only": key in ml,
                     "ratio": round(ratios.get(key, 0.0), 4)})
    out["deletion"][name] = {"total": len(rows),
                             "flagged_new": sum(r["missing_new"] for r in rows),
                             "flagged_lcs_only": sum(r["missing_lcs_only"] for r in rows),
                             "still_covered": [r for r in rows if not r["missing_new"]]}

# ---- 守衛執行診斷：14 個 log keys ----
LOG_KEYS = {
    "27B": ["了解印花稅業務移轉至土地增值稅科的配合事項", "了解房屋稅系統業務調整（稽查股/征收股）",
            "分發文康活動禮券（扣除點心費後）", "嚴禁轉傳科內群組訊息至外部", "抽籤決定今年文康活動主辦人",
            "採購文康活動點心（含工程師份）並拍照佐證", "整理下週一內機檢查現場",
            "盤點多元支付現狀並思考AI創新方案", "詢問現金發放程序是否麻煩（決定發禮券或現金）",
            "追蹤辦公室黴味處理進度與廠商報價", "預備組織改名相關系統權限、設備調整"],
    "Gemma": ["瑞里發放活動之現場執行（含宣導單發放）"],
    "MoE": ["注意組織調整後之系統權限、系統名稱變更（地價稅科、土地增值稅科、使用牌照稅科、煙酒及稅務管理科、稽徵股、徵收股等）及業務移撥（印花稅移土地增值稅科、檢舉業務移煙酒及稅管科）",
            "準備下週一下午之內機檢查，將物品歸位"],
}
for name, path in [("27B", R27), ("Gemma", RGE), ("MoE", RMO)]:
    rec = path.read_text(encoding="utf-8")
    hs = S._normalize_action_key(rec); sents = S._split_record_sentences(rec)
    for l in LOG_KEYS[name]:
        key = S._normalize_action_key(l)
        if key in hs:
            out["guard_eval_diag"].append({"record": name, "key": key[:26], "path": "rule1-substring"})
            continue
        ratio, window = S._action_key_best_window(key, hs, bigram_index_of(hs))
        nearest = max(sents, key=lambda s: S._lcs_length(key, s)) if sents else ""
        terms = [t for t in S.ACTION_NEGATION_TERMS if t in key]
        nums = S._ACTION_NUMBER_PATTERN.findall(key)
        out["guard_eval_diag"].append({
            "record": name, "key": key[:26], "path": "lcs", "ratio": round(ratio, 4),
            "terms_in_key": terms, "nums_in_key": nums,
            "term_in_window": {t: (t in window) for t in terms},
            "term_in_nearest_sentence": {t: (t in nearest) for t in terms},
            "num_in_window": {n: (n in window) for n in nums},
            "num_in_nearest_sentence": {n: (n in nearest) for n in nums},
        })
print(json.dumps(out, ensure_ascii=False, indent=1))
```

</details>

`rev9_adversarial.py`（殘留邊界掃描）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/p3_probe/rev9_adversarial.py
```

<details><summary>rev9_adversarial.py 全文</summary>

```python
"""rev9 守衛 adversarially：把「嚴禁」放在與反轉目標不同距離處，找出白名單邊界。"""
import json, re, sys
sys.path.insert(0, "/Users/hsiaojohnny/dev/convert")
from backend.services.summarization import SummarizationService as S
NEVER = re.compile(r"(?!x)x")
def guards_off(keys, hs, local_sentences=None):
    t, p = S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN
    S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = (), NEVER
    try: return S._find_missing_action_keys(keys, hs, local_sentences=local_sentences)
    finally: S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = t, p
key = S._normalize_action_key("嚴禁將科內群組訊息（含照片）外流至任何外部渠道")
tgt = "得將科內群組訊息（含照片）外流至任何外部渠道"
rows = []
for g in range(0, 26):
    hay = "嚴禁" + "啊" * g + tgt + "。"
    hs = S._normalize_action_key(hay)
    sents = S._split_record_sentences(hay)
    mg, ratios = S._find_missing_action_keys({key}, hs, local_sentences=sents)
    ml, _ = guards_off({key}, hs, local_sentences=sents)
    rows.append({"gap": g, "rule1": key in hs, "ratio": round(ratios.get(key, 0.0), 4),
                 "missing_new": key in mg, "missing_lcs_only": key in ml})
print(json.dumps(rows, ensure_ascii=False))
# 第二族：嚴禁在同句前段、反轉句在後（逗號隔開）
rows2 = []
for g in range(0, 26):
    hay = "嚴禁遲到，" + "啊" * g + tgt + "。"
    hs = S._normalize_action_key(hay)
    sents = S._split_record_sentences(hay)
    mg, ratios = S._find_missing_action_keys({key}, hs, local_sentences=sents)
    ml, _ = guards_off({key}, hs, local_sentences=sents)
    rows2.append({"gap": g, "ratio": round(ratios.get(key, 0.0), 4),
                  "missing_new": key in mg, "missing_lcs_only": key in ml})
print(json.dumps(rows2, ensure_ascii=False))
```

</details>

微觀探針（rev9 §6 最後幾列）可內嵌執行（heredoc 結尾字串以 `PY` 為界）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python - <<'PY'
import re, sys; sys.path.insert(0, ".")
from backend.services.summarization import SummarizationService as S
NEVER = re.compile(r"(?!x)x")
def guards_off(keys, hs, ls=None):
    t, p = S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN
    S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = (), NEVER
    try: return S._find_missing_action_keys(keys, hs, local_sentences=ls)
    finally: S.ACTION_NEGATION_TERMS, S._ACTION_NUMBER_PATTERN = t, p
for label, key_text, hay in [
    ("數字缺失", "查詢文康活動經費13600元之核銷程序", "請確認文康活動經費約一萬多元之核銷程序"),
    ("千分位",   "查詢文康活動經費13600元之核銷程序", "查詢文康活動經費13,600元之核銷程序"),
    ("全形",     "查詢文康活動經費13600元之核銷程序", "查詢文康活動經費１３６００元之核銷程序"),
    ("原樣",     "查詢文康活動經費13600元之核銷程序", "查詢文康活動經費13600元之核銷程序"),
    ("否定同義", "嚴禁將科內群組訊息外流至外部渠道",   "禁止將科內群組訊息外流至外部渠道"),
    ("2位數日期缺失", "排定9月30日辦理防詐宣導", "排定9月20日辦理防詐宣導"),
]:
    key = S._normalize_action_key(key_text); hs = S._normalize_action_key(hay)
    ls = S._split_record_sentences(hay)
    mg, ratios = S._find_missing_action_keys({key}, hs, local_sentences=ls)
    ml, _ = guards_off({key}, hs, ls)
    print(label, "| 規則1:", key in hs, "| LCS %.4f" % ratios.get(key, 0),
          "| 守衛判遺漏", key in mg, "| LCS-only", key in ml)
PY
```
