# P4 波跨 OS 稽核：macOS（LM Studio）vs Windows 11（Ollama）

- 稽核日期：2026-09-23（Asia/Taipei）
- 稽核對象：commit `da37407`（P4 波：逐條對帳／忠實度絆索／標註去重複化／引擎取樣同源）
- 分支：`fix/qwen-local-quality-parity`
- 方式：唯讀（`git show`／`rg`／`sed -n`）；未修改產品或測試檔；未跑任何測試套件；本報告為本次唯一新增檔案。
- 讀者提醒：severity 只描述「對 Windows/Ollama 這條路徑」的影響；`[VERIFIED]`＝本次唯讀可證、`[UNVERIFIED]`＝無實機證據。

## 1. Findings 總表

| 檔案:行 | 類別 | 問題 | 對 Windows 或 macOS 的影響 | 嚴重度 | 最小修法建議 |
|---|---|---|---|---|---|
| `scripts/e2e/run_owned_e2e.py:74,79,184` | 時區／tzdata | 模組 import 即執行 `TAIPEI = ZoneInfo("Asia/Taipei")`；`pyproject.toml`／`uv.lock`／`requirements.txt`／`requirements.windows-cuda.txt` 皆無 `tzdata` 依賴（`rg` 無命中）。`[VERIFIED]` | Windows 無系統 tz database → import 即 `ZoneInfoNotFoundError`，runner 完全無法啟動；以 importlib 載入 runner 的 `tests/test_t20260923_p4d_runner_quality_gate.py:36,99-100` 與 `tests/test_owned_e2e_acceptance.py:33,82-85` 在 Windows 執行時同樣直接失敗。macOS 不受影響。註：此三行非 P4 新增（`da37407^` 同檔 `:73` 已存在），但 P4 的 `--quality-mode` 驗證工具就建在此檔案上 | **BLOCKER**（限 Windows 上 runner／測試執行） | pyproject 加 `tzdata` 依賴，或 `try: ZoneInfo(...) except ZoneInfoNotFoundError: timezone(timedelta(hours=8))` 優雅降級 |
| `backend/services/summarization.py:3285-3305,3386,199`＋`backend/core/config.py:251-258,314-318` | 模型／provider（取樣參數） | P4-C 讓 Ollama 取樣改讀 config（top_p 0.8／top_k 20／repeat_penalty 1.08），取代 P4 前寫死 0.95／64／1.08（`:199` 為 rollback 常數）。0.8／20 的調校脈絡在 `config.py:247-256` 明載是「LM Studio Splash 引擎」用值。`[VERIFIED]` | Windows 預設解碼行為自 P4 起靜默改變，且無任何 Windows/Ollama 實機 A/B 證據（commit 自述「Windows／Ollama 實機仍 `[UNVERIFIED]`」）；0.8/20 vs 0.95/64 可能改變輸出品質與重複性。`.env.example`／compose 皆未列這三鍵（`rg` 無命中），管理員不會看到新預設 | **MAJOR** | 先在 Windows/Ollama 實機做同音檔舊/新參數 A/B（可用 `LOCAL_LLM_SAMPLING_TOP_P=0.95`、`LOCAL_LLM_SAMPLING_TOP_K=64` 回舊值），達標前或於 Windows compose 明示三鍵值 |
| `backend/core/config.py:287-292,304-308,309-313,280-283`＋`backend/services/summarization.py:1602,2929,2986` | 語意預設（品質開關 default-on） | P4-A 覆蓋率對帳預設 `enforce`（問題進補強清單）＋P4-B 忠實度絆索預設 True＋P4-D 標註去重複化預設 True；`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 預設 2。plan §9.3/§4.2 凍結 `enforce` 為預設（`.agent/tasks/.../plan.md:89`），並自載「每輪補強 +350–400 s」成本。`[VERIFIED]` | Windows 首次部署即改變生成迴圈語意（問題清單變長 → 觸發補強輪）與輸出內容；P4-A 的數字／日期抽取依賴逐字稿段落列格式（`summarization.py:1453-1461`、`backend/core/text_postprocess.py:752-753` `[start-end] 發言者：`），Windows ASR 逐字稿是否符合此格式未經實測；若不符，期望集合為空 → 只留 WARNING＋`cov_expected_*=0`（fail-soft，不炸但 P4-A 零效益且多燒算力） | **MAJOR**（未驗證的預設行為變更；非規格違反） | Windows 首跑以 `LOCAL_LLM_RECORD_COVERAGE_MODE=observe`＋`LOCAL_FIDELITY_TRIPWIRES=false` 取得基線，確認 `cov_expected_*`＞0 再逐項開 `enforce` |
| `backend/services/summarization.py:2823,3353`＋`docker/docker-compose-windows-gpu.yml:118` | 模型／provider（context 來源） | context 預算來源不對稱：LM Studio 用本次 loaded instance 的 `context_length`（可 32K/128K），Ollama 永遠用 settings（Windows compose 16384）；runner 只 log `context_window_source` 對帳（`:3353`）。`[VERIFIED]` | 兩引擎不是同一把尺（上限不同）；Ollama 無法受益於 4090 可承載的更大視窗（16384 為 4090 VRAM 實測值，屬刻意設定）。`summarization.py:3106-3121` 的 correction 路徑直接呼叫引擎、未設 `_context_window_source`，log 會回 "settings"（僅觀測） | MINOR（設計明載 W-2） | 文件化不對稱；未來若要同源，需讀 Ollama `/api/show` 的模型 context 上限（超出本波） |
| `backend/services/summarization.py:2760,3369,3383,3619,3229,3865` | 重試／復原不對稱 | 瞬時重試共用 `LOCAL_LLM_TRANSIENT_RETRIES`（`:3229` Ollama／`:3865` LM Studio，同源）；但空回應復原有別：Ollama 只有 `for attempt in range(2)` 升溫重試（`:3369`）與升溫規則（`:3383`），LM Studio 另有 `_recover_lmstudio_empty_response`（`:3619`）growth/replay 系列；`allow_reasoning_retry` 僅作用 LM Studio（`:2760` docstring）。`[VERIFIED]` | Windows/Ollama 遇到「思考吃預算／空輸出」情境時韌性低於 macOS/LM Studio；既有行為，非 P4 引入 | MINOR | 登錄差異即可；後續波再評估對 Ollama 對齊 stop-replay 類復原 |
| `scripts/e2e/run_owned_e2e.py:252-285,1926` | subprocess／程序終止 | `terminate_owned_process` 僅在 `os.name == "posix"` 用 killpg（SIGTERM→SIGKILL）；Windows 分支只有 `proc.terminate()/kill()`（只殺 uvicorn 本體）；`start_new_session=(os.name == "posix")` 亦然。`[VERIFIED]` | Windows runner 收尾可能殘留 ASR/ffmpeg 等子孫程序與暫存檔佔用（runner 自身 child，非產品）；不影響生成結果 | MINOR | Windows 以 `taskkill /T /F /PID` 或 Job Object 殺整棵樹 |
| `scripts/e2e/measure_coverage.py:869-872,893,906` | 編碼（BOM） | `_read_text` 嚴格 `data.decode("utf-8")`，BOM 一律 `UnicodeDecodeError`→exit 2；全 repo 無 `utf-8-sig`（`rg` 無命中）。P4 runner `--coverage-checklist` 會把 checklist 交給此工具。`[VERIFIED]` | Windows 記事本／部分工具另存的 JSON 清單常帶 BOM → 覆蓋率觀測直接失敗（observe 為 fail-soft，但 required／人工解讀會誤判「工具壞了」） | MINOR（暴露面限工具鏈） | `data.decode("utf-8-sig")` 或先剝 `\ufeff` |
| `backend/core/platform_config.py:88-92` | 硬編 URL／平台分支 | 非 darwin-arm64 的 native 預設回 `http://host.docker.internal:1234`。`[VERIFIED]` | 裸機 Windows（未裝 Docker Desktop 或 hosts 未加項目）在「Ollama 不可用 → fallback LM Studio」時 URL 不可解析；Ollama 為主路徑不受影響 | MINOR `[UNVERIFIED]`（實際 hosts 行為視機器） | native Windows 改 `127.0.0.1:1234`（用 `sys.platform`／container 偵測細分） |
| `scripts/e2e/rerun_local_summarize.py:45,68` | 硬編路徑（macOS） | 預設逐字稿 `Path("/Users/hsiaojohnny/Downloads/20260922134904_逐字稿.txt")`。`[VERIFIED]` | Windows 手動重播須顯式帶 `--transcript`；非 P4 檔案、非產品路徑 | MINOR | 預設改 `None`＋缺省時提示；或允許 env 覆寫 |
| `backend/services/summarization.py:4396-4400,4470-4475`＋`backend/core/config.py:53-55`＋`docker/docker-compose-windows-gpu.yml:87` | 模型 hardcode | `LOCAL_LLM_MODEL` 預設 `gemma4:31b`；gemma4 專屬別名解析（`:4396-4400`）；`_build_ollama_pull_command` 對 gemma4 前綴固定回 `ollama pull gemma4:31b`（`:4470-4475`）。`[VERIFIED]` | 以 qwen 等非 gemma4 模型出錯時，建議指令可能誤導（功能不受影響，模型可一行設定覆蓋）；非 P4 引入。另 4090 使用者若沿用預設會拉 31B（VRAM 壓力），屬既有預設 | MINOR | pull 建議依 configured_model 生成；compose 說明 4090 可改用較小標籤 |
| `docker/docker-compose-windows-gpu.yml:49,86-87` | 部署設定（compose 覆寫） | `environment:` 區塊寫死 `OLLAMA_BASE_URL=http://host.docker.internal:11434`、`LOCAL_LLM_MODEL=gemma4:31b`；`env_file`（`:49`）同鍵會被覆蓋；P4 新鍵（coverage/sampling/diversify）在此檔與 `.env.example` 皆未列。`[VERIFIED]` | Windows 管理員改 `.env` 對這兩鍵無效；P4 全部走程式預設（enforce/tripwires/diversify 全開），站點無顯式可見度 | MINOR | 改為 `${OLLAMA_BASE_URL:-http://host.docker.internal:11434}` 形式；P4 鍵至少註解列出 |
| `config.yaml:18`＋`backend/core/platform_config.py:167-181,308` | 硬編 URL（legacy） | `config.yaml` 的 `llm.ollama.base_url: http://localhost:11434` 由 legacy `get_llm_provider()`／CLI 讀取；產品 `Settings`（pydantic env）不讀此檔。`[VERIFIED]` | 對後端執行路徑無影響；僅 legacy 工具在 Windows 上仍寫死 localhost | MINOR（建議標註 legacy 即可） | 保持原狀；文件加註或日後移除 |
| `backend/core/fidelity_checks.py:300`＋`scripts/e2e/measure_record_quality.py:421,428,435`＋`scripts/e2e/run_owned_e2e.py:854,244,844` | 編碼（顯式 UTF-8） | P4 新增／改動的檔案讀寫全部顯式 `encoding="utf-8"`；子程序 `encoding="utf-8", errors="replace"`＋`PYTHONIOENCODING=utf-8`；binary 讀取（`:387,1461,1918`）不需編碼。`[VERIFIED]` | Windows cp950 風險在此範圍已排除；僅 BOM 情境見上一列 | OK | 維持 |
| `backend/core/fidelity_checks.py:277-285,313`＋`data/entities/entity_registry.json:1` | 路徑／正規化 | registry 路徑用 `os.path.dirname/os.path.join/os.path.abspath` 組合；JSON 檔首字元為 `{`（無 BOM）。`[VERIFIED]` | 分隔符與絕對路徑在 Windows 正常；內容比對用 Unicode 折疊（裏/裡/里…）與 OS 無關 | OK | 維持 |
| `scripts/e2e/run_owned_e2e.py:809,1815`＋`backend/api/routes.py:322,384`＋`backend/services/task_processor.py:421` | glob／locale／strftime | `glob(f"*_{task_id}.md")` 的樣式為 ASCII task_id；`strftime` 僅用 `%Y%m%d%H%M%S`／`%Y-%m-%d` 類，無 `%-d`（Windows 會炸的格式）。`[VERIFIED]` | Windows glob 大小寫不敏感也不影響（樣式 ASCII）；locale 不影響數值 | OK | 維持 |
| `scripts/e2e/run_owned_e2e.py:198,395,848,1920` | subprocess／shell | 全部 list argv＋`sys.executable`；無 `shell=True`／`.sh`／`bash`／`which`／`chmod`／`fcntl`／`pty`／`fork`／`signal`（P4 檔案 `rg` 無命中；`os.killpg` 僅 posix 分支）。`[VERIFIED]` | Windows 可直接執行；引號／空白檔名安全 | OK | 維持 |
| `backend/core/platform_config.py:46-55`＋`backend/services/summarization.py:2708-2741,4298-4307`＋`scripts/e2e/run_owned_e2e.py:1974-1982,2065-2067`＋`backend/api/routes.py:556-557` | provider 判斷 | Windows：`LOCAL_LLM_PROVIDER=auto` → `resolve_local_llm_provider` 回 "auto" → `_select_local_engine` Ollama 優先；`check_ollama_health` 對 lmstudio provider 短路（`:4303-4306`）；runner 由 `/api/config` 讀 `effective_local_llm_provider`，Ollama 時 `lmstudio_inventory_gate=False` → 豁免 `model_inventory_unique`／`model_snapshot_consistent`（`:2067`）。`[VERIFIED]` | Windows+Ollama 下 runner 共通 gate 的 provider 條件成立、不誤殺；macOS auto 固定 LM Studio，兩者分流條件互相獨立 | OK | 維持 |
| `backend/core/text_postprocess.py:752-753,864-883,908,1213-1215,1278`＋`scripts/e2e/run_owned_e2e.py:156` | 正規化／版本釘死 | 規則 6 為純字串操作（`splitlines` 處理 CRLF；無檔案 I/O、無平台分支）；開關 `_source_tag_diversify_enabled` 以 getattr 容錯預設 True；量尺 `metric_version="tag_traceability-1.1.0"`（`:1278`）與 runner 釘死值（`:156`）一致。`[VERIFIED]` | 兩平台行為一致；runner 版本不符會 FAIL（釘版設計） | OK | 維持 |
| `tests/test_t20260922_record_quality.py:327-328,385-386` | 測試（隔離） | `git show da37407` 顯示兩條既有契約測試新增 `_validate_record_source_coverage`／`_validate_record_fidelity` 的 monkeypatch 隔離（非 skip/xfail），理由為「否則多一輪補強使呼叫次數≠2」；新驗證器契約由新測試檔把關。`[VERIFIED]` | 非放寬；但該兩測試不再覆蓋「新驗證器開啟時」的呼叫次數，屬覆蓋轉移 | OK（附註） | 維持；如要更嚴，可在新測試檔補「開啟時輪數上限」契約 |

