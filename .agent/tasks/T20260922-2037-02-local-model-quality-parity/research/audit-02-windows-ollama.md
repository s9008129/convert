# 跨平台稽核報告 02 — Windows 11 + RTX 4090 + Ollama（地端品質修復 P2 可查核性波）

- **稽核角色**：跨平台（macOS/Windows）與 Ollama 相容性稽核員（唯讀）
- **日期**：2026-09-23　**工作目錄**：`/Users/hsiaojohnny/dev/convert`
- **受查快照**：分支 `fix/qwen-local-quality-parity`，commit `b3db34a`（P2 波：`f1e6bfe` / `3fec08f` / `e90040b` / `b3db34a`）
- **受查問題**：這波模型無關的確定性後處理（出處標註吸附等）在 Windows + Ollama 上是否會壞或行為不一致？

## 0. 方法與限制宣告

- 全程**唯讀**：只使用 `git show`／`sed`／`grep` 讀取；**未啟動後端、未執行任何測試或 E2E、未呼叫 LM Studio 或 Ollama、未跑 >60 秒指令**。
- 本報告所有「檔案:行號」除非另有標註，一律**以 commit `b3db34a` 的內容為準**（逐條用 `git show b3db34a:<path>` 核對過）。
- ⚠️ 稽核期間工作樹**有其他流程正在寫入**：進場時 dirty 為 `plan.md`、`backend/core/text_postprocess.py`，稽核中途 `backend/services/summarization.py` 也被寫入（mtime 00:27）。因此**工作樹行號會漂移，本報告不引用工作樹行號**；工作樹的未提交 P3 修復只用 `git diff` 內容描述。
- 受查檔案內容指紋（sha256 前 16 碼，皆為 `b3db34a` 版本）：

| 檔案 | sha256(16) |
|---|---|
| `backend/core/text_postprocess.py` | `2ce4d90eae2a0ee9` |
| `backend/services/summarization.py` | `76d2fc7d4fb5966f` |
| `backend/core/platform_config.py` | `145ef922afccf266` |
| `backend/core/config.py` | `829951362eda588c` |
| `docker/docker-compose-windows-gpu.yml` | `67a9fe4e50704b3d` |
| `doc/操作手冊/部署更新手冊_v4.1.md` | `ad7b46d436cd76c7` |
| `doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md` | `86627473b454bd90` |
| `scripts/e2e/run_owned_e2e.py` | `c79da56a469abcd0` |
| `tests/test_platform_provider_routing.py` | `058f9d247bf0434f` |

## 1. 結論（TL;DR）

**可以用。** 這波修復在 Windows 11 + Ollama 上**不會被平台分支或引擎分支繞過**：後處理模組 `text_postprocess.py` 內完全沒有平台／引擎判斷；LM Studio 與 Ollama 都經由同一條 `_summarize_with_local_pipeline` → `_finalize_record_text(mode="local")`，呼叫同一組確定性後處理步驟（程式碼與 docstring 皆有明示，見 §2）。

**但「能跑到」不等於「已在 Windows 驗過」**：目前所有 E2E 證據（含 Gemma 4 31B 真實音檔、獨立驗收）都是 **macOS + LM Studio**；Windows + Ollama 全屬「程式碼與設定層可推得、尚未實機驗證」。

**已知會壞／會不一致的地方（依嚴重度）**：

1. **committed `b3db34a` 的吸附有邊界缺陷**（時間戳恰為段落界線時「倒退一格」、函式非冪等）——C1 獨立驗收已抓到，但**修復尚未提交**（僅存在於工作樹 P3 diff）。直接部署 `b3db34a` 會繼承此缺陷（與平台無關）。
2. **修復是 fail-soft 靜默 no-op**：diarization 不可用或逐字稿段落格式不是 `[HH:MM:SS - HH:MM:SS] 發言者：` 時，吸附不作用、不報錯，紀錄照常產出但可查核性悄悄變差。
3. **Windows 不能直接跑 full E2E**：`scripts/e2e/run_owned_e2e.py` 的模型快照閘門打的是 **LM Studio** `/api/v1/models`（`:266`）；Ollama-only 機器上 full 模式會 gate 失敗。需改用 `--smoke` 或產物驗收工具（§4.4）。
4. **context 預算不對稱**：Ollama 受 `LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`（程式預設 8192／GPU compose 16384）限制；LM Studio 用「實測載入 instance context」。換引擎後長會議切塊／整併必然不同，Mac 的驗收數字不能直接沿用。
5. **引擎回傳格式差異**：Ollama 路徑只讀 `message.content` 與 final chunk metrics（`load_duration`/`eval_count`/`prompt_eval_count`/`done_reason`），**不解析 reasoning/usage**；LM Studio 有完整 usage/reasoning recovery。對本波修復（吃最終文字）無影響，但診斷與 retry 行為不同。

