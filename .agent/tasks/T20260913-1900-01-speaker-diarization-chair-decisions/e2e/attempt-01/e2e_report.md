# E2E 獨立驗收報告 — attempt-01（Stage 05）

- TASK_ID：`T20260913-1900-01-speaker-diarization-chair-decisions`
- PLAN_REVISION：1（未變更；本次未觸發 replan）
- 稽核角色：Stage 05 獨立驗收稽核員（fresh context）。**唯讀產品程式碼**：未修改 `backend/`、`frontend/`、`tests/`、`scripts/`、config 或任何產品檔案；未 `git commit`／`git add`；未重啟服務；未輸出任何 API key。
- 寫入範圍：僅 `e2e/attempt-01/`（本檔）與 `result.md`。
- 稽核時間：2026-09-13 20:31–20:46（Asia/Taipei）
- 受驗對象：任務 `3d7f76d3`（`0903-科務會議.m4a`，`processing_mode=cloud`、`template_id=section_meeting`）
- 服務：`http://localhost:9527`（PID 54026，稽核全程未觸碰）
- 總判定：**ACCEPTED**（C1 PASS／C2 PARTIAL／C3 PASS／C4 PASS；全測試 784 passed / 2 skipped）

## 0. Goal Baseline（由 `plan.md` §0 重建；非引用實作者敘述）

1. 使用者痛點：45 分鐘多人會議錄音，AI 逐字稿分不出誰在說話；**最重要的是辨識出主席（科長）的裁示**，因為那是整場會議的核心與後續方向。
2. 主成果：上傳多人會議錄音＋選「科務會議」模板後 → (a) 逐字稿可看到**發言者分群標籤＋時間戳**；(b) 會議紀錄的「主席裁示／決議」**確實來自主席發言且可回溯**；(c) 雲端模式＋科務會議模板**端到端完成**，Word／Markdown 輸出正常。
3. CORE（不做＝任務失敗）：C1 分群標籤逐字稿、C2 主席裁示歸屬規則、C3 真實音檔 E2E、C4 diarization fail-soft（失敗不得擋任務）。
4. SUPPORTING／BEST_EFFORT：S1 角色推斷、S2 發言者統計、S3 裁示→quote+時間戳對照表；B1 重疊語音、B2 100% 純度、B3 真實姓名辨識——**皆非 blocking**。
5. 全域 blocking 條件（僅此）：**C2／C3 任一「無法以真實音檔證據證明」時，任務不得宣稱完成**。語意契約：`發言者N` 是分群編號不是姓名；無法確認主席身分時填「（待確認）」，不得硬猜。

## 1. 稽核方法與唯讀聲明

- 證據來源：`GET /api/tasks/3d7f76d3`、`/api/tasks/3d7f76d3/transcript`、`/api/tasks/3d7f76d3/result?format=md|docx&doc=record|attachment`（`curl -m 60`）、`data/outputs/*` 實體檔、`logs/app.log` 執行期日誌、原始音檔切片重轉寫（Apple SpeechAnalyzer CLI）、產品程式碼唯讀審閱、pytest。
- 未執行（能力限制，誠實標註）：**人工聽音訊＝未抽聽（無法聽音訊）**。時間軸換手點改用「ffmpeg 切 14 秒片段 → 以 `apple_speech_cli` 重新轉寫 → 與逐字稿同時間區間文字比對」作為替代證據（方法論限制見 §2.5）。
- 服務唯讀：稽核期間只呼叫 GET 端點；未上傳、未觸發任務、未重啟。

## 2. C1 — 逐字稿含發言者分群標籤＋時間戳

**判定：PASS（主成果達成；碎裂品質有明確 caveat，見 §2.4）**

### 2.1 標籤格式、數量與分佈 [VERIFIED]

