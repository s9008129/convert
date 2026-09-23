# Gemma 4 31B（E5）E2E 預檢報告（唯讀）

- 任務：`T20260922-2037-02-local-model-quality-parity`｜階段：E5 gemma 預檢（preflight，非驗收）
- 稽核時間：2026-09-23 12:20–12:35（Asia/Taipei）｜模式：**唯讀**
- 硬約束遵循：未載入／卸載任何模型、未對 `http://127.0.0.1:1234/v1/chat/completions` 發出任何請求、未啟動 backend、未 kill 任何 process；僅使用 `GET /v1/models`、`lms ps/ls/--help`、`GET 127.0.0.1:58881/api/config`、檔案讀取。
- 同期現況：`qwen3.8-27b-splash` E2E（E5 場）正在執行中 — `lms ps` 顯示 `GENERATING`／17.38 GB／CONTEXT 128000（live 觀測）；backend `data/cache/e2e/p4-qwen27b-e5/backend.log:23`（12:14:30 啟動行）。

## 結論

- `[VERIFIED]` **模型 id 對應無阻礙**：使用者給的 `gemma-4-31B-it-MLX-4bit` 只是**磁碟目錄名**；LM Studio 實際 API model id 為 **`gemma-4-31b-it-mlx`**（全小寫、無 `-4bit` 尾綴）。runner 的「唯一 loaded 模型」gate **不比對模型名稱**，故不會對不上。
- `[VERIFIED]` **gate 唯一真風險＝同時載入兩顆 LLM**：runner 要求「恰好 1 個 loaded LLM model／1 個 instance」（`scripts/e2e/run_owned_e2e.py:489-506`），backend 亦同構拒絕多顆並載（`backend/services/summarization.py:2823-2826`、`:2894-2899`）。→ **E5 前必須先卸載 qwen**。
- `[VERIFIED]` **檔案齊全**：4 個 safetensors shard（合計 18,412,016,832 B）＋ tokenizer／chat template／`processor_config.json`；量化為 **MLX 4bit affine**（`config.json`：`quantization.bits=4, group_size=64`；LM Studio metadata `quantization.name="4bit"`, `format="mlx"`）。**沒有獨立 mmproj 投影檔**（vision 走統一權重，`architectures=["Gemma4ForConditionalGeneration"]`；文字會議紀錄任務不需要它）。
- `[VERIFIED]` **context 疑慮可排除**：`num_ctx=8192` 只是**設定顯示值與 Ollama 路徑的尺**（來源：`backend/main.py:110` 讀 `settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`，預設定義 `backend/core/config.py:198-201`）。LM Studio 路徑的權威視窗是**已載入 instance 的 `context_length`**（`backend/services/summarization.py:3016-3026`）→ gemma 歷史 5 場實跑皆為 `71936`；E1/E2 日誌顯示規劃 `needs_chunking=False`、`chunk_budget=65999`（逐字稿 est 11712 tokens）→ **不會因同一套設定掉品質**。前提：載入 gemma 時 context 不要設得比需求小（建議 ≥65536，勿用 tiny context）。
- `[VERIFIED]` **記憶體需先卸載 qwen**：本機總 RAM ≈ 48 GiB（51,539,607,552 B）；qwen 現佔 17.38 GB，gemma 權重 18.44 GB → 同時駐留 ≈35.8 GB 權重＋兩份 KV＋系統，48 GiB 機器會嚴重壓縮／降速（目前 free ≈73 MiB、compressor ≈10.9 GiB、swap used 204.88 MB，live 觀測）。
- `[VERIFIED]` **歷史 gemma 5 場全部 PASS**（C1/D1/D2/E1/E2），同一 model key、同一音檔、同一模板；E1/E2 之量尺 checklist 同一（`cf012d1f…`）→ **E5 可直接沿用同一 gate**。
- `[UNVERIFIED]` gemma 在 E5 同一 build（`818b71e`）上的實際結果尚未產生（本次只做預檢，未跑）。

## 模型 id 對應