## 2. 可達性驗證：Windows/Ollama 一定走得到修復

（每條 [VERIFIED]，附 `檔案:行號`，皆為 `b3db34a` 內容）

- **後處理模組無平台分支**：`backend/core/text_postprocess.py:14-19` 只 import `re`、`typing`、`backend.core.logger.log`；模組內無 `platform`／`sys.platform`／`os.name`。
- **自動化護欄防回歸**：`tests/test_platform_provider_routing.py:180-187`（後處理模組禁止出現平台字串）、`:190-195`（引擎分派禁止平台字串）、`:198-210`（同輸入下吸附結果與引擎無關；重複呼叫結果一致）。
- **引擎選擇依設定＋健康狀態，不依 OS**：`backend/services/summarization.py:1937-1972`。Windows 的 `LOCAL_LLM_PROVIDER=auto` 是「Ollama 優先，不可用才試 LM Studio」；若 Ollama 有相符模型但服務異常會**直接 RuntimeError，不靜默 fallback**（`:1961-1965`）。
- **分派點**：`summarization.py:1974-2017`（`_generate_with_local_engine`）依 engine 字串分派到 Ollama／LM Studio；兩條實作最終都進 `_summarize_with_local_pipeline`（`:2019`，內 `:2027` 選引擎）。
- **同一條 pipeline 呼叫同一組收尾**：最終生成後 `summarization.py:2138`、每輪補強後 `:2180`，都呼叫 `_finalize_record_text(..., mode="local", transcript=transcript)`；本體 `:2214`，其 docstring `:2229-2246` 明寫「此步與引擎、模型無關（LM Studio／Ollama 共用同一條 `_summarize_with_local_pipeline`）……`transcript` 缺席時完全不作用」。
- **local-only gate 與步驟序**：`summarization.py:2254-2255`（`finalize_record` → `if mode != "local": return`，雲端路徑 byte 級不變）；地端步驟 `:2266-2272`：術語修正 → **標註吸附（`:2269`）** → 表格標註清除 → 佔位符修復 → 跨節去重。
- **平台預設只決定「選哪個引擎」**：`backend/core/platform_config.py:31-43`（darwin arm64 → lmstudio；其餘 → auto）、`:46-55`（auto 僅在 darwin 改寫為 lmstudio）；Windows 因此走 auto → Ollama 優先。
- **Ollama 呼叫路徑**：`summarization.py:2325-2402`（串流 `/api/chat`、`think=False` 預設＋400 相容降級 `:2415-2432`、`done_reason=length` 接受 `:2377-2383`；metrics `:2390-2402`）。
- **模板契約**：`backend/core/templates.py:386-388`（section_meeting `speaker_traceability=True`）、`:406`（禁止表格內標註）、`:474`（record_term_fixes）；吸附只在「local 模式＋有逐字稿」時作用。

## 3. 風險清單

### R-01 Windows 實機從未驗證 — [VERIFIED]

- 證據：`doc/操作手冊/部署更新手冊_v4.1.md:429` 自述「Windows 實機（RTX 4090 ＋ Ollama）尚未實機驗證」；`.agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/` 下各 attempt（A1/B1/B2/C1/C2）皆為 macOS + LM Studio。
- 影響：所有「會動」的結論都是程式碼層；Ollama 版本差異、模型 tag、GPU offload、host-gateway 連通性需實機確認。
- 對策：§4 實機驗收。

### R-02 吸附是靜默 no-op（fail-soft） — [VERIFIED]

- 證據：`backend/core/text_postprocess.py:843-844`（`iter_transcript_segments` 無段落即原樣回傳）；逐字稿產生端 fail-soft 契約 `backend/services/task_processor.py:165-213`（`:168-169` 明寫「任一前提缺少即維持純文字逐字稿」；`:178-181` 時間軸守門；`:202` diarization 呼叫）。
- 影響：Windows 上若 diarization 模型沒放好或時間戳守門不過，吸附完全不作用、紀錄照常產出、不報錯。
- 對策：上線清單把「diarization 就緒＋產物 traceability 指標」列為必驗。