指令（節錄）：
```bash
curl -s -m 60 http://localhost:9527/api/tasks/3d7f76d3/transcript -o /tmp/e2e_transcript_3d7f76d3.txt
# 以 regex ^\[(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})\]\s*發言者(\d+)： 統計
```
原始輸出（節錄）：
```
HTTP 200 size=38149
【發言者標註說明】本逐字稿由系統依語音特徵自動分群標註，「發言者N」為分群編號、不是姓名；…
【發言者統計】
- 發言者1：00:37:28（85%，84 段，首次發言 00:00:00） 首句節錄：管他那個大主任的那個…
- 發言者2：00:03:45（9%，49 段，首次發言 00:11:13）…
- 發言者3：00:02:21（5%，34 段，首次發言 00:05:57）…
- 發言者4：00:00:08（0%，6 段）／發言者5：00:00:04（3 段）／發言者6：3 段…／發言者7：2 段／發言者8：1 段

[00:00:00-00:05:36] 發言者1：管他那個大主任的那個你已經賣沒出來嗎…
[00:11:13-00:11:41] 發言者2：毛你第一次吃便當啊你你就也是我辦的啊…
```
統計結果：
```
total labeled lines: 183
speaker counts: {1: 84, 2: 49, 3: 34, 4: 6, 5: 3, 6: 4, 7: 2, 8: 1}
malformed label lines: 0
has 發言者統計: True   has 發言者標註說明: True
per-speaker 標註時長：S1 2254s(85.5%) / S2 224s(8.5%) / S3 141s(5.3%) / S4 8s / S5 4s / S6 2s / S7 2s / S8 1s
標註總覆蓋 2636s（音檔 2695s，覆蓋 97.8%）；首標籤 00:00:00、末標籤結束 00:44:54
```
執行期日誌（`logs/app.log`）[VERIFIED]：
```
backend.services.diarization diarize:286 - diarization 完成：682 段、8 位發言者、音檔 2695s、耗時 151.2s（RTF 0.056）
backend.services.task_processor _label_speakers:223 - 發言者標註完成：8 位發言者、183 段發言（diarization 682 段、threshold=0.6）
```
→ 標籤格式、時間戳、統計區塊**全部存在**；與實作者宣稱的「682 段／8 位發言者／151.2s／RTF 0.056」一致。

### 2.2 碎裂檢查（客觀指標）[VERIFIED]

```
labels with duration <5s: 102 (55.7%)
  per speaker: {1: 28, 2: 34, 3: 24, 4: 6, 5: 3, 6: 4, 7: 2, 8: 1}
zero/negative duration labels: 13
標籤 0 秒範例：00:14:05-00:14:05 S3「就是」／00:18:19-00:18:19 S5「有」／00:21:14-00:21:14 S6「人家的例」
發言者4–8 全部只出現在 <5 秒片段（合計 16 句、16 秒）
```
判讀：
- 主要三人（S1/S2/S3）承載 99.3% 發言量，符合「至少 A/B/C 可區分」的 CORE 要求。
- 但 **8 群中有 5 群（S4–S8）是 <5 秒的零星碎句**（單字、應答、疑似雜訊/重疊語音），且存在 **13 個 0 秒標籤**。這屬計畫書已預期的 over-clustering 殘留（plan §5 風險1），非新問題，但確實是「明顯碎裂」訊號，量測數字如實記錄於此。

### 2.3 一處疑似「同一句被拆成兩個發言者」[VERIFIED]

```
[00:42:51-00:43:03] 發言者3：…就說我們算一個示範點看看有沒有下<他>
[00:43:03-00:44:15] 發言者1：們他有認同。對啊你情工可是工廠那味道…
```
兩行在句中被切開（「…看看有沒有下」＋「們他有認同」合成「看看有沒有下文，他們有認同」）。以原始音檔 2576–2590s 切片重轉寫，Apple ASR 將該段判為**連續 9.96 秒單一 segment**，顯示此處的 S3→S1 邊界可能是分群/對位造成的假換手（詳 §4.3 之 C2 個案 5）。計畫書 B2（100% 純度）屬 BEST_EFFORT，故不構成 CORE 失敗，但列入殘留風險。

### 2.4 時間軸換手點抽驗（替代法；人工聽感＝未抽聽）[VERIFIED 之替代證據]

**未抽聽：無法聽音訊**（稽核者無音訊聽覺能力）。替代做法：`ffmpeg -ss <boundary-7> -t 14` 切出片段 → `apple_speech_cli transcribe --input <clip> --locale zh-TW --output-format json` 重新轉寫 → 比對逐字稿同時間區間的文字。此法可獨立驗證「時間軸與文字對位正確」，**不能**驗證「聲音是否真的換人」。

