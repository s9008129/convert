# 殘餘缺口登錄報告（residual-gap-01）

- 任務 ID：`T20260922-2037-02-local-model-quality-parity`｜角色：殘餘缺口登錄員（唯讀＋單一報告檔）
- Repo／分支／HEAD：`/Users/hsiaojohnny/dev/convert`、`fix/qwen-local-quality-parity`、`ea510e5`
- 製表時間：2026-09-23 12:40–12:45（Asia/Taipei；12:43 依 `attempt-E5-qwen27b-p5/README.md` 產品層量測回填一次）
- 方法（全部可回溯）：`git log --oneline -40`／`git show --stat`／`rg`／`sed -n` 讀既有檔與 runtime log；**未修改任何既有檔、未 `git add`／`commit`、未跑 pytest、未呼叫任何模型**（gemma E5 重跑同期進行中，全程避開重 CPU）。本報告為唯一新增檔。
- 判讀限制：狀態＝「repo 內可查證的程式／資料」判定；「本輪是否已驗證」只認有產物的證據，commit message 的聲稱一律標「未重跑」。E5 場（qwen）runner 未落地量測，故相關數字以「in-run 覆蓋檢查」與「本報告輕量字面計數」呈現並明確標示，**不冒充正式量尺**。
- 來源依據：`e2e/quality-parity-01/report.md` §七（建議 1–5）與 §A.4（建議 6）；`e2e/timing-forensics-02/report.md` §7；`e2e/glossary-replay-verify-01/report.md`（P5-A.1 離線獨立複核）；各場 runtime log 與 attempt 產物。

---

## 一、品質建議逐條登錄（來源：quality-parity-01 §七；第 6 條來自 §A.4）

| # | 建議 | 狀態 | 證據（commit 或 file:line） | 對使用者的影響（「我的紀錄會變好多少？做了沒？」） | 本輪是否已驗證 |
|---|---|---|---|---|---|
| 1 | 校正層改「保護詞表＋同音替換白名單」驅動 | 已實作 | `7176929`（機制）、`5247436`（詞表擴充＋紀錄層）、`ce99502`（觸發判定 perf）；`backend/core/glossary.py:128`（`protected_terms`）、`:150`（`apply_known_corrections`）；`backend/services/correction.py:126`（`_is_glossary_correction`）、`:137`（`_would_destroy_protected_term`）、`:144`、`:338`（確定性套用）；資料檔 `data/glossary/確定性誤辨校正.txt`（180 行；實測 43 組配對、47 組排除複合詞、14 個保護詞） | 「內機→內稽」這類 ASR 誤辨**不再取決於你載入哪顆模型**（27B 以前漏修它，直接吃掉一條核心事實）。換模型也會被修好 | 部分已驗證。離線重播獨立複核：43 組全數命中、115 次替換、「→11 處」結尾可重現（`glossary-replay-verify-01/report.md`；但前置基準「60 處」不可重現，六種定義實測 24/22/57/116/126/128，下降方向不變）。E2E（產品層，`attempt-E5-qwen27b-p5/README.md`）：逐字稿亂碼 109→15 次（46→13 型）、紀錄亂碼 10→5 次、`F021`（內稽）已涵蓋；但 runner verdict 未落地（見 §三-3） |
| 2 | 數字／金額強制進表 | 部分實作 | `818b71e`（整串數字邊界＋行首編號不算證據；`backend/services/summarization.py:204-208`、`:1580`、`:1600`、`:1882-1888`）；金額待確認訊息 `backend/core/fidelity_checks.py:847-855`；併入既有補強清單 `backend/services/summarization.py:3137-3139`（不新增閘門） | 有算式可回推的數字（13,600＝17×800）會被補進紀錄；孤立的舊例數字（吃便當 `600` 元）仍可能漏，你得自己翻逐字稿 | **in-run 已大幅改善、正式量尺未跑**。E4（`818b71e`）補強後仍漏 15／600／100（E4 app log:105、停損 :112；`attempt-E4.../run_notes.md:73` `number_missing_tokens`＝3 項）＝未達「為空」驗收。E5-qwen 第 1 輪列 15／600／100（E5 app log:107）→ 第 2 輪僅剩日期（:112）→ 終局 `cov_missing_number=0`（9/9，:118）＝目前最佳；`measure_record_quality.py` 的 `number_missing_tokens` 於 E5 尚未公布（`README.md` 未列） |
| 3 | 不確定專名可見性標註（「（疑似：…）」） | 部分實作 | 僅「補強提示訊息」要求模型自己標：`backend/core/fidelity_checks.py:461-462`（疑似變體）、`:467-468`（疑似自創）、`:854-855`（疑似捏造）。**紀錄層後處理標註器不存在**：`rg 疑似 backend/` 只再中 `summarization.py:1349／3419`（機敏／CPU offload），無任何「生成後在名詞後插入標註」的程式 | 佩魯／西龍股／電做科這類**無 ground truth 的亂碼仍原樣進紀錄**；你無法從紀錄分辨那是真實單位名還是聽錯 | 未達驗收。E5-qwen 紀錄仍有 `西龍股`×2／`省員`×1／`平上`×1／`煙酒文神股`×1（與 `attempt-E5-qwen27b-p5/README.md` 一致：E4 7 型/10 次、E5 4 型/5 次，且全屬「無 ground truth 不登錄」類）；`unsupported_entities_count` E4＝3（`attempt-E4.../record_quality.json`），E5 未量 |
| 4 | 決議表欄位不留空（空白格填「（待確認）」） | 未實作 | 只有「日期骨架佔位符」修復：`backend/core/text_postprocess.py:376`（`_MISSING_TEXT`）、`:391-413`（`normalize_unfilled_placeholders`，處理的是模型照抄範本佔位符）；**沒有**「空白決議格填（待確認）」規則（`rg 決議 backend/core/text_postprocess.py` 無填補邏輯） | 決議表的承辦單位／解除列管／繼續列管欄**還是空白**（六場皆 2/3 空白、後兩欄 100% 空白，quality-parity-01 §A.2）；你得自己回逐字稿找 | 未驗證（規則不存在）。E5-qwen 紀錄仍有 12 個空表格欄（E4 13；本報告輕量計數） |
| 5 | 臨時動議寫入少數意見 | 未實作 | 模板節已存在：`backend/core/prompt_templates/section_meeting.py:83`；`rg 少數意見 backend/ tests/`＝**0 命中**；無「非主持人／發言量前 3 名之外」判準 | 第三節常是「（待確認）」；少數／反對意見不會進紀錄 | 未驗證 |
| 6 | 紀錄層再劣化防護（§A.4 新增） | 已實作 | `5247436`；`backend/core/text_postprocess.py:548`（`apply_record_term_fixes`）＋`:572-574`（套用同一份詞彙表 `錯=>對`）；接線 `backend/services/summarization.py:3260`（`finalize_record`）→ `:3267-3274`（僅 `mode == "local"`；雲端輸出 byte 級不變） | 模型在生成階段自己把「差勤」寫成「拆勤」時，**紀錄層有第二道確定性防線**（同詞表、跨模型、跨 OS 共用） | 部分已驗證。E5-qwen 紀錄已無 `猜情／拆勤／工廠科`（E4 尚有 `猜情`×1、`工廠科`×2）＝紀錄亂碼 7 型/10 次 → 4 型/5 次（`attempt-E5-qwen27b-p5/README.md`）；紀錄層契約測試在 `tests/test_record_term_fixes.py` |

