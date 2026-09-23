# 跨 OS 可攜性稽核報告 — P5-A / P5-A.1（Windows 11 + Ollama）

- 稽核者：跨作業系統可攜性稽核員（唯讀稽核；**本輪未修改任何產品程式碼**，唯一新增檔案＝本報告）
- 受稽分支/commit：`fix/qwen-local-quality-parity` @ `7176929`（P5-A）→ `5247436`（P5-A.1）→ `ce99502`（觸發判定改看修正後文字）
- 稽核環境：macOS（Apple Silicon）＋ `uv 0.9.24`。Windows 條件以「離線純 Python 模擬」驗證（零 LLM 成本，全程未接任何 LLM）
- 稽核時間：2026-09-23；受稽檔案：`data/glossary/確定性誤辨校正.txt`、`backend/core/glossary.py`、`backend/core/text_postprocess.py`、`backend/services/correction.py`（另掃描 `backend/**/*.py` + `main.py` 的 POSIX-only 假設）

## 結論

**`WINDOWS_SAFE_WITH_NOTES`**

- 無 Windows blocker：三層（逐字稿清理／校正／紀錄）全部走 `os.path`／`open(encoding="utf-8")`，無 `fcntl`/`SIGKILL`/`/tmp` 寫死/`shell=True`/`shlex`/`"/"` 拼接，且與 provider 無關（Windows `auto` 預設即 Ollama，見證據 4）。
- 詞表讀取對 CRLF 耐受、空目錄/不存在目錄/檔案不可讀皆 fail-soft（實測 a/a2/權限探針，見 §實測）。
- NOTE-1（BOM，唯一實質風險）：`utf-8` 不解 BOM。現行資料檔**無 BOM**（已驗位元組），故今天無害；但若在 Windows 用記事本另存「UTF-8 含 BOM」：(i) 首行註解會變成垃圾詞項（實測 b）；(ii) 若首行是 `錯=>對` 配對，該條規則會以 `\ufeff錯形` 登錄而**靜默失效**（實測 b2）。建議 `encoding="utf-8-sig"`（僅建議，未動工）。
- NOTE-2：`GLOSSARY_DIR` 若填相對路徑，以「行程 CWD」解析（`os.path.abspath`）；Windows 服務/排程啟動的 CWD 常非專案根，建議文件標明用絕對路徑。
- NOTE-3：以記事本「ANSI（CP950）」另存詞表 → `UnicodeDecodeError` 不被 `except OSError` 攔（實測 cp950 探針），會上拋；屬編輯器誤用情境，非現況。
- NOTE-4：`backend/core/platform_config.py:141` 讀 `/proc/1/cgroup` 是 POSIX 路徑，但有 `except FileNotFoundError` 護欄，Windows 會落到環境變數 fallback（非 P5-A 範圍）。
- `[UNVERIFIED]`：Windows 11 實機與 Ollama 實機均未執行（見 §未驗證）。

## 證據

### 1. 檔案讀取（編碼／BOM／CRLF／路徑寫法）

- 詞表唯一的檔案讀取已明示 UTF-8：`backend/core/glossary.py:64`
  ```python
  with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
  ```
  → 不依賴 Windows 預設 cp950/GBK，該風險被明確切斷。
- 設定檔亦固定 UTF-8：`backend/core/config.py:689-691`（`SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`）。
- `os.listdir`/`os.path` 可攜寫法（無硬編碼分隔符）：
  - `backend/core/glossary.py:29`（預設目錄 `os.path.join(dirname(__file__), "..", "..", "data", "glossary")`）
  - `backend/core/glossary.py:34-41`（`os.path.join` / `os.path.getmtime` / `os.listdir`）
  - `backend/core/glossary.py:48`（`os.path.abspath` 正規化）、`:59-64`（`os.path.isdir` / `os.listdir` / `os.path.join`）
  - P5-A 三檔中 `"/"` 字串拼接 0 命中（見 §實測 P4 掃描）。
