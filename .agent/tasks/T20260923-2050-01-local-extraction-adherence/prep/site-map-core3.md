# P7-C 實作落點圖（CORE-3：確定性專名正規化／L1）— 唯讀分析產物

- 任務：`T20260923-2050-01-local-extraction-adherence`（P7-C，CORE-3／C3a／C3b）
- 分支／HEAD：`fix/qwen-local-quality-parity` / `ab2528b`（分析時 `git status --porcelain` 僅 `?? .agent/tasks/T20260923-2050-01-local-extraction-adherence/`）
- 本檔性質：**只讀**。不含產品碼修改、**不含任何模型呼叫**（本輪另有一場 E2E 佔用 GPU，故只用檔案分析／離線純字串重算）。所有行號皆為 `ab2528b` 當下實讀值。
- 引註約定：`檔案:行號`；`[VERIFIED]`＝本次實讀原始碼／實檔確認；`[INFERRED]`＝由實讀推得；`[UNKNOWN]`＝無法證實。
- 樣本：P7-B gemma E8 場（`data/cache/e2e/p7b-gemma31b-e8/`），素材 `0903-科務會議.m4a`、模板 `section_meeting`。
- **不要把本檔當成計畫**（plan rev1 受審中；語意決策以 plan／獨立審查為準）。

## 白話結論（5 行內）

1. 現行 4 條硬編碼規則（`section_meeting.py:141-146`）掛在 `apply_record_term_fixes`（`text_postprocess.py:548-577`），在 `_finalize_record_text` 裡是**地端第一步**（`summarization.py:3736`）；雲端根本不經過（`:3722-3723`）。
2. 新階段唯一安全插入點＝ **`:3736` 之後、`:3737` 之前**。硬約束是「必須在 `dedupe_cross_section_items`（`:3750`）之前」，因為去重的判重前提會被任何後續改寫破壞（`:3743-3746` 註解 ＋ `tests/test_t20260922_record_quality.py:531`）。
3. 可決定性判定的三個關鍵：紀錄側候選**直接重用忠實度絆索的 `_candidate_names`**（`fidelity_checks.py:357-378`）、逐字稿側候選用**同後綴＋等長滑動視窗**（不可用「最大連續漢字塊」）、近音用**既有逐音節拼音混淆組**（`correction.py:29-35`、`:93-106`）。
4. **唯一性必須定義在「字面」上**（不能先 fold 再判唯一）：本場逐字稿 `瑞理`（`:20`）與 `瑞裏`（`:15`）並存，fold 後同形 ⇒ 先 fold 會誤判為「唯一」。
5. 本樣本離線實測：P1/P2 作用域只有 **1 個** token 符合條件（`煙酒文申股`）且**唯一候選**（`煙酒文神股`）⇒ 只會修 1 條；`瑞理`／`西龍股` **都不會被修好**（前者逐字稿沒有可用候選、後者逐字稿自己就有此字面）。

---

## 1. 現況（落點與資料結構）

### 1.1 `SECTION_MEETING_RECORD_TERM_FIXES`

| 項目 | 位置 | 內容 |
|---|---|---|
| 契約註解 | `backend/core/prompt_templates/section_meeting.py:133-140` | 「只收『已有逐字稿語境可確證』的 ASR 同音誤辨」「**雲端提示詞與輸出完全不動**」「與 `SECTION_MEETING_GLOSSARY_CORRECTIONS` 嚴格分離」[VERIFIED] |
| 定義 | `section_meeting.py:141-146` | `tuple[tuple[str, str], ...]`＝4 條 `(regex, 取代字串)`：`征收股→徵收股`、`增收股→徵收股`、`人事總數(?=…Email／郵件／寄／偽造／釣魚)→人事總處`、`瑞裏→瑞里` [VERIFIED] |
| 對照組（逐字稿層） | `section_meeting.py:118-127` | `SECTION_MEETING_GLOSSARY_CORRECTIONS`（雲端／地端共用的逐字稿校正層；本波**不得互改／互相滲入**）[VERIFIED] |
| 模板欄位 | `backend/core/templates.py:173-175` | `record_term_fixes: tuple[tuple[str, str], ...] = ()` [VERIFIED] |
| 注入 | `backend/core/templates.py:474` | `record_term_fixes=section_meeting.SECTION_MEETING_RECORD_TERM_FIXES` [VERIFIED] |
| 凍結契約（**不得擴充此 tuple**） | `tests/test_record_term_fixes.py:59-67` | 逐字元斷言「恰為這 4 條」（名稱／順序／字面即介面）[VERIFIED] |
| 其他模板 | `tests/test_record_term_fixes.py:153-157`、`:162-166` | `section_meeting` 帶 4 條；其他模板維持空 tuple [VERIFIED] |