| 來源 | 值 | 證據 |
|---|---|---|
| 使用者給的名稱 | `gemma-4-31B-it-MLX-4bit` | 使用者指令 |
| 磁碟目錄（檔名） | `~/.lmstudio/models/lmstudio-community/gemma-4-31B-it-MLX-4bit/` | `find`／`ls -la` 結果（live 觀測） |
| LM Studio OpenAI 相容 API id | **`gemma-4-31b-it-mlx`** | `GET http://127.0.0.1:1234/v1/models` → `data[].id`（live 觀測） |
| `lms ls` identifier | `gemma-4-31b-it-mlx`（31B／gemma4／18.44 GB） | `~/.lmstudio/bin/lms ls`（live 觀測） |
| LM Studio native `/api/v1/models` key | `gemma-4-31b-it-mlx` | `.agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-E4-qwen27b-p4-final/model_snapshot.json:26` |
| display_name／architecture | `Gemma 4 31B Instruct`／`gemma4` | 同上 `:27`／`:28` |
| 量化／格式 | `{name:"4bit", bits_per_weight:4}`／`format:"mlx"` | 同上 `:29-32`／`:37` |
| max_context_length | `262144` | 同上 `:36` |
| capabilities | `vision:true, trained_for_tool_use:true` | 同上 `:38-41` |
| 歷史 E2E instance_id／context | `gemma-4-31b-it-mlx`／`71936` | `attempt-E1-gemma31b-p4/model_snapshot.json:7`、`:10`、`:11`（C1/D1/D2/E2 同型：`:7`、`:11`） |

**「唯一 loaded 模型」gate 判定（不會因名稱對不上）**：

- `[VERIFIED]` gate 只數「native inventory 中 `type=="llm"` 且有 `loaded_instances`」的模型數，**完全不解析、也不比對模型名稱**：抓取 `scripts/e2e/run_owned_e2e.py:307`（`capture_model_snapshot`）→ `:321`（`GET /api/v1/models`）→ `:331`（`if model.get("type") == "llm" and instances:`）→ `:350-353`（`loaded_instance_ids`／`unique_loaded_llm_count`／`openai_compat_model_ids`）。
- `[VERIFIED]` 判定本體：`:489-506` `validate_model_inventory_unique` — 必須「恰好 1 model、恰好 1 instance」；不一致訊息為 `model inventory 違規：loaded LLM model 數量=…`（`:494-497`）。
- `[VERIFIED]` 前後一致：`:509-524` `validate_model_snapshot_consistent`（start/end 的 model/instance/context 必須相同）。
- `[VERIFIED]` 兩檢查列入必要清單：`:2067`（`model_inventory_unique`）、`:2076`（`model_snapshot_consistent`）；provider 拆分定義於 `:193`、`:1328`、`:1346`，豁免路徑 `:1989-2003`。E4 的 `openai_compat_model_ids` 為空陣列（`attempt-E4-qwen27b-p4-final/model_snapshot.json:20`）也不影響 gate（gate 讀 native shape）。
- `[VERIFIED]` 唯一 FAIL 情境＝**兩顆 LLM 並載**：`loaded LLM model 數量=2` → gate FAIL；backend 端亦會回 `LMSTUDIO_MULTIPLE_LOADED_LLMS` 並要求只保留一個（`backend/services/summarization.py:2823-2826`、`:2894-2899` 的 `請設定 LMSTUDIO_MODEL 或只保留一個`）。
- `[VERIFIED]` `LMSTUDIO_MODEL` override 目前未設定（`backend/core/config.py:69-71` default `None`；E5 執行中 `GET :58881/api/config` 顯示 `lmstudio_model: null`、`local_llm_model: "qwen3.8-27b-splash"`）。若日後要設 override，**值必須用 `gemma-4-31b-it-mlx`**；輸入含 `-4bit` 的字串不會匹配（override 以 `model_key`／`instance_id` 精確集合比對：`backend/services/summarization.py:2818-2821`；錯誤 `LMSTUDIO_MODEL_NOT_LOADED`：`:2898-2899`）。

## 設定與記憶體

### context length（`num_ctx=8192` 的出處）