- `sorted(os.listdir(directory))`（`backend/core/glossary.py:60`）→ 檔名以 code point 排序（非 locale），跨 OS 載入順序固定（`公務詞彙.txt` → `確定性誤辨校正.txt`）。
- CRLF 耐受：`open(..., "r")` 未指定 `newline` → universal newlines 將 `\r\n` 轉 `\n`；`raw_line.strip()`（`backend/core/glossary.py:66`）為第二層保險。實測 (b) 證實。
- BOM：`utf-8` codec 保留 `\ufeff`；`str.strip()` 與行尾註解 regex（`backend/core/glossary.py:69`）都不吃 `\ufeff`。現行資料檔無 BOM（`xxd` 首 3 bytes `23 20 e7`）；實測 (b)/(b2) 見影響。
- `settings.GLOSSARY_DIR` 空字串/相對路徑解析：
  - 預設 `""`（`backend/core/config.py:403-406`；文件化於 `.env.example:96`）。
  - 空值 → 套件相對 fallback（`backend/core/glossary.py:26-29`）→ `os.path.abspath`（`:48`）。Windows 安裝在 `C:\...\convert` 時解析為 `C:\...\convert\data\glossary`；Docker 情境相符（`docker/docker-compose-windows-gpu.yml:167` 將 `../data/glossary` 掛到 `/app/data/glossary`，而套件路徑 `backend/core/../../data/glossary` 在容器內即 `/app/data/glossary`）。
  - 非空相對路徑 → `abspath` 以行程 CWD 為基準（NOTE-2）。

### 2. 詞表資料檔本身（Windows 字元／排序穩定性／locale）

- 檔名 `確定性誤辨校正.txt`：NTFS 合法（無保留名 `CON/PRN/...`、無 `\ / : * ? " < > |`、無結尾空白或句點）。內容純 UTF-8 文字（`file`：`Unicode text, UTF-8 text`）；**無 BOM、無 CR**（`bom False / crlf 0 / lf 180`）。
- 「長形優先」確定性：`backend/core/glossary.py:169`
  ```python
  for wrong, right in sorted(corrections, key=lambda pair: -len(pair[0])):
  ```
  key 為整數長度、Python `sort` 保證穩定 → 同長詞以「登錄順序」為 tie-break；登錄順序＝`sorted(os.listdir)` 的檔序 ＋ 檔內行序，皆確定。無 `locale.strxfrm`/`setlocale` 依賴。
- 全 `backend/`＋`main.py` 掃 `import locale|setlocale|strxfrm`：0 命中（§實測 P5）。
- 資料檔語法（`!複合詞`／`錯=>對`／行尾 `#` 註解）解析於 `backend/core/glossary.py:69-90`；單字配對放行規則於 `:143-147`；排除詞阻擋替換於 `:179-209`。

### 3. POSIX-only 假設掃描（範圍：`backend/**/*.py` ＋ `main.py`）

| 檢查項 | 結果 | 證據 |
|---|---|---|
| `fcntl` / `signal`（含 SIGKILL）/ `os.fork` / `pwd` / `grp` / `resource` / `setsid` | 0 命中 | §實測 P1 |
| `subprocess` `shell=True` / `shlex` | 0 命中 | §實測 P2；4 處 `subprocess`（`backend/services/device_detector.py:88`、`backend/services/diarization.py:165`、`backend/services/asr_apple/apple.py:300`、`backend/services/asr_apple/apple_cli.py:370`）皆未用 shell；`asr_apple` 為 macOS 專屬層 |
| `/tmp` 寫死 | 0 命中 | §實測 P3；暫存檔用跨平台 `tempfile.mkstemp`（`backend/services/diarization.py:162`、`backend/services/asr_subprocess.py:131`） |
| 路徑分隔符 `"/"` 拼接 | P5-A 三檔 0 命中 | §實測 P4 |
| 唯一 POSIX 路徑字面 | `backend/core/platform_config.py:141` `open('/proc/1/cgroup')`（`is_docker()`）；`:143` `except FileNotFoundError` → Windows fallback 到 env var（`:147`）。非 P5-A 範圍、Ollama 路徑不經此函式（僅 `get_default_lmstudio_base_url` 用，`:90`） | §實測 P6 |

### 4. Provider 無關性（provider=ollama 同樣生效）

三層入口全部與引擎解耦，provider 判斷只出現在 `summarization.py` 的引擎選擇處：