### 1.2 `apply_record_term_fixes`（實作與呼叫點）

| 項目 | 位置 | 內容 |
|---|---|---|
| 定義 | `backend/core/text_postprocess.py:548-577` | 形狀 `(text, fixes) -> (text, list[(pattern, replacement)])`；**只回報實際命中**的規則；`if not text: return text, []` [VERIFIED] |
| 第二層（P5 詞表） | `text_postprocess.py:572-576` | 同層再套 `glossary.apply_known_corrections`（`backend/core/glossary.py:155-181`）⇒ 紀錄層與逐字稿層吃同一份模型無關詞表 [VERIFIED] |
| 呼叫點（全 repo 唯一） | `backend/services/summarization.py:3736` | `text, applied_fixes = apply_record_term_fixes(text, term_fixes)`；`term_fixes` 來自 `getattr(template, "record_term_fixes", ())`（`:3735`）[VERIFIED] |
| 雲端不經此路徑 | `summarization.py:3722-3723` | `if mode != "local": return normalize_unfilled_placeholders(text, template=template)` [VERIFIED] |

### 1.3 `_finalize_record_text` 的順序位置（地端，`ab2528b`）

| # | 步驟 | 行號 | 備註 |
|---|---|---|---|
| 0 | `finalize_record`（全模式共用） | `summarization.py:3716` | 雲端／地端共用 [VERIFIED] |
| — | `mode != "local"` 直接返回 | `:3722-3723` | 雲端路徑到此結束 [VERIFIED] |
| 1 | **術語修正** `apply_record_term_fixes` | `:3736` | ← 新階段建議插在這之後 |
| 2 | 標註吸附 `snap_source_tags_to_transcript` | `:3737` | 需要 `transcript` [VERIFIED] |
| 3 | 表格標註清除 `strip_source_tags_from_table_rows` | `:3738` | [VERIFIED] |
| 4 | 佔位符修復 `normalize_unfilled_placeholders` | `:3739` | [VERIFIED] |
| 5 | 佔位符正規化（P7-B；開關 `LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT` 預設 True） | `:3746-3748` | [VERIFIED] |
| 6 | **跨節去重** `dedupe_cross_section_items`（嚴格最後一步） | `:3750` | [VERIFIED] |
| 7 | 匯總 log（只在有變化時輸出） | `:3751-3775` | [VERIFIED] |

順序不變式的原文出處：`summarization.py:3699-3713`（docstring：cloud/local 切分＋固定順序）與 `:3743-3746`（「位置刻意排在 dedupe 之前——去重需要『切除尾端括號後完全相等』的判重前提」）[VERIFIED]。

地端兩個呼叫點都走同一條：初稿 `summarization.py:3521`、每輪補強 `:3600`（皆 `mode="local"` 且帶 `transcript`）[VERIFIED]。

### 1.4 守「順序」的測試（file:line）

| 契約 | 測試 | 關鍵斷言 |
|---|---|---|
| 雲端 `mode="cloud"` 與 v4.8.0 舊流程**逐字元相同**，且不被地端修正污染 | `tests/test_t20260922_record_quality.py:451-480` | `:468`／`:470`／`:472`；污染反證 `:478-480` [VERIFIED] |
| 地端術語修正＋表格標註清除生效、正文標註保留 | `:482-500` | [VERIFIED] |
| **佔位符修復先於去重、去重嚴格最後** | `:502-537` | `:531` `assert calls == ["normalize", "dedupe"]`（monkeypatch 側錄呼叫序）[VERIFIED] |
| 地端兩呼叫點都走 `mode="local"` | `:595-665` | `:637` `assert finalize_modes == ["local", "local"]` [VERIFIED] |
| `mode="local"`＋逐字稿才吸附；`mode="cloud"` byte 不變 | `:706-721` | [VERIFIED] |
| P7-B 步驟「開關可關＝byte 不變」「雲端不受開關影響」 | `tests/test_t20260923_p7b_placeholder_normalize.py:290-317`、`:318-323` | 同檔 `:1-10` 說明「函式不讀設定、保持純函式」的慣例 [VERIFIED] |

