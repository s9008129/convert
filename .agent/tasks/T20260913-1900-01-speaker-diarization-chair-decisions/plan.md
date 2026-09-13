# T20260913-1900-01-speaker-diarization-chair-decisions — Plan

TASK_ID: T20260913-1900-01-speaker-diarization-chair-decisions
PLAN_REVISION: 1
TASK_CLASS: STANDARD
REVIEW_REQUIRED: YES
INDEPENDENT_ACCEPTANCE_REQUIRED: YES
E2E_REQUIRED: YES

## 0. Goal Contract（白話）

使用者痛點（Owner 原話轉譯）：
1. 45 分鐘多人會議錄音，AI 逐字稿無法分辨誰在說話（主管？承辦？廠商？），
   整理紀錄時無法精準知道哪一段話是誰說的。
2. 最重要的是：要能辨識出**這一場會議的主席（科長）所下的決議（裁示）**，
   因為那是整場會議的核心與後續方向。

Primary outcome（驗收主體）：
- 上傳多人會議錄音（驗證檔：`~/Downloads/0903-科務會議.m4a`）並選「科務會議」模板後：
  a. 逐字稿可看到**發言者分群標籤＋時間戳**（至少 A/B/C 可區分；同一人不被拆成多個標籤的比例愈高愈好）。
  b. 會議紀錄的「主席裁示／決議」內容**確實來自主席發言**，且可回溯（時間＋發言者＋原文）。
  c. 雲端模式（Gemini）+ 科務會議模板端到端可完成，輸出 Word/Markdown 正常。

CORE（不做＝任務失敗）：
- C1 說話者分群逐字稿（diarization → 對位 → 標籤逐字稿；含時間戳）。
- C2 主席裁示萃取規則：紀錄中「科長指示及提醒事項／決議」只能來自主席（科長）發言或
     其轉述之上級指示；他人（承辦、廠商、其他單位）發言不得寫成主席裁示。
- C3 以真實音檔（0903-科務會議.m4a）完成 E2E 驗證並留存證據。
- C4 fail-soft：diarization 不可用時，系統行為與現行版本完全一致（不得因新層失敗而擋任務）。

SUPPORTING（提升品質，非全域 veto）：
- S1 角色推斷（主席/承辦/廠商/其他單位）＋角色證據（quote+time）。
- S2 發言者統計（發言量、turn 數）輔助角色判斷。
- S3 主席裁示對照表（可下載附件或另存 JSON），供人工核對。

BEST_EFFORT（明確不 blocking）：
- B1 重疊語音（兩人同時說話）完美分離。
- B2 逐字稿 100% 發言者純度（遠場會議不可能）。
- B3 依人聲辨識真實姓名（法律與技術上皆不承諾；角色以內容證據推斷）。

全域 blocking 條件（僅此）：
- 若 C2/C3 任一無法以真實音檔證據證明，任務不得宣稱完成。

## 1. 現況與根因（第一性原理）

現行流程：上傳 → ASR（Apple/Whisper）→ 逐字稿（純文字）→ 確定性清理 → LLM 校正
→ LLM 摘要/紀錄（模板系統提示詞）→ DOCX/MD。

根因（資訊在哪裡遺失）：
- R1 聲學資訊從未被使用：ASR 只輸出文字，發言者身分（voice identity）沒有任何來源。
- R2 結構資訊被丟棄：ASR 明明有 segment 時間戳（Apple：304 段/10 分鐘，中位 1.08s；
  Whisper：chunk start/end），但 `task_processor._obtain_transcript` 只取 `.text`，
  時間戳全數在流程中被丟棄（`backend/services/task_processor.py:131-146`）。
- R3 模板提示詞只能靠語意猜測主席：`section_meeting.py` 已寫「主持人通常為科長」，
  但沒有發言者標籤當證據，模型無法區分「科長裁示」與「他人發言被科長覆述」。
- R4 無追溯機制：紀錄中的每句話無法對回逐字稿片段，錯誤無法被發現。

## 2. 技術選型（研究結論）

候選與評估：見 `doc/規格與設計/發言者分離與主席裁示-研究與設計.md`（研究報告本體）
與 subagent 研究檔案（`/tmp/research/diarization_landscape.md` 等）。

決策方向（待調校實驗定案參數）：
- 首選：**sherpa-onnx offline diarization**（pyannote segmentation-3.0 + 3D-Speaker CAM++ zh）
  - 全離線、無需 HF token（模型在 GitHub releases）、CPU 可跑（實測 RTF≈0.06）、
    跨平台 wheel（macOS arm64 / Windows / Linux）、Python API。
  - 實測（10 分鐘切片）：覆蓋率 93.2%、主持人 cluster 佔 65.6%（符合本場會議預期）、
    threshold 需調校以解 over-clustering（57 clusters → 目標 5~12）。
- 次選：pyannote.audio（gated/HF token；作為品質對照，不作正式部署候選，除非首選品質不足）。
- 明確淘汰（現階段）：NVIDIA Sortformer（GPU/CUDA 依賴，違反 CPU 可跑約束）；
  雲端 diarization API（違反離線約束）；Apple 原生（macOS 26 SpeechAnalyzer 無 diarization API）。