- 逐字稿清理層（零 LLM）：`backend/services/task_processor.py:240-242`（`clean_transcript` 無條件執行）→ `backend/core/text_postprocess.py:231-260` → `:257` `apply_official_term_fixes` → `:218-220` `apply_known_corrections`（純 Python、資料檔驅動）。
- 校正層：`backend/services/correction.py:306-320`（`generate_fn` 由呼叫端注入；本檔唯一 "lmstudio" 字樣是 `:366` 註解裡的 error code 舉例，無 provider 分支）。呼叫端注入：`backend/services/task_processor.py:259-272`（`summarization_service.generate_local(...)`）。確定性誤辨先修再交 LLM：`backend/services/correction.py:335-349`；觸發判定改看修正後文字：`:351-357`（ce99502）。同音閘門＋保護詞護欄：`correction.py:137-153`、`:189-201`。
- Provider 分支點（`backend/services/summarization.py`）：`:2916` `resolve_local_llm_provider`；`:2926-2929` `provider == "ollama"` → 回 `"ollama"`；`:2936-2938` 非 Mac 的 `auto` 先試 Ollama → **Windows 預設即 Ollama**；`:2969-2970` 引擎分派 `engine == "ollama"` → `_summarize_with_ollama`（`:3512`）。`backend/core/platform_config.py:46-55`：`auto`→lmstudio 僅 `darwin+arm64`（`:53-54`）→ 非 LM Studio-only。
- 紀錄層：`summarization.py:526-529`（非 CLOUD → `_summarize_with_local_pipeline`，`:2995-3003`）→ `:3117-3122`／`:3179-3184` 以 `mode="local"` 呼叫 `_finalize_record_text` → `:3261-3262` 雲端提前 return、地端續行 → `:3274` `apply_record_term_fixes` → `backend/core/text_postprocess.py:572-574` `apply_known_corrections`。Ollama 與 LM Studio 共用同一條 pipeline，故詞表修正同樣生效。
- 補充：ASR hotwords 也吃同一份詞表（`backend/services/transcription.py:410-416`、`:450-454`），Windows Whisper 路徑同樣生效。

## 實測（指令＋實際輸出）

> 說明：輸出中 ANSI 色碼已移除，其餘逐字保留（含 logger 行）。探針全程零模型呼叫；scratch 檔一律在 `/tmp/probe_scratch/`。

### (a) `GLOSSARY_DIR` 指向空目錄 → fail-soft
```bash
mkdir -p /tmp/probe_scratch/glossary_empty
DATA_DIR=/tmp/probe_scratch GLOSSARY_DIR=/tmp/probe_scratch/glossary_empty uv run --frozen python -c 'from backend.core.glossary import load_glossary, apply_known_corrections, protected_terms; terms, corr = load_glossary(force=True); print("terms =", terms); print("corrections =", corr); print("protected =", protected_terms()); print("apply =", apply_known_corrections("下週一要做內機檢查"))'
```
```
2026-09-23 12:23:39 | INFO | backend.core.logger:setup_logger:84 - 日誌系統初始化完成 (目錄: /tmp/probe_scratch/logs)
terms = []
corrections = []
protected = ()
apply = ('下週一要做內機檢查', [])
```

### (a2) 加成：`GLOSSARY_DIR` 指向不存在目錄 → 同樣 fail-soft
```bash
DATA_DIR=/tmp/probe_scratch GLOSSARY_DIR=/tmp/probe_scratch/does_not_exist uv run --frozen python -c 'from backend.core.glossary import load_glossary, apply_known_corrections; terms, corr = load_glossary(force=True); print("terms =", terms, "corrections =", corr); print("apply =", apply_known_corrections("內機")[0])'
```
```
terms = [] corrections = []
apply = 內機
```

