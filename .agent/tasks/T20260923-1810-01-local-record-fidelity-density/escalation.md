# Stage 04 升級（escalation）— P7-B：兩條阻斷條文皆未達＋§7 停損對 qwen 觸發

- 提出者：實作者（Stage 04）　日期：2026-09-23　分支：`fix/qwen-local-quality-parity`
- 受測程式碼：`5cff85f`（gemma 場）／`66add73`（qwen 場，僅多 `.agent/` 證據）
- 計畫：`plan.md` **PLAN_REVISION 4**，指紋 `sha256＝dc11dd1167418ab9fbad8325b723566cd9e3df4d2db1cf8e1c3272c2994e08fc`（Stage 05 已重算確認）
- 證據：`e2e/attempt-P7B-gemma31b-e8/`、`e2e/attempt-P7B-qwen27b-e8/`、`e2e/attempt-P7B-stage05/verification-report.md`

## 0. 為何升級（而不是就地做 bounded fix）

1. **plan §7 停損條文對 qwen 觸發**：`(1,814.9 − 1,023.2) / 1,023.2 ＝ +77.38% ≥ 15%` **且** §5 ①（`coverage_core ≥ 27/28`）未達
   ⇒ 條文明定「停用 CORE-1b（`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS=0`）並改走 CORE-1c 備援」。
   這是**行為／優先序語意變更**，非執行者可自行放行（plan §7 原文：「任何語意變更若在 E2E 造成回退，
   走 Planner 重規劃，不由執行者就地改語意」）。
2. **條文在跨模型同時開啟時不可直接套用**：gemma 的 +19.0%（21/28 → 25/28）主要來自**同一顆** CORE-1b（尾段分塊）；
   全域停用會回吐 gemma 已證實的成果，而 gemma 場並未觸發停損（+11.90% < 15%）。
   審查 I14 預告的「§7 無純時間回退出口」缺口在此**成真**。
3. **§5 的 qwen ① 門檻本身在實測變異內**：qwen 同模型同素材重跑的歷史擺動為 `0.7857 ↔ 0.9643`（18 個百分點），
   而 ①的門檻差只有 2 條（7.1pp）⇒ **單場不可判定**。放行或否決都會是雜訊決定，屬量尺／閘門設計問題。

## 1. 已確立的事實（皆經 Stage 05 獨立重算）

| 項目 | 結果 | 依據 |
|---|---|---|
| gemma §5 主驗收（尾段 7 條 ≥6 且 F044 命中） | **FAIL**：結構命中 2/7（寬鬆計 4/7）、**F044 未命中** | verification-report §1.3 |
| gemma `coverage_core` | 21/28 → **25/28（+19.0%）**；`coverage_all` +15.4% | 同上 |
| gemma 既有標註門檻 | **回退**：`on_start_tag_ratio` 0.9615 → 0.84（observe 模式不進 verdict） | verification-report §1.2 |
| qwen ①（`coverage_core ≥27/28`） | **FAIL**：25/28（−7.1%）；missing F019／F054／F056 | verification-report §1.4 |
| qwen ②（密度：leaf ≤62 且平均 ≥48 字） | **PASS**：78 → 37 條（−52.6%）、42.5 → 61.2 字（+44.0%）、0 近似重複 | verification-report §1.5 |
| qwen 缺失歸因 | **生成側**：F019／F056 **在萃取筆記裡都有**（notes L47／L199）⇒ §3 備援①「尾段補萃取」預期無效 | verification-report §5-C |
| §7 停損 | qwen **觸發**（+77.38%）、gemma **未觸發**（+11.90%） | verification-report §1.6 |
| 兩場機制檢查 | verdict PASS、16/16 checks、DOCX `unzip -t` OK、sha256 與 manifest 一致 | verification-report §1.2 |

## 2. 執行者已做／刻意未做

- **已做**：CORE-1a／1b／2a／2b、SUPPORTING-1、§8 三件套（`5cff85f`）；兩場正式 E2E；Stage 05 獨立複驗；
  兩份下一波唯讀研究；證據登錄（`66add73`、`b1c3904`）。
- **刻意未做（避免自我放行）**：不放行／不變更 §7 停損處置、不放寬任何既有門檻、不改 `LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS`、
  不動 §5 驗收語意、不放寬 5 項 runner 門檻、不改雲端提示詞與共用常數。

## 3. Planner 的最小決策集合

- **D1｜CORE-1b（分塊）命運**：保留（並承認 qwen 時間成本）／降級／改為**時間預算自適應**（模型無關）。
  約束：不得以模型名或平台名分支；全關須 byte 級回本波前。
- **D2｜主驗收門檻形式**：單場門檻改為**配對／多場中位數**（可證偽且對變異穩健）。
- **D3｜下一波槓桿挑選**：verification-report §5 的 A–G（逐條對帳擴充／第 3 輪補強／備援①／縮小分塊／
  消融 2 場／標註吸附／補 E2E 投影）中決定順序與預算。
- **D4｜gemma 標註落點回退**處理（僅能走 SUPPORTING-2 語意變更，且不得放寬既有門檻）。

## 4. 執行者建議（僅供 Planner 參考，不具效力）

1. **先做 E（歸因消融）**：2 場 qwen（各 ≈30 分鐘）檢驗「生成紀律三開關是否造成 coverage −2 條、
   密度 −52.6%」的因果；這是把 A／B／C 從推測升級為證據的**唯一**路徑。
2. **同時做 G（零成本）**：把 `full_document_item_count`／`full_document_avg_item_chars` 補進 runner 投影（只補投影、不加門檻）。
3. **D1 不採「全域停用」**：改為時間預算自適應（例如以「本場已用時間 ÷ 同模型歷史中位數」決定是否啟動第二塊萃取），
   屬語意變更，須在 rev5 明列並經 Stage 02 審查。
4. **D2 建議形式**：同模型同素材**配對比較**（新場 vs 基線場）＋「≥2 場取中位數」，並在 rev5 預先登錄基線值。

## 5. 現況

- 目前**沒有**進行中的 E2E 或模型工作（LM Studio 現載入 `qwen3.8-27b-splash`，ctx 131072）。
- 分支共 3 個 commit（`5cff85f`、`66add73`、`b1c3904`）**尚未 push**。
- 本升級不阻擋「把已證實的成果登錄」；阻擋的是「宣告本波完成」與「自行改語意」。
