# Stage 05 獨立驗收報告 — P7-B（T20260923-1810-01-local-record-fidelity-density）

## 0 受驗快照與角色宣告

- 角色：**Stage 05 獨立驗收員（唯讀）**。不得修改產品碼／`plan.md`／`handoff.md`／既有 `review/**`・`e2e/**`；唯一寫入＝本檔。**未 commit**。
- Repo／分支：`/Users/hsiaojohnny/dev/convert`、`fix/qwen-local-quality-parity`、`HEAD=66add7366aeb841832246be11da141d2872929b2`（ahead origin 3）。
  - 工作樹未追蹤物＝`.agent/.../e2e/attempt-P7B-qwen27b-e8/`、`research/next-wave-code-levers.md`、`research/next-wave-gap-p7b.md`（**非本驗收產物**，未動）。
- 計畫指紋：`sha256(plan.md)=dc11dd1167418ab9fbad8325b723566cd9e3df4d2db1cf8e1c3272c2994e08fc` [VERIFIED]（`shasum -a 256` 實跑，與 handoff 宣告一致）。
- `handoff.md` 指紋：`f4c6d91d76e4f55ddc97f20b797d4a03e2d4301ff8025b3b0f8a4c6b3e2b2bc6`（未在計畫中宣告比對值；僅登錄）。
- **受測程式碼版本**：gemma 場 `expected=actual=5cff85f6372fc69b541f1d7b30b0b229d5fb6006`；qwen 場 `expected=actual=66add7366aeb841832246be11da141d2872929b2`。
  `git show --stat 66add73`＝11 檔全在 `.agent/` 下（證據／審查附錄），**未動任何 `backend/**`・`tests/**`** ⇒ 兩場受測產品碼同一（5cff85f 樹）[VERIFIED]。