⇒ 這些測試只鎖「normalize 在 dedupe 之前」與「雲端不變」。插入新階段只要滿足：(a) 只在 `mode=="local"` 分支內、(b) 在 `:3750` 之前、(c) 預設關閉時完全不動文字與 log ⇒ 不會打破任何既有斷言 [INFERRED]。

---

## 2. 新增階段 `LOCAL_LLM_PROPER_NOUN_NORMALIZE`（預設 False）

### 2.1 插入點（建議寫法）

```python
# backend/services/summarization.py，插在 :3736 與 :3737 之間
if getattr(settings, "LOCAL_LLM_PROPER_NOUN_NORMALIZE", False):
    text, noun_stats = normalize_local_proper_nouns(text, transcript or "", template)
```

| 決策 | 結論 | 理由（含出處） |
|---|---|---|
| 在 `apply_record_term_fixes` **之後** | 是 | 詞表是**已審核的固定誤辨**，優先權高於機器推斷；反序會讓 `瑞裏→瑞里`（`section_meeting.py:145`）被本階段輸出繞過 [INFERRED] |
| 在 `dedupe_cross_section_items`（`:3750`）**之前** | **硬約束** | 去重前提「切除尾端括號後完全相等」（`:3743-3746`；測試 `:531`）[VERIFIED] |
| 在 `snap_source_tags_to_transcript`（`:3737`）**之前** | 是 | 讓本階段能明確「跳過 `SOURCE_TAG_PATTERN`（`text_postprocess.py:491`）覆蓋的括號」，不動發言者標籤（snap 明文「不代模型改歸屬」`text_postprocess.py:1074`）[INFERRED] |
| 不插在 `normalize_unfilled_placeholders_ext`（`:3748`）與 dedupe 之間 | 可行但較差 | 技術上唯一硬約束仍是 before dedupe；但 `:3748` 是格式收斂的收尾，且 P7-B 已宣告自己「刻意排在 dedupe 之前」（`:3743-3746`），插在它後面會讓語意分層變模糊 [INFERRED] |
| 不得放 `finalize_record` 之前、不得進 `mode != local` | 是 | 會違反 `:3722-3723` 與 `tests/test_t20260922_record_quality.py:451-480` [VERIFIED] |

### 2.2 判定程序（可實作、可稽核、模型無關）

前置：`if not text or not transcript or template is None: return text, zero_stats`（fail-soft；`transcript` 缺席則整步 no-op，沿用 `snap_source_tags_to_transcript` 的 fail-soft 精神 `text_postprocess.py:1092`）。