### R-03 committed 吸附邊界缺陷（倒退一格＋非冪等） — [VERIFIED]

- 證據：`backend/core/text_postprocess.py:868`、`:876` 用**閉區間** `seg[0] <= seconds <= seg[1]` 取第一個命中段落 → 時間戳恰等於前段 `end` 時被拉回前段 `start`；`:883` 位移 >120s 保留原值。C1 獨立驗收：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-C1-gemma31b-fix/verify_independent.md:123-145`（7 個改變值中 6 個是倒退、非冪等）；工作樹 `plan.md` R24（`:273`）。
- 影響：時間精度受損（主指標 `on_start_tag_ratio` 無感＝指標盲區），對已吸附文字再跑一次會再退一格。**與平台／引擎無關**，Windows/Ollama 一樣會中。
- 現況：工作樹有**未提交** P3 修復（`git diff backend/core/text_postprocess.py`）：新增 `_segment_contains`（半開區間 `[start,end)`、零長度段落退化單點；rev 9 定稿改回閉區間 `[start,end]`）、`_pick_containing_segment`（`start == seconds` 優先→冪等）、規則 0 全域段首保護與新觀察值 `kept_on_start`／`backward_moves`／`max_backward_seconds`（舊名 `snapped_across_segment`＝rev 8 工作名，恆 0 無鑑別力，已移除）；docstring 改 v1.1。上線時應確認「修復是否納入部署快照」，並在驗收檢查 `kept_on_start`（已是段首的標註未被搬動）與 `backward_moves`／`max_backward_seconds`（後退僅限段落內吸附、幅度受觀測）。

### R-04 Windows 不能直接跑 full E2E（runner 為 LM Studio 專用） — [VERIFIED]

- 證據：`scripts/e2e/run_owned_e2e.py:266`（模型快照打 `{lmstudio_base_url}/api/v1/models`）、`:1083-1084`（full 需 `--audio`）、`:1243-1247`（`model_inventory_unique` gate）、`:1279`（`model_snapshot_consistent` gate）。`--smoke` 則明確「快照唯讀記錄、不可達/非唯一不 veto」（`:1236-1237`），required 僅 `backend_started/health_ok/build_revision_match/child_terminated`（`:1291-1293`）。
- 影響：在 Ollama-only 機器跑 full E2E 會誤判失敗。
- 對策：Windows 驗收改用 `--smoke`＋產物驗收（§4.4）。

### R-05 context 預算不對稱 — [VERIFIED]

- 證據：`backend/core/config.py:188-192`（`LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`、`LOCAL_LLM_RESERVED_OUTPUT_TOKENS`）；`docker/docker-compose-windows-gpu.yml:118-119`（16384／2048）；LM Studio 走 loaded instance context（研究文件 §10.4 硬前提清單第 5 點 `:819-821` 亦記此不對稱）。
- 影響：換引擎後長會議切塊／整併不同；Mac 量到的品質數字不能當 Ollama 驗收基準。
- 對策：以實機產物指標為準；需要時調 `.env`（改完要 `up -d`）。

### R-06 Ollama 回傳格式差異（reasoning/usage） — [VERIFIED]

- 證據：Ollama 只讀 `message.content`（`summarization.py:2325-2385`）＋ final chunk metrics（`:2387-2402`），**無 usage 解析**；LM Studio 解析 `usage`／`reasoning_content/reasoning`（`:3119-3145`），有 reasoning-only recovery（`:2878-2973`）；think 標籤另有共用清理 regex（`:1153-1154`）。
- 影響：本波修復不受影響（吃最終 Markdown）；但 Ollama 若 `think=False` 不生效、模型仍吐思考內容，只靠清理 regex 兜底（共用路徑，Windows 一樣生效）。
- 對策：驗收時肉眼檢查紀錄不含思考段落；若日誌出現「模型不支援 think 參數，改以相容模式重送」（`:2430-2432`）屬預期降級、不是錯誤。

### R-07 換行符（\r\n） — [INFERRED]（低風險）

- 證據：吸附端用 `splitlines()`（`text_postprocess.py:794`、`:391`），對 CRLF 安全；段落／標註 regex 不受換行影響（`:752-754`、`:479`）。表格清除與去重使用 `split("\n")`（`:522`、`:678`）：若**模型輸出**是 CRLF，行尾會殘留 `\r`，但 `TABLE_ROW_PATTERN` 用 `^\s*\|`、去重 key 先做 `\s+` 正規化，實務上不影響判定。
- 影響：理論風險低；逐字稿由系統自己以 `\n` 產生（`backend/services/speaker_transcript.py` 的 join），真正的風險只在「模型輸出 CRLF」。
- 對策：實機驗收時對產物 grep `\r`，發現再開單。

### R-08 編碼（cp950/utf-8） — [VERIFIED]

- 證據：檔案讀寫明確 utf-8——`backend/services/file_manager.py:198/210/229/249`；logger `backend/core/logger.py:54/67`；ASR 子程序 `backend/services/asr_subprocess.py:65/84/143`（含 `PYTHONIOENCODING=utf-8`）。
- 影響：產品路徑（容器內 Linux＋明確 utf-8）不受 Windows console codepage 影響；風險只在「人在 Windows 上用 PowerShell 5.1 讀寫檔」（`>`／`Out-File` 預設 UTF-16LE）。
- 對策：上線清單要求用 UTF-8 工具檢視產物。

### R-09 `os.startfile`／subprocess／asyncio policy — [VERIFIED]（查無風險點）

- 證據：全 repo grep `os.startfile`、`set_event_loop_policy`、`ProactorEventLoop` → `backend/`、`scripts/` 無命中。Windows 唯一執行路徑是 Docker（容器內 Linux）；`asr_subprocess.py` 以 `sys.executable` 啟動子程序（跨平台）。

### R-10 時間/時區（tzdata） — [UNVERIFIED]（只影響 E2E 工具，不影響產品）

- 證據：`scripts/e2e/run_owned_e2e.py:68`、`:73` 用 `ZoneInfo("Asia/Taipei")`；`docker/Dockerfile.gpu:27` 設 `TZ=Asia/Taipei`；`requirements.txt`／`pyproject.toml` **無 `tzdata` 條目**（grep 無命中）。
- 影響：容器內通常靠系統 tzdata 沒問題；若在 **Windows 主機直接**（非容器）跑 E2E 工具，Python 3.9+ 需要 `tzdata` 套件，缺了會 `ZoneInfoNotFoundError`。**需要實機或乾淨環境確認**。
- 對策：Windows 直跑工具前 `uv pip install tzdata`，或改在容器內跑。

### R-11 compose `environment` 蓋 `.env`（換模型/端點陷阱） — [VERIFIED]

- 證據：`docker/docker-compose-windows-gpu.yml:86-87`（`OLLAMA_BASE_URL=http://host.docker.internal:11434`、`LOCAL_LLM_MODEL=gemma4:31b`）；`environment` 優先於 `env_file`。
- 對策：改那兩行＋`docker compose -f docker-compose-windows-gpu.yml up -d`（手冊 `:420` 已寫）。