- 素材：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a` sha256 `982151f4629ade0c38f164b57a2f105c1e305677e7e10e4dc0e252f1ac012828` ✔（run_summary＋manifest＋自行重算三方一致）。
  - **逐字稿 sha256 不同**：gemma 族（E6／E7C／E8）＝`fd40a2018def853580bda83db26f9939b7a053cf1f0049ff80b08829e75b72bf`；qwen 族（E6b／E8）＝`b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`。
    ⇒ **同模型前後對照（E7C↔E8、E6b↔E8）逐字稿完全相同（乾淨對照）；跨模型比較含逐字稿混淆** [VERIFIED]。
- 約束遵守：**全程零模型呼叫**（未 curl LM Studio、未跑 backend）；未跑全 suite；僅用既有零呼叫儀器（`measure_coverage.py`／`measure_record_quality.py` 之欄位讀取）＋`rg`／`shasum`／`unzip -t`／`nl`／python 讀 JSON。

## 1 逐項驗收結論（含算式與出處）

### 1.1 plan 指紋
`dc11dd1167418ab9fbad8325b723566cd9e3df4d2db1cf8e1c3272c2994e08fc` ＝ 預期值 ✔ **[VERIFIED]（PASS）**

### 1.2 兩場 verdict 與 16 項 checks
| 場 | verdict | checks | failure_reasons | build_revision_match | model_inventory_unique | docx_downloaded | formal_docx_valid |
|---|---|---|---|---|---|---|---|
| gemma e8 | PASS | 16/16 true | `[]` | true | true | true | true |
| qwen e8 | PASS | 16/16 true | `[]` | true | true | true | true |

- 模型載入快照：gemma e8＝`gemma-4-31b-it-mlx`（ctx 71,936，unique=1）；qwen e8＝`qwen3.8-27b-splash`（ctx 131,072，unique=1）[VERIFIED]（`model_snapshot.json`）。`qwen3.6-35b-a3b-splash` 在清單中但**未載入**（gate 只計 loaded）→ 本波未測，符合使用者指示。
- DOCX：4 檔（每場 `meeting_record.docx` ＋ `backend_data/outputs/*.docx`）`unzip -t` 全 **OK**；且兩兩 sha256 相同並等於 manifest：
  gemma `b4e4f82be838ab21225731cf041ac5d3b1b83ef89cb1fcc121db232825c8d638`、qwen `19e5054341bfbe82b2ff65ee2a48b9f00a8f3ec82762358d64f8a50c0ab0e93c` [VERIFIED]。
- `task_final.json`：status=completed、progress=100、`summary_failed=false`、`processing_mode=local`、`template_id=section_meeting` [VERIFIED]。
- **但（重要）**：gemma e8 的 `quality.check_failures` **非空**（2 項既有門檻不合格，`--quality-mode observe` 下不進 verdict）：
  `on_start_tag_ratio=0.84`（門檻 ≥0.95）、`on_start_tag_ratio_excluding_zero=0.8095`（門檻 ≥0.9）。
  對照 gemma E7C（P7-A）＝`0.9615 / 0.95` **全過** ⇒ **此維度是 P7-B 相對回退**（qwen e8 則 5/5 全過，`1.0/1.0`，`exact_tag_ratio` 0.0641→0.7027 大幅改善）[VERIFIED]。

### 1.3 gemma 主要驗收（§5 阻斷）：尾段 7 條事實逐條判定
判準（本驗收員自訂、全項一致）：**HIT**＝交付 `.md` 內存在可辨識該事實核心命題的原文片段（主體＋關鍵細節），且經逐字稿核對非虛構；**PARTIAL**＝主體在但載重細節缺或失真；**MISS**＝無片段。
事實清單＝`quality/fact_checklist.json` F044／F054／F055／F056／F060／F065／F066。

| 事實 | 交付 `.md`（`0903-科務會議_5444cdef.md`） | 逐字稿（`data/cache/e2e/p7b-gemma31b-e8/transcript.txt`） | 判定 |
|---|---|---|---|
| F044 年底選舉・政治敏感 | **無片段**（`選舉`／`政治`／`敏感`／`謹慎`／`年底` 全 0；僅「甄選」「檢舉」字串誤中 L38/L67） | L145 `[00:25:23-00:26:08]`「現在年底要選舉了哦，就大家小心哦…扯到政治這邊就特別要小心」 | **MISS** |
| F054 搬遷時程可能拖很久 | L61「2. 心理準備：**因搬遷時間可能拖延**…（科長，00:41:51）」 | L163 `[00:32:34-00:33:07]`「我覺得我們會搬進去的時間可能會拖很久」 | **HIT**（標註時間有誤，見 §3） |
| F055 三樓淹水溢到禮堂走廊 | **無片段**（`三樓`／`禮堂`／`走廊`／`感恩` 全 0；唯一淹水句 L60 指「新辦公室／露臺」） | L177 `[00:33:57-00:34:38]`「我們三樓…水都從感恩室一直溢出來…驛到禮堂」；L179「一直延伸到我們這個走廊來」 | **MISS** |
| F056 防水層刨除→排水管破損滲水 | L60「新辦公室因**露臺排水管堵塞**及**防水層施工**導致淹水」（機制被寫成「堵塞」） | L185 `[00:35:21-00:39:44]`「幾乎把那個防水層整個刨掉他重新做防水…刨掉之後整個水管…排水管跟空氣管」、「看到有管子的地方他就整個都把它封起來」 | **PARTIAL**（主體在、機制失真） |
| F060 政風室旁空辦公室黴味重 | L60「目前雖已排乾但**黴味嚴重**」（無 `政風室`、無 `空辦公室`、無 `工產科`） | L187 `[00:39:47-00:42:51]`「**政風室旁邊這一個空的辦公室**就是我跟你講淹水那一個…他要做工廠科的辦公室…都是黴味」 | **PARTIAL**（指涉實體缺定位） |
| F065 兩階段搬遷・工產科＋財管科 | L63「財政四科分**兩階段**搬遷，**第一階段由工產科及財管科先搬入**…（科長，00:44:15）」 | L189 `[00:43:03-00:44:15]`「財政四科搬遷這件事情它分兩階段第一階段有兩個課要先進來就是工產科跟財管科」 | **HIT** |
| F066 新聞行銷處接收（局長室／會議室改用途） | **無片段**（`新聞行銷`／`局長室`／`處長`／`副處` 全 0） | L189「局長室以後會變成新聞學校處處長的辦公室那隔壁的會議室會變成副處長的辦公室」 | **MISS** |

**結論：命中 2/7（F054、F065）；寬鬆計（HIT＋PARTIAL）＝4/7；F044 未命中。** §5 門檻「命中 ≥6 **且** F044 命中」⇒ **FAIL**（此結論對判準鬆緊不敏感）。
補充：F044／F066 在 P7-A E7C 交付 `.md` 亦為 0 命中（自行 `rg` 複核）⇒ 屬**本波未改善**，非新回退；F048 由 E7C covered → E8 missing 為**新回退**（見 1.4）。

### 1.4 coverage（觀察值；自行重跑 `measure_coverage.py`，非僅讀 JSON）
| 場 | covered_core | coverage_all | supporting | missing_core | 與 run_summary 一致 |
|---|---|---|---|---|---|
| gemma E7C（P7-A 對照） | 21/28＝0.7500 | 0.5821 | 0.4615 | F044,F054,F055,F056,F060,F065,F066 | ✔ |
| gemma **E8** | **25/28＝0.8929** | 0.6716 | 0.5128 | F044,**F048**,F066 | ✔ |
| qwen E6b（P6-A 對照） | **27/28＝0.9643** | 0.8657 | 0.7949 | F055 | ✔ |
| qwen **E8** | **25/28＝0.8929** | 0.7612 | 0.6667 | **F019**,F054,**F056** | ✔ |

- gemma：+4 條 core（+19.0% 相對）、`coverage_all` +15.4%；代價是 **F048 回退**。
- qwen：**−2 條 core（−7.1% 相對）、`coverage_all` −12.1%**。
- 儀器語意自證（讀 `scripts/e2e/measure_coverage.py` docstring＋實測 `facts[].matched_group_index`）＝**group 內 AND／group 間 OR、全文（文件級）字面共現**，非語意、非同句。
  已證實兩個 **false positive**：F055 在 gemma e8 由 `matched_group_index=2`＝`["颱風","淹水"]` 觸發，但 `颱風` 在 L43（土地卡重印）、`淹水` 在 L60（新辦公室）→ 不同事實跨行共現；F060 由 index=3＝`["工產科","霉味"]` 觸發（L63＋L60）⇒ **probe 命中 ≠ 該事實寫進紀錄**（本驗收以結構判定為準，符合 §5「覆蓋率降為觀察值」）[VERIFIED]。

### 1.5 qwen ①（§5 阻斷）：`coverage_core` ≥27/28
自行重跑＝**25/28**（missing F019／F054／F056）< 27/28 ⇒ **未達（FAIL）**。
結構複核支持儀器：`倉庫`／`颱風` 在交付 `.md` 為 0（F019 的「颱風→倉庫漏水→土地卡損毀」因由缺，僅保留重印動作 L17/L18/L69）；`防水`／`排水管` 為 0（F056 全缺）；F054 僅「同仁需做好長期在現址辦公之心理準備」（L60）＝PARTIAL。**[VERIFIED]**

### 1.6 qwen ②（非阻斷）：密度目標
定義依 §5：leaf item＝`^\s*\d+\.`；平均字元＝同批 ad-hoc（去 `N.` 前綴與空白後 `len`）。
- 方法自證：E6b 上 `rg -c`＝**78**、ad-hoc 平均＝**42.5** ⇒ **逐位重現計畫所載基線**（定義確認）。
- qwen E8：**37 條**（≤62 ✔；自 78 **−52.6%**，門檻 ≥20% 降幅）、平均 **61.2 字**（≥48 ✔；自 42.5 **+44.0%**，門檻 ≥12% 升幅）⇒ **PASS**。
- 儀器獨立交叉核對：runtime `quality/record_quality.json` 之 `full_document_item_count=37`、`full_document_avg_item_chars=61.2` ⇒ 與 ad-hoc 完全相同 [VERIFIED]。
- 對照：gemma E8＝23 條／60.7 字（E7C 23／49.7，平均 **+22.1%**、條數 0%）；雲端 C5 基線＝28 條／65.1 字。
- 注意：`instruction_item_count`（gemma 21／qwen 18）定義不同，**未混用** [VERIFIED]。

### 1.7 §7 停損（時鐘＝runner 牆鐘；pipeline 僅交叉核對）
| 場 | wall（runner） | 同模型對照 | 增幅 | pipeline total（交叉核對） |
|---|---|---|---|---|
| gemma E8 | 2378.5 s | E7C 2125.5 s | **+11.90%**（253.0/2125.5） | 1827.4 s（E7C 1570.2，+16.38%） |
| qwen E8 | 1814.9 s | E6b 1023.2 s | **+77.38%**（791.7/1023.2） | 1497.3 s（E6b 769.6，+94.55%） |

- gemma：增幅 <15% ⇒ **停損未觸發**（即使 §5 主驗收未達，§7 是「AND」條件）。
- qwen：增幅 ≥15% **且** §5 主驗收未達（① FAIL）⇒ **停損觸發**：依 §7 應「停用 CORE-1b（`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS=0`）並改走 CORE-1c 備援」。
- 成本機制（log 實查，非推測）：gemma `chunk_count` 1→2、`logical_generations` 4→5、extraction 340.6→406.1 s、final_and_refine 1229.6→1421.3 s；qwen `chunk_count` 1→2、`logical_generations` 3→5、**補強輪 1→2**、extraction 166.8→427.6 s、final_and_refine 602.7→1069.7 s。
  ⇒ qwen 的 +77% 主要來自**呼叫數增加**（分塊 2 次萃取＋多 1 輪補強），非單次推論變慢 [INFERRED，有 log 支撐]。
- 備援①邊界（§7 已載）：+150.5 s ⇒ qwen +14.7%、gemma +7.1%；**單獨使用 <15%**，與 CORE-1b 同時開啟 ≥15% 才須回 Planner。

### 1.8 耗時對帳（兩者不可混算）
| 場 | runner 牆鐘 | task（API created→completed） | pipeline total | extraction | final_and_refine |
|---|---|---|---|---|---|
| gemma E8 | 2378.5 s | 2370.8 s（19:21:13.9→20:00:44.7） | 1827.4 s | 406.1 s | 1421.3 s |
| qwen E8 | 1814.9 s | 1808.0 s（20:02:48.1→20:32:56.2） | 1497.3 s | 427.6 s | 1069.7 s |

⇒ 牆鐘 −pipeline ＝ 551.1 s（gemma）／317.6 s（qwen）＝ASR（15.8／15.6 s）＋上傳／排隊／DOCX render／輪詢等非 pipeline 段。**§7 停損只認牆鐘**；pipeline 僅交叉核對（gemma 兩鐘方向相反：牆鐘 +11.9%、pipeline +16.4%）。
**未登錄項**：run_notes.md（§5 量測表列有）在兩場 attempt 目錄中**不存在** ⇒ 牆鐘僅能自 `run_summary.started_at/finished_at` 取得 [VERIFIED]。

### 1.9 分塊預註冊預測核對（CORE-1b）
- 離線重播 `evidence/p7b-chunk-replay/replay.json`（0 呼叫）：budget 6000 ⇒ `n_chunks=2`、`chunk_est_tokens=[5960, 5918]`、chunk2 首行 `[00:22:09-00:22:`、尾段探針 6/7（`F060=false`）✔ 與計畫 §3 一致。
- 實跑：log「萃取筆記零損串接：**2 份**」＋pipeline metrics `chunk_count=2` ✔ ⇒ **「恰 2 塊」命中** [VERIFIED]。
- **已知估算落差**（同 replay.json）：budget 6000 列 `estimated_chunk_count=3` 而 `n_chunks=2` ⇒ 估算器高估 1 塊（僅影響規劃／顯示，實測以 `chunk_count=` 為準）。
- 實跑 chunk2 的精確起點時間未落 log／notes ⇒ **[UNKNOWN]**（代理觀察：gemma notes chunk2 最早引用的時間戳＝`[00:22:44]`，與預測 `[00:22:09]` 同段鄰近）。
- CORE-1a 落檔 ✔：`debug/extraction-notes/notes-20260923-193703-2c452049.md`（gemma）／`notes-20260923-201506-466dd7bc.md`（qwen），檔頭含 `chunk_count=2 raw_notes=2`。

### 1.10 歸因證據（CORE-1a 的目的：分辨「萃取漏」vs「生成漏」）
| 事實 | 萃取筆記是否已有素材 | 交付 `.md` | 歸因 |
|---|---|---|---|
| gemma F044 | **無**（`選舉` 僅出現在會議資訊日期行「僅提到近期為年底選舉前」；`政治/小心/敏感/謹慎` 全 0） | 無 | 萃取側（模型未把裁示寫成議題／決議） |
| gemma F048 | **有**（notes L90「發生科內辦公室照片外流至 Line 群組（LB）之事件」） | 無 | **生成側**（僅寫了指令 L47/L26，未寫照片事證） |
| gemma F055 | **無**（`三樓/禮堂` 0） | 無 | 萃取側 |
| gemma F060 | **無定位**（`政風室` 0；`黴味` 有） | L60 部分 | 萃取側（定位缺） |
| gemma F066 | **無**（`新聞行銷/局長室` 0） | 無 | 萃取側 |
| qwen F019 | **有**（notes L47「上次颱風平上班日，土地稅科倉庫嚴重漏水，影響土地卡」） | 無 | **生成側** |
| qwen F056 | **有且精確**（notes L199「刨掉舊防水層，導致早期埋設的排水管外漏，大雨時水從破損排水管滲入」） | 無 | **生成側** |
| qwen F055 | **有（含禮堂／走廊）**（notes L198「水溢至禮堂、走廊、辦公室」） | 部分（缺禮堂／走廊） | 生成側（細節截斷） |

- 決定性：qwen 第 2 輪補強問題清單**明文包含**「議題遺漏 6 項：**土地稅科倉庫漏水與土地卡重印**」——機制看到了、仍未被寫入 ⇒ 生成／遵循度問題＋`LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2` 上限（§3 備援②已預先登錄「放行第 3 輪 ≈+17% 單場時間」）。
- gemma 的補強清單只抓到「禁止科內訊息外流（待辦）」與「業務移撥」⇒「資訊外洩」議題被視為已涵蓋（因指令句存在）、**照片事證未進期望集合** ⇒ 期望集合粒度不足（議題級 vs 事實級）。

## 2 Gate 判定

| 受驗條文 | 判定 | 理由（一句） |
|---|---|---|
| runner 場次完整性（16 checks／DOCX／build 指紋） | **PASS** | 兩場 16/16、failure_reasons 空、DOCX `unzip -t` OK 且 sha 與 manifest 一致、受測程式碼版本自證同一。 |
| gemma §5 主要驗收（7 條 ≥6 且 F044 命中；阻斷） | **FAIL** | 結構式命中 2/7（寬鬆 4/7）< 6，且 F044 全 `.md` 無任何語句（逐字稿 L145 明確存在）。 |
| qwen ①（`coverage_core` ≥27/28；阻斷） | **FAIL** | 自行重跑 25/28 < 27/28（E6b 27/28 → 退步 2 條；結構複核亦缺 F019 因由與 F056）。 |
| qwen ②（密度；非阻斷） | **PASS** | 37 條 ≤62 且平均 61.2 字 ≥48，兩路量測（ad-hoc＋儀器）一致。 |
| §7 停損 | gemma：**NOT_TRIGGERED**（+11.90% < 15%）；qwen：**TRIGGERED** | qwen +77.38% ≥15% 且主驗收未達 ⇒ 依 §7 停用 CORE-1b、走 CORE-1c；依 §3「二選一」與本場歸因（生成側），證據指向**備援②**而非備援①。 |
| gemma 既有品質門檻（observe 模式，不進 verdict） | **FAIL（不阻斷）** | `on_start` 0.84／`excl0` 0.8095 兩項不合格，且相對 E7C（0.9615／0.95 全過）為回退。 |

**整體**：本波兩條阻斷條文皆 **FAIL** ⇒ P7-B **不可宣告達標**；qwen 腿另觸發 §7 停損。密度維度（qwen ②）是本波唯一明確達標的主要指標。

## 3 反 gaming 抽驗（交付 `.md` 原文 vs 逐字稿原文）

1. **gemma F054（新命中）** — `.md` L61「因搬遷時間可能拖延，同仁需做好在臨時辦公室『長期抗戰』之心理準備（科長，00:41:51）」 ↔ 逐字稿 L163 `[00:32:34-00:33:07]`「我覺得我們會搬進去的時間可能會拖很久」。
   → 內容＝忠實改寫（非關鍵詞堆砌、非捏造）；**但標註時間 00:41:51 與來源段不符**，且逐字稿無「長期抗戰」字面 ⇒ 屬既有標註落點弱點（見 1.2 的 0.84）之具體實例，非 gaming。
2. **gemma F065（新命中）** — `.md` L63「財政四科分兩階段搬遷，第一階段由工產科及財管科先搬入；提及 10 月底（待確認）就要搬進來了（科長，00:44:15）」 ↔ 逐字稿 L189 `[00:43:03-00:44:15]`「…分兩階段第一階段有兩個課要先進來就是工產科跟財管科」「10月底就要搬進來了」。→ 忠實；日期未捏造、未知年份正確標「（待確認）」。
3. **qwen F055（新由 miss→cover）** — `.md` L58「三樓感恩室（音譯）漏水影響多層樓層，廠商已處理積水並封閉管路…正風室（音譯）旁空辦公室（將改為工廠科辦公室）黴味極重」 ↔ 逐字稿 L177/L179（三樓／感恩室／溢到禮堂／延伸到走廊）、L185（「他看到有管子的地方他就整個都把它封起來…應該不會再淹了」）、qwen notes L198/L201。→ 每項子句皆可溯源（含「封閉管路」）；**禮堂／走廊被截掉**，屬漏細節而非捏造。
4. **陰性對照**：gemma F044 — 逐字稿 L145 明確有裁示，`.md` 完全沒有 ⇒ 確認漏寫係**模型／流程**所致，而非事實清單瑕疵或 ASR 變體。

## 4 殘餘風險

1. **單場變異**：計畫自載「尾段萃取是機率性的（run-01／run-02 命中集合不同）」，且 F044 在歷史 5 場 gemma（E1／E2／E5b／E6／E7C）皆 0 命中；兩場各 1 次、無中位數 ⇒ 上述 gate 結論不宜外推為「穩定分布」。
2. **`coverage` 是字面、文件級量尺**：已實證 false positive（gemma F055／F060）與 false negative（改寫即漏）⇒ 不得作為唯一驗收尺；qwen ① 的阻斷條文本質仍建立在此尺上（本案結構複核恰與儀器同向，僅降低、未消除此風險）。
3. **跨模型比較含混淆**：gemma／qwen 兩族逐字稿 sha 不同（ASR＋校正差異），跨模型落差不可全歸模型；同模型前後對照則乾淨（E7C↔E8、E6b↔E8 逐字稿相同）。
4. **Windows／Ollama 實機 `[UNVERIFIED]`**（本機 macOS；§8 的 skip-reason 觀測與 engine 參數化測試只證同碼路徑，不證實機）。
5. **`estimated_chunk_count` 高估**（6000 ⇒ 估 3、實際 2）——規劃／顯示層風險；實測請以 pipeline `chunk_count=` 為準。
6. **E2E 追蹤證據缺密度欄位**：runner 投影的 `record_quality.json` 無 `full_document_item_count`／`full_document_avg_item_chars`（僅 runtime 檔有）⇒ qwen ② 的成果無法在既有 E2E 證據鏈直接查核（L6 缺口，未新增／放寬任何門檻）。
7. **gemma 標註落點回退**（0.9615→0.84；excl0 0.95→0.8095）＝既有門檻不合格但 observe 模式不阻斷；改善途徑（`snap_source_tags_to_transcript` 相似度）屬**語意變更**，須 Planner（SUPPORTING-2 本波預設 False）。
8. **時間已成迭代瓶頸**：qwen 單場 ≈30 分鐘、gemma ≈40 分鐘；任何「多一輪補強（≈+17%）」或「縮小分塊（+1 呼叫）」都會撞 §7 的 15% 預算 ⇒ 後續槓桿都需顯式成本決策。
9. **A 類佔位符**（可填未填，5 處在「全體同仁」列）與**彙整表第 1 欄**「（（待確認））」仍為已知缺口（計畫已 defer，未動語意）。
10. **Stage 04 自檢缺口（流程）**：兩場 E2E 的已 commit 產物中**未見**「§5 七條事實逐條判定」的自檢紀錄（`rg` 全任務目錄無命中／未命中清單）⇒ 阻斷條文未在實作階段被檢核，直到本 Stage 05 才暴露。

## 5 對下一波的建議（只列選項與代價；不自行變更語意）

- **A（對準本場歸因）**：擴充既有「逐條對帳」期望集合的**粒度與範圍**——把「萃取筆記已有、交付紀錄未寫」的事實視為硬性缺漏（不只待辦／決議／數字／日期），並處理 qwen F019 型「機制看到了仍未寫入」的遵循度問題。代價：主要為提示詞／期望抽取邏輯（地端專屬區塊，雲端 byte 不變），零新呼叫類型；但屬語意變更 ⇒ **Planner**。
- **B（放行第 3 輪補強）**：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 2→3。代價：計畫已預估 **≈+17% 單場牆鐘**（≥15% 預算，qwen 場將再觸 §7）⇒ 須顯式決策；對「筆記已有、紀錄未寫」型（qwen F019／F056、gemma F048）最直接。
- **C（備援①尾段補萃取）**：§7 停損之預設路徑。代價 +150.5 s（qwen +14.7%／gemma +7.1%）；**本場證據顯示 qwen 的兩條缺失皆為生成側，備援①預期對其無效** ⇒ 若仍選①，宜同時登錄「不預期改善 F019（00:08 段、非尾段）」。
- **D（縮小分塊以救萃取側）**：ceiling 6000→5500（離線重播：3 塊）。代價 +1 次萃取呼叫（時間可能再 >15%）；目標＝gemma F055／F066／F044 型萃取側漏寫。
- **E（歸因消融，最小版 2 場）**：CORE-2a 三紀律開／關各 1 場，檢驗「壓縮是否造成 qwen coverage 退步（−2 條）與密度大幅改善（37 條）」的因果。代價：2×≈30 分鐘 qwen 場；**這是把 A/B/C 從推測升級為證據的唯一路徑**。
- **F（標註落點）**：僅能走 SUPPORTING-2（`LOCAL_LLM_TAG_SNAP_SIMILARITY`，語意變更）⇒ Planner；不得放寬既有 5 項門檻。
- **G（證據鏈補洞）**：把 `full_document_item_count`／`full_document_avg_item_chars` 補進 runner 投影（只補投影、不加門檻），讓密度成果可在 E2E 證據直接查核。