### (b) 詞表檔含 CRLF + BOM → `apply_known_corrections` 仍正確
```bash
DATA_DIR=/tmp/probe_scratch uv run --frozen python -c '
import os
d = "/tmp/probe_scratch/glossary_crlf_bom"
os.makedirs(d, exist_ok=True)
content = "# 註解行\r\n內機=>內稽\r\n護數=>戶數\r\n!境內機\r\n差勤\r\n"
with open(os.path.join(d, "測試詞表.txt"), "wb") as f:
    f.write(b"\xef\xbb\xbf" + content.encode("utf-8"))
print("written", os.path.getsize(os.path.join(d, "測試詞表.txt")), "bytes, bom=True crlf=True")
'
```
```
written 68 bytes, bom=True crlf=True
```
```bash
DATA_DIR=/tmp/probe_scratch GLOSSARY_DIR=/tmp/probe_scratch/glossary_crlf_bom uv run --frozen python -c '
from backend.core.glossary import load_glossary, apply_known_corrections, protected_terms
terms, corr = load_glossary(force=True)
print("terms repr =", repr(terms))
print("corrections =", corr)
fixed, applied = apply_known_corrections("下週一要做內機檢查，戶數100戶，境內機房")
print("fixed =", fixed)
print("applied =", applied)
print("protected =", protected_terms())
'
```
```
2026-09-23 12:23:59 | INFO | backend.core.glossary:load_glossary:98 - 詞彙表載入完成：4 詞、2 條已知誤辨修正
terms repr = ['\ufeff# 註解行', '內稽', '戶數', '差勤']
corrections = [('內機', '內稽'), ('護數', '戶數')]
fixed = 下週一要做內稽檢查，戶數100戶，境內機房
applied = [('內機', '內稽', 1)]
protected = ('內稽', '戶數', '差勤')
```
判讀：CRLF 無影響；BOM 使首行註解變成垃圾詞項 `'\ufeff# 註解行'`（僅污染 hotwords/詞表，不影響替換）；`!境內機` 排除生效（`境內機房` 不動）。

### (b2) 加成：BOM 且首行是配對 → 該條規則靜默失效（NOTE-1 的證據）
```bash
DATA_DIR=/tmp/probe_scratch uv run --frozen python -c '
import os
d = "/tmp/probe_scratch/glossary_bom_firstline"
os.makedirs(d, exist_ok=True)
with open(os.path.join(d, "bom_pair.txt"), "wb") as f:
    f.write(b"\xef\xbb\xbf" + "內機=>內稽\r\n護數=>戶數\r\n".encode("utf-8"))
'
DATA_DIR=/tmp/probe_scratch GLOSSARY_DIR=/tmp/probe_scratch/glossary_bom_firstline uv run --frozen python -c '
from backend.core.glossary import load_glossary, apply_known_corrections
terms, corr = load_glossary(force=True)
print("corrections repr =", repr(corr))
fixed, applied = apply_known_corrections("下週一內機檢查，戶數100戶")
print("fixed =", fixed, "| applied =", applied)
'
```
```
corrections repr = [('\ufeff內機', '內稽'), ('護數', '戶數')]
fixed = 下週一內機檢查，戶數100戶 | applied = []
```

### (c) 同一輸入 100 次結果一致（確定性；真實 repo 詞表，43 條全載）
```bash
DATA_DIR=/tmp/probe_scratch uv run --frozen python -c '
import hashlib
from backend.core.glossary import apply_known_corrections
sample = "下週一內機檢查，護數統計，猜勤與拆勤，泡麵好吃，後麵那間麵店，評審員到場，境內機房，土地稅客"
runs = [apply_known_corrections(sample) for _ in range(100)]
first = runs[0]
print("runs =", len(runs))
print("unique_fixed =", len({r[0] for r in runs}), "unique_applied =", len({tuple(r[1]) for r in runs}))
print("all_equal =", all(r == first for r in runs))
print("fixed =", first[0])
print("applied =", first[1])
print("sha256 =", hashlib.sha256(first[0].encode("utf-8")).hexdigest())
'
```
```
2026-09-23 12:24:14 | INFO | backend.core.glossary:load_glossary:98 - 詞彙表載入完成：121 詞、43 條已知誤辨修正
runs = 100
unique_fixed = 1 unique_applied = 1
all_equal = True
fixed = 下週一內稽檢查，戶數統計，差勤與差勤，泡麵好吃，後面那間麵店，評審員到場，境內機房，土地稅科
applied = [('土地稅客', '土地稅科', 1), ('內機', '內稽', 1), ('護數', '戶數', 1), ('拆勤', '差勤', 1), ('猜勤', '差勤', 1), ('麵', '面', 1)]
sha256 = f7745db8b55c26b124725180060c7853c4763aa29ea9180154b9944d1ca61c64
```
加成（跨 locale／跨行程；兩個獨立行程＝不同預設 PYTHONHASHSEED）：
```bash
LC_ALL=en_US.UTF-8 DATA_DIR=/tmp/probe_scratch uv run --frozen python -c '...同一 sample、100 次...'
LC_ALL=C DATA_DIR=/tmp/probe_scratch uv run --frozen python -c '...同一 sample、100 次...'
```
```
2026-09-23 12:24:14 | INFO | backend.core.glossary:load_glossary:98 - 詞彙表載入完成：121 詞、43 條已知誤辨修正
locale = en_US.UTF-8
unique_fixed = 1 unique_applied = 1
sha256 = f7745db8b55c26b124725180060c7853c4763aa29ea9180154b9944d1ca61c64

2026-09-23 12:24:30 | INFO | backend.core.glossary:load_glossary:98 - 詞彙表載入完成：121 詞、43 條已知誤辨修正
unique_fixed = 1
sha256 = f7745db8b55c26b124725180060c7853c4763aa29ea9180154b9944d1ca61c64   ← 兩次與 (c) 完全相同
```

