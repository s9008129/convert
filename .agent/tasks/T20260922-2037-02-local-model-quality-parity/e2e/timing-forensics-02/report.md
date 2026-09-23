# 會議紀錄生成耗時鑑識報告（timing-forensics-02）

- 角色：唯讀效能鑑識（未修改任何既有檔案、未跑測試套件、未呼叫 LM Studio 生成、未動 `data/cache/e2e/p4-qwen27b-e4/**`；唯一寫入＝本檔）
- 日期：2026-09-23（Asia/Taipei）；分支 `fix/qwen-local-quality-parity`
- 共同音檔：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`，長度 **2695.061 s**（E4L:34、D1L:34）
- 硬體（`system_profiler SPHardwareDataType` 實測）：MacBook Pro `Mac16,8` / **Apple M4 Pro 12 核（8P+4E）** / **48 GB** 統一記憶體
- 本版與 `timing-forensics-01` 同一方法，新增 **E4（本輪最新、已完賽）**、**E3**、**E2**，並把 prefill／decode 用 LM Studio **伺服器端**統計重算

## 0. 摘要（先看這裡）

1. **最新場 E4（`qwen3.8-27b-splash`）= 任務端到端 985.2 s（16.4 分）／runner 牆鐘 992.24 s**，比 E3 的 1396.12 s **快 28.9%**；差別幾乎全部來自「補強只跑 1 輪就停損」（E4L:109）。
2. E4 耗時結構：**本機 LLM 809.5 s（82.2%）**＝ **prefill（讀提示）481.3 s（48.9%）＋ decode（產生內容）328.2 s（33.3%）**；**固定成本 ASR 15.89 s＋diarization 153.0 s＝168.9 s（17.1%）**；**DOCX 只有 1.04 s（0.1%）**。
3. **M4 Pro 不是主瓶頸。** 同一台機器、同一支音檔、同一晚：MoE `qwen3.6-35b-a3b-splash` 的 prefill 為 **~632–833 tok/s**、decode **59.4–191.0 tok/s**；dense `qwen3.8-27b-splash` 為 **~98 tok/s**、**25.8–30.7 tok/s**；`gemma-4-31b-it-mlx` 為 **~72 tok/s**、**~10 tok/s**（§5）。慢的根源是「**模型架構 × 提示量 × 呼叫次數 × 補強輪數**」。
4. 使用者手動那場（`836fcae7`，17:59:40 完成）= **303.9 s**（ML22:1050，MoE＋逐字稿快取命中）；另一場手動 dense 27B（`b20c90a7`，17:47:46）= **1029.9 s**（ML22:958，快取命中）。同機差 **3.4 倍**，再次指向模型吞吐而非硬體。

## 1. 證據來源與量測定義

**Log 代號**

| 代號 | 檔案 |
|---|---|
| `E4L` | `data/cache/e2e/p4-qwen27b-e4/backend_data/logs/structured_2026-09-23.jsonl` |
| `E3L` | `data/cache/e2e/p4-qwen27b-e3/backend_data/logs/structured_2026-09-23.jsonl` |
| `E2L` | `data/cache/e2e/p4-gemma31b-e2/backend_data/logs/structured_2026-09-23.jsonl` |
| `E1L` | `data/cache/e2e/p4-gemma31b-e1/backend_data/logs/structured_2026-09-23.jsonl` |
| `D1L` | `data/cache/e2e/p3-gemma31b-d1/backend_data/logs/structured_2026-09-23.jsonl` |
| `D2L` | `data/cache/e2e/p3-gemma31b-d2/backend_data/logs/structured_2026-09-23.jsonl` |
| `B2L` | `data/cache/e2e/p2-27b-fix-01/backend_data/logs/structured_2026-09-22.jsonl` |
| `ML22` | `data/logs/structured_2026-09-22.jsonl`（手動場） |
| `LMS23` | `~/.lmstudio/server-logs/2026-09/2026-09-23.1.log` |
| `LMS22` | `~/.lmstudio/server-logs/2026-09/2026-09-22.1.log` |
| `E4S` | `.agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-E4-qwen27b-p4-final/run_summary.json` |

**量測定義**（全部取 log 時間戳／自報秒數，非估算）

- 「任務秒」＝ backend `處理完成，耗時: x秒`；「runner 牆鐘」＝ `run_summary.finished_at − started_at`（E4S）。
- 「語意校正秒」＝ 第一筆校正呼叫的時間戳 → `語意校正完成` 行。
- 「萃取／首版／補強 N」＝ pipeline metrics 的 `duration_seconds`（`extraction`／`final_and_refine`）＋ 相鄰呼叫行時間戳切段（同 E3 run_notes 定義）。
- 「prefill 秒」＝ LM Studio **伺服器端** `Done · … · TTFT x s` 的 TTFT 加總（splash 格式模型）；「decode 秒」＝ **推導** Σ(`output ÷ tok/s`)；gemma（MLX 格式）改用 `Prompt cache restore: cached_tokens=0 uncached_tokens=N` → `Prompt processing progress: 100.0%` 兩個時間戳差（純 prefill）＋ decode ＝ backend 段時長 − prefill。
- 「tok/s」若無伺服器端直方圖，皆標「推導」。

## 2. 各場次牆鐘時間總表

| 場次 | 完成時間（Asia/Taipei） | 模型（LM Studio key） | logical gens／補強輪 | 逐字稿 | 任務秒 | runner 牆鐘秒 | 證據 |
|---|---|---|---|---|---|---|---|
| **E4**（最新） | 09-23 11:21:54 | `qwen3.8-27b-splash` | 3／**1 輪（停損）** | 冷跑：ASR 15.89＋diar 153.0 | **985.2** | **992.24** | E4L:116、E4L:111、E4S |
| **E3** | 09-23 10:37:10 | `qwen3.8-27b-splash` | 4／2 輪（跑滿） | 冷跑：ASR 15.62＋diar 155.1 | **1384.9** | **1396.12** | E3L:122、E3L:117 |
| B2（P4 前） | 09-22 21:46:49 | `qwen3.8-27b-splash` | 4／2 輪 | 冷跑 | 1703.0 | 1709.73 | B2L:116、B2L:111 |
| 手動 `b20c90a7` | 09-22 17:47:46 | `qwen3.8-27b-splash` | 8（chunk=4、merge=1） | **快取命中**（ML22:874） | **1029.9** | —（非 runner） | ML22:958、ML22:953 |
| **E2** | 09-23 09:56:57 | `gemma-4-31B-it-MLX-4bit` | 4／2 輪 | 冷跑：ASR 16.2＋diar 152.4 | 2099.2 | 2107.87 | E2L:128、E2L:123 |
| **E1** | 09-23 05:38:42 | `gemma-4-31B-it-MLX-4bit` | 4／2 輪 | 冷跑：ASR 15.8＋diar 152.0 | 2270.8 | 2278.77 | E1L:143、E1L:138 |
| D2（P4 前） | 09-23 03:58:57 | `gemma-4-31B-it-MLX-4bit` | 2／0 輪 | 冷跑：ASR 15.5＋diar 152.0 | 1241.7 | 1251.13 | D2L:106、D2L:101 |
| D1（P4 前） | 09-23 01:55:49 | `gemma-4-31B-it-MLX-4bit` | 2／0 輪 | 冷跑：ASR 15.6＋diar 151.7 | 1218.6 | 1227.22 | D1L:106、D1L:101 |
| 手動 `836fcae7` | 09-22 17:59:40 | `qwen3.6-35b-a3b-splash`（MoE） | 8（chunk=4、merge=1） | **快取命中**（ML22:966） | **303.9** | —（非 runner） | ML22:1050、ML22:1045 |

補充（同一份 `.docx` 的到手時間，非生成時間）：`b20c90a7` 任務完成後 **+219.1 s** 才出現 DOCX（ML22:958→ML22:959）；`836fcae7` **+124.3 s**（ML22:1050→ML22:1051）。`[INFERRED]` 這是下載動作觸發的轉檔，不是生成變慢；runner（E2E）場的 DOCX 一律 1–5 s。

### 2.1 手動兩場的階段拆解（同一支音檔、逐字稿快取命中）

| 階段 | `b20c90a7`（dense 27B，1029.9 s） | `836fcae7`（MoE 35B-A3B，303.9 s） | 證據 |
|---|---|---|---|
| ASR＋diarization | **0（快取命中）** | **0（快取命中）** | ML22:874、ML22:966 |
| 語意校正（12 次） | 111.96 | **33.79** | ML22:876→ML22:923、ML22:968→ML22:1015 |
| pipeline 合計 | 917.8 | **270.0** | ML22:953、ML22:1045 |
| － 萃取 | 449.4 | 98.2 | 同上 |
| － 合併（merge，chunk=4） | 191.7 | 46.0 | 同上 |
| － 首版＋補強 | 276.7 | 125.8 | 同上 |
| DOCX（下載觸發，非生成） | +219.1 | +124.3 | ML22:959、ML22:1051 |

> 兩場呼叫數相同（校正 12＋生成 8＝20 次）、音檔相同、快取狀態相同，**唯一差異是模型**：3.39 倍。這是「不是 M4 的問題」最直接的同機對照。

## 3. E4 階段拆解（時間戳逐筆，證據＝E4L 行號）

| 階段 | 起（時間戳） | 訖（時間戳） | 秒 | 佔任務 985.2 s | 證據 |
|---|---|---|---|---|---|
| ASR（apple 引擎，fail-closed） | 11:05:29.072 | 11:05:45.573 | **15.89** | 1.6% | E4L:30、E4L:34 |
| diarization（pyannote，8 位發言者） | 11:05:45.573 | 11:08:18.609 | **153.0** | 15.5% | E4L:35 |
| 語意校正（12 次 LLM 呼叫） | 11:08:18.980 | 11:09:27.098 | **68.1** | 6.9% | E4L:40–E4L:87 |
| 萃取筆記（extraction，1 次呼叫） | 11:09:27.109 | 11:13:46.060 | **259.0** | 26.3% | E4L:91、E4L:92、E4L:111 |
| 主合併／首版生成（1 次呼叫；`merge=0.0`，chunk=1） | 11:13:46.064 | 11:17:37.847 | **231.8** | 23.5% | E4L:96、E4L:102 |
| 補強第 1 輪（1 次呼叫） | 11:17:37.851 | 11:21:54.227 | **256.4** | 26.0% | E4L:102–E4L:111 |
| 後處理（術語／吸附）＋ DOCX | 11:21:54.228 | 11:21:55.266 | **1.04** | 0.1% | E4L:116、E4L:117 |
| 第 2 輪 | — | — | **0（被停損）** | 0% | E4L:109（問題集合與上一輪相同 → 停止再補強） |
| 合計 | 11:05:29.072 | 11:21:55.266 | 985.2＋1.0 | — | — |

- pipeline metrics：`{'extraction': 259.0, 'merge': 0.0, 'final_and_refine': 488.2, 'total': 747.1}`、`logical_generations=3`（E4L:111）。
- 三個最大項＝**萃取 26.3%＋補強 26.0%＋首版 23.5%＝75.8%**；固定成本 17.1%；DOCX 0.1%。
- 停損理由（逐字）：`本地摘要補強未收斂（問題集合與上一輪相同，共 4 項）→ 停止再補強，避免白燒與重生成造成的品質退化`（E4L:109）；問題集合＝數字遺漏 2（15、600）、日期遺漏 1（週一）、專名待確認（煙酒文宣股）、金額待確認（E4L:102）。

## 4. 每階段呼叫次數與 token（E4／E3 對照）

**E4（15 次呼叫；LMS23:7125–7910）**

| 階段 | 呼叫次數 | Σ prompt tokens | Σ cached | Σ output tokens | prefill 秒（ΣTTFT） | decode 秒（推導） | 段總計 |
|---|---|---|---|---|---|---|---|
| 語意校正（`_summarize_with_lmstudio`，temp 0.3、max 3072、`allow_reasoning_retry=False`） | 12 | 13,586 | 13,376 | 3,729 | 6.5 | 56.0 | 68.1 |
| 萃取（temp 0.6、max 8192、retry=True） | 1 | 12,474 | 0 | 3,482 | 124.1 | 135.0 | 259.1 |
| 首版生成（temp 0.7、max 8192、retry=True） | 1 | 17,983 | 1,824 | 2,051 | 163.1 | 68.6 | 231.7 |
| 補強第 1 輪（temp 0.7、max 8192、retry=True） | 1 | 20,296 | 1,856 | 2,051 | 187.6 | 68.6 | 256.2 |
| **合計** | **15** | **64,339** | **17,056** | **11,311** | **481.3（48.9%）** | **328.2（33.3%）** | **809.5** |

- 全場 `reasoning_chars=0`、`reasoning_tokens=None`（LM Studio 端每個回應都如此，例：E4L:103）；`semantic_attempts=0`、`network_retries=0`（E4L:111）→ **沒有重試或 thinking 溢出行為**。
- 規劃行：`context_window=128000(lmstudio_instance), estimated_tokens=11712, chunk_budget=122063, merge_visible_target=4096, merge_feasible_input=118858, merge_provider_output=3072, needs_chunking=False`（E4L:91）→ **沒有 context 溢出，也沒有被 8192 夾住**。

**E3（16 次呼叫；LMS23:6197–7056）**

| 階段 | 呼叫次數 | Σ prompt | Σ output | prefill 秒 | decode 秒（推導） | 段總計 |
|---|---|---|---|---|---|---|
| 語意校正 | 12 | 13,586 | 3,729 | 58.2 | 57.4 | 120.1 |
| 萃取 | 1 | 12,475 | 3,527 | 121.8 | 131.6 | 253.4 |
| 首版生成 | 1 | 18,026 | 2,573 | 181.6 | 85.2 | 266.8 |
| 補強第 1 輪 | 1 | 20,894 | 2,582 | 210.8 | 84.1 | 294.9 |
| 補強第 2 輪 | 1 | 20,843 | 2,582 | 193.8 | 84.1 | 277.9 |
| **合計** | **16** | **85,824** | **14,993** | **766.2（55.3%）** | **441.3（31.9%）** | **1,207.5** |

**E4 vs E3 的三個關鍵差異（同模型、同提示、同機器）**

1. **校正階段 120.1 → 68.1 s（−43%）**：E4 的 12 連發全部命中 prompt 前綴快取（E3 只有後 10 筆命中 768–800；前 2 筆 `cached=0`，TTFT 10.9／11.2 s → E4 全數 0.5–0.7 s）。證據：E3L 呼叫行（10:16:56.923…）與 LMS23:6197 起 vs E4L:40 起與 LMS23:7125 起。
2. **補強輪數 2 → 1**：E3 第 1 輪的問題含**假陽性**（議題「公務車使用」括號詞組；E3L:104）與**B1 邊界假陽性歸屬**（E3L:105 前後），使第 2 輪跑滿；E4 的問題集合全是真缺口且「與上一輪相同」→ 停損（E4L:109）。省下約 256–295 s。
3. **輸出量變小**：3 個大呼叫 output 3,482＋2,051＋2,051＝7,584 tokens（E3 為 3,527＋2,573＋2,582＝8,682），且 E4 沒有第 2 輪 → decode 少約 113 s。

## 5. 對照組：同機不同模型的吞吐（不是 M4 的問題）

| 模型（同機 M4 Pro / 48 GB） | prefill 實測／推導 | decode 實測 | 證據 |
|---|---|---|---|
| `qwen3.6-35b-a3b-splash`（MoE 35B/A3B，手動場） | **~632–833 tok/s**（input 3,667／TTFT 4.4 s；input 7,385 cached 1,824／TTFT 8.8 s） | 生成 **59.4–81.7**；校正 **155.8–191.0** | LMS22:5010、LMS22:5396、LMS22:4394–4954 |
| `qwen3.8-27b-splash`（dense 27B，E4） | **~98.2 tok/s**（Σ(uncached)/ΣTTFT ＝ 47,283/481.3） | **25.8–30.7**（大呼叫）／**56.7–71.5**（校正） | LMS23:7787、LMS23:7848、LMS23:7910、LMS23:7671–7725 |
| `gemma-4-31B-it-MLX-4bit`（dense 31B，D1） | **~72.4 tok/s**（13,178 tokens／182 s prefill） | **~10.2–11.4**（推導：大呼叫 1,744／1,551 tokens、decode 164.4／151.4 s → 10.6／10.2；校正 294 tokens／26 s → 11.3） | LMS23:1571→LMS23:1582、D1L:96–D1L:97 |

- **倍率（同階段對同階段）**：prefill — MoE 是 dense 27B 的 **6.4–8.5 倍**、gemma 31B 的 **8.7–11.5 倍**。decode — 生成段 MoE 59.4–81.7 對 27B 25.8–30.7＝**2.3–2.7 倍**、對 gemma 10.2–10.6＝**5.6–8.0 倍**；校正段 MoE 155.8–191.0 對 27B 56.7–71.5＝**2.2–3.4 倍**、對 gemma ~11.3＝**13.8–16.9 倍**。
- 同一支 45 分鐘音檔的「生成段」比較：MoE 手動場 270.0 s（ML22:1045）vs E4 747.1 s → **2.8 倍**；其中 MoE 是 8 次呼叫、E4 是 3 次呼叫，**呼叫更少還快 2.8 倍**。
- gemma 場的 2 輪補強讓 E1 的生成段達 1,743.6 s（E1L:138），比 D1 整場 1,218.6 s 還長 → 補強輪數的槓桿與硬體無關。

## 6. 瓶頸結論（一句話）

**「主瓶頸是 dense 27B 的 prefill（~98 tok/s）乘上每次 1.8–2 萬 token 的提示量（E4 佔 48.9%），其次是 decode 輸出量（33.3%）；固定成本 ASR＋diarization 只佔 17.1%，DOCX 0.1%，而 M4 Pro 本身不是瓶頸——同一台機器跑 MoE 模型 prefill 快 6–8 倍、decode 快 2–6 倍。」**

- 歸因拆解（E4、任務 985.2 s）：模型吞吐（prefill 481.3＋decode 328.2）＝ **82.2%**；提示量／呼叫次數（3 個大呼叫各 1.2–2.0 萬 token，`cached` 僅 0／1,824／1,856）＝ **其中最大單一因子**；補強輪數＝ **26.0%（已由停損從 2 輪降到 1 輪）**；ASR 1.6%、diarization 15.5%、DOCX 0.1%；**等待／重試＝0**（`semantic_attempts=0, network_retries=0`，E4L:111）。
- 「M4 不是主瓶頸」的證據形式＝**反事實對照**（同機、同音檔、同晚換模型 6–8 倍差距），**不是**硬體儀器量測。`[UNKNOWN]` 本報告沒有 GPU 利用率／記憶體頻寬／功耗（`powermetrics` 需 sudo、Instruments 未使用）；若要硬性排除散熱或頻寬因素，需補這類量測。既有環境證據：`parallel=4` 已開但 backend 全程序列呼叫；context 自動配置 working_set 37.44 GiB／safe_ceiling 34.44 GiB（48 GB 機），無 OOM。

## 7. 可操作建議（不放寬任何品質門檻；2–3 項）

1. **讓大呼叫吃到 prompt 前綴快取（最高性價比，屬提示「組裝順序」而非語意變更）**
   - 觀察：E4 的 3 個大呼叫 prompt 1.2–2.0 萬 token，`cached` 只有 0／1,824／1,856 → TTFT 124.1／163.1／187.6 s（LMS23:7787／7848／7910）。同一批校正呼叫因為前綴一致，快取命中後 TTFT 由 3–11 s 降到 0.5–0.7 s（E3 vs E4）。
   - 預期效果：若把「固定規則／模板／評分準則」集中在提示最前面（逐段證據往後放），三大呼叫各吃下約 8k 前綴 → 每次省 60–80 s，全場可省 **約 180–240 s（−18%～−24%）**。`[INFERRED]`（依 prefill 速率與快取後 TTFT 推算，未實測）。
   - 風險：需回歸驗證來源標註、覆蓋率、B1 歸屬不變；**不得**改雲端提示詞、不得改閘門門檻。
2. **保留／重用逐字稿快取（省固定成本，與模型無關）**
   - 觀察：E2E 冷跑每場都重付 ASR 15.89＋diarization 153.0＝**168.9 s（17.1%）**；兩場手動測試因為命中快取（ML22:874／ML22:966）完全不付這筆。
   - 預期效果：同一音檔重跑（例如換模型比品質）時 **−17% 牆鐘**，且不影響生成內容。
   - 風險：快取鍵必須含音檔 sha256（現行已含，`982151f4…`）；不同音檔或去人聲版本不可誤用；需確認產品端 UI 是否會誤導使用者以為「有快取＝沒重跑」。
3. **把「真缺口」的停止條件寫成顯性終態（省一輪補強，但屬語意變更需走 Plan/Review）**
   - 觀察：E4 已因「問題集合與上一輪相同」停損而只跑 1 輪（E4L:109）→ 相對 E3 省 256–295 s。但目前停損後仍把缺口留在紀錄裡（數字 15、600；日期 週一），靠讀者自行發現。
   - 預期效果：若在停損時直接把未涵蓋項目寫成「（待確認）」並結束（不再多跑一輪），每場最多再省 **約 230–260 s（−23%～−26%）**。
   - 風險：**這是「終態語意／閘門行為」變更** → 依 `workflow-routing` 必須走 **Plan／Review**，不得由執行者自行放寬；需產品端同意「顯性缺漏標記」可接受。
- **禁區（不得為省時間而動）**：既有閘門門檻、`off` 模式行為、`task_processor.py:259/262`、雲端提示詞。特別是**不要**為了加速而調降 `max_tokens`、關掉校正或降低覆蓋率檢查——校正階段本來就沒有 thinking（`reasoning_chars=0`），時間主要卡在 prefill，調這些只會傷品質。

## 8. 附錄：原始引用行（可回溯）

**LM Studio 伺服器端（E4）**
- `LMS23:7787` `11:13:46 Done · input 12,474 · cached 0 · output 3,482 · TTFT 124.1s · 25.8 tok/s`
- `LMS23:7848` `11:17:37 Done · input 17,983 · cached 1,824 · output 2,051 · TTFT 163.1s · 29.9 tok/s`
- `LMS23:7910` `11:21:54 Done · input 20,296 · cached 1,856 · output 2,051 · TTFT 187.6s · 29.9 tok/s`
- 校正 12 連發：`LMS23:7125`（`input 1,121 · cached 1,120 · output 260 · TTFT 0.5s · 68.0 tok/s`）…`LMS23:7725`（`input 1,116 · cached 1,088 · output 249 · TTFT 0.7s · 65.0 tok/s`）

**LM Studio 伺服器端（E3）**
- `LMS23:6865` `10:23:10 Done · input 12,475 · cached 0 · output 3,527 · TTFT 121.8s · 26.8 tok/s`
- `LMS23:6927` `10:27:36 Done · input 18,026 · cached 0 · output 2,573 · TTFT 181.6s · 30.2 tok/s`
- `LMS23:6991` `10:32:31 Done · input 20,894 · cached 0 · output 2,582 · TTFT 210.8s · 30.7 tok/s`
- `LMS23:7056` `10:37:09 Done · input 20,843 · cached 1,824 · output 2,582 · TTFT 193.8s · 30.7 tok/s`

**LM Studio 伺服器端（gemma D1／MLX）**
- `LMS23:1571` `01:43:30 Prompt cache restore: cached_tokens=0 uncached_tokens=13178` → `LMS23:1582` `01:46:32 Prompt processing progress: 100.0%`（＝182 s prefill，72.4 tok/s）
- `LMS23:1635` `01:49:17 … uncached_tokens=17040` → `LMS23:1648` `01:53:18 … 100.0%`（＝241 s prefill，70.7 tok/s）

**LM Studio 伺服器端（MoE 手動 836fcae7）**
- `LMS22:4394` `17:54:39 Done · input 1,099 · cached 0 · output 280 · TTFT 1.6s · 182.0 tok/s`（校正）
- `LMS22:5010` `17:55:40 Done · input 3,667 · cached 0 · output 1,990 · TTFT 4.4s · 75.4 tok/s`
- `LMS22:5396` `17:59:40 Done · input 7,385 · cached 1,824 · output 2,045 · TTFT 8.8s · 61.7 tok/s`

**Backend 行（E4）**：`E4L:30`（開始）／`E4L:34`（ASR 15.89 s）／`E4L:35`（diar 153.0 s）／`E4L:87`（校正完成，採納 22 處替換）／`E4L:91`（上下文規劃）／`E4L:92`（萃取呼叫）／`E4L:96`（首版呼叫）／`E4L:102`（補強第 1 輪，4 項問題）／`E4L:109`（停損）／`E4L:110`（殘留問題）／`E4L:111`（pipeline metrics＋cov_*）／`E4L:116`（任務完成 985.2 s）／`E4L:117`（DOCX）