| # | 換手點 | 逐字稿（該時段） | 片段重轉寫（節錄） | 對位 |
|---|---|---|---|---|
| 1 | 00:11:13 S1→S2 | 「…這個活動呢去年四十放嬌…」→「毛你第一次吃便當啊…」 | `這個活動呢去年是放假嘛對不對對不對你有跟小朋忙吃第一次吃便當你也是我辦的啊對` | 一致 |
| 2 | 00:16:49 S1→S2 | 「…一個人 800塊嘛我們」→「有 17個人所以 13600…」 | `要收收本來都要簽收啊…一個人 800塊嘛我們有 17個人所以 13600。而且你買點心你還要考慮他們` | 一致 |
| 3 | 00:21:01 S1→S3 | 「…洗車這個不要嘿」→ S3「我突然想到有一個人他開公務車…」 | `然後聽說有人開自己的車到辦公室洗車這個不要嘿…可是我突然想到有一個人他說他開公路車…` | 一致（ASR 同音差異：公務車/公路車） |
| 4 | 00:33:07 S1→S2 | 「…搬進去的時間可能會拖很久…」→ S2「沒有水啊。有有些還有稍微啦…」 | `的時間可能會拖很久…我早上去尋啊沒有水啊。有有些還有稍微啦那邊…` | 一致 |
| 5 | 00:43:03 S3→S1 | 「…我們算一個示範點看看有沒有下」→「們他有認同…」 | `…就說我們算一個示範點看看有沒有效他他有認同。對你請工可是工廠有那味道…` | 文字一致；**換手本身存疑**（見 §2.3） |

→ 5 處時間軸與文字對位**全部一致**（抽驗數 ≥ plan V2a 要求的 5 處）；第 5 處的換手正確性無法以本替代法證明。

### 2.5 C1 判定

- 標籤格式／時間戳／統計區塊／標籤數與分佈：**PASS**。
- 碎裂品質（S4–S8 碎群、13 個 0 秒標籤、1 處疑似句中被拆）：**未達乾淨水準，屬計畫已預期的 over-clustering 殘留**，不影響 A/B/C 可區分的主成果。
- 結論：**PASS（caveat 已記錄）**。

## 3. C2 — 「主席裁示／科長指示及提醒事項／決議」只能來自主席發言

**判定：PARTIAL**（規則三處存在且以真實輸出可回溯多數裁示；但有 ≥3 個具體案例把非主席發言內容寫成科長裁示／交辦；且紀錄本身無「裁示→發言者＋時間＋quote」結構化欄位）。

### 3.1 程式碼事實：裁示歸屬規則 [VERIFIED]

```
backend/core/prompt_templates/section_meeting.py:44  «科長指示及提醒事項» 與 «決議事項辦理情形彙整表» **只收錄主席（科長）所下之裁示與交辦**；其他與會者…不得寫成科長裁示。
backend/core/prompt_templates/section_meeting.py:45  科長轉述上級…須寫明指示來源…不得記成科長本人之指示
backend/core/prompt_templates/section_meeting.py:104 「二、科長指示及提醒事項」與彙整表只能寫主席（科長）的裁示與交辦…
backend/core/prompts.py:23-25                        ### 發言者標註與裁示歸屬…「主席裁示事項」只收錄主席（主持人）的裁決與交辦…
config.yaml:106-108                                  （同上段落，內容與 prompts.py 一致）
```
三處**皆存在**規則 [VERIFIED]。CI 強制範圍需精確陳述：`tests/test_system_prompt_validation.py::test_config_yaml_prompt_matches_python_source` 以正規化字串比對強制 `config.yaml` ↔ `prompts.py` 一致 [VERIFIED]；**未找到**任何測試斷言 `section_meeting.py` 的裁示歸屬規則文字（該檔在 CI 只有編號階層類斷言）→ 「三處同步（CI 強制）」應修正為「**三處皆有規則；CI 只強制其中兩處配對**」[VERIFIED]。

### 3.2 案例抽驗（≥3 案例；逐字稿標籤＋時間）

主席＝`發言者1`（科長）之判斷依據 [INFERRED，多點一致]：發言量 85%、開場主持（「我先講一下哦」）、主導局務會議轉知、被紀錄敘述明確標為「科長說…」（以下 3 例皆與 S1 對齊：`[00:11:41] S1「那是你要辦」`→紀錄「科長說那是你要辦的啦」；`[00:43:03] S1`→紀錄「科長回應『他們有認同』」；`[00:44:36] S1「今天你仔細去聞整間都是味道」`→紀錄「科長說今天仔細去聞，整間都是味道」）。