## 2. 兩 provider 對稱性盤點（P4 抽象層）

共用同一套（`[VERIFIED]`）：
- 引擎分派：`summarization.py:2745` `_generate_with_local_engine` → `_summarize_with_ollama`（`:3307`）／`_summarize_with_lmstudio`（`:3506`）。
- 管線與驗證：`_summarize_with_local_pipeline`（`:2790`）同一份覆蓋率（`:1602`）／忠實度（`:1765`）／逐字稿在最終生成的決策；P4 所有開關皆在此層，與 provider 無關。
- 瞬時重試：`LOCAL_LLM_TRANSIENT_RETRIES`（Ollama `:3229`、LM Studio `:3865`）；逾時同源（`LOCAL_LLM_REQUEST_TIMEOUT`／`LOCAL_LLM_STREAM_IDLE_TIMEOUT`，Ollama `:3148,3155`；LM Studio 同一組 settings）。
- 溫度：generation 用 `LOCAL_LLM_GENERATION_TEMPERATURE`，重試升溫規則兩引擎一致（Ollama `:3383`）。

不對稱（本次確認）：
1. 取樣鍵覆蓋面：Ollama 有 top_p／top_k／repeat_penalty；LM Studio 只送 top_p／top_k（Splash 對 penalty 回 400，`:3292`）→ `LOCAL_LLM_SAMPLING_REPEAT_PENALTY` 對 macOS 無效。
2. context 授權來源：LM Studio instance `context_length` vs Ollama settings（`:2823`／`:3353`）。
3. 空回應復原：LM Studio 有專屬 recovery 系列（`:3619`），Ollama 只有 2 次空重試（`:3369`）。
4. `allow_reasoning_retry` 僅 LM Studio（`:2760`）。
5. runner 生命週期：posix killpg vs Windows 單一 terminate（`:252-285`）。