- `[VERIFIED]` log 值來源：`backend/main.py:110`（`num_ctx={settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS}`）；欄位定義 `backend/core/config.py:198-201`（default `8192`，描述「本地 LLM 實際可穩定使用的上下文 token 預算」）。
- `[VERIFIED]` 覆蓋方式＝環境變數／`.env`（`LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`，範例 `.env.example:102`）。**`config.yaml:32` 的 `num_ctx: 8192` 對後端無效**：`backend/core/config.py:4-5` 明言「後端僅讀取環境變數／.env；config.yaml 只供舊版 CLI 使用」。
- `[VERIFIED]` 降級桿另有一顆：`LOCAL_LLM_DEGRADED_CONTEXT_TOKENS`（default 8192，`backend/core/config.py:355-358`；`.env.example:118`）——只在 warmup 偵測 offload 且自我修復失敗時，把「本任務」降級（Ollama 路徑語意）。
- `[VERIFIED]` **LM Studio 路徑不使用 settings `num_ctx` 做規劃**：權威視窗＝本次選定 loaded instance 的 `context_length`（`backend/services/summarization.py:3016-3026`，註解 `T20260922-1349-01 RC-3`；來源登錄 `:3027`；log 於 `:3031-3033`）。`_effective_context_tokens`（`settings` 那條）只走 Ollama 請求（`:3483-3489`、options `num_ctx` 於 `:4851-4860`）。
- `[VERIFIED]` 實證對照：gemma E1 log `context_window=71936(lmstudio_instance), estimated_tokens=11712, chunk_budget=65999, needs_chunking=False`（`data/cache/e2e/p4-gemma31b-e1/backend_data/logs/app_2026-09-23.log:94`）；qwen E4 log `context_window=128000(lmstudio_instance)`（`data/cache/e2e/p4-qwen27b-e4/backend_data/logs/app_2026-09-23.log:94`）。
- `[VERIFIED]` 結論：**gemma 31B 跑同一套時，不會因「config 顯示 8192」而品質掉**——只要 LM Studio 載入 gemma 時 context ≥ 逐字稿需求（歷史 71936 即可；建議 ≥65536）。`[INFERRED]` 若載入時 context 設得極小（< ~15k），規劃會切塊（chunking）→ 對「完整會議紀錄」品質不利，應避免。
- `[VERIFIED]` gemma 載入上限：模型支援 `max_context_length=262144`（`attempt-E4-.../model_snapshot.json:36`），但歷史成功場都用 `71936`（同檔 `:11`），本機 48 GiB 不宜開滿。

### 檔案與量化（磁碟實況）

- `[VERIFIED]` 路徑與檔案（`ls -la` live 觀測）：`config.json`(6,046 B)、`chat_template.jinja`(18,683 B)、`generation_config.json`(208 B)、`model.safetensors.index.json`(205,370 B)、`processor_config.json`(1,339 B)、`tokenizer.json`(32,169,626 B)、`tokenizer_config.json`(22,863 B)；4 個 shard：`model-00001..00004-of-00004.safetensors` = 5,366,617,542＋5,361,642,569＋5,367,276,098＋2,316,480,623 = **18,412,016,832 B**（≈17.15 GiB；`du -sh` 顯示 17G）。
- `[VERIFIED]` 量化：`config.json` → `"quantization": {"group_size": 64, "bits": 4, "mode": "affine"}`（＋同值 `quantization_config`）、`"dtype": "bfloat16"`、`"architectures": ["Gemma4ForConditionalGeneration"]`、`"model_type": "gemma4"`；LM Studio metadata 另一把尺：`quantization.name="4bit"`、`size_bytes=18444440967`（18.44 GB，含 non-weight 檔）（`attempt-E4-.../model_snapshot.json:29-33`）。
- `[VERIFIED]` **無 mmproj／vision projector 檔**：目錄清單與 `find` 均無 `mmproj*`／`*vision*` safetensors；vision 由統一權重（`Gemma4ForConditionalGeneration`）＋`processor_config.json` 承載，LM Studio 亦標 `capabilities.vision=true`（`attempt-E4-.../model_snapshot.json:38-41`）。文字任務不受影響。