> 建議 1 的附帶更正：commit `5247436` message 記「45 個排除複合詞／15 個保護詞」，實測（含 `glossary-replay-verify-01` 獨立複核）為 **47／14**；機制不受影響，數字以檔案實測為準。

## 二、耗時面向建議（來源：timing-forensics-02 §7）

| # | 建議 | 狀態 | 證據 | 對使用者的影響 | 本輪是否已驗證 |
|---|---|---|---|---|---|
| T1 | 大呼叫吃 prompt 前綴快取（固定規則集中到最前面） | 未實作 | timing-forensics-02 §7-1；E4 三大呼叫 `cached`＝0／1,824／1,856、TTFT 124.1–187.6 s | 換模型比品質的每場約可省 **180–240 s（−18%～−24%，推導值）** | 未實測（本輪未動提示組裝順序） |
| T2 | 逐字稿快取重用 | 部分（機制已存在；「換模型重用」未自動化） | 手動兩場快取命中（ML22:874／ML22:966）；快取鍵含音檔 sha256；E2E runner 參數清單（`scripts/e2e/run_owned_e2e.py`）無 reuse 選項 → runner 場都冷跑 | 同音檔重跑省 ASR＋diarization **168.9 s（−17%）**，且不影響內容 | 已驗證（手動場實際命中）；runner 場未支援 |
| T3 | 真缺口停止條件寫成顯性終態 | 未實作 | §7-3；E4 停損後 15／600 缺口留在紀錄（E4 app log:112）；E5 則改以「跑滿 2 輪到缺口歸零」處理（見 §三） | 每場最多再省 ~230–260 s，但屬**語意／閘門行為變更**，需走 Plan/Review，不得由執行者自行放寬 | 未實作 |

## 三、本輪明確未驗證／無法驗證（含時間戳）