## 3. 測試覆蓋缺口（只描述，未修改）

1. P4 管線級測試僅 mock `lmstudio`：`tests/test_t20260923_p4a_record_coverage.py:629,663`、`tests/test_t20260923_p4b_fidelity_wiring.py:281,314`。沒有任何以 `ollama` 引擎走完整 `_summarize_with_local_pipeline` 的 golden／整合測試。
2. Ollama 僅 payload 級覆蓋：`tests/test_t20260923_p4a_record_coverage.py:516`（`test_P01` 斷言 options 讀 config），未覆蓋 Ollama 在覆蓋率／忠實度／補強迴圈下的行為。
3. 跨平台執行無自動化：repo 無 `.github/workflows`（`ls` 不存在）；runner 的 provider 拆分測試（`tests/test_t20260923_p4d_runner_quality_gate.py:36,99`）只在「執行機器」上跑 → Windows 才會現形的問題（如 §1 第一列 tzdata）無 CI 攔截。
4. 無真實 Ollama E2E 證據：commit 自述下一步才是「真實音檔 E2E（Gemma 4 31B 與 Qwen3.8-27B 各一次）＋獨立驗收」，且「Windows／Ollama 實機仍 `[UNVERIFIED]`」。
5. Windows provider 路由邏輯有純函式測試（`tests/test_platform_provider_routing.py`），但無 Windows OS 依賴面（tzdata、檔案鎖、程序終止）測試。