| 步 | 動作 | 落點／重用 | 產物 |
|---|---|---|---|
| S1 | **紀錄側候選**：`_candidate_names(text)` | `backend/core/fidelity_checks.py:357-378`（只取高訊號位置：引號 `「…」` `:108`、命名動詞前 `:109-111`；後綴白名單 `ORG_SUFFIXES` `:56-74`；剝限定詞 `:349-351`；核心不得含後綴字 `:75-79`；token≥3、stem≥2） | `suspects`（本樣本 10 個，見 §3.3） |
| S2 | **前置條件（C3a）**：逐字稿沒有 → `if _fold(W) in _fold(transcript): skip` | `_fold` `fidelity_checks.py:192-196`；`fold_map` `data/entities/entity_registry.json:19-28`（`裏/裡/理→里`、`徵→征`、`菸→煙`、`臺/檯→台`） | `eligible`（本樣本 1 個） |
| S3 | **逐字稿側候選**：`suf = _suffix_of(W)`（`:353-354`）＋**同後綴＋等長滑動視窗**（對逐字稿每個 `suf` 位置 `i` 取 `T[i-len(W)+1:i+1]`，全漢字才收）＋**字面**去重 | 新程式；**不可**沿用 `_transcript_suffix_candidates`（`:380-392`）的「最大連續漢字塊」抽取（會把「叫做煙酒文神股」整塊吃掉，等長比對就找不到候選）[VERIFIED：離線重算] | `C(W)` |
| S4 | **近音判定**：`len(stem)` 相等 ∧ 逐音節 `_syllables_near` | `backend/services/correction.py:29-35`（`{zh,z}{ch,c}{sh,s}{l,n}{f,h}{r,l}`／`{in,ing}{en,eng}{an,ang}{uan,uang}{ian,iang}{o,e}{uo,o}`）、`:85-91`、`:93-106`；`pypinyin` 依賴 `requirements-correction.txt:13`（產品已在用 `correction.py:79-82`） | 通過者入 `C(W)` |
| S5 | **唯一才替換**：`len(C(W)) == 1` → 以逐字稿**字面**替換；否則原樣 | §2.3 | `replacements` |
| S6 | **保護區段**：`SOURCE_TAG_PATTERN`（`text_postprocess.py:491`）覆蓋的括號內一律不動 | 同上 | 不動標籤 |

**「相似度門檻」的定義**：本設計的門檻是**結構性**的（同後綴 ＋ 同長度 ＋ 逐音節近音），不是分數門檻——因為替換需要一個**可指出來源的字面字串**，而分數沒有對齊資訊（無法回答「要抄哪一段」）。若要多一道保險，可把既有 Dice（`fidelity_checks.py:230-235`）＋`VARIANT_DICE_MIN = 0.75`（`:43`）當成 AND 條件；本樣本 `煙酒文申股` 對 `煙酒文神` Dice≈0.80、對 `煙酒為神`≈0.60 ⇒ 仍唯一 [VERIFIED：離線重算；`[UNKNOWN]`：其他場次未校準]，建議第一版先不加、以觀測決定。

**為何不用模型（5 點）**：①決定性（同輸入同輸出）；②可稽核（每個替換都能指出逐字稿來源字面）；③零呼叫／零牆鐘（成本見 `plan.md:103`）；④模型無關（本專案禁止模型／平台分支，`tests/test_platform_provider_routing.py:180-187`）；⑤已有同精神先例（`correction.py:109-124` 同音閘門、`glossary.apply_known_corrections` `glossary.py:155-181`）。

### 2.3 「不唯一 ⇒ 維持原文」的實作點

| 情況 | 條件 | 行為 | stats |
|---|---|---|---|
| 唯一候選 | `len(C(W)) == 1` | 替換（**唯一會改文字的分支**：`text = text.replace(w, r)`，且跳過保護 span） | `replaced += 1`；`replacements.append((w, r))` |
| 多候選（不唯一） | `len(C(W)) >= 2` | `continue`（原文不動） | `kept_ambiguous += 1`；記候選清單 |
| 無候選 | `len(C(W)) == 0` | `continue` | `kept_no_candidate += 1` |
| 逐字稿已有 | S2 命中 | `continue` | `skipped_in_transcript += 1` |
| 逐字稿缺席／`pypinyin` 不可用 | 前置或 import 失敗 | 整步 no-op（原文） | `skipped_reason = "no_transcript"｜"pinyin_unavailable"` |

（`pypinyin` fail-soft 的既有樣式可參考量尺 `_pinyin_available()`，`scripts/e2e/measure_coverage.py:167-175` [VERIFIED]）

### 2.4 「不可能捏造新事實」的可測性質

