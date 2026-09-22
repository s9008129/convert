# attempt-C1-gemma31b-fix（Gemma 4 31B 修復後 E2E）執行筆記

- 目的（plan rev6 §7 **N-1**，CORE）：證明「出處標註確定性吸附」**不是為 qwen-splash 客製**——
  換**第三方模型家族**仍達標。使用者指定：只測 `qwen3.8-27b-splash` 與本顆 Gemma，**不測 MoE 35B**。
- 模型：`gemma-4-31B-it-MLX-4bit`（LM Studio `model_key=gemma-4-31b-it-mlx`、`publisher=lmstudio-community`、
  `arch=gemma4`、`compatibility_type=mlx`、`quantization=4bit`、`loaded_context_length=71936`）。
- HEAD：`e90040b`（E2E runner 的 clean-worktree preflight 通過；`build_revision` 前後一致）
- 音檔：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…012828`，與 A1／B1／B2 同一支）
- 模板／模式：`section_meeting`／`local`
- 唯一載入模型：`model_snapshot.json` 與 `model_snapshot_end.json` 皆 `unique_loaded_llm_count=1`（＝gemma）
- verdict：**PASS**（16 項 required checks 全過、exit 0、`failure_reasons=[]`）
- **獨立驗收**（fresh context，`verify_independent.md`，292 行）：**通過**。重跑量測 57 個 leaf 值 **0 diff**、
  hash 三件自力重算相符、人工 seeded 抽樣 10 筆 **10/10** 為真實段落起點；同時提出 3 項本檔已更正的發現。

## 一、CORE 指標與閘門（plan §4-3；門檻未更動）

| 閘門 | 門檻 | 本場實測 | 判定 |
|---|---|---|---|
| `on_start_tag_ratio`（主指標，speaker-agnostic） | ≥ 0.95 | **1.000**（20/20） | PASS |
| `on_start_tag_ratio_excluding_zero` | ≥ 0.90 | **1.000**（17/17） | PASS |
| `traceable_tag_ratio` | ≥ 0.95 | **1.000** | PASS |
| `body_source_tag_count`（退化防線） | ≥ 17 | **20** | PASS |
| `table_source_tag_count` | == 0 | **0** | PASS |

觀察值（非閘門）：`tagged_item_ratio` 1.000、`cross_section_duplicate_pairs` 0、
`instruction_item_count` 11、`char_count` 1,927、`zero_time_tag_count` 3（0.15）、
`distinct_tag_time_ratio` **0.55**（11 種時間戳／20 標註；27B 0.288、MoE 0.786）、
`exact_tag_ratio` 0.0（本場全部標註用角色名「科長」，逐字稿只有「發言者N」→ 結構性失真，非退步）、
`known_term_fix_hits` left 0／right 4（`徵收股` 1、`瑞里` 3；逐字稿側仍有 3 處 ASR 誤形）。

## 二、吸附日誌與**邊際貢獻**（獨立驗收更正 §三之誤）

- 最終生成後（23:36:44）與補強第 1 輪後＝最終輸出（23:43:36）各一次，日誌均為
  `吸附 17 處（段落內 0／最近段落 0／跨發言者 17；不可回溯保留 0）`。
- **更正（獨立驗收以模型原始輸出重跑吸附）**：完整統計為
  `{"segments":183,"tags":20,"snapped":17,"changed":8,"snapped_speaker_mismatch":17,"kept_far":3,"untraceable":0}`。
  **`kept_far` 為 3（不是 0）**——3 筆（`00:31:34`×2、`00:42:51`）落在長段落、位移 > 120 s，
  依精度保護保留原時間戳。backend.log 不記錄 `changed`／`kept_far`，本檔初版誤推為 0，在此如實更正。
- **吸附前後對照**（同一份模型原始輸出、同一支儀器）：

  | 指標 | 吸附前（模型原始） | 吸附後（交付 md） |
  |---|---|---|
  | `on_start_tag_ratio` | 0.95（19/20，**恰壓門檻線**） | 1.000（20/20） |
  | `on_start_tag_ratio_excluding_zero` | 0.9412（16/17） | 1.000（17/17） |
  | `traceable_tag_ratio` | 1.0 | 1.0 |
  | `distinct_tag_time_ratio` | 0.70（14 種） | 0.55（11 種，吸附整併所致） |

  → 本場唯一真正 off-start 的標註（`00:10:04`）確實由吸附救回（→`00:08:15`），主指標 +0.05。
  **但即使完全不吸附，五閘門在本樣本也會全數通過**（主指標 0.95 恰好壓線）。
  因此正確讀法是：**本場達標主要來自 Gemma 自己寫對了絕大多數段首**，
  吸附提供的是保險與邊際改善——既不是「吸附救回一群爛標註」，也不是「吸附無作用」。

## 三、耗時（runner ≈1,670 s／任務 1,659.6 s）

| 階段 | 時間 | 證據 |
|---|---|---|
| ASR | 15.8 s | `elapsed_seconds=15.824`（apple、音檔 2695.1 s、1,340 段） |
| diarization | 153.3 s（682 段、8 位發言者、RTF 0.057） | `backend.log` diarization 完成 |
| 逐字稿語意校正 | 360 s（12 次小呼叫，每次約 29–30 s） | 23:18:47 → 23:24:47（45 段中 8 段修正、1 段放棄、採納 27 處替換） |
| 抽取（單次大呼叫） | 335.0 s（prompt 12,583 tokens） | pipeline metrics `extraction: 335.0` |
| 最終生成 | 382 s（prompt 16,194 tokens） | 23:30:22 → 23:36:44 |
| 補強第 1 輪 | 412 s（prompt 17,533 tokens） | 23:36:44 → 23:43:36 |
| LLM pipeline 小計 | 1,129.3 s（`merge_rounds=0`、`chunk_count=1`、`logical_generations=3`） | pipeline metrics |

**本場只跑 1 輪補強，且補強後收斂**（log 無「本地摘要仍有待補強問題」警告）——第 1 輪問題僅
「待辦事項遺漏 1 項」。對照 B2（27B）同題材為 **2 輪**、補強後**仍剩 6 項假陽性**（P1-17）。

**時間去哪了**：ASR＋diarization 只佔 169 s（10%）；**語意校正＋LLM pipeline 約佔 90%**。
LM Studio server log 顯示本模型走 **VLM 路徑**、`prompt processing` 以 ~70 tok/s 級速度推進
（例：12,583-token 抽取呼叫的 prefill 約 3 分鐘）→ 除 decode 外，**prefill 是可觀成本**。
此為 LM Studio 端該模型／runtime 的觀測，非本專案程式碼造成。

## 四、與前兩場的對照（同音檔、同模板、同模式、同儀器 v1.1.0、**皆單次抽樣**）

| 指標 | Gemma 4 31B（本場，C1） | dense 27B（B2） | MoE 35B-A3B（B1） |
|---|---|---|---|
| `on_start_tag_ratio` | **1.000**（20/20） | 1.000（52/52） | 1.000（14/14） |
| `on_start_tag_ratio_excluding_zero` | **1.000** | 1.000 | 1.000 |
| `traceable_tag_ratio` | 1.000 | 1.000 | 1.000 |
| `body_source_tag_count` | 20 | 52 | 14 |
| `table_source_tag_count` | 0 | 0 | 0 |
| `distinct_tag_time_ratio`（辨別力） | 0.55 | 0.288 | 0.786 |
| `instruction_item_count` | 11 | 25 | 14 |
| `char_count` | 1,927 | 4,062 | 2,124 |
| 補強輪數／是否收斂 | **1／收斂** | 2／未收斂（假陽性 6 項） | 2／收斂（2→1 項） |
| 任務耗時 | 1,660 s | 1,703 s | 442 s |

## 五、獨立驗收另發現的兩件事（本檔如實登記；**不影響本場五閘門判定**）

### 5.1 「倒退一格」精度損失 —— 指標盲區（P2 候選）

7 個唯一改變值中，**6 個是把模型本來就寫對的段首，拉回上一段的起點**：
`00:19:49→00:19:39`、`00:29:13→00:29:10`、`00:06:14→00:05:57`、`00:14:36→00:14:34`、
`00:18:09→00:18:06`、`00:43:03→00:42:51`（另 1 個 `00:10:04→00:08:15` 是**真修正**）。

- 成因：吸附用「逐字稿順序中第一個含此秒數的段落」且段落 end 為**閉區間**；逐字稿大量存在
  「上段結尾＝下段起點」的相鄰鏈時，會選到上一段的 `start`。
- 落點仍是**真實段落起點** → `on_start_tag_ratio` 仍計命中（1.0 無感），
  但**標註指向的語句精度退步**。例：md「詢問現金發放之行政程序（科長，00:18:06）」
  實際內容是**發言者1 於 `[00:18:09-00:18:19]`**。
- **吸附非冪等**：對已交付 md 再套一次吸附仍 `changed=4`，連續套用單向後退不收斂
  （`00:19:39→35→34→31→08`）。建議規則 3 優先選 `start == t` 的段落，或 end 改開區間。
  **本檔不作任何程式碼變更**；分級 P2 候選，需另開計畫修訂。

### 5.2 內容涵蓋不足的實證（反例）

逐字稿有、交付 md **完全沒有**的內容（grep 逐條驗證）：`省員`、`小秘書`、`嘉義`、`選舉`、`視察`、
`排水管`、`露臺`、`藤蔓`、`李飛`。其中「省員／小秘書／嘉義／李飛」**出現在萃取階段筆記** →
屬**最終生成涵蓋不足**，不是檢索失敗。
另有 19 處「（待確認）」。幻覺檢查：**未發現憑空捏造的條目**（最接近者為 md 的「消耗稅科」，
逐字稿 ASR 作「校費稅科」，未被 term-fix 命中）。

→ **正確讀法**：「本場達標」＝**標註可查核性達標**，**不等於**「紀錄整體品質達到 27B 水準」；
涵蓋率不在五閘門內，本場仍是三個模型裡涵蓋廣度最低者。

## 六、本場無法證明的事

1. **涵蓋率／忠實度**：無事實探針、無 ground truth（`unsupported_entities` 永不作為閘門）；
   §5.2 提供的是**反例方向**的證據，不是量化覆蓋率。
2. **與雲端 Gemini 的相對差距**：本場**未**跑雲端對照；且本儀器對雲端不公平（雲端路徑不經吸附層）。
3. **模型本質優劣**：單次抽樣（抽取 temp 0.6、最終／補強 temp 0.7），run-to-run 變異未量化。
4. **Ollama／Windows 實機**：本場仍是 macOS ＋ LM Studio。
5. **DOCX 視覺版面**：僅驗 zip 結構（17 entries）與 `word/document.xml` 存在。
6. **「全程 clean worktree」不可完全重建**：執行窗內（23:23:04）有**並行 session** 寫入
   `doc/操作手冊/部署更新手冊_v4.1.md`（文件、非執行路徑程式碼）；`run_summary.json` 為 PASS
   可推得 preflight 當時通過，但 porcelain 內容未落入工件。

## 七、模型無關性的意義

吸附機制位於兩平台、兩引擎**共用**的 `_finalize_record_text(mode="local")`
（`backend/services/summarization.py:2138/2180/2269`），`backend/core/text_postprocess.py` 內
零平台分支、零模型名分支。本場首次以**非 qwen 家族**模型實證同一組閘門全數達標——
把「模型無關」從**共用管線推論**推進為**第三方模型家族的實測證據**。
獨立驗收的反證掃描亦失敗：`model_snapshot` 唯一載入 gemma、`backend.log` 43 處生成呼叫全 gemma、
LM Studio server log 執行窗內 15 次生成全 gemma、**無非 gemma 呼叫**。
