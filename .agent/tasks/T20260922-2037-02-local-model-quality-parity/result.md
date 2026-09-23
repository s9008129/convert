# result.md — T20260922-2037-02-local-model-quality-parity 任務收尾（Stage 05）

- 撰寫者：Stage 05 獨立驗收員（本檔為收尾角色唯一寫入；產品碼／`plan.md`／`handoff.md`／既有 evidence 全程唯讀）。
- 收尾時間：2026-09-23（台北）。受驗 build：`818b71e6cc96934e922361d54b362b76ce1e0a2e`（expected==actual，`[VERIFIED]`）。
- 驗收判決（E4 場）：`ACCEPTED_WITH_GAPS`；細節＝`e2e/attempt-E4-qwen27b-p4-final/verify_independent.md`。

## 一、主要成果（primary outcome）

**達成。** 地端流程（LM Studio，`processing_mode=local`）在真實音檔 `0903-科務會議.m4a`（2695.1 s）上**能正常生成會議紀錄檔**：`0903-科務會議_a5abfc7c.md`（2,717 字）＋ `.docx`（40,535 B）皆產出、DOCX 結構獨立複核有效、任務 `completed`、`summary_failed=false`、`runner verdict=PASS`（16/16 checks、`failure_reasons=[]`）。`[VERIFIED]`

- 產物：`data/cache/e2e/p4-qwen27b-e4/backend_data/outputs/0903-科務會議_a5abfc7c.{md,docx}`（`data/**` gitignored；tracked 證據以 sha256 留痕）。
- 牆鐘：runner 992.243 s；任務 985.157 s（log「耗時: 985.2秒」）。其中本機 LLM＝815.5 s（82.8%）；ASR 15.9 s、diarization 153.0 s。
- 量尺（觀測值，不列 verdict）：`coverage_all 0.7015`／`core 0.8214`（23/28）／`record_quality.checks` 5/5 true；`coverage.json` 除 `label` 外與我重跑 **byte 相同**；5 支 sha256 全對。`[VERIFIED]`

## 二、任務收尾（task closure）

| 驗收面 | 狀態 | 依據 |
|---|---|---|
| CORE-1 檔案生成＋閘門 | **達成** | E4 §三（16/16、DOCX、終態） |
| CORE-2 三項修補 in-run | **(a)(c)(d) 達成；(b) 字面達成、證據力受限** | E4 §四（`cov_missing_topic=0`、`cov_missing_number=2`、1 輪＋停損；E4 標註全為角色名「科長」→ B1 命名空間不覆蓋） |
| CORE-3 數字可重現 | **達成** | E4 §二（byte 相同／11 鍵全等／sha 全對） |
| CORE-4 殘餘逐條定性 | **達成** | E4 §五（3 真缺＋1 合法待確認＋`100塊` 真缺；無假陽性） |
| CORE-5 宣稱如實 | **達成（附更正要求）** | E4 §六（6 項宣稱全相符；`run_notes.md` 2 處內部錯誤須更正） |
| 四槓桿（P4-A/B/D CORE＋P4-C SUPPORTING） | **皆已生效並有 in-run 證據** | 見§三 |
| 獨立驗收 | **完成** | E3（`ACCEPTED_WITH_GAPS`，修補已落地）→ E4（本判決） |

## 三、四槓桿生效證據（模型無關；LM Studio／Ollama 共用同一 pipeline）

| 槓桿 | 內容 | 生效證據 |
|---|---|---|
| **P4-A** 逐條對帳（議題／決議／數字／日期；只回報不改寫） | `LOCAL_LLM_RECORD_COVERAGE_MODE`（預設 observe） | E4 log:114 `cov_missing_topic=0`（E3 假陽性 1→0）、`cov_missing_number=2`（真缺 `15`／`600` 正確揭露）、`cov_missing_date=1`；離線重播 E3 素材 `missing_topic 1→0`、`missing_number 0→2` |
| **P4-B** 忠實度絆索 A/B/C（0 成本、確定性） | `LOCAL_FIDELITY_TRIPWIRES`（預設 on） | E4：`number_fabricated=0`、`entity_flags=1`（`煙酒文宣股` kind=variant）、`number_missing_tokens=['600塊','100塊','15%']`；B1 新舊碼重播 E3 `14→0`（我實跑） |
| **P4-D** runner 品質閘門＋標註辨別力 | `--quality-mode off|observe|required`、`LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED` | E4 observe：`record_quality` 投影進 tracked evidence、5/5 checks、`gate_effect=none`；P4-D `required` 升級未做（plan §9.9 本波不做，保持） |
| **P4-C** 取樣與 context 同源（SUPPORTING） | 地端統一走 `_summarize_with_local_pipeline`（`summarization.py:2995`；provider 分派同源）；context 由 LM Studio instance 能力解析 | E4 log:93 `context_window=128000(lmstudio_instance)`（不再被 settings 8192 夾住）；`portability-audit-02`：四槓桿零模型名分支、Ollama 取樣同源、開關可攜 PASS |

歷史 root cause（已修，v4.7.4 起）：①可見目標 900-token 硬 gate 被移除；②`LOCAL_LLM_DISABLE_THINKING` 補到 LM Studio 路徑；③規劃視窗改依 instance 實際 `context_length`。

## 四、品質落差現況（同一支音檔、同模板、同尺；皆單場觀察值 n=1）