| 案例 | 紀錄條目 | 逐字稿來源 | 判定 |
|---|---|---|---|
| A | 二、（七）3「不要開自己的車到辦公室洗車」＋彙整表同列 | `[00:19:49-00:21:01] 發言者1`「聽說有人開自己的車到辦公室洗車這個不要嘿」 | ✅ 可回溯到主席（單一一致） |
| B | 二、（九）1「科內群組訊息不得外流…此項列入會議記錄」 | `[00:29:14-00:31:34] 發言者1`「我們科內的群組你不要把他外流出去…不要把它轉傳出去」 | ✅ 可回溯到主席 |
| C | 二、（五）1「下禮拜一內機，全體相關同仁將東西放好…」 | `[00:08:15-00:10:04] 發言者1`「下個禮拜一我們要做內機哦…你們有些東西該放好就放好」（該長段亦含土地卡重新列印＝二、（四）1） | ✅ 可回溯到主席 |
| D | 二、（十）1「西龍股提出多元支付創新…尤其要與AI有關」 | `[00:29:14-00:31:34]`／`[00:31:34-00:32:33] 發言者1`「西龍股這邊的那個多元支付可能要想要有沒有什麼創新…尤其是跟 AI 有關係的」 | ✅ 可回溯到主席 |
| E | 二、（十一）5「向對方表達『我們算一個示範點』。」＋**彙整表列（辦理情形欄＝科長：）** | 源頭為 `[00:42:51-00:43:03] 發言者3`「我跟他講你的想法就說我們算一個示範點看看有沒有下文」；主席 `[00:43:03-00:44:15]` 僅回「他們有認同」 | ❌ **非主席內容被寫成科長指示／交辦** |
| F | 二、（三）2「公文會辦整理各科室發哪個村里資料（承辦待確認）」 | 源頭為 `[00:06:56-00:07:08] 發言者3`「科長有個公文會辦…他把所有各科室的那個是發哪一個村里」；主席僅回「對都有整整理」 | ❌ 非主席內容列為科長指示 |
| G | 二、（六）11「可類似慶生聚會形式」／（六）3「點心部分包含工程師」 | 源頭為 `[00:17:29-00:17:36] 發言者3`「好像類似慶生…」／`[00:16:49-00:16:55] 發言者2`「你買點心你還要考慮他們的工程師」 | ❌ 非主席內容列為科長指示（彙整表同列主辦） |

抽驗結果：7 案例中 **4 例（A–D）可回溯到單一一致的主席發言**、**3 例（E–G）為非主席發言被寫入「科長指示及提醒事項」／彙整表**。部分項目（如文康活動）在 `三、（二）臨時動議及與會同仁意見` 另有正確的「與會同仁建議」記錄，顯示模型有區辨能力，但同內容仍重複出現在科長段 → 歸屬一致性不足。

### 3.3 「可回溯」程度界定 [VERIFIED]

- **逐字稿層**：有時間＋發言者＋原文 → 人工可比對（本報告 §3.2 即以此完成 7 案例）。
- **紀錄層**：`0903-科務會議_3d7f76d3.md` 內 **[hh:mm:ss] 時間戳出現次數＝0**；「二、科長指示及提醒事項」與 65 列彙整表**均無**「發言者N＋時間＋quote」欄位；全檔僅在 `一、報告事項` 有 5 處 `發言者N` 引註。
- 設計文件已載明此為未實作項：`doc/規格與設計/發言者分離與主席裁示-研究與設計.md` §4.2（目標 schema：`verbatim_quote`＋`evidence_utterance_ids`＋`evidence_time`…）與 §4.4「**沒有**確定性驗證器…主席身分判斷完全由 LLM 依內容證據完成…C2 目前為提示詞級保證，需人工抽驗」[VERIFIED]。
- 因此 C2 的「可回溯」= **人工可回溯（靠標籤逐字稿）**；**不是**紀錄內建證據鏈，也**沒有**程式級驗證器（plan 的 S3 未實作，屬 SUPPORTING 非 CORE）。

### 3.4 C2 判定

