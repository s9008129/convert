# attempt-E4-qwen27b-p4-final 執行紀錄（`Qwen3.8-27B-Splash` @ HEAD `818b71e`，真實音檔 E2E）

> 本檔由執行 agent 撰寫（繁體中文）。數字一律由 `run_summary.json`／`task_final.json`／`sha256_manifest.json`／
> `backend_data/logs/app_2026-09-23.log`／重跑量尺取得；寫入範圍僅本目錄（append-only）。
> 本場是 **P4-A 收尾修補（`818b71e`：數字對帳整串邊界＋B1 歸屬集合語意）落地後，27B 的最終驗證場**，
> 也是使用者要求「不要測 35B-A3B、專注 27B」的最後一次真實音檔 E2E。

## 0. 自核結果

| 查核項 | 方法 | 結果 |
|---|---|---|
| HEAD／build revision | `run_summary.expected/actual_build_revision` | `818b71e6cc96934e922361d54b362b76ce1e0a2e`（相等） |
| 來源音檔 | `sha256`（Downloads 原檔＝stored upload） | `982151f4…012828`（45,107,503 bytes） |
| 逐字稿 | `sha256` | `c4136d39b92f…737b6`（**與 E3 的 `b3cb89a6…`、E2／D1 的 `199d37b5…` 不同**） |
| 紀錄 md | `sha256` | `45a942c37fb3bd640ed4cb30d75ae7cf016799f523b050712eed7815e0e2cd13` |
| DOCX | `sha256` | `89d88e40…5d6f78`＝`sha256_manifest.meeting_record_docx_sha256` |
| 量尺重跑 | runner 內建 `measure_coverage.py`（釘版清單 sha `cf012d1f…`） | `coverage_all 0.7015`／`core 0.8214`（23/28） |
| 閘門 | `run_summary.json` | `verdict=PASS`、`failure_reasons=[]`、16/16 checks 全 `true` |
| 品質檢查 | `record_quality.json .checks` | 5/5 全 `true`、`check_failures=[]`、`table_source_tag_count=0` |
| 模型 | `model_snapshot(.end).json` | `unique_loaded_llm_count=1`、instance `qwen3.8-27b-splash`、`base_url=http://127.0.0.1:1234` |

## 一、受測設定

| 項目 | 值 | 來源 |
|---|---|---|
| 模型 | `Qwen3.8-27B-Splash`（LM Studio key `qwen3.8-27b-splash`） | `model_snapshot.json` |
| 處理模式 | `processing_mode=local`；`effective_local_llm_provider=lmstudio` | `run_summary.engine` |
| 模板 | `section_meeting` | `task_final.template_id` |
| task_id | `a5abfc7c` | `task_final.json` |
| 執行窗（runner 牆鐘） | 2026-09-23T11:05:23.833 → 11:21:56.075；**992.2 s（16:32.2）** | `run_summary` |
| 任務端到端（產品） | 11:05:29.072 → 11:21:54.229；**985.2 s**；log「耗時: 985.2秒」 | `task_final.json`＋log |
| 觀測模式 | runner `--quality-mode observe` | 啟動命令 |
| 執行前置 | 乾淨工作樹 preflight 通過（HEAD `818b71e`） | runner stdout |

啟動命令：

```
uv run python scripts/e2e/run_owned_e2e.py \
  --audio "/Users/hsiaojohnny/Downloads/0903-科務會議.m4a" --template section_meeting \
  --processing-mode local \
  --artifacts-dir .agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-E4-qwen27b-p4-final \
  --runtime-dir data/cache/e2e/p4-qwen27b-e4 \
  --quality-mode observe \
  --coverage-checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json
```

## 二、耗時分解（證據：`backend_data/logs/app_2026-09-23.log`）

| 階段 | 秒數 | 佔比 | 關鍵數字 |
|---|---|---|---|
| ASR（apple，fail-closed） | **15.9** | 1.6% | `audio_duration_seconds=2695.061`、RTF 0.0059、`segment_count=1340`、dropped 0 |
| diarization | **153.0** | 15.5% | 682 段、8 位發言者、RTF 0.057；標註後 183 段發言 |
| 語意校正（LLM） | **68.4** | 6.9% | 45 段中 8 段有修正、1 段放棄、**採納 22 處替換** |
| 摘要 round 0（紀錄生成） | **258.9** | 26.3% | `prompt_tokens=12474`、`completion_tokens=3482`、`finish_reason=stop` |
| 摘要（萃取筆記） | **231.7** | 23.5% | 產出 3220 tokens 筆記、零損串接 |
| 摘要 round 1（品質補強） | **256.3** | 26.0% | 補強未收斂（問題集合與上一輪相同，共 4 項）→ 依設計停止再補強 |
| DOCX 轉換 | 1.0 | 0.1% | 紀錄 md → DOCX |
| **合計** | **985.2** | 100% | **本機 LLM 呼叫（校正＋3 次生成）＝ 815.3 s（82.8%）** |

