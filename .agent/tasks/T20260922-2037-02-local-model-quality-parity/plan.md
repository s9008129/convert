# T20260922-2037-02-local-model-quality-parity — PLAN（P2 可查核性波）

- TASK_ID: `T20260922-2037-02-local-model-quality-parity`
- PLAN_REVISION: 2（rev 1＝品質波開場：27B／MoE 實測與根因量測；rev 2＝把「模型無關的可查核性修復」定為本波 CORE，並把其餘槓桿列為後續波）
- TASK_CLASS: STANDARD｜REVIEW_REQUIRED: YES｜INDEPENDENT_ACCEPTANCE_REQUIRED: YES｜E2E_REQUIRED: YES（真實音檔 `0903-科務會議.m4a` ＋ `section_meeting` ＋ `local`）
- 分支：`fix/qwen-local-quality-parity`（自 `fix/local-lmstudio-record-quality` HEAD `4f1fb23` 開出）
- 前波：`T20260922-1930-01-local-record-quality-parity`（P1 品質波，已完成並推送；本波不重做其成果）

## 0. 使用者需求（不可縮小）

1. 讓 Mac ＋ LM Studio（`qwen3.8-27b-splash` dense 27B、`qwen3.6-35b-a3b-splash` MoE 35B-A3B）用 `section_meeting`
   生成的會議紀錄品質「接近雲端 Gemini」。
2. 深度的研究與優化規劃。
3. 另開分支修好 27B／35B 兩顆模型的品質問題。
4. **新增需求（本輪）**：優化機制必須**與模型無關**——日後在辦公室 Windows 11 ＋ RTX 4090 ＋ Ollama、
   跑 Gemma 4 31B 時也要一體適用，不得只為 LM Studio 現有模型客製。

## 1. Goal Contract

**設計原則（回應需求 4）**：品質保證必須落在「模型無關的確定性層」——
①逐字稿事實層（段落時間表、詞彙表、來源標註）、②確定性後處理、
③確定性驗證與補強清單。提示詞只負責「告訴模型規則」，不得成為品質的唯一依靠。

**CORE（本波，具全域阻斷力）**

- **CORE-1 出處標註真實性**：地端紀錄的正文出處標註，其時間戳必須落在逐字稿的真實段落上，
  且優先落在**該標註指名發言者**的段落內。
  - 量測：`exact_tag_ratio`（時間戳恰為某真實段落起點／正文標註數）與
    `tags_inside_same_speaker_segment / tags_total`。
  - 基線（實測，0903 場）：MoE 35B `exact 4/27 = 14.8%`；dense 27B `exact 46/61 = 75.4%`。
  - 驗收線：吸附後 `exact_tag_ratio ≥ 0.8` 且 `traceable_tag_ratio ≥ 0.95`。
  - 退化防線：`body_source_tag_count ≥ 17`（前波 CORE-1 防線沿用；避免模型少寫標註換分數）。
- **CORE-2 模型無關性**：修復必須位於 LM Studio／Ollama 共用的地端管線
  （`_summarize_with_local_pipeline` → `_finalize_record_text(mode="local")`），
  且不得依賴模型名稱、模型家族或引擎特有參數。
  - 驗收：單元測試以「假引擎」與純函式契約證明；程式碼不得出現模型名分支。

**SUPPORTING**

- S-1：量測儀器 `measure_record_quality.py` 增列 `tag_traceability`（與產品共用同一份段落解析定義）。
- S-2：研究文件新增「P2 波」章節，記錄 27B vs MoE 實測對照與模型無關設計。
- S-3：真實音檔 E2E（MoE；時間允許再補 27B）＋吸附前後對照。

**BEST_EFFORT**：27B 的第二輪 E2E、Ollama 引擎路徑的實機驗證（本機無 Ollama 服務）。
**明確排除**：溫度／取樣再校準（P1-3，需 A/B 實驗設計）、覆蓋率檢查表（P1-4）、
Gemma 4 31B 實測（本機無模型；48GB 承載性 `[UNVERIFIED]`）。

**全域阻斷**：只有 CORE-1／CORE-2 具阻斷力。

## 2. 本波根因（實測）

| ID | 根因 | 證據 | 影響 |
|---|---|---|---|
| R20 | 模型寫得出標註，但時間戳多半是「段落內的任意秒數」 | MoE：27 個標註僅 4 個落在段落起點；27B：61 個中 46 個 | 標註看似可查核、實際查不到 → 使用者對紀錄的信任度低於雲端 |
| R21 | 同一份紀錄中 25/27（MoE）、61/61（27B）的時間戳**落在正確發言者的段落內** | 逐字稿段落時間表比對（本波新儀器） | 證明可用「吸附」確定性修復，不需重生成 |
| R22 | 前波的「可回溯率 37%」量尺只看「時間戳是否存在於逐字稿」 | 前波 quality review | 量尺不一致會誤導決策 → 本波建立共用定義 |

## 3. 工作項（本波）

- W1：`snap_source_tags_to_transcript`（確定性吸附；fail-soft；僅 `speaker_traceability` 模板）。
- W2：接進 `_finalize_record_text(mode="local")`，順序＝術語修正 → **吸附** → 表格標註清除 → 佔位符 → 去重。
- W3：量測儀器新增 `tag_traceability`（含 `exact_tag_ratio`）。
- W4：單元測試（吸附／fail-soft／cloud 不變／量測共用定義）。
- W5：E2E（真實音檔、`section_meeting`、`local`）＋吸附前後對照。
- W6：研究文件與本計畫回填實測數字；commit＋push。

## 4. 驗收（Stage 05）

1. `pytest tests/ -q --ignore=tests/test_end_to_end.py` 全綠（前波基準 881 passed／2 skipped）。
2. E2E：真實音檔、`section_meeting`、`local`、clean HEAD、`verdict=PASS`。
3. 品質：`exact_tag_ratio ≥ 0.8`、`traceable_tag_ratio ≥ 0.95`、`body_source_tag_count ≥ 17`、表格標註 = 0。
4. 雲端不變性：`mode="cloud"` 對既有輸入 byte 級不變（單元測試釘住）。

## 5. 風險

- 吸附可能把「本來就正確但不在起點的時間戳」改寫 → 但改寫目標仍為同一發言者的同一段落，語意不變（`[VERIFIED]` 以段落邊界定義）。
- 模型改用角色名（如「科長」）而非 `發言者N` 時，`exact` 不計入 → 以 `tags_inside_any_segment` 保底，不會 false FAIL。
- 單次抽樣（temperature 0.7）：E2E 數字僅為單場證據，不外推。