### 記憶體可行性

- `[VERIFIED]` 機器：Apple M4 Pro；總 RAM `sysctl -n hw.memsize` = **51,539,607,552 B ≈ 48 GiB**。
- `[VERIFIED]` 現況（live）：`lms ps` → `qwen3.8-27b-splash … GENERATING 17.38 GB CONTEXT 128000`（唯一 loaded）；`vm_stat` → free pages 4,661×16 KiB ≈ **73 MiB**、compressor ≈ 715,944×16 KiB ≈ **10.9 GiB**、wired ≈ 1,445,547×16 KiB ≈ **22.1 GiB**；`sysctl vm.swapusage` → used 204.88 MB／total 1024 MB。
- `[INFERRED]` gemma 4bit 權重 18.44 GB；@65536 context（f16 KV）粗估 KV ≈3–5 GB＋runtime ≈2–4 GB → 單獨載入 ≈24–28 GB，48 GiB 可承載（歷史同機已 5 次以 71936 成功跑完，見下節）。
- `[VERIFIED]` **同時駐留風險高**：17.38＋18.44 = 35.8 GB 權重＋兩份 KV（qwen @128000 很大）＋macOS/App → 在 48 GiB 上會出現壓縮、swap、甚至 CPU offload（offload 會使生成速度崩落並觸發降級桿）。→ **建議先卸載 qwen，再載 gemma**；這也同時滿足 runner gate（恰好 1 LLM）與 backend 自動選模。

## 建議指令（未執行）

> 以下僅供你（或主執行 agent）在 **E5 qwen 場收工後** 執行；本次預檢**未執行任何** `lms load/unload`。`lms` 不在本 shell PATH，請用絕對路徑（`~/.lmstudio/bin/lms`，已驗證存在且可執行）。參數名皆已用 `lms load --help`／`lms unload --help` 驗證存在（live 觀測）。

```bash
# 1) 先卸載 qwen（釋放 17.38 GB；避免兩顆 LLM 並載 → 兩邊 gate 都 FAIL）
~/.lmstudio/bin/lms unload qwen3.8-27b-splash

# 2)（可選）先估資源、不載入
~/.lmstudio/bin/lms load gemma-4-31b-it-mlx --estimate-only -c 65536

# 3) 載入 gemma（--gpu max＝全 GPU；-c 65536 與歷史 71936 同級，避免開滿 262144）
~/.lmstudio/bin/lms load gemma-4-31b-it-mlx --gpu max -c 65536 --identifier gemma-4-31b-it-mlx

# 4) 驗證恰好 1 個 LLM loaded（runner 與 backend 的共同前提）
~/.lmstudio/bin/lms ps
```

- `[VERIFIED]` 不要加 `--ttl`（或設遠大於 E2E 時長）：生成途中自動卸載會使 `model_snapshot_consistent`（`scripts/e2e/run_owned_e2e.py:509-524`）FAIL。
- `[VERIFIED]` 不要同時保留任何其他 LLM（含 `qwen3.6-35b-a3b-*`）；embedding 模型不算 LLM（`backend/services/summarization.py` 讀 `/api/v1/models` 的 `type=="llm"`），可保留。
- `[UNVERIFIED]` `-c 65536` 在本機的實際速度與品質未測（歷史為 71936）；若你要完全對齊歷史條件，可改用 `-c 71936`。`--auto` 僅 Bionic 可用（help 明載），本機請明示 `-c`。

## 歷史 gemma 結果

`[VERIFIED]` 全部 5 場（同一音檔 `0903-科務會議.m4a`、同一模板 `section_meeting`、`local` 模式、LM Studio provider）**runner verdict=PASS**，且 `model_inventory_unique=true`、`model_snapshot_consistent=true`（例：`attempt-E2-gemma31b-p4a-fix/run_summary.json:21`、`:31`、`:35`；其餘各場 `run_summary.json:35` 同）。

