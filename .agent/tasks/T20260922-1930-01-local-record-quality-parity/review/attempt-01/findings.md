# Stage 02 獨立計畫審查 — attempt-01（對 PLAN_REVISION 2）

- 審查者：獨立子代理（fresh context，唯讀）
- 受審版本：`plan.md` PLAN_REVISION 2
- 閘門結論：**`PLAN_REVISION_REQUIRED`**
- 備註：該審查 session 未落地任何檔案；本檔為其輸出之**逐項忠實轉錄**（內容未經刪改語意，僅排版）。

## Goal Baseline（審查者重建）

在 Mac 上用 LM Studio（`qwen3.8-27b-splash` 27B 與 `qwen3.6-35b-a3b-splash` 35B）生成**科務會議（section_meeting）**
紀錄，品質不得與雲端 Gemini 差太多；當前最痛的缺口是「可查核性」（地端出處標註 0 vs 雲端 24）與忠實度／覆蓋率。
E2E 與評分工具是達成該目標的手段，不是目標本身。

## 結論

計畫方向（把驗收場換成使用者的 `section_meeting`、忠實度／重複／覆蓋率入絆索）對準使用者目標；
但 W2/W3 與 CORE-2/CORE-4 之間存在**可證實的內部矛盾**，且共用路徑（雲端）被隱性改動、驗收工具量不到 CORE 指標。
這些都是修訂可解，不是 BLOCKED。

## 必要修改清單（10 項，rev 3 逐項回應）

1. W2 `dedupe_chair_rulings` 的「完全相同」判準對真實 fixture 命中 0/10，與 CORE-2 直接矛盾。
   實測：attempt-01 的 10 條「決議」與「三、主席裁示事項」10 條**正規化後仍不相同**，差異是主席條目尾端
   「（主辦單位…，協辦單位：無，辦理期程：（待確認））」；**切除尾端括號 metadata 後才 10/10 相等**。
   改法：明確定義正規化與判準、指名 donor/target、fixture 寫死預期移除數。
2. 去重會製造新的補強問題：`辦理期程` 只出現在主席裁示條目，而 `general` 模板將它列為必要欄位
   （`templates.py:212`、`extra_field_patterns`）；若該節寫「無」→ 立即報「缺少辦理期程」→ 補強輪寫回 →
   再去重，2 輪燒完。改法：保留 metadata（或併入保留條目）＋加「dedupe 後 `_validate_summary_quality`
   issues 不增加」回歸測試；且去重必須是 `_finalize_record_text` 的最後一步。
3. R7/CORE-2/CORE-3 證據來自 `general`，但 CORE E2E 是 `section_meeting`：`section_meeting` 沒有「決議／主席裁示」
   兩節（`prompt_templates/section_meeting.py:74-84`；使用者實檔只有彙整表＋一、科長轉知＋二、科長指示及提醒），
   也無「自創會議名稱」（標題由模板固定）。改法：依模板拆開判準。
4. CORE-1 缺可重跑的量測工具與失敗備案：`check_record_output.py` 僅 9 項結構檢查；
   `run_owned_e2e.py` 必要檢查清單（1234-1249）無品質指標 →「≥90% 條目」無儀器可證。
   改法：新增確定性計數（沿用 `_SOURCE_TAG_PATTERN`）並定義未達門檻時的下一步。
5. CORE-4 不可被現有工具驗證且單次取樣與研究結論衝突（研究 §8.5 結論 5）→ 降為 SUPPORTING
   或定義可重跑代理指標＋取樣規則。
6. 共用路徑的隱性語意變更未申報：`_validate_summary_quality`(952)、兩支 builder、`_finalize_record_text`(2157)
   都是地端／雲端共用；若不加開關會同時改變雲端輸出與補強行為，而 §8.3 的雲端 C 欄是對照基準。
   改法：明示 local-only 或 both；若 both 須同版重跑雲端基準。
7. W4 未聲明模型覆蓋：使用者目標是 27B＋35B，runner 卻要求單一已載入模型（`model_inventory_unique`）。
8. 捏造絆索的能力邊界：`find_unsupported_entities` 攔不到「逐字稿內即錯誤的專名」（如 `煙酒為神穀` 是 ASR 誤辨）；
   CORE-3 的「歸零」缺可重跑量測。改法：指明量測方式並列明不處理範圍。
9. 設計經濟性：`dedupe_chair_rulings` 應放既有 `backend/core/text_postprocess.py`；驗證器可作 `summarization.py`
   方法並重用 `_normalize_action_key`(901)／`_extract_action_table_keys`(934)；若仍要新模組須寫明理由。
10. 小事實修正：（a）issues 清單**無上限**，只有待辦標籤預覽 `ACTION_ISSUE_PREVIEW_LIMIT=12`（127/1015）；
    （b）測試基準數字與架構書不一致，請寫實際指令與基準；（c）§2 R6 引 `run_owned_e2e.py:734` 已過時
    （工作區版已實作 `--template`／`template_applied`）；（d）`data/outputs/*`、`data/cache/*` 被 gitignore
    （`.gitignore:54-55`），fixture 必須**內嵌**。

## 風險清單（審查者）

- **最大不確定**：`section_meeting` 地端是否真的吐出「（發言者N，hh:mm:ss）」——規則注入與絆索在程式面已證實會跑，
  但模型遵循度**從未被量測**；這是 CORE-1 的成敗點。
- 溫度 0.7 的 run-to-run 變異可讓單次 CORE 判準翻盤。
- 新絆索假陽性可能吃掉 2 輪補強額度並增加固定成本（每場多 2 次生成）。
- `find_missing_note_items` 對「筆記本身就缺的主題」無效。
- 去重若誤動 `section_meeting` 彙整表，會連動確定性產生的「列管資料」附件（`templates.py:build_tracking_attachment`）。

## 查證過的程式碼證據（審查者，行號）

- 規則注入與閘門：`summarization.py:114`、`153-154`、`1258-1266`（docstring 已過時）、`1285`、`1329`、`1626`、`1649`、
  `1026/1046`、`2101`、`2132`；`templates.py:169`（預設 False）、`384`（`section_meeting=True`）、`211/256`。
- 流程與上限：`summarization.py:952`、`1004-1023`、`1974`、`2093/2128`、`2107/3210`、`2157-2173`、`2186`、
  `3062-3072`（0903 場 min_chars 實算 804 字）、`3140-3205`；`config.py:224-227`、`253-258`、`270-273`。
- 上層不改寫：`task_processor.py:331-338`、`388-395`。
- 驗收工具：`run_owned_e2e.py:733-745`、`827-836`、`1234-1249`；`check_record_output.py:71-80`；
  `.agent/.../attempt-02/task_final.json`（`template_id: "general"`）。