## 4. 結論：Windows + Ollama 不修任何東西能不能跑？

- 產品執行路徑（後端＋Ollama 生成／P4 品質管線本體）：**預期可運作，信心＝中（MEDIUM）**。理由：P4 涉及的程式碼無 Windows 硬阻斷（無 shell 依賴、無 `/tmp`／`Users` 寫死於產品路徑、檔案 I/O 顯式 UTF-8、路徑以 `os.path` 組合、`strftime` 無 `%-` 格式、provider 判斷在 Windows 成立）；但全 repo 無 Windows 實機證據，且 P4-C 取樣變更＋預設全開的品質開關屬未驗證行為。`[UNVERIFIED]`（「能跑」與「品質不退步」是兩件事；後者未證）。
- P4 品質驗證工具（`scripts/e2e/run_owned_e2e.py` 的 `--quality-mode`／`--coverage-checklist`）：**不修則不可運作，信心＝高（HIGH）**。理由：Windows 上 import 即 `ZoneInfoNotFoundError`（tzdata 未宣告），其兩個測試模組同因 importlib 載入而失敗（§1 第一列）。
- 品質對等（macOS LM Studio vs Windows Ollama）：**目前不成立為已證事實，信心＝低（LOW）**。理由：取樣參數在 Windows 的預設值已改變且未 A/B；context 授權來源不對稱；覆蓋率抽取器對逐字稿格式的假設未在 Windows 驗證；P4-A 自載每輪補強 +350–400 s 的成本／輪數治理亦僅在 macOS 27B/Gemma 場域量測。