### 加成探針：檔案不可讀（模擬 Windows 鎖定/權限）→ fail-soft；cp950 檔 → 上拋
```bash
# 目錄內 locked.txt(0o0) + ok.txt
DATA_DIR=/tmp/probe_scratch GLOSSARY_DIR=/tmp/probe_scratch/glossary_perm2 uv run --frozen python -c 'from backend.core.glossary import load_glossary, apply_known_corrections; terms, corr = load_glossary(force=True); print("corrections =", corr); print("apply =", apply_known_corrections("要做內機檢查，看護數")[0])'
```
```
2026-09-23 12:28:06 | WARNING | backend.core.glossary:load_glossary:92 - 讀取詞彙表 locked.txt 失敗: [Errno 13] Permission denied: '/tmp/probe_scratch/glossary_perm2/locked.txt'
2026-09-23 12:28:06 | INFO | backend.core.glossary:load_glossary:98 - 詞彙表載入完成：1 詞、1 條已知誤辨修正
corrections = [('護數', '戶數')]
apply = 要做內機檢查，看戶數
```
```bash
# 以 cp950 位元組存檔的詞表
DATA_DIR=/tmp/probe_scratch uv run --frozen python -c '
import os
d = "/tmp/probe_scratch/glossary_cp950"
os.makedirs(d, exist_ok=True)
with open(os.path.join(d, "ansi.txt"), "wb") as f:
    f.write("內機=>內稽\r\n".encode("cp950"))
'
DATA_DIR=/tmp/probe_scratch GLOSSARY_DIR=/tmp/probe_scratch/glossary_cp950 uv run --frozen python -c '
try:
    from backend.core.glossary import load_glossary
    load_glossary(force=True)
    print("no error")
except Exception as exc:
    print("RAISED:", type(exc).__name__, str(exc)[:120])
'
```
```
RAISED: UnicodeDecodeError 'utf-8' codec can't decode byte 0xa4 in position 0: invalid start byte
```
（`UnicodeDecodeError` 非 `OSError` 子類，`backend/core/glossary.py:91` 的 `except OSError` 不攔 → 見 NOTE-3。）

### 掃描指令（§證據 3）
```bash
rg -n "fcntl|SIGKILL|signal\.|os\.fork|import pwd|import grp|import resource|setsid" backend main.py --glob '*.py'   # exit=1（0 命中）
rg -n "shell\s*=\s*True|shlex" backend main.py --glob '*.py'                                                    # exit=1
rg -n '/tmp' backend main.py --glob '*.py'                                                                       # exit=1
rg -n '"\/"' backend/core/glossary.py backend/core/text_postprocess.py backend/services/correction.py             # exit=1
rg -n "import locale|setlocale|strxfrm" backend main.py --glob '*.py'                                             # exit=1
rg -n '/proc|\.dockerenv' backend main.py --glob '*.py'   # 命中 platform_config.py:136,141（有護欄，見證據 3）
```