| 場次 | 引擎 | 事實 all／core | 46 探針 | 亂碼殘留 | 字元 | 備註 |
|---|---|---|---|---|---|---|
| **C5** 雲端基線 | `gemini-3.5-flash-lite`＋地端校正 | 0.8060／0.8929 | 0.652 | **1** | 2,593 | runner 未收尾（觀察值） |
| B2（27B 前 P4） | qwen3.8-27b | **0.8209／0.8929** | 0.848 | 18 | 4,062 | 事實最好但最冗長 |
| E3（27B P4） | qwen3.8-27b | 0.7761／0.8571 | 0.761 | 18 | 3,396 | 修補前 |
| **E4（27B 收尾）** | qwen3.8-27b | 0.7015／0.8214 | 0.674 | **9** | 2,717 | 本場；避險（待確認）29 次 |
| E1／E2（gemma P4） | gemma-4-31b-it-mlx | 0.6119／0.8214（兩場同） | 0.652／0.652 | 0／1 | 2,552／2,318 | 事實明顯較低 |

- `[VERIFIED]` **差距集中在兩個維度**：(1) ASR 亂碼修復——27B 三場 18／18／9 次 vs 雲端 1 次；(2) 取捨策略——雲端高密度壓縮、地端逐段鋪陳。**事實覆蓋面**地端最好的一次（B2 0.8209）已略勝雲端、E4 最差的一次輸 10.5pt；**細節留存**（46 探針）地端多數場次勝雲端（B2 0.848、E3 0.761、E4 0.674 vs C5 0.652）。
- `[VERIFIED]` 使用者主觀感受「Qwen 27B 不如 Gemma 31B」在**事實量尺**上與資料相反（E4 0.7015／0.8214 vs E1/E2 0.6119／0.8214），但 gemma 場的**文字乾淨度**略佳（亂碼 0／1 vs 9）且條目較短 → 主觀落差合理來源＝文字乾淨度與密度，而非事實量。（詳見 `e2e/quality-parity-01/report.md` §六。）

## 五、Scoped blockers／殘餘風險（不得誇大）

1. **[UNVERIFIED] Windows 11＋RTX 4090＋Ollama 實機未驗**：靜態／payload 級相容（模型無關、開關可攜、取樣同源、Ollama 路徑共用 pipeline）已 PASS，但實機 E2E 未執行（`plan §9.5/§9.6 F3/F4` 兩層驗收的第二層）。
2. **E4 標註歸屬未被真正驗證**：29 個標註全用角色名「科長」，落在 B1 可檢命名空間（`發言者\d+`）之外 → 0 筆問題不可解讀為「已驗證正確」。修補本身已由 E3 素材重播證明（14→0）。
3. **決議類覆蓋在本場 no-op**：萃取筆記「議題與決議」的決議抽取 0 項（log:102／109 警告 ×2；E3 亦同）→ 紀錄 13 列決議表「辦理情形」全為「（待確認）」，可讀性不足。
4. **校正層穩定缺陷（n=3）**：`內機/內稽`、`拆勤`、`西龍股`…；E4 交付逐字稿仍 `內機`×2、紀錄整條略去 → core `F021` 未涵蓋（B2／E3 同）。E4 另出現**紀錄層再引入亂碼**（`猜情（出勤）`）。
5. **品質回退 vs E3 屬單場抽樣**：`all` −7.5pt、`core` −3.6pt，同時亂碼減半、`（待確認）` 17→29 → 判為**取捨漂移**，不可宣稱「修補造成品質下降」，亦不可宣稱聚合達標（n=1）。
6. **已知量尺盲區**（`pre-push-review-01` 登錄）：議題詞級覆蓋可能被碎片命中接受；數字殘留全形／項目符號形式（`１５．`、`• 15.`）未檢；B1 中段重疊不再回報。本場未觀察到被觸發。
7. **`run_notes.md` 2 處內部錯誤**（階段標籤對調、E3 輪數誤值）＋1 處登錄缺口（決議 no-op）→ 應以 append-only addendum 更正後再引用。
8. **時間面**：E4 992 s；較 D1（gemma 前 P4，1227 s）快、較 E3（1396 s）快 28.9%。慢的主因＝dense 27B 的 prefill（~98 tok/s × 每次 1.8–2 萬 token）＋decode，**不是 M4 Pro 不夠力**（同時段 MoE 模型 prefill 快 6–8 倍；`e2e/timing-forensics-02/report.md`）。本場補強只 1 輪（比 E3 少 1 輪 ≈ 256 s）。

## 六、證據索引（tracked）

- 驗收：`e2e/attempt-E4-qwen27b-p4-final/verify_independent.md`（本判決）、`run_summary.json`、`coverage.json`、`record_quality.json`、`sha256_manifest.json`、`run_notes.md`（附更正要求）。
- 前場：`e2e/attempt-E3-qwen27b-p4a-fix/verify_independent.md`（`ACCEPTED_WITH_GAPS`，三缺陷）＋`d562691` escalation STOP-5~7。
- 支撐：`e2e/timing-forensics-02/report.md`（耗時）、`e2e/quality-parity-01/report.md`（雲端落差）、`e2e/portability-audit-02/report.md`（跨 OS 可攜）、`e2e/pre-push-review-01/report.md`（推送前審查）、`doc/操作手冊/地端模型品質優化與驗證手冊_v4.10.md`（操作手冊）。
- 修補：`849e934`（議題假陽性）、`eb9dfeb`（B1 集合語意）、`818b71e`（數字整串邊界）；測試基準 `DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py` → 1066 passed, 2 skipped（前置報告所載，本稽核未重跑全套）。