**PARTIAL**：CORE 規則已落地且多數裁示可回溯到主席（改善幅度：baseline `42fbaee7` 逐字稿 0 個發言者標籤、彙整表空白 → 新紀錄 13 個主題／63 列彙整表且 4/7 抽驗案例正確回溯，並新增 `三、（二）與會同仁意見` 區塊）；但「他人發言不得寫成主席裁示」在抽驗中有 3 個具體反例，且無結構化證據欄位。未達「全部來自主席」的嚴格不變式，但**已以真實音檔證據證明改善與可回溯性**（plan §0 全域 blocking 條件為「無法證明」，非「完美」）。

## 4. C3 — 真實音檔 E2E 完成且輸出可下載

**判定：PASS**

### 4.1 任務狀態 [VERIFIED]
```
GET /api/tasks/3d7f76d3 →
{"task_id":"3d7f76d3","original_filename":"0903-科務會議.m4a","file_size":45107503,
 "status":"completed","progress":100.0,"stage":"完成","processing_mode":"cloud",
 "template_id":"section_meeting","started_at":"2026-09-13T20:15:28.485092",
 "completed_at":"2026-09-13T20:27:17.541770","error_message":null,"summary_failed":false}
```
耗時 709.06s（與宣稱 709.1s 一致）。日誌 [VERIFIED]：`任務 3d7f76d3 處理完成，耗時: 709.1秒`、`Ollama Cloud 摘要生成成功，模型: deepseek-v4.1-flash`（5 次雲端呼叫，**無任何 Gemini 呼叫**）、`Ollama Cloud` provider 由啟動日誌確認（`cloud_provider=ollama_cloud, cloud=deepseek-v4.1-flash`）。

### 4.2 下載與檔案有效性 [VERIFIED]
```bash
for q in "format=md&doc=record" "format=md&doc=attachment" "format=docx&doc=record" "format=docx&doc=attachment"; \
  do curl -s -m 60 -o out -w '%{http_code} %{size_download}\n' "http://localhost:9527/api/tasks/3d7f76d3/result?$q"; done
```
```
record.md      HTTP=200 size=26797
attachment.md  HTTP=400 size=40    {"detail":"附件僅支援 docx 格式"}
record.docx    HTTP=200 size=49584
attachment.docx HTTP=200 size=40541
file: record.docx = Microsoft OOXML；attachment.docx = Microsoft OOXML
python-docx/zipfile 開檔：zip_ok=True（testzip 無錯）、17 個 OOXML parts、
  record.docx：94 段落 + 1 表格（64 列；含「科長指示及提醒事項」「決議事項辦理情形彙整表」）
  attachment.docx：3 段落 + 2 表格（2 列、64 列）
shasum：下載 record.md == 磁碟 `_record.md`（8237bd3c…）；`_3d7f76d3.docx` == `_record.docx`（066a18e9…）
```
`doc=attachment&format=md` 回 400 屬設計（附件僅支援 docx）[VERIFIED，訊息即為說明]；`format=docx&doc=attachment` 正常 200。

### 4.3 輸出內容抽樣 [VERIFIED]
- `0903-科務會議_3d7f76d3.md`（26,797 B）：開頭為「（待確認）」欄位（會議時間/地點/主持人未在音檔明示），含「二、科長指示及提醒事項」13 主題、「三、歷次會議列管案件討論或臨時動議」含「（二）臨時動議及與會同仁意見」，及 63 列決議彙整表。
- 逐字稿 38,149 B 含標籤版（§2.1）；`/api/tasks/3d7f76d3/transcript` 與磁碟檔一致。
- baseline 對照 [VERIFIED]：`42fbaee7_逐字稿.txt` 發言者標籤數＝0；`42fbaee7.md` 彙整表僅「決議事項：」無資料列 → 改善成立。

### 4.4 附帶之 fail-soft 實證（任務未因此失敗）
```
20:18:31 WARNING correction.correct_transcript:310 - 校正遇 provider 穩定失敗（LMSTUDIO_UNREACHABLE），熔斷後續 LLM 校正，剩餘段落保留原文
20:18:31 INFO correction.correct_transcript:345 - 語意校正完成：45 段中 0 段有修正、0 段放棄、採納 0 處替換
```
→ 地端 LM Studio 未開（`LOCAL_LLM_PROVIDER=auto`），語意校正 fail-soft 跳過，任務照常完成 [VERIFIED]（與使用者說明一致，未列為缺失）。
殘留品質警告（非阻擋）[VERIFIED]：`Ollama Cloud 摘要仍有待補強問題: 待辦事項遺漏 47 項`（經 2 輪補強由 71→47），`summary_failed=false` 不受影響。