### R-12 後處理契約只在「科務會議 + local 模式」生效 — [VERIFIED]

- 證據：`backend/core/templates.py:386-388/406/474`；`summarization.py:2255`（`mode != "local"` 直接 return，雲端 byte 級不變）；`:1289`（`if mode != "local" or not speaker_rule`）。
- 影響：其他模板或雲端模式沒有吸附，這是設計、非缺陷；驗收時要用科務會議＋本地模式。

### R-13 主機端 Ollama 效能前提 — [VERIFIED]（文件已載，易漏）

- 證據：`docker/docker-compose-windows-gpu.yml:233` 註解明列主機【必要】環境變數 `OLLAMA_FLASH_ATTENTION=1`、`OLLAMA_KV_CACHE_TYPE=q8_0`；`:176-177` `extra_hosts: host.docker.internal:host-gateway`。
- 影響：沒設會慢（offload/KV cache 未優化），不至於壞，但會讓長會議 timeout 風險上升。
- 對策：列進主機設定檢查清單。

## 4. Windows 11 + RTX 4090 + Ollama 上線前檢查清單

> 前提：產品跑法＝Docker（`docker/docker-compose-windows-gpu.yml`），Ollama 跑在 Windows 主機（`host.docker.internal:11434`）。

### 4.1 設定（三層，改了都要 `up -d`，不是 `restart`）