- `[VERIFIED]` 瓶頸是**本機 LLM 推論**（82.8%），不是 ASR（1.6%）也不是 diarization（15.5%）；`logical_generations=3`。
- `[VERIFIED]` 本場**只跑 1 輪補強就停**（`_summarize_with_local_pipeline:3146` 判定問題集合未收斂 → 停止），仍殘留 `600塊`／`100塊`／`15%`／`週一`。

## 三、品質量測（觀測，不列 verdict）

| 指標 | 值 | 對照（E3／雲端 C5） |
|---|---|---|
| `coverage_all`／`coverage_core` | 0.7015／0.8214（23/28） | E3 0.7761／0.8571；C5 0.8060／0.8929 |
| 未涵蓋 core | `F021`、`F045`、`F054`、`F065`、`F066` | `F021` 與 B2／E3 相同（`內機`／`內稽` 校正缺口） |
| 出處標註 | 29 個、20 個不同時間戳（`distinct 0.690`）、`00:00:00` 6 個 | E3 45／0.667／8 |
| `exact_tag_ratio`／`same_speaker` | 0.000／0/29 | **全部標註都用「科長」角色名** → 量尺以逐字稿「發言者N」為 ground truth，屬系統性扣分 |
| `number_fabricated` | **0** | 地端四場皆 0 |
| `entity_flags` | **1**（`煙酒文宣股`、kind=`variant`） | 已註冊變體待確認；非捏造 |
| `number_missing_tokens` | `600塊`、`100塊`、`15%`（3） | E2 0 項、E3 2 項 |
| 亂碼殘留（20 型清單，`/tmp/qp01/garble7.py`） | **9 次／6 型** | E3 18 次、B2 18 次、C5 1 次 |
| 46 項細節探針（`/tmp/qp01/probe7b.py`） | 31/46 = 0.674 | E3 0.761、B2 0.848、C5 0.652 |

## 四、與 E3 的差異（同模型、同引擎、只差 build）

| 指標 | E3（`0d34fa1`） | E4（`818b71e`） | 方向 |
|---|---|---|---|
| `coverage_all` | 0.7761 | 0.7015 | −7.5pt |
| `coverage_core` | 0.8571 | 0.8214 | −3.6pt |
| 細節探針 | 0.761 | 0.674 | −8.7pt |
| 亂碼殘留 | 18 次 | 9 次 | **改善 2 倍** |
| `（待確認）` | 17 | 29 | 避險大增 |
| 條目數／均字／最長 | 45／37.2／98 | 29／43.2／69 | 更接近雲端壓縮策略 |
| 補強輪數 | 1（收斂後停） | 1（未收斂即停） | 相同 |

- `[VERIFIED]` 兩場唯一差別是 build 與取樣（temperature 0.6→0.7），**方向相反的兩個指標（事實下降、乾淨度上升）同時出現** → 本場的差異屬「取捨策略漂移」，不宜宣稱修補造成品質改變。
- `[VERIFIED]` `內機`／`內稽` 校正缺口在 E4 **第三次重現**（交付逐字稿仍是 `內機` 2 次、紀錄整條略去）→ 27B 校正層穩定缺陷。
- `[OBSERVED]` E4 把逐字稿快取的 `猜情`（ASR 亂碼，7 場逐字稿皆有 2 次）**首次抄進紀錄**（「猜情（出勤）」）→ 紀錄層也會二次引入亂碼，不只沿用。

## 五、已知限制

1. `[VERIFIED]` 單次抽樣（temperature 0.7）→ 本場為**觀察值**，不可與 E3／B2 直接比大小；aggregate 宣稱需 ≥2 次取中位數（plan §9.3 F1②）。
2. `[VERIFIED]` 產物落點：`data/cache/e2e/p4-qwen27b-e4/backend_data/outputs/0903-科務會議_a5abfc7c.{md,docx}`（`data/**` gitignored，證據以 sha256 留痕）。
3. `[VERIFIED]` runner 產出的品質檔為**觀測值**（`observation_only=true`、`gate_effect=none`），不影響 `verdict`。