## 5. C4 — fail-soft（模型缺失／逾時／解碼失敗／時間軸不可用／快取不污染）

**判定：PASS**

### 5.1 程式碼事實（唯讀審閱）[VERIFIED]
| 位置 | 行為 |
|---|---|
| `backend/services/diarization.py::diarize` | `ENABLE_DIARIZATION=false`→`None`；`DiarizationUnavailable`（套件/模型缺失）→`None`＋warning；其餘任何例外→`None`＋warning（`except Exception`，fail-soft 契約註解） |
| `backend/services/diarization.py::diarize_async` | `asyncio.wait_for(..., DIARIZATION_TIMEOUT_SECONDS=900)`；`TimeoutError`→`None`＋warning；執行緒派工例外→`None`＋warning |
| `backend/services/task_processor.py::_label_speakers` | 無 chunks→`None`；**時間軸守門在 diarization 之前**（有效時間區段 < 一半即跳過，避免 Apple null→0.0 產生錯誤標籤）→`None`；diarization 回 `None`→`None`；對位結果空→`None`；任何例外→`None`＋warning。**全部只影響標註，不拋出任務** |
| `task_processor.py::_obtain_transcript` | 標註成功→以 `get_asr_cache_signature()`（含 diarization 參數）存快取；標註失敗→**只存** `get_unlabeled_asr_cache_signature()`（`"diarization:off"`）→ **失敗不污染標註快取**，模型恢復後仍會重試標註 |
| `file_manager.py::_diarization_cache_signature` | `ENABLE_DIARIZATION=false`→`"diarization:off"`；否則簽章含 threshold／num_clusters／min_duration_on／min_duration_off（參數變更即換 key）；快取路徑由 signature 決定（`get_cached_transcript/save_transcript_cache` 皆帶 signature） |
| `backend/core/asr_model_resolver.py::build_asr_cache_signature` | 新增 `diarization` 欄位（預設 `"diarization:off"`）併入 sha256 簽章 → 有/無標籤逐字稿不會互相誤用 |

### 5.2 聚焦測試與全套測試 [VERIFIED]
```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=./data .venv/bin/python -m pytest tests/test_diarization_failsoft.py tests/test_speaker_transcript.py -q
→ 42 passed, 2 warnings in 1.05s

cd /Users/hsiaojohnny/dev/convert && DATA_DIR=./data .venv/bin/python -m pytest tests/ -q
→ 784 passed, 2 skipped, 3 warnings in 9.73s   （與預期 784/2 一致）
```
聚焦測試覆蓋：停用、模型缺失、sherpa import 失敗、引擎載入例外、音檔缺失、解碼後 0 樣本、引擎 0 turn、引擎例外、async 逾時、thread 派工失敗、無 chunks、時間軸不可用（全零時間軸）、diarization 回 None、標註例外吞掉、標註成功路徑；對位側：0 秒 segment、無重疊時就近指派、gap 合併、標籤排序與格式…等 [VERIFIED]。

### 5.3 C4 判定
**PASS**：四種失敗模式（模型缺失／逾時／解碼失敗／時間軸不可用）皆回 `None` 且任務照常完成；快取以獨立 key 隔離，失敗不污染標註快取；另有真實運行實例（LM Studio 不可用→校正熔斷→任務完成）佐證同類 fail-soft 行為。

## 6. 額外稽核