| 性質 | 可測命題 | 對應單元測試名（新檔 `tests/test_t20260923_p7c_proper_noun_normalize.py`） |
|---|---|---|
| **P1 來源封閉** | ∀ `(w→r) ∈ stats.replacements`：`r` 是本場逐字稿的**連續子字串**（字面）∧ `r != w` ∧ `_fold(w)` ∉ `_fold(transcript)` | `test_N4_替換字串必須是逐字稿既有子字串_不捏造` |
| **P2 冪等** | `f(f(x)) == f(x)`（替換後 `r` 已命中逐字稿 ⇒ 第二輪 S2 跳過） | `test_N5_冪等_f_f_x_eq_f_x` |
| **P3 失敗即原樣** | 0 候選／多候選／逐字稿缺席 ⇒ `out == text`（byte 級） | `test_N2_無候選時原樣保留`、`test_N3_多候選時原樣保留_不唯一`、`test_N6_逐字稿缺席時_byte不變` |
| **P4 不跨後綴／不跨長度** | 候選必須同 `_suffix_of` 且等長（`瑞理村` 不得吸到 `…股` 候選） | `test_N9_候選集合只認同後綴同長度_不得跨後綴吸附` |
| **P5 標籤不動** | `（稽查股，00:05:12）` 這種標註內的 token 不替換 | `test_N11_來源標註括號內不替換` |
| **P6 開關契約** | 開關 False ⇒ 與不實作本階段逐字元相同；`mode="cloud"` ⇒ 兩值輸出一樣 | `test_N8_地端收尾會呼叫_且開關可關`、`test_N7_雲端路徑不受開關影響`（樣板：`tests/test_t20260923_p7b_placeholder_normalize.py:290-323`） |

補充（**交付層**不變量，只量測、不加門檻）：交付紀錄的專名候選集合 ⊆ 逐字稿字面 ∪ registry ∪ 詞表右側。量尺：`scripts/e2e/measure_record_quality.py:302-313`（`find_unsupported_entities`）與 `:445-449`（`unsupported_entities_registry_aware`；該欄位明文「**永不作為閘門**」`:441-443`）[VERIFIED]。

### 2.5 開關登錄與接線

| 項目 | 落點 |
|---|---|
| 設定定義 | 照 `backend/core/config.py:693-702`（`LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT` 區塊與註解風格）；本階段 `default=False`（plan C3b）[VERIFIED] |
| `.env.example` | 照 `.env.example:162-167`（佔位符正規化區塊）樣式新增 [VERIFIED] |
| 呼叫端 | `backend/services/summarization.py:3736` 之後（§2.1） |
| 純函式本體 | 建議放 `backend/core/text_postprocess.py`（與 `apply_record_term_fixes` 同檔同層）——**注意**該檔被 `tests/test_platform_provider_routing.py:180-187` 掃「不得含平台字串」[VERIFIED] |
| skip 語意 | 照 plan §7：skip 路徑記 `skipped_reason`（observation-only）[VERIFIED：`plan.md:123`] |

### 2.6 本樣本離線重算（純字串，零模型呼叫）

| 作用域 | suspects | 逐字稿已有（S2 跳過） | 唯一候選（會改） | 多候選（保持） | 無候選（保持） |
|---|---|---|---|---|---|
| **P1/P2 高訊號（建議）** | 10 | 9 | **1**（`煙酒文申股 → 煙酒文神股`） | 0 | 0 |
| 寬作用域（後綴類滑動視窗 3–7 字） | 77 | — | 3（**同一族的巢狀視窗**：`煙酒文申股`／`酒文申股`／`文申股`） | 0 | 74 |

⇒ 寬作用域會產生 66+ 個雜訊候選（如 `禁止科內群組`、`長轉知局`、`嚴厲處`）；多數會因 0 候選而不動，但假陽性面被放大。**第一版建議採 P1/P2**，寬作用域先當「觀測儀器」跑 [INFERRED]。

---

## 3. 實際案例對照（P7-B gemma E8）

樣本：交付紀錄 `data/cache/e2e/p7b-gemma31b-e8/backend_data/outputs/0903-科務會議_5444cdef.md`；逐字稿 `..._5444cdef_逐字稿.txt`（段落格式 `[HH:MM:SS-HH:MM:SS] 發言者N：…`）。

### 3.1 三錯形逐條回查（**最重要：有兩個不會被修好**）

