# uv 管理說明 —— 給用過 conda、覺得 Python 環境很麻煩的你

> **文件目的**：v4.2 起本專案的 Python 環境改用 **uv** 管理。這份文件用白話解釋：uv 是什麼、它能不能解決你的痛點、跟 conda 差在哪、離線內網能不能用。
> **一句話版**：uv = 一個超快的小工具，把「裝 Python、建虛擬環境、裝套件、鎖版本」四件事變成**一個指令**，而且環境壞了隨時可以一鍵重建。

---

## 一、你的痛點，uv 怎麼解？

| 你以前的痛 | 以前的日子（conda / 手動 venv） | 用 uv 之後 |
|---|---|---|
| **每個專案要自己顧一個虛擬環境** | 要記得 `conda create`、`conda activate`，切換專案容易搞混、環境名字一堆 | 環境「跟著專案資料夾走」：進到專案目錄打 `uv sync`，它自動建好 `.venv` 並裝好所有套件。**你不需要記環境名，也幾乎不需要 activate**（用 `uv run xxx` 直接執行） |
| **不同專案要不同 Python 版本** | 要另外裝好幾套 Python 或用 conda 管，版本打架 | 專案設定檔寫明「本專案要 Python 3.11+」，uv 發現你電腦沒有時**會自動下載一份專用的**，不動到系統、不影響其他專案 |
| **套件版本衝突、換台電腦裝不起來** | `requirements.txt` 只寫大概版本，今天裝和明天裝結果可能不同 | 本專案多了一個 `uv.lock` 檔，**73 個套件的精確版本全部鎖死**。任何電腦、任何時間 `uv sync`，裝出來的環境保證一模一樣 |
| **環境壞掉（像我們這次 venv 因 Python 更版而報廢）** | 手動重建、重裝、除錯半天 | 把 `.venv` 資料夾整個刪掉，`uv sync` 一鍵長回來（實測本專案約 1-2 分鐘） |
| **conda 又肥又慢** | 一個環境動輒好幾 GB、解相依等很久 | uv 用 Rust 寫的，**快 10-100 倍**；所有專案共用一個全域快取，同一套件只存一份，磁碟省很多 |

**結論：是的，uv 能解決你說的痛點**——前提是「純 Python 專案」（本專案就是）。唯一 conda 比 uv 強的地方見第四節。

---

## 二、日常你只需要記 4 個指令

在專案資料夾（`D:\dev\convert`）打開終端機：

| 你想做什麼 | 指令 |
|---|---|
| 建好/修好整個環境（第一次、或環境怪怪的時候） | `uv sync` |
| 跑測試 | `uv run pytest tests/ -q` |
| 啟動後端服務 | `uv run uvicorn backend.main:app --host 0.0.0.0 --port 9527` |
| 幫專案加一個新套件（會自動更新鎖定檔） | `uv add 套件名` |

就這樣。不用 activate、不用記環境名、不用管 Python 裝在哪。

> 安裝 uv 本身（一次性）：`winget install astral-sh.uv`（Windows）或
> `curl -LsSf https://astral.sh/uv/install.sh | sh`（Mac/Linux）。uv 本體只是**一個小小的執行檔**。

---

## 三、離線內網（沒有 Internet）能用嗎？

**能，但要先「備糧」**——這點跟 conda 一樣（conda 離線也要先 conda-pack 打包），不是 uv 的缺點。原理很簡單：uv 本身不需要網路，需要網路的是「下載套件」這個動作，所以只要把套件先搬進去就行。

### 做法 A：帶「快取」進去（最簡單，推薦）

1. 在**有網路**的電腦上：`uv sync` 跑過一次（套件全部進到 uv 的全域快取資料夾）。
2. 把兩樣東西複製到內網機（隨身碟/光碟）：
   - uv 執行檔本身（單一 .exe）
   - 快取資料夾：`%LOCALAPPDATA%\uv\cache`（整包複製到內網機同樣位置）
3. 在內網機的專案資料夾執行：`uv sync --offline` → 完成，全程不碰網路。

### 做法 B：帶「wheel 倉」進去（最正式，適合要長期維運的內網）

1. 有網路的電腦：
   ```
   uv export --format requirements-txt -o requirements.lock.txt
   pip download -r requirements.lock.txt -d wheelhouse\
   ```
2. 把 `wheelhouse\` 資料夾（所有 .whl 檔）帶進內網。
3. 內網機：`uv pip install --no-index --find-links wheelhouse\ -r requirements.lock.txt`

### 一個重要提醒：Python 直譯器也要先帶

若內網機連 Python 都沒有，先在有網路的機器 `uv python install 3.12`，把
`%APPDATA%\uv\python` 下載好的資料夾一併帶進去。

### 本專案的內網部署其實走 Docker（更省事）

正式環境（GPU 主機）是 Docker 部署：映像建好後整包匯出（`docker save`）→ 隨身碟 → 內網機 `docker load`，連 uv 都不用碰。上面 A/B 做法是給「要在內網機直接開發/除錯」的情境用的。

---

## 四、uv vs conda 誠實對照（什麼時候 conda 仍有優勢）

| 面向 | conda | uv |
|---|---|---|
| 速度 | 慢（解相依常等數分鐘） | **極快**（秒級） |
| 環境還原精準度 | environment.yml（不完全精準） | **uv.lock 完全精準** |
| Python 版本管理 | ✅ 會 | ✅ 會（自動下載、專案綁定） |
| 磁碟占用 | 每個環境獨立肥大 | **全域快取共用**，省空間 |
| **非 Python 的系統軟體**（如 CUDA 函式庫、ffmpeg） | ✅ **能裝**（這是 conda 唯一明顯優勢） | ❌ 不管這塊 |
| 學習成本 | 中 | 低（4 個指令） |

本專案的非 Python 相依（ffmpeg、CUDA）由 **Docker 映像**負責，所以 conda 的唯一優勢在這裡用不到——可以放心全面改用 uv。

---

## 五、本專案現況（你不用做任何事，這裡只是記錄）

- `pyproject.toml`：專案定義＋依賴清單（人看的）
- `uv.lock`：73 個套件精確鎖定（機器看的，**不要手改**）
- `requirements.txt` / `requirements-correction.txt`：**保留給 Docker build 用**，與 pyproject 同步維護
- 開發機的 torch 已設定走 CPU 版來源（不會誤下載 2GB 的 CUDA 版；GPU 推論在 Docker/遠端主機）