### 6.1 是否超出計畫範圍 [VERIFIED]
```
git status --short（20:36 首次觀測）: 19 modified（含 .env.example/.env.local.example/README.md/
backend/api/routes.py/backend/core/asr_model_resolver.py/backend/core/config.py/section_meeting.py/
prompts.py/main.py/models/schemas.py/file_manager.py/summarization.py/task_processor.py/config.yaml/
doc/README.md/frontend/js/app.js/pyproject.toml/requirements.txt/tests/test_api_routes.py/uv.lock）
＋ untracked：backend/services/diarization.py、speaker_transcript.py、scripts/download_diarization_models.py、
tests/test_diarization_failsoft.py、tests/test_speaker_transcript.py、tests/test_cloud_provider_switch.py、
doc/規格與設計/發言者分離與主席裁示-研究與設計.md
git diff --stat: 20 files changed, 498 insertions(+), 58 deletions(-)（當時）
```
- plan §3 列舉範圍：diarization.py、speaker_transcript.py、config.py、task_processor.py、file_manager.py、section_meeting.py＋summarization.py、download_diarization_models.py、requirements.txt、docs → **全部在內**。
- 超出 plan §3 列舉但有正當依據者：`asr_model_resolver.py`（快取簽章，屬 §3.5 語意）、`tests/*`、`frontend/js/app.js`、`api/routes.py`、`models/schemas.py`、`main.py`、`.env*`、`README.md`、`uv.lock` —— 其中 routes/schemas/main/app.js/.env* 屬**使用者中途要求的雲端 provider 切換（Gemini→Ollama Cloud）**，已落檔於同任務 `goal.md`（20:35）與 `handover.md`（20:37，皆非本次稽核所寫）；未見與 plan 語意衝突。
- 未發現可疑/無關改動（無 data/ 產物或模型檔進入版控；`models/` 為 gitignore）[VERIFIED 部分：`git status` 未列 models/ 或 data/]。
- **注意**：20:38 觀察到 git index 已被外部程序 stage（`.git/index` mtime 20:38；狀態由 ` M` 變 `M `/`A `），並新增 `goal.md`/`handover.md`。**本稽核未執行任何 git 寫入**（僅 status/diff/log 唯讀指令）；此為併行工作者的動作，記錄備查。

## 7. 額外發現

1. `data/outputs/` 存在與主輸出同內容的複本（`_record.md`、`_record.docx`，sha256 相同）→ 清理項，非缺陷。
2. `GET .../result?format=md&doc=attachment` 回 HTTP 400「附件僅支援 docx 格式」；使用者提供的 endpoint 矩陣含此組合，實際設計僅支援 docx [VERIFIED]。
3. 摘要品質驗證器仍回報「待辦事項遺漏 47 項」（補強 2 輪後）；屬 WARNING 級、不影響 `summary_failed`，但顯示雲端摘要完整性仍有限 [VERIFIED]。
4. 日誌仍有 `device_detector: 偵測到 Apple Silicon，使用 MPS 加速` 訊息，而 Apple ASR 路徑不使用 MPS → 易誤導（handover §4 亦自承待修）[VERIFIED 日誌存在；語意誤導為 INFERRED]。
5. `section_meeting.py` 的裁示歸屬規則無 CI 斷言（僅 `prompts.py`↔`config.yaml` 配對受測）→ 「三處同步 CI 強制」說法需下修 [VERIFIED]。
6. 本稽核未抽聽音訊（能力限制），所有「換手合理」結論僅止於時間對位層級 [VERIFIED 之限制聲明]。

## 8. 殘留風險

| # | 風險 | 級別 | 依據 |
|---|---|---|---|
| R1 | 裁示歸屬仍屬提示詞級保證＋人工抽驗；無程式級驗證器（計畫 R-8／設計 §4.4） | 中（CORE 相關） | §3.3、§3.4 |
| R2 | 抽驗 7 案例有 3 例非主席內容被寫成科長裁示／交辦（含 1 例彙整表承辦寫「科長」） | 中 | §3.2 E/F/G |
| R3 | 分群碎裂：8 群中 5 群為 <5 秒碎群、13 個 0 秒標籤、1 處句中被拆換手 | 低－中 | §2.2、§2.3 |
| R4 | 無 ground truth（真實人數、逐句歸屬皆未知），8 群 ≠ 8 人；S4–S8 可能是同一人的碎群或雜訊 | 中 | §2.2 |
| R5 | ASR 同音錯字（例：公務車/公路車）與長段落合併（S1 最長單段 336 秒）使人工回溯成本提高 | 低 | §2.4、§2.1 |
| R6 | 雲端摘要完整性：待辦遺漏 47 項警告仍在；語意校正因 LM Studio 未開全程未生效 | 低 | §4.4、§6.3 |
| R7 | 重疊語音（B1）、100% 純度（B2）、真實姓名（B3）均未處理——計畫已列 BEST_EFFORT | 低（非 blocking） | plan §0 |