1. **compose 內寫死（會蓋 `.env`）**：`docker/docker-compose-windows-gpu.yml:86-87`
   - `OLLAMA_BASE_URL`：預設 `http://host.docker.internal:11434`（Ollama 不在預設埠才改）。
   - `LOCAL_LLM_MODEL`：填**實際安裝的 Ollama tag**（預設 `gemma4:31b`；例：`ollama list` 顯示的 tag）。
2. **`.env` 可調（容器 env_file）**：`LOCAL_LLM_PROVIDER=ollama`（建議**顯式**，避免 auto 在 Ollama 不可達時誤走 LM Studio 分支）、`LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`、`LOCAL_LLM_RESERVED_OUTPUT_TOKENS`、`LOCAL_LLM_DISABLE_THINKING=true`、`LOCAL_LLM_KEEP_ALIVE`、`LOCAL_LLM_REQUEST_TIMEOUT`、`LOCAL_LLM_STREAM_IDLE_TIMEOUT`（config.py `:58/:188-192/:274/:288/:298/:302`；compose 預設 `:110/:118-129`）。
3. **Windows 主機（Ollama 程序）環境變數**：`OLLAMA_FLASH_ATTENTION=1`、`OLLAMA_KV_CACHE_TYPE=q8_0`（compose `:233` 明列「必要」）；容器連不到主機時另設 `OLLAMA_HOST=0.0.0.0:11434` 並確認防火牆允許 11434（`:176-177` 已給 host-gateway 對應）。

### 4.2 模型名稱怎麼填

- Windows 上 `ollama list` 看實際 tag → 填進 compose 的 `LOCAL_LLM_MODEL`（compose 值蓋 `.env`）。
- 找不到相符模型時後端會嘗試同家族變體自動對應；仍找不到即**直接報錯、不會靜默換模型**（`summarization.py:1937-1972` 行為路徑）。
- 不要填 LM Studio 的 model identifier（如 `publisher/model` 格式）；Ollama 要的是 tag。

### 4.3 要驗證的 Ollama API 行為（實機）

1. `curl http://127.0.0.1:11434/api/tags`：服務與模型 tag 存在。
2. 容器內：`docker compose -f docker-compose-windows-gpu.yml exec backend curl -s http://host.docker.internal:11434/api/tags`：host-gateway 連通。
3. `POST /api/chat`（`stream:true`）回傳結構：`message.content`、`done_reason`、`load_duration`/`eval_count`/`prompt_eval_count`（`:2325-2402` 會讀這些欄位）。
4. `think` 參數相容性：送 `think:false`；400 時後端自動降級重送（`:2425-2432`），確認日誌出現降級訊息但任務照常完成。
5. `options.num_ctx` 生效（Ollama 對超限的行為是「滿了以 `done_reason=length` 收尾」，後端接受 length 不誤殺，`:2377-2383`）。
6. 長生成時的串流行為：chunk 間閒置 > `LOCAL_LLM_STREAM_IDLE_TIMEOUT` 才會判卡死（`:2325-2350` 註解即為此設計）。

### 4.4 要在 Windows 上跑的測試（依序）

1. **純函式（不需模型，最快）**：
   `uv run pytest tests/test_platform_provider_routing.py tests/test_t20260922_record_quality.py tests/test_record_quality_metrics.py tests/test_record_table_tags.py tests/test_record_term_fixes.py tests/test_record_dedupe.py -q`
   （含「後處理模組無平台分支」「引擎無關」「吸附冪等」護欄；皆為純函式。）