## 5. 不確定項清單 `[UNVERIFIED]`

1. `[UNVERIFIED]` 目標 Windows Python 環境是否已有 tzdata（被其他套件帶入／環境差異）→ 若有，§1 第一列降為非阻斷；本次僅證「本 repo 依賴清單未宣告」。
2. `[UNVERIFIED]` Windows/Ollama 以新取樣值（0.8／20／1.08）之輸出品質；無實機 A/B 數據。
3. `[UNVERIFIED]` Windows ASR 逐字稿是否同為 `[start-end] 發言者：` 格式（plan §9.3 自列唯一待驗；不符時 P4-A 期望集合為空、零效益）。
4. `[UNVERIFIED]` 裸機 Windows 對 `host.docker.internal` 的可解析性（決定 LM Studio fallback 是否可達；Ollama 主路徑不受影響）。
5. `[UNVERIFIED]` Windows 實務上 `--coverage-checklist` 是否會帶 BOM（影響 §1 第七列暴露機率）。
6. `[UNVERIFIED]` Windows 產出 md/docx 之換行（CRLF）與 macOS（LF）造成 `sha256` 證據跨平台不可比對的影響範圍（產品自身以 universal newlines 讀回，行為應一致）。
7. `[UNVERIFIED]` Windows 使用者實際部署形態（Docker compose vs 裸機 uv）→ 決定 §1 第九、十一列的暴露面。