## 9. 未竟事項（明確未實作／未驗證）

1. **S3 未實作**：無「裁示→`speaker_id`＋`evidence_time`＋`verbatim_quote`」結構化欄位、無 `RULE_VIOLATION_NON_CHAIR` 等確定性驗證器、無可下載的裁示對照 JSON／附件（設計 §4.2/§4.4）。
2. 角色推斷進階設計（簽到單／議程綁定、程序語規則 R1–R8、人工複核隊列、`degraded_mode="no_role"`）未實作。
3. 未驗證項：人工聽感核對（無能力）、重疊語音分離品質、Windows/Docker 路徑實機驗證、`doc=attachment&format=md` 之外其他 endpoint 組合。
4. 併行變更（provider 切換、`goal.md`/`handover.md`、git staging）發生於稽核期間，未納入本次判定；`plan.md` §3 未列出 provider 切換（僅見於 goal/handover）→ 計畫文件與實作清單存在登載落差。

## 10. 判定彙總

| 項目 | 判定 | 關鍵證據 |
|---|---|---|
| C1 分群標籤逐字稿 | **PASS** | 183 標籤／8 群／格式零錯誤／統計區塊存在；5 處時間軸對位重轉寫一致；碎裂 caveat 已記錄 |
| C2 主席裁示歸屬 | **PARTIAL** | 規則三處存在、4/7 案例正確回溯主席；3 案例非主席內容入科長段；無結構化 quote/時間欄位、無程式級驗證 |
| C3 真實音檔 E2E | **PASS** | `completed`/`progress=100`/`summary_failed=false`/709.1s；md+docx 下載 200；OOXML 有效；Ollama Cloud 5 次雲端呼叫成功 |
| C4 fail-soft | **PASS** | 四類失敗皆回 `None`、時間軸守門先於 diarization、快取分 key；42 聚焦測試＋784 全套測試綠燈 |
| 測試總表 | **PASS** | `784 passed, 2 skipped`（符合預期） |
| 範圍控制 | **PASS（含登載落差）** | 未見無關改動；provider 切換屬使用者中途要求但未登載於 plan §3 |

---

## 附錄 A — 主線複核更正（2026-09-13 22:20，append-only：原文未刪改，僅追加更正）

本附錄由**主線**（非原稽核者）於報告產出後、以 fresh-context 唯讀子代理複核時發現的三處「計數措辭」更正；**不改變 gate（ACCEPTED）與 C1–C4 任何判定**。更正均有可重跑指令：

1. **紀錄檔 `發言者N` 引註數**：原 §3.3 寫「全檔僅 5 處 `發言者N` 引註」。實測為 **5 行、共 10 處**：
   `rg -o '發言者[0-9]+' data/outputs/0903-科務會議_3d7f76d3.md | wc -l` → `10`；分布於 md 行 `84`／`85`／`86`／`92`／`93`（全在「一、科長轉知局務會議工作報告及相關注意事項」區塊）。結論方向（僅第一區塊有、`二、`／`三、` 皆無）不變。
2. **決議彙整表列數**：原 §3.3 寫「65 列彙整表」。實測為 **63 筆資料列**（`65` 是含表頭與分隔線的 pipe 行數）：
   `awk '/決議事項辦理情形彙整表/,0' data/outputs/0903-科務會議_3d7f76d3.md | rg -c '^\|'` → `65`（含 2 行表頭）→ 資料列 63；與本報告 §3.4／§4.2／§10 的「63」一致。
3. **雲端呼叫次數**：原 §4（C3 證據）與 §10 寫「5 次雲端呼叫成功」。實測為 **7 次**（全程皆 Ollama Cloud，0 次 Gemini）：
   `logs/app.log` 之 `Ollama Cloud 摘要生成成功，模型: deepseek-v4.1-flash` 出現於 `20:20:13`／`20:21:02`／`20:21:20`／`20:22:10`／`20:23:45`／`20:24:24`／`20:27:17`（chunks 1,177／1,156／1,111／871／1,543／1,436／1,615；期間無失敗重試紀錄）。

三處更正後，報告所述證據仍全部成立；gate 與 C1 PASS／C2 PARTIAL／C3 PASS／C4 PASS 不變。