2. **啟動＋health gate**：`uv run python scripts/e2e/run_owned_e2e.py --smoke`（快照閘門在 smoke 不 veto，`:1236-1237/1291-1293`）——注意此步驟會啟動後端，屬部署煙霧測試，請在允許的時段執行。
3. **產物驗收（真正回答「吸附在 Windows+Ollama 有沒有作用」）**：在 Windows 以「科務會議模板＋本地模式」跑一份真實錄音後：
   - `uv run python scripts/e2e/measure_record_quality.py --record <紀錄.md> --transcript <逐字稿.txt> --template section_meeting`
     （此工具只**輸出量測**、不判定；閘門數字出自工作樹 plan.md `:63-67/:117-119`）
     驗收閘門：`table_source_tag_count == 0`、`body_source_tag_count >= 17`、`traceable_tag_ratio >= 0.95`、`on_start_tag_ratio >= 0.95`、`on_start_tag_ratio_excluding_zero >= 0.9`；研究文件 §10.5 的 `>= 0.9` 是「換引擎前哨」寬鬆線（同一指標、用途不同，plan.md `:117-119` 已釐清）。
   - `uv run python scripts/e2e/check_record_output.py --md <紀錄.md> --docx <紀錄.docx>`（`:708-709`）。
   - 若部署快照含 P3 修復，另確認 `kept_on_start`／`backward_moves`（後退僅限段落內吸附，幅度另見 `max_backward_seconds`；舊名 `snapped_across_segment`＝rev 8 工作名，恆 0 無鑑別力，已移除）。
4. **不可用 full E2E 作 Windows 首驗**（R-04：LM Studio 快照閘門會失敗），除非先接受已知限制或補 runner 支援。

## 5. 既有文件待補（只回報，未修改檔案）

### 5.1 `doc/操作手冊/部署更新手冊_v4.1.md`（Windows 章節 `:418-429`）

- 缺 **`LOCAL_LLM_PROVIDER` 語意**：Windows 建議顯式設 `ollama`（避免 auto 在 Ollama 不可達時轉 LM Studio 分支），現在完全沒提。
- 缺 **吸附 v1.0→v1.1 errata**：`b3db34a` 的閉區間缺陷（倒退一格／非冪等）與工作樹 P3 的修法（rev 9 定稿＝閉區間 `[start,end]`＋段首命中優先＋規則 0 全域段首保護）、新觀察值 `kept_on_start`／`backward_moves`／`max_backward_seconds`（舊名 `snapped_across_segment`＝rev 8 工作名，恆 0 無鑑別力，已移除）——上線決策需要知道「部署哪個版本」。
- 缺 **Windows E2E runner 限制**：runner 模型快照為 LM Studio 專用（`run_owned_e2e.py:266`），Windows 首驗請用 `--smoke`＋`measure_record_quality.py`／`check_record_output.py`，避免照抄 Mac 的 full E2E 指令誤判。
- 缺 **diarization 模型部署步驟細節**：`:425` 只寫「由 `scripts/download_diarization_models.py` 預載」與容器路徑 `/app/models/diarization`；未寫「在 Windows 上要在哪個環境執行、模型檔案如何進容器」。
- 缺 **時區/編碼前提**：`TZ=Asia/Taipei`（Dockerfile.gpu `:27`）與「Windows 主機直跑 E2E 工具需 `tzdata`」的提醒。

### 5.2 `doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md`

- §10.4（`:791` 起，含 `:808` 起「硬前提清單 errata 2026-09-22」）與 §10.5（`:824` 起）已涵蓋模型無關論證、Windows 硬前提與換引擎 SOP（含門檻關係 0.9 vs 0.95 的釐清）；**仍待補：**
  - 「Windows E2E runner 為 LM Studio 專用」這個事實（§10.4 第 3 點只談 compose 寫死，沒談 `run_owned_e2e.py` 的模型快照閘門與替代驗收指令）。
  - **吸附 v1.0 已知缺陷（倒退一格／非冪等）與 v1.1 修法的 errata**（目前文件只到修復前敘述；工作樹 plan.md 亦指出研究文件「吸附後」數字是推論值不可重現，需一併更正）。
  - C1 之後的 P3 修復尚未回填（工作樹未提交）。

## 6. 未驗證與未執行項目（範圍宣告）

- [UNVERIFIED] Windows 11 + RTX 4090 + Ollama 的實機行為（本報告所有 Windows/Ollama 結論均為程式碼與設定層推得；本次未實機、未啟動任何服務）。
- [UNVERIFIED] Windows 主機直跑 `run_owned_e2e.py` 的 tzdata 可用性（R-10）。
- [UNVERIFIED] Ollama 實際版本對 `think`／`num_ctx`／串流的支援差異（僅確認程式碼有降級與接受邏輯）。
- 未執行：任何 pytest、E2E、後端啟動、LM Studio／Ollama 呼叫。
- 本報告寫入 `data/cache/staging/crossos/`（gitignored 暫存區）；**未修改任何 git 追蹤檔案**。