| 場次（attempt） | runtime 目錄 | model_key／instance context | verdict | 會議紀錄字數 | quality 重點 | 耗時 |
|---|---|---|---|---|---|---|
| **C1** `attempt-C1-gemma31b-fix` | `data/cache/e2e/p2-gemma31b-fix-01` | `gemma-4-31b-it-mlx`（`model_snapshot.json:7`）／71936（`:11`） | PASS（`run_summary.json:35`） | 1,927 | 標註起點比 1.0；未留 coverage.json | 1,669.8 s（`run_summary.json:5/:6`） |
| **D1** `attempt-D1-gemma31b-p3` | `data/cache/e2e/p3-gemma31b-d1` | `gemma-4-31b-it-mlx`／71936 | PASS（`:35`） | 1,955 | 標註起點比 0.9583；**無 coverage.json**（數字見下註） | 1,227.2 s |
| **D2** `attempt-D2-gemma31b-head` | `data/cache/e2e/p3-gemma31b-d2` | `gemma-4-31b-it-mlx`／71936 | PASS（`:35`） | 1,951 | coverage all **0.5075**／core **0.6786**，miss 9 條（`coverage.json:18/:19/:21`） | 1,251.1 s |
| **E1** `attempt-E1-gemma31b-p4` | `data/cache/e2e/p4-gemma31b-e1` | `gemma-4-31b-it-mlx`／71936 | PASS（`:35`） | 2,552（`record_quality.json:15`） | coverage all **0.6119**／core **0.8214**，miss `[F019,F044,F054,F056,F066]`；unsupported 4（`:62`）；observe 模式下 `quality_on_start_tag_ratio_ok=false`（0.931＜0.95，`record_quality.json:69,:72-73`，不入 verdict） | 2,278.8 s |
| **E2** `attempt-E2-gemma31b-p4a-fix` | `data/cache/e2e/p4-gemma31b-e2` | `gemma-4-31b-it-mlx`／71936 | PASS（`:35`） | 2,318（`coverage.json:6`） | coverage all **0.6119**／core **0.8214**，miss `[F044,F048,F060,F065,F066]`（`coverage.json:18/:19/:21`）；unsupported 2（`record_quality.json:62`）；**quality 檢查全數 True、無失敗**（`:69,:72`） | 2,107.9 s |

- `[VERIFIED]` 每場 backend 啟動行格式一致：`LLM: provider=lmstudio, model=LM Studio（依已載入模型）, num_ctx=8192, keep_alive=30m`（例：`data/cache/e2e/p2-gemma31b-fix-01/backend_data/logs/app_2026-09-22.log:22`；D1/D2/E1/E2 同型見各 `backend_data/logs/app_2026-09-23.log:22`）。
- `[VERIFIED]` 量尺同版同清單：E2 `attempt-E2-gemma31b-p4a-fix/coverage.json:2` 記錄 `metric_version=coverage-1.0.0`、`:9` 記錄 `checklist_sha256=cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001` → **E5 可直接沿用同一 gate／同一量尺**。
- `[UNVERIFIED]`（我未重跑此量尺）D1 的 coverage 值（all 0.5075／core 0.6786）出自 `e2e/quality-parity-01/report.md:204`（離線補測；D1 attempt 目錄本身無 `coverage.json`）→ 引用時標明來源，**不與 D2 自身的 `coverage.json` 混淆**。

## 未驗證

- `[UNVERIFIED]` gemma 在 E5 target build `818b71e` 與 P4 後三項修補下的實際表現（尚未跑；本報告只做預檢）。
- `[UNVERIFIED]` gemma 以 `-c 65536` 載入後的實際速度／品質（歷史條件為 `71936`）；以及 `lms load` 在本機版本的預設 context 行為（建議永遠明示 `-c`）。
- `[UNVERIFIED]` E5 期間的可用記憶體是否足夠「不卸載 qwen 就載 gemma」——本報告以記憶體數據判定**不建議**並載；未實測（受唯讀／勿動模型約束）。
- `[UNVERIFIED]` 其他模型（`qwen3.6-35b-a3b-*`）是否在本機被其他流程佔用；本次只確認 `lms ps` 只有 qwen 一顆。
- `[UNVERIFIED]` Windows／Ollama 路徑（RTX 4090 主機）不在本次 Mac LM Studio 預檢範圍。