### 加成：既有回歸測試（25 passed）
```bash
DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/test_deterministic_transcript_corrections.py tests/test_record_term_fixes.py -q
```
```
.........................                                                [100%]
25 passed in 0.64s
```

### 加成：模組原始碼 provider 字樣檢查（證明非 LM Studio-only）
```bash
DATA_DIR=/tmp/probe_scratch uv run --frozen python -c '
import inspect
from backend.services import correction
from backend.core import glossary, text_postprocess
for m in (correction, glossary, text_postprocess):
    s = inspect.getsource(m)
    print(m.__name__, "| ollama:", ("ollama" in s.lower()), "| lmstudio:", ("lmstudio" in s.lower()), "| openai:", ("openai" in s.lower()))
' 2>&1 | grep -v "日誌系統"
```
```
backend.services.correction | ollama: False | lmstudio: True | openai: False   ← 唯一 lmstudio 字樣在 correction.py:366 註解（error code 舉例）
backend.core.glossary | ollama: False | lmstudio: False | openai: False
backend.core.text_postprocess | ollama: False | lmstudio: False | openai: False
```

## 未驗證（`[UNVERIFIED]`）

- `[UNVERIFIED]` **Windows 11 實機未跑**：本報告的 Windows 條件（空目錄/不存在目錄/CRLF/BOM/權限/相對路徑）是在 macOS 以相同 CPython 語意模擬；未在 Windows 上跑過 `uv run`、未驗 NTFS 大小寫不敏感、Windows 長路徑（>260 字元）、Windows 檔案共享鎖定的真實行為。
- `[UNVERIFIED]` **Ollama 實機未跑**：provider=ollama 只由靜態證據（§證據 4 的 file:line）證明；本輪未啟動 Ollama、未做 LM Studio↔Ollama 對照跑（零模型成本原則）。
- `[UNVERIFIED]` 記事本「另存 BOM/ANSI」的真實復現：BOM/CP950 檔以位元組寫入模擬，行為依 CPython utf-8 codec 語意；未用 Windows 記事本實際操作。
- `[UNVERIFIED]` 非 P5-A 範圍未逐行稽核：`backend/core/logger.py` 日誌檔編碼、`frontend/`、`scripts/windows/*`、`apple_speech_cli/`（macOS 專屬）僅在 §證據 3 的關鍵字掃描範圍內。
- `[UNVERIFIED]` 詞表檔在 Windows checkout 時的實際行尾（本機無 `.gitattributes`；`core.autocrlf` 未設定的 Windows 預設會轉 CRLF，本報告已證 CRLF 耐受，但未在 Windows 實際 checkout 觀察）。

## 建議修補（僅建議，本輪未動工）

1. **`encoding="utf-8-sig"`**（`backend/core/glossary.py:64`）：一行改動同時容忍 BOM 與現況檔案（無 BOM 檔輸出位元組不變）。搭配測試：BOM＋首行配對仍生效（可直接改編實測 b2 案例）。優先度：中（唯一有實際失效路徑的項目）。
2. **`except (OSError, UnicodeDecodeError)`**（`backend/core/glossary.py:91`）：讓「以 ANSI/CP950 誤存」的詞表也 fail-soft（現況會上拋，可能終止任務的確定性清理步驟）。優先度：低。
3. **`GLOSSARY_DIR` 相對路徑語意**：文件標明「建議絕對路徑」，或改以專案根（`Path(__file__).resolve().parents[2]`）為基準 resolve（`backend/core/glossary.py:26-29`）。優先度：低（NOTE-2）。
4. 可選：新增 `.gitattributes`（如 `data/glossary/*.txt text eol=lf`）降低跨平台 diff 噪音（CRLF 已證耐受，此項純為整潔）。優先度：低。
5. `backend/core/platform_config.py:141`：`except FileNotFoundError` 可放寬為 `except OSError`（Windows 上 `/proc/1/cgroup` 理論上可能以 `NotADirectoryError`/`PermissionError` 形式失敗）。非 P5-A 範圍、優先度：低。

---
稽核結論：`WINDOWS_SAFE_WITH_NOTES`（0 blocker；4 條 note 全部為可選強化，且皆有實測或 file:line 證據支撐）。