| 交付紀錄錯形（行號） | 逐字稿所有字面變體（次數＋行號） | S2 前置條件 | `C(W)` | 判定 | 結果 |
|---|---|---|---|---|---|
| `瑞理村`（`.md:16`、`:42`） | `瑞理` 1（逐字稿 `:20`）／`瑞裏` 1（`:15`）／**`瑞里` 0** | ① 此 token **不在** P1/P2 候選內（表格儲存格／正文裸名）⇒ 第一版根本不入選；② 若改用寬作用域：`fold(瑞理村)=瑞里村` ∉ `fold(逐字稿)` ⇒ eligible | **0**（逐字稿 `村` 只 1 次，且是 `:17`「那一個村裏」的 `一個村`，與 `瑞理` 非近音） | 保持原文 | **不會被修好** |
| `西龍股`（`:23`、`:25`、`:50`、`:52`；含表格共 6 次） | `西龍股` 1（`:159`）／`徵收股` 2（`:12`） | **不成立**：`西龍股` 逐字稿自己就有 1 次 ⇒ S2 直接跳過 | — | 保持原文 | **不會被修好** |
| `煙酒文申股`（`:37`） | `煙酒文神股` 1（`:12`）／`煙酒為神股` 1（`:12`）／`文申` 0 | 成立（`fold(煙酒文申股)` 不在 fold 逐字稿） | **{`煙酒文神股`}**（1 個；`煙酒為神股` 因 `文`/`為` 非近音被排除） | 唯一候選 ⇒ 以逐字稿字面替換 | **會被修好（唯一一條）** |

對照組（**不得被動到**）：`稽查股`／`徵收股`（紀錄 `:35`）逐字稿都有（`:12`）⇒ S2 跳過 [VERIFIED]。

### 3.2 為什麼「不唯一／逐字稿沒有正解」比「能修好」更重要

- `瑞理`／`瑞裏`／`瑞里` 三形拼音**完全相同**（lǐ）；逐字稿同場**並存**兩種（`:15`、`:20`），而 checklist 認定的正解 `瑞里` 在該場逐字稿出現 **0 次** ⇒ 任何「以逐字稿為真值」的規則都**不可能**產出 `瑞里`。
- `西龍股` 在逐字稿 `:159` 有字面 ⇒ 逐字稿本身也是聽錯的變體；要修它只能靠**官方白名單**（`data/entities/entity_registry.json`），不是這條槓桿。
- 因此 `research/next-wave-gap-p7b.md:218` 的預期「`coverage` F014（瑞里）直接由缺轉有」在本樣本**不成立** [VERIFIED：該場逐字稿 `瑞里` 出現 0 次]。效果量尺應改為：`unsupported_entities_registry_aware` 1 → 0（本樣本），以及 `known_term_fix_hits.right_by_form.瑞里` **維持 0**（預期不變；若驗收時變動，表示有別的機制動了文字）。

### 3.3 P1/P2 候選實測（本樣本 10 個）

`地價稅科`、`土地增值稅科`、`使用牌照稅科`、`稽查股`、`徵收股`、`煙酒及稅務管理科`、`煙酒文申股`、`欠稅管理股`、`消費稅科`、`煙酒管理科` [VERIFIED：以 `fidelity_checks._candidate_names` 對實檔離線重跑]。
其中 9 個 fold 命中逐字稿 ⇒ 只剩 `煙酒文申股` 走完整判定。**`瑞理村`、`西龍股` 都不在這 10 個之內**（前者在表格儲存格、後者是正文裸名，皆非 P1/P2 高訊號位置）[VERIFIED]。

### 3.4 補洞選項 L1b（需 Planner 決策，非本階段範圍）

要讓 F014（瑞里）真的被修好，需要「**registry 正名替換**」：`data/entities/entity_registry.json:136-140` 已登錄 `瑞里`（fold `裏/裡/理→里`；來源含 `fact_checklist F014` 與 `section_meeting.py:145`）[VERIFIED] ⇒ 規則「紀錄 token 的 fold 命中 registry 條目 ⇒ 以 registry 名替換」可修 `瑞理村→瑞里村`、`瑞裏→瑞里`。此舉改動交付文字、權威來源是**策展白名單**（不是逐字稿）⇒ 屬語意變更，須回 Planner；且須處理同名不同實體的假陽性（見 §4.1）[INFERRED]。