## 3. 設計（最小完整變更）

新增模組：
1. `backend/services/diarization.py`（新）
   - `diarize_file(audio_path) -> Optional[DiarizationResult]`：ffmpeg 解 16k mono → sherpa-onnx
     → turns[(start,end,speaker)]；任何失敗回 None＋warning（fail-soft，C4）。
   - 模型路徑解析：`models/diarization/`（Docker 掛載 `/app/models` 同構）。
2. `backend/services/speaker_transcript.py`（新）
   - `build_speaker_labeled_transcript(segments, turns) -> (labeled_text, stats)`
   - 對位規則：每個 ASR segment 以「時間重疊最大」的 turn 決定 speaker；連續同 speaker
     且 gap < 1.5s 合併成 utterance；輸出格式：
     `[00:12:34-00:12:58] 發言者1：…`
   - 開頭插入統計區塊（各發言者發言量%、turn 數）供 LLM 判角色（S2）。
3. `backend/core/config.py`（改）：`ENABLE_DIARIZATION`、`DIARIZATION_THRESHOLD`、
   `DIARIZATION_NUM_CLUSTERS`、`DIARIZATION_MODEL_DIR`、`DIARIZATION_MIN_DURATION_*`。
4. `backend/services/task_processor.py`（改）：ASR 後（或與 ASR 平行）呼叫 diarization；
   成功→標籤逐字稿（供校正/摘要/下載）；失敗→照舊（純文字）。
5. `backend/services/file_manager.py`（改）：cache signature 併入 diarization 設定；
   逐字稿下載檔在有分群時輸出標籤版（同一檔案，維持既有檔名與端點）。
6. `backend/core/prompt_templates/section_meeting.py` + `backend/services/summarization.py`（改）：
   - 萃取提示詞：新增「發言者與裁示歸屬」欄位（時間＋發言者＋原文引述）。
   - 科務會議系統提示詞：主席裁示歸屬規則（C2）與證據要求。
   - 通用模板同步最小規則（一般會議）：主席/主持人裁示 vs 他人意見。
7. `scripts/download_diarization_models.py`（新）：下載/驗證模型（idempotent）。
8. `requirements.txt`（改）：新增 `sherpa-onnx`（平台 wheel 存在；Apple 路徑不載入 torch）。
9. docs：`doc/規格與設計/發言者分離與主席裁示-研究與設計.md`（研究＋設計）
   ＋ README/使用者手冊最小更新（逐字稿含發言者標籤說明）。

語意契約（凍結）：
- 發言者標籤為**系統自動分群**，非姓名；紀錄不得把「發言者N」當人名寫入。
- 主席裁示必須有逐字稿依據；無法確認主席身分時，以「（待確認）」呈現，不得硬猜。
- diarization 失敗＝回退現行行為，不改變任何既有 error/fallback 語意。

## 4. 驗證計畫

V1 單元測試：對位/合併/標籤格式、fail-soft、cache signature、模板 prompt 規則、
   既有測試不回歸（`pytest tests/`）。
V2 真實音檔 E2E（C3）：
   - 用 0903-科務會議.m4a（2695s）以**雲端 Gemini + section_meeting** 跑完整流程
     （owned E2E runner 或 API 上傳），驗收：
     a. 逐字稿含發言者標籤與時間戳（抽驗 ≥5 處發言者切換合理）。
     b. 紀錄「二、科長指示及提醒事項」與「決議彙整表」內容可回對到主席發言區段。
     c. `summary_failed=false`、DOCX/MD 可下載。
     d. 與 baseline（現行無標籤輸出）比較：裁示歸屬正確性改善（人工抽驗 ≥3 案例）。
V3 獨立驗收（Stage 05）：由未參與實作者的 fresh context 子代理，用真實輸出檔
   （md/docx/逐字稿）與 evidence 做 requirement-by-requirement 稽核。

## 5. 風險與降級

- 風險1 遠場 over/under-clustering：以 threshold 調校 + 統計（最大 cluster）緩解；
  仍失敗時，主席裁示萃取仍可用「發言量＋主持語句」語意證據（S3 證據鏈）。
- 風險2 Docker/Windows 首次使用需下載模型：下載腳本＋缺模型時 fail-soft（不擋任務）。
- 風險3 逐字稿變長（加入標籤）造成 LLM 輸入膨脹：標籤格式精簡（時間區間+短標籤），
  雲端 chunk 切分不得切斷 utterance（以 utterance 邊界切）。
- 風險4 既有測試對逐字稿格式/快取的斷言：逐一更新並記錄。

## 6. 停止／升級條件

- 若真實音檔 E2E 顯示「主席裁示歸屬」無可證實的改善 → 停止並回報 PLANNER_REPLAN。
- 若 sherpa-onnx 在此音檔連「主持人 vs 其他人」都無法穩定區分 → 升級方案（pyannote/其他），
  並回到 Stage 01 修訂本計畫（不得在實作中自行改語意）。
