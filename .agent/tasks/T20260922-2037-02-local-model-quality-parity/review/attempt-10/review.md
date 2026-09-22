# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02，attempt-10）

- 受審對象：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md`。
- `REVIEWED_PLAN_REVISION`：**13**（開審時為 **rev 12**；審查期間 Planner 依另一位獨立技術驗證者（非閘門）之「2 處文本殘留互斥」判定遞增為 rev 13——delta 經本審查 **byte 級機械反推證明**＝純文本更正，見「rev 13 delta 驗證」節）。
- `REVIEWED_PLAN_SHA256`：**`1673d647254873fb2bc3fd188df7c8f8adcec0bd12a1155bdd89861ccb707a4c`**（自量 2026-09-23 03:01 CST，與 Planner 獨立值一致；收審複量見文末「收尾」）。
  - 開審量測（rev 12）：**`9e20b337dba609d6738eca653ae14aa6828722694ef8884ddc35b8b8a4202538`**（02:55／02:57 CST；該版於審查期間被遞增取代）。
- 審查時間：2026-09-23 02:55–03:12（Asia/Taipei）。
- 審查者：獨立 Stage 02（fresh context；read-only）。未參與本計畫修訂、未參與實作／驗收。
- 唯一寫入：`review/attempt-10/`（本檔＋`snapshot_plan.sha256`）。未修改 `plan.md`、產品碼、測試、`e2e/*`、`quality/*`、`doc/*`、`review/attempt-01`～`09`；重現實驗全寫 `/tmp/rev10/`。全程未碰 port 9527、未重啟 LM Studio、未重跑 E2E（離線審查）。
- 環境事實：分支 `fix/qwen-local-quality-parity`、HEAD＝`c298cc8`。工作樹含 rev 10～13 未提交變更：`backend/core/text_postprocess.py`（sha256 `f08a873c…`）、`backend/services/summarization.py`（`0c988b9d…`）、`tests/test_t20260922_2037_p3_parity.py`（`d5e32f94…`）、`quality/snap_interval_variant_check.md`、兩份 doc、`research/audit-02/03` errata、`e2e/attempt-D1-gemma31b-p3/*`（均屬受審範圍內之宣稱）。
- 審查期間變更（如實記錄，皆已納入受審）：①02:53 前後（rev 12 期、平行落地）——`doc/操作手冊/部署更新手冊_v4.1.md` 附註標題加「rev 12 如實界定（規則 2 例外）」＋部署驗收條目限縮；研究文件 §11.2／§11.4／§11.6 限縮＋新增 §11.7；`quality/snap_interval_variant_check.md` 檔尾 append（原前綴未動、0 deletions）。②02:5x～03:00（rev 13 期）——`research/audit-02`（`:74`、`:171`）與 `audit-03`（`:140`）各加 `**rev 12 errata（2026-09-23）**` 行（原句保留）；`plan.md` 提升 rev 13（2 處就地文本更正）；`tests:8` 限縮。**影響判定＝無**（皆為已申報之文本層收斂，經下方逐處複核；不觸及行為／數字／fixture）。

## rev 13 delta 驗證（「零行為差異／零語意變更」核實）

- **機械反推（byte 級）**：以 `/tmp/rev10/rev12_reconstruction.py` 對現行 rev 13 逆套用 Planner 宣稱的 5 處 `plan.md` 文本變更（①標題＋`PLAN_REVISION` 行；②移除 rev 13 條目；③`:558` 就地標記還原；④`:547` rev 13 基準句移除；⑤§8.8 attempt-10 條目＋界線句還原）→ 重建檔 sha256 ＝ `9e20b337dba609d6738eca653ae14aa6828722694ef8884ddc35b8b8a4202538`＝**開審實測 rev 12 值**（byte 精確命中；delta＝889 bytes，全部為文本）。
- **行為級**：`text_postprocess.py` 現值 `f08a873c…`＝`quality/snap_interval_variant_check.md:830`（rev 12 期量測）所引值，mtime `02:46:37` < rev 13 遞增時刻（`plan.md` mtime `03:00:21`；`tests` mtime `02:59:59`）→ **rev 12 之後未再動過產品碼**；`tests` 之 rev 13 差異僅檔頭 docstring `:8`。實跑全套與 fixture／mutant／fuzz 行為在現行樹重現 rev 12 記載之全部數字（見「實跑數字彙總」）。
- 處置：**不需另起一輪審查**；本輪全部結論以 **rev 13** 為受審版本。

## Goal Baseline（先於計畫框架、從權威來源重建）

1. 使用者痛點＝Mac＋LM Studio 地端模型（`qwen3.8-27b-splash` 27B dense、MoE 35B-A3B；另指定實測 `gemma-4-31B-it-MLX-4bit`）用 `section_meeting` 生成的會議紀錄「品質跟雲端 Gemini 差很多」→ 要**接近雲端且可被證明**。
2. 硬性附加需求：修復機制**模型無關**、macOS（LM Studio）與 Windows 11＋Ollama（RTX 4090）都適用；本輪使用者指定只測 27B＋Gemma 4 31B。
3. 本波（P3 可查核性波）成功標準＝「修復有量尺證明（絆索有鑑別力、缺陷被量到並歸零）＋缺口被量到且公開＋**所有宣稱與實測域一致**」；不宣稱已達雲端品質（C2 雲端基線因 Gemini 503 未取得，PRIMARY_OUTCOME 未達成——plan 已如實揭露）。
4. 不得折損既有綠線：`mode="cloud"` byte 不變、閘門不低於 rev 6（`on_start_tag_ratio ≥0.95`）、測試全綠。
5. 如實性紀律：單次抽樣不得外推；不得把閘門全綠表述成品質達標；未取得雲端基線不得發布地端 vs 雲端比較。

## Top-down（目標對齊／必要性／關鍵路徑／閘門比例／失效圍堵／耦合／設計經濟）

- 目標對齊：rev 13 的唯一內容＝把 attempt-09 阻斷項 R4（規則 2 跨段後退之宣稱互斥）做**文本層完全收斂**（就地更正＋fixture＋已知限制）；不引入行為／語意／數字變更 → 與「機制模型無關、跨平台共通、可被證明」的目標一致，且不觸發需重跑 E2E 的語意變更。
- 必要性：rev 12→13 的每一項皆為如實性必要（自標全域阻斷的 CORE-5 宣稱必須為真），無鍍金項。
- 關鍵路徑：本波核心＝「吸附修復可被證明」；CORE-5 為其最後閘門；R4 收斂為關鍵路徑末端，現已到達。
- 閘門比例：§8.6-7 明示**不把**地端 vs 雲端缺口設為全域阻斷（單樣本＋近似量尺）＝正確；反之 CORE-5 自標 `[全域阻斷]`，其宣稱真值必須成立——R4 屬此類，現已收斂（逐處見下）。
- 失效圍堵：規則 2 跨段類已以「風險⑤＋回歸 fixture＋doc／docstring／手冊／audit errata」四路圍堵；fixture 具**實證鑑別力**（mutant 停用規則 2 → `2 failed／20 passed`，見下）。
- 設計經濟：總變更＝文本限縮＋1 fixture＋1 測試函式；無新依賴、無架構變更、無行為變更。
- 耦合與優先序：audit errata 以追加式落地（原句保留）；未見新的不當耦合或優先序倒置。

## Bottom-up（repo 接地、契約、安全、序列、驗證）

- 實作對計畫：常數 `TAG_SNAP_TOLERANCE_SECONDS=180`／`TAG_SNAP_MAX_SHIFT_SECONDS=120`（`text_postprocess.py:758/:762`）；docstring（`:890-901`）與行為端註解（`:953-955`、`:990`、`:1003`）之如實界定與 §8.4 文字逐條一致。
- 契約：`SOURCE_TAG_PATTERN` 明示接受 `HH:MM`（秒可省）→ 規則 4 的可達輸入類論證成立；吸附與量尺共用閉區間語意（attempt-09 已複核，rev 13 未觸及）。
- 安全／隱私：本波未涉；audit errata 之追加式修正（原句保留、緊隨否證）符合 append-only 紀律；`quality` 追加 0 deletions。
- 序列：D1 於 `c298cc8`（rev 9 語意）執行；rev 10～13 對「全含秒」的 D1 標註皆零影響（規則 4 只動無秒路徑）。
- 驗證（本輪實跑；詳見下節）：全套測試 **936 passed／2 skipped（9.21 s）**；R4 三例與 v1.0 對照重現；mutant／fuzz 在現行樹重跑。
- D1 引用如實性：`e2e/attempt-D1-gemma31b-p3/run_summary.json` `verdict=PASS`、16/16 checks、`actual_build_revision=c298cc8…`；§8.9 之數字（`coverage_core=0.6786`／`all=0.5075`、`on_start=0.9583`、`kept_on_start=23`、7 筆吸附全屬 cross-speaker、`nearest` 0 筆）與 artifacts 對得上；「單一會議、單次抽樣、不得外推」「C2 未取得、不得發布比較」皆已如實揭露 → **無誇大**。`verify_independent.md:117` 之「不跨段後退」句已自帶域限（「在 D1 輸入上成立」＋D1 log「最近段落 0」）→ 屬真實敘述（餘見殘留建議）。

## R4 收斂判定（attempt-09 引用的六處＋rev 13 兩處新更正，逐處重驗；皆 `[VERIFIED]`）

1. **`plan.md` rev 9 條目（原引 `:47`；現 `:44-48`）**：原句後**就地**加註「（rev 12 更正：規則 2 的 nearest 容忍仍可跨段後退，見 §8.4／§8.7 風險⑤）。」→ 原句與即時更正同處並存，**無互斥**。
2. **`plan.md` §8.4（現 `:440-448`，另 `:463`、`:471`）**：新增「**rev 12 如實界定**」＝保證「已是真實段首的值不被搬動」＋「所有被接受的值都是不動點」；**不**保證後退一律同段；規則 2（180 s）例外＝可跨段後退（落點仍是真實段首、仍為不動點）＋指向 fixture；`:463` 觀察值定義與 `:471`「必要條件（rev 12 更正：**不是**『所有後退都在段落內』）」皆已就地限縮。
3. **`plan.md` §8.6-4③（現 `:558`；次行 `:560-562`）**：原句就地補「（**rev 13 就地更正：本句不成立於規則 2，見次行**）」；`:560-562` 之「**rev 12 更正（如實）**」把驗收③限縮為「規則 1／3 的後退在段落內；規則 2 的跨段後退以 fixture 釘住並公開」。attempt-09 指其為「唯一只靠事後更正者」——**已解除**。
4. **`plan.md` §8.7（現 `:595` 如實界線；`:615-623` 風險⑤）**：如實界線明載「**不**保證所有後退都在同一段落內（規則 2 例外，見風險⑤）」；風險⑤＝完整登記（最小反例 Δ32 s、曾觀測 Δ45／Δ55 s、非本波引入（v1.0 同輸出）、本波處置＝限縮＋fixture＋**不改行為**、收緊規則 2 列下一波候選）；`:623` 另載「三次真實 E2E 的產品 log 皆『最近段落 0』（規則 2 未被觸發）」。
5. **`backend/core/text_postprocess.py` docstring（現 `:890-901`）**：「三者合起來才足以保證『已是段首的值不被搬動』，且**所有被接受的值都是不動點**」；緊接「**後退幅度（如實，rev 12／審查 attempt-09 R4）**」段＝規則 1／3 落點限制＋規則 2 例外＋最小反例＋「非本波引入、列已知限制，本波只如實限縮宣稱、不改行為」。行為端註解同步（`:955`、`:1003`）。
6. **研究文件 §11（§11.2 `:947-948`；§11.4 `:975`；§11.6 `:1028`；§11.7 `:1038-1050`）**：§11.2「不含『後退必在同一段落內』—規則 2 例外：可跨段後退」；§11.4「規則 1／3 在段落內，規則 2 nearest 容忍例外＝可跨段後退」；§11.6 同旨並指向 §11.7；§11.7＝《rev 12 修訂：規則 2「跨段後退」如實界定》（白話根因／最小反例／不改行為理由）。
7. **`tests/test_t20260922_2037_p3_parity.py:8`（rev 13 新更正）**：原「兩者合起來才保證『一般輸入不跨段後退』」→「兩者合起來才保證『**已是段首的值不被搬動**』」；與同段 `:11-13` 的 rev 12 如實界定**不再互斥**。
8. **`research/audit-02`（`:73-74`、`:170-171`）／`audit-03`（`:139-140`）errata**：三處原句「後退僅限段落內吸附」保留＋緊隨「**rev 12 errata（2026-09-23）**」逐句否證（「不成立於規則 2；只有規則 1／3 的後退在段落內」），並導向 §8.7 風險⑤／§11.7；`audit-02:171` 明示 `kept_on_start` 敘述**仍成立**（未被誇大為普遍失效）。機械掃描（`rg`，排除 `.git`／`data`／`review`）確認全部殘句皆為上述①已就地更正②被引述之舊宣稱③如實界定④audit 原文＋errata⑤D1 專屬限域敘述——**無現行互斥**。

- 附帶（受審範圍內其他宣稱位置）：`quality/snap_interval_variant_check.md:824` 之限縮、操作手冊 `:496` 附註（標題「rev 12 如實界定（規則 2 例外）」＋部署驗收「規則 1／3 在段落內；規則 2 例外＝可跨段後退，屬已知限制、以回歸 fixture 釘住」）皆已同步，**無過度保守或新互斥**。

## fixture 鑑別力與已知限制的可達性（attempt-09 R4 之最小修正要求）

- **fixture 非空轉**：`test_snap_規則2_nearest_可跨段後退_落點仍是該發言者真實段首且冪等`（`tests:202-219`）釘住 `（發言者2，00:00:34）`→`00:00:02`（Δ32 s；`snapped_nearest=1`、`backward_moves=1`、`max_backward_seconds=32`；第二輪 `changed=0`），且 `assert once != text`（確保規則 2 路徑**真的被走過**）。
- **mutant 實證**：①`nearest` 只准往後（`nearest[0]>=seconds`）→ 輸出變 `00:00:32`、測試必掛；②「時間戳落在任何段內即不走 nearest」→ 同上必掛；③`TAG_SNAP_TOLERANCE_SECONDS=0`（停用規則 2）→ **2 failed／20 passed**（恰為 rev 13 條目所載數字；失敗者＝`test_snap_無秒標註_目標為整分鐘時可吸附且冪等`＋本 fixture）。
- **可達性與 D1 觀測域**：D1 四份 log「最近段落 0」共 9 次（規則 2 在真實素材未觸發）→ 屬**宣稱域**問題而非掩蓋；§8.7:623 已如實記載。

## R1–R3 與 M1–M4 複核（實跑；全部仍成立）

- **R1（無秒標註冪等）**：冪等 fuzz 5000 回合（含 35% 無秒標註、隨機段落）→ `non_idempotent=0`、`start_value_moved=0`、`changed_tags=1843`、`changed_to_non_start=0`；規則 4 相關測試全綠（停用規則 2 時亦見其依賴關係，見上）。`[VERIFIED]`
- **R2（驗收一致性）**：「不到三」僅存於歷史更正說明（`plan.md:58`、`:401`）；現行門檻 `\d{2,}`（`summarization.py:162`）與 §8.3:400「門檻＝`\d{2,}`」、「不到兩位數」（`:400`、`:527`）一致；測試反例 `9月30日→9月20日`（`tests:370-371`）在樹。`[VERIFIED]`
- **R3（attempt-05 記載）**：`review/attempt-05/review.md:4`＝`REVIEWED_PLAN_REVISION: 6`、`:102`＝`PLAN_APPROVED`；`plan.md:506-508` 已更正並標註來源。`[VERIFIED]`
- **M1（絆索措辭）**：`plan.md:452-463`＝具鑑別力絆索（冪等／規則 0 有作用）＋觀察值（`kept_on_start`／`kept_precision`／`backward_moves`／`max_backward_seconds`）；rev 13 未改語意。`[VERIFIED]`
- **M2（`0.9333`）**：`plan.md:384` 與 `tests:370` 一致（0.933）；`0.9375` 之出處為否定同義替換（attempt-09 已複量，rev 13 未觸及）。`[VERIFIED]`
- **M3（輪數）**：`backend/core/config.py:270-272` `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` `default=2`；與 §8.7 一致。`[VERIFIED]`
- **M4（可查核性閘門不受阻斷）**：`plan.md:612-613`「規則 0 只保證『不動』不保證『歸屬正確』…對可查核性閘門**不阻斷**」；D1 `kept_on_start=23/24`、`on_start=0.9583` 自洽。`[VERIFIED]`

## 實跑數字彙總（本輪獨立重跑）

- 全套測試：`DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py` → **936 passed／2 skipped in 9.21 s**（與 rev 13 條目「936／2」一致）。
- R4 最小反例（真函式，`/tmp/rev10/probe_r4.py`）：Δ32／Δ45／Δ55 三例皆吸到 `00:00:02`（`snapped_nearest=1`、`backward_moves=1`、`max_backward_seconds=32／45／55`），二次套用 byte 相同（`s2 changed=0`）＝**冪等**；v1.0 重建（`git show e90040b` 原文 `exec`）三例輸出與現行樹 **byte 相同**＝「非本波引入（v1.0 同輸出）」**成立**。
- fixture mutant（`PYTHONPATH=/tmp/rev10 … -p mutator`，`TAG_SNAP_TOLERANCE_SECONDS=0`）：**2 failed／20 passed**（恰如宣稱）。
- （註：`probe_r4.py` 內附舊 fuzz 區塊之 `changed_to_non_start=1845` 係**未先篩『值有被改寫』**之寬鬆計數（把規則 4 原樣保留者也計入），**勿引用**；權威口徑＝`/tmp/rev10/probe_fuzz2.py` 之 0。）
- rev 13 delta 機械反推：重建 sha256＝`9e20b337…`（byte 精確命中；delta＝889 bytes）。
- 關鍵 sha256（現行樹）：`text_postprocess.py`＝`f08a873c…`、`summarization.py`＝`0c988b9d…`、`tests`＝`d5e32f94…`、`plan.md`＝`1673d647…`。

## 殘留項與建議（皆非阻斷）

- **N1（流程註記）**：審查期間受審物遞增（rev 12→13，另 doc／audit errata 追加式落地）——已 byte 級機械證明為純文本且語意零變更；紀律維持：**舊核准不得沿用**，本判定僅綁定 rev 13。
- **N2／N3（attempt-09 遺留、未見專項處理）**：①`plan.md` §8.7 風險②（現 `:609-611` 一帶）仍未列「月份／單位數字改寫（`9月30日→10月30日`，ratio 0.7273）」子案（文件完備性建議）；②`plan.md:427`「228 個標註」為 D1 前掃描（本輪全 records＝252 筆、仍 0 無秒）——建議標註掃描時點；兩者皆不影響實質結論。
- **N4（D1 觀測域）**：attempt-09 指「nearest 未在既有材料觸發」→ 已由 `plan.md:623` 如實記載圍堵。
- **N5（措辭對齊，新）**：§8.8 之 attempt-09 條目寫「受審＝rev 10」，較 attempt-10 條目的「開審 rev X、審查期間被 rev Y 取代、正式受審＝rev Y」慣例少了遞增敘述（attempt-09 自述「本判定綁定 rev 11」；該 delta 已由其 byte 級證明＝§8.9 標籤）——不影響任何結論，建議日後如實對齊。
- **`verify_independent.md:117`**：`e2e/attempt-D1-gemma31b-p3/verify_independent.md` 之「不跨段後退」句已自帶「在 D1 輸入上成立」域限，且 D1 log「最近段落 0」；建議（非必須）加一句「規則 2 例外不影響本判定（未觸發）」以絕誤讀。
- **不得外推之界線（沿用）**：單一會議、單次抽樣、Windows 實機 `[UNVERIFIED]`、PRIMARY_OUTCOME（品質對齊雲端）未達成（C2 Gemini 503 未取得基線）——plan 均已如實揭露，本審查不另擴張要求。

## 收尾

- 開審量測（rev 12，02:55／02:57 CST）：`9e20b337dba609d6738eca653ae14aa6828722694ef8884ddc35b8b8a4202538`。
- 定稿量測（rev 13，03:01 CST）：`1673d647254873fb2bc3fd188df7c8f8adcec0bd12a1155bdd89861ccb707a4c`；本檔寫入後複量：**同值**（見同目錄 `snapshot_plan.sha256`）。
- 本審查未修改任何其他檔案；`review/attempt-10/` 僅含本檔與 `snapshot_plan.sha256`；探針寫入 `/tmp/rev10/`。

## 閘門

**`PLAN_APPROVED`**——綁定 `PLAN_REVISION 13`＋sha256 `1673d647254873fb2bc3fd188df7c8f8adcec0bd12a1155bdd89861ccb707a4c`。阻斷項：**無**。

## 附錄：可重現指令（節錄）

```bash
# 全套測試
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py
# R4 三例＋v1.0 對照＋mutant（探針內舊 fuzz 數字勿引用）
DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/rev10/probe_r4.py
# 冪等 fuzz（權威口徑）
DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/rev10/probe_fuzz2.py
# 規則 2 停用 mutant
PYTHONPATH=/tmp/rev10 DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/test_t20260922_2037_p3_parity.py -q -p mutator
# rev 13 delta 機械反推
DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/rev10/rev12_reconstruction.py
# 殘留宣稱掃描
rg -n '不跨段後退|後退僅限|只在段落內|所有後退' --hidden -g '!.git/*' -g '!data/*' -g '!*/review/*' .
```