---

## 4. 風險與界線

### 4.1 可能被誤改的情況

| 情境 | 具體例子（本樣本可查） | 為什麼會發生 | 現有防線／建議 |
|---|---|---|---|
| **同場並存變體（最高風險）** | 逐字稿同時有 `工產科` 2 次（`:189`）與 `工廠科` 1 次（`:187`）；`data/glossary/確定性誤辨校正.txt:14-15` 明文把 `工廠科` 列為「無 ground truth…一律不臆測、不登錄」 | 「以逐字稿為真值」在逐字稿自身不一致時失效：紀錄若寫**第三種**變體，只要逐字稿裡剛好只有**一個**近音候選，就會被吸附過去 | S2＋唯一性只能防「多候選」，**不能防「唯一但錯」**。建議只在高訊號位置（P1/P2）作用，並把「逐字稿內互為近音的同後綴 token 對數」列為觀測值 |
| 同音不同實體（股別） | `瑞理`／`瑞裏`／`瑞里`（拼音全同 lǐ）；`哪個辦公室`≈`那個辦公室`（`:17`） | 拼音混淆組無法分辨語意 | 字面唯一性（同場兩形 ⇒ 不唯一 ⇒ 不動）；正名只能靠 registry（§3.4） |
| 地名／村里 vs 單位同形 | 後綴集含 `村／里／局／處`（`fidelity_checks.py:56-74`） | 村里名與單位名共用後綴 | 等長＋同後綴＋近音三重條件；第一版排除表格欄位 |
| 標籤內發言者被改 | `（稽查股，00:05:12）` 這種以單位當發言者的標註 | 標註文字也是正文 | S6 保護 `SOURCE_TAG_PATTERN`（`text_postprocess.py:491`） |
| 表格承辦單位 | `| … | 西龍股： |`（`.md:23`） | 表格欄位沒有語境可驗 | 第一版作用域（P1/P2）天然不含表格；日後若擴大必須先加觀測 |

### 4.2 建議的觀測指標（**只量測、不改行為**）

| 指標 | 來源／落點 | 本樣本基線 | 期望 |
|---|---|---|---|
| `unsupported_entities_registry_aware` | `scripts/e2e/measure_record_quality.py:445-449`、`:486-487` | `["煙酒文申股"]`（`data/cache/e2e/p7b-gemma31b-e8/quality/record_quality.json`） | 0 筆 |
| `fidelity.entity_flags`／`entity_kinds` | `backend/core/fidelity_checks.py:436-455`；本樣本 JSON | `entity_flags=1`、`entity_kinds=["variant"]` | 1 → 0 |
| 逐字稿「近音同後綴 token 對數」＝假陽性面 | 離線純字串重算（本檔 §4.1 的方法） | **2**：`工廠科≈工產科`、`哪個辦公室≈那個辦公室` | 觀察值（不設門檻） |
| `known_term_fix_hits.right_by_form.瑞里` | `scripts/e2e/measure_record_quality.py:276-300` | 0（逐字稿 `瑞裏` 1、`瑞里` 0） | 本槓桿**維持 0** |
| 新階段自身 counters（`suspects/eligible/replaced/kept_ambiguous/…`） | 新函式 stats ＋ log 行 | — | observation-only；開關關閉時**不得**出現 |

---

## 5. 既有契約（不得破壞）