1. **Windows 11＋RTX 4090＋Ollama 實機**：僅靜態稽核 — `model-agnostic-audit-01/report.md`（`MODEL_AGNOSTIC_WITH_NOTES`，六個品質層零模型名分支）＋`crossos-p5-audit-01`（`WINDOWS_SAFE_WITH_NOTES`）；無任何實機產物。
2. **`gemma-4-31B-it-MLX-4bit` 的 P5 後 E2E**：12:40 首次嘗試被 runner decision-validity gate 擋下（worktree 不乾淨）＝`attempt-E5-gemma31b-p5/run_summary.json` `verdict=FAIL`、`failure_reasons=[repo worktree 不是 clean]`；12:41 起以 clean HEAD（`ea510e5`）重跑中（`attempt-E5-gemma31b-p5b`，runtime `p4-gemma31b-e5b`），**結果未定**。
3. **E5-qwen（`qwen3.8-27b-splash`，build `ce99502`）runner 層無 verdict**：任務已完成（`耗時 1273.7 秒`、12:35:48）、DOCX 已出（12:38:01）；`attempt-E5-qwen27b-p5/README.md` 已如實登錄事故（runner 以 `nohup … &` 背景啟動後被執行環境回收，backend child 存活把任務跑完）與**產品層量測**（逐字稿亂碼 109→15 次、紀錄 10→5 次、`coverage_all 0.6866／core 0.7857`、`F021` 已涵蓋、紀錄亂碼「≤3」自訂門檻未達＝實測 5）。runner 的 16 項 checks／verdict 待 `attempt-E5-qwen27b-p5b` 重跑（README 記載；截至製表該目錄尚未建立）。
4. **無 ground truth 的亂碼仍在**（刻意不登錄，`5247436`／`7176929` message）：佩魯／西龍股／電做科／工廠科／煙酒文神股／於正／審兒園／省員／土地稅卡；E5-qwen 紀錄仍見 西龍股／省員／平上／煙酒文神股。
5. **`審員` 刻意不登錄**：審核員／審計員兩解互斥（同段落另有正確形「審核員」，`5247436`）。
6. **C5 雲端 runner 未收尾**（`f001e93`）；所有品質數字為單次抽樣（temperature 0.6/0.7），**不可外推**；E1–E4 單模型僅一場。
7. **建議 2／3／4／5 的驗收指標本輪皆未達**：`number_missing_tokens` 尚未有「為空」的正式量測（E5 僅 in-run＝0）；疑似標註器不存在；決議表空白率未動；少數意見 0 條。
8. **決議類覆蓋檢查實際 no-op**：「決議期望集合為空」在 E3／E4／E5 都出現（E4 app log:102／109；E5 app log:104／111／117）→ `cov_expected_decision=0`，代表**這幾場的「決議對帳」保障沒有真正跑到**；E4 獨立驗收已列為登錄缺口（`attempt-E4.../verify_independent.md:132`）。
9. **E5 補強輪曾引入新捏造**：第 1 輪後檢查抓到「紀錄出現逐字稿沒有的『1000元』」（E5 app log:113）→ 第 2 輪移除（終版紀錄已無 1000 元）；證明補強輪本身有引入失真風險（此為機制已知取捨，需持續觀測）。
10. **本報告本身是新增未提交檔**（依任務硬約束不 `commit`）；後續 E2E 的 clean-worktree gate 會看到它 → 重跑前需先登錄。

## 四、殘餘風險誠實清單（只列未解決）

- **品質還沒到雲端水準**：E4 `coverage_all 0.7015／core 0.8214`、E5 `0.6866／0.7857` vs 雲端 `0.8060／0.8929`（`README.md`＋quality-parity-01 §A.3）——P5 校正波把「亂碼」大幅壓低，但**事實覆蓋率沒有同步拉近雲端**（差異落在 temperature 0.7 單次抽樣噪音內）。
- **數字遺漏的「正式量尺」未歸零**：E4 漏 15／600／100；E5 僅 in-run 覆蓋 9/9＝0 缺漏，`measure_record_quality.py` 未在 E5 公布。
- **決議表空白格與臨時動議少數意見兩條建議完全沒動**：你仍會看到空白格與「（待確認）」。
- **「（疑似：…）」後處理標註器不存在**：無 ground truth 亂碼（9 型清單）以原形直接進紀錄。
- **補強輪的兩難**：E5 跑滿 2 輪才讓日期歸零，牆鐘 1273.7 s（比 E4 多 ~290 s）；且第 1 輪曾捏造 `1000元`（已清）。收斂速度與品質仍在拉鋸。
- **抽樣變異大**：E3→E4 同模型、只差 build 就 0.7761→0.7015 → 任何單場數字不得當結論。
- **Windows／Ollama 未實機驗證**；**gemma 31B 的 P5 後 E2E 未完成**。
- **決議對帳（建議 2/4 的資料前提）實際上沒生效**：決議期望集合抽取為 0，已連續三場。