| 契約 | 出處（測試 file:line） | 對本階段的要求 |
|---|---|---|
| `mode != local` **byte 不變** | `tests/test_t20260922_record_quality.py:451-480`（`:468`／`:470`／`:472` 三種呼叫形）、`:706-721`、`tests/test_t20260923_p7b_placeholder_normalize.py:318-323` | 新階段只能在 `summarization.py:3722-3723` 之後的地端分支內；不得進入 `finalize_record` |
| `LOCAL_LLM_RECORD_COVERAGE_MODE=off` **不得有新 log／metrics** | `tests/test_t20260923_p4a_record_coverage.py:377-390`（一行回 `[]`、無 log、無 `cov_*`）、`:395-414`（pipeline golden：紀錄與 log 逐字相同）、`:497-515`（連 WARNING 都要靜音）、`tests/test_t20260923_p4b_fidelity_wiring.py:224-244`（關閉時 log 逐字相同且檢查器 0 呼叫）；語意定義 `backend/core/config.py:287-292` | 本階段新增 log **不得**掛在 coverage 路徑；`LOCAL_LLM_PROPER_NOUN_NORMALIZE=false` ⇒ 不呼叫、不 log、無 metrics（新測試 N8） |
| 無平台／模型分支 | `tests/test_platform_provider_routing.py:180-187`（`text_postprocess` 不得含 `sys.platform`／`platform.system`／`os.name`／`darwin`／`win32`／`linux`）、`:190-198`（引擎分派）、`:199-215`（引擎無關的函式級 byte 等同） | 新程式碼放 `text_postprocess.py` 會直接被掃；不得出現模型名 |
| `SECTION_MEETING_RECORD_TERM_FIXES` 凍結（恰 4 條） | `tests/test_record_term_fixes.py:59-67`、`:153-157`、`:162-166` | **衝突提示**：不得擴充該 tuple；必須新開關＋新函式（與 plan C3b「僅新增獨立階段」一致） |
| 全關＝byte 級回 `ab2528b` | `plan.md:116`、`:121-124` | 開關 False 時整步 no-op |

[UNKNOWN]：`LOCAL_LLM_PROPER_NOUN_NORMALIZE` 這個名字目前**不存在**於 `backend/core/config.py`（本次 `rg` 無命中）⇒ 需等 plan rev1 通過審查後才有實作落點 [VERIFIED]。

---

## 6. 證據索引

| # | 主題 | 位置 |
|---|---|---|
| 1 | 四條凍結規則 | `backend/core/prompt_templates/section_meeting.py:133-146`；`tests/test_record_term_fixes.py:59-67` |
| 2 | 詞表層實作 | `backend/core/text_postprocess.py:548-577`；`backend/core/glossary.py:155-181`；`data/glossary/確定性誤辨校正.txt:14-17` |
| 3 | 收尾順序 | `backend/services/summarization.py:3699-3713`、`:3719-3723`、`:3728-3732`、`:3735-3750`、`:3751-3775` |
| 4 | 順序／雲端契約測試 | `tests/test_t20260922_record_quality.py:451-480`、`:502-537`（`:531`）、`:595-665`（`:637`）、`:706-721` |
| 5 | 候選抽取與支持判定（重用） | `backend/core/fidelity_checks.py:43`、`:56-79`、`:108-113`、`:192-235`、`:349-354`、`:357-378`、`:380-392`、`:395-433` |
| 6 | 近音判定（重用） | `backend/services/correction.py:29-35`、`:79-82`、`:85-106`、`:109-124`；`requirements-correction.txt:13` |
| 7 | 量尺（重用） | `scripts/e2e/measure_record_quality.py:276-300`、`:302-313`、`:439-449`；`scripts/e2e/measure_coverage.py:167-175`、`:197-247` |
| 8 | 保護區段／表格定義 | `backend/core/text_postprocess.py:491`、`:498-503`、`:508-518`、`:1074`、`:1092` |
| 9 | 開關樣式 | `backend/core/config.py:287-292`、`:693-702`；`.env.example:162-167` |
| 10 | 白名單／fold | `data/entities/entity_registry.json:19-28`、`:43`、`:59-62`、`:136-140`、`:211-214`、`:221-225` |
| 11 | 樣本 | `data/cache/e2e/p7b-gemma31b-e8/backend_data/outputs/0903-科務會議_5444cdef.md:16,23,25,35,37,42,50,52,63`；`..._逐字稿.txt:12,15,17,20,159,187,189`；`data/cache/e2e/p7b-gemma31b-e8/quality/record_quality.json`、`coverage.json` |
| 12 | plan／前波研究 | `.agent/tasks/T20260923-2050-01-local-extraction-adherence/plan.md:77-83`、`:103`、`:116`、`:123`、`:136`；`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/research/next-wave-gap-p7b.md:215-220` |
