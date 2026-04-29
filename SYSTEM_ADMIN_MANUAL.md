# 系統管理手冊

版本：1.0
更新日期：2025-12-08

說明：
本手冊以非技術人員易讀的方式，說明本專案的系統架構、程式架構、部署（Windows BAT 與 Docker）、設定檔（config.yaml）、環境變數、GPU 加速需求、維護建議與常見問題。建議系統管理員與維運人員依本檔操作或傳給開發人員以取得協助。

---

## 1. 系統架構說明（高階）

- 使用者介面（Frontend）：若專案包含前端，通常部署成靜態檔案或獨立容器，提供使用者互動介面。
- 應用程式伺服器（Backend）：主要程式入口在 `main.py` 與 `src/` 下的模組，負責處理請求、商業邏輯與檔案處理。
- 資料目錄（data/）：儲存輸入、輸出或模型檔案等。請注意資料備份與權限設定。
- Docker 化（docker/）：專案提供 Docker 化支援以利跨環境部署。

此架構使系統可在本機（Windows）或伺服器（Docker/容器）運行，並且支援有/無 GPU 的情況。

---

## 2. 程式架構說明（以非技術語言）

- `main.py`：程式的啟動檔，類似「開關」，啟動後會讀取設定檔、初始化必要元件，然後開始提供服務或執行工作。
- `src/`：放程式碼的資料夾，內含處理資料、計算或與外部系統互動的程式。
- `docker/`：若存在，包含容器化所需的檔案（例如 Dockerfile、docker-compose.yml）。
- `config.yaml`：系統設定檔，定義埠號、資料路徑、外部服務連線資訊與運行參數。
- `requirements.txt`：Python 相依套件清單，系統要運行必須安裝上面列的套件。

總結：系統就是一組程式（src）由主程式（main.py）啟動，並依 config.yaml 的設定運作；為了方便與一致性，常把整個系統包成 Docker 映像檔來啟動。

---

## 3. Windows BAT 檔（部署）說明

說明：若在 Windows 環境，以 BAT 檔方便啟動服務或建立開機排程，以下為常見範例：

example_start.bat（範例）:

@echo off
REM 啟用 Python 虛擬環境（若使用 venv）
call "%~dp0\.venv\Scripts\activate.bat"
REM 安裝相依套件（第一次或更新時使用）
REM Windows + NVIDIA GPU 請優先使用 install_deps.py，避免裝到 CPU-only torch
python install_deps.py
REM 啟動主程式
python main.py

example_stop.bat（範例）:

@echo off
REM 終止程式（可以用 taskkill 指令，視實際啟動方式而定）
REM 範例：以名稱終止（請改為實際進程名稱）
taskkill /IM python.exe /F

注意：
- 若要將程式設為 Windows 服務，建議使用第三方工具（如 NSSM）或建立排程 (Task Scheduler) 以達到開機自動啟動與監控重啟。
- 若使用虛擬環境，BAT 中路徑應改為實際 venv 所在位置。

---

## 4. 系統服務與 Docker 啟動/關閉/重啟說明

若使用 Docker（建議在伺服器環境）：

常見命令（需安裝 Docker / docker-compose）：

- 建置映像（在專案根目錄）：
  docker build -t project-name .
- 以容器執行：
  docker run --name project-container -p 8000:8000 project-name
- 使用 GPU（需安裝 NVIDIA Docker 支援）：
  docker run --gpus all --name project-container -p 8000:8000 project-name
- 若使用 docker-compose（若存在 docker-compose.yml）：
  docker-compose up -d        # 啟動
  docker-compose down         # 停止並移除容器
  docker-compose restart      # 重新啟動
- 單一容器操作：
  docker start <container>
  docker stop <container>
  docker restart <container>
  docker logs -f <container>

注意事項：
- 啟動前請確認 `config.yaml` 的網路埠與宿主機無衝突。
- 若要追蹤服務狀態，使用 `docker ps` 與 `docker logs`。

---

## 5. config.yaml 說明（範例與常見欄位）

說明：config.yaml 是以簡潔的文字方式定義系統行為。範例欄位（實際請參考專案中的 config.yaml）：

- server:
  port: 8000            # 服務埠號
  host: 0.0.0.0         # 綁定位址

- logging:
  level: INFO           # 記錄等級（DEBUG/INFO/WARNING/ERROR）
  file: logs/app.log    # 日誌檔案路徑

- paths:
  data_dir: data/       # 資料目錄
  models_dir: models/   # 模型或大型檔案的位置

- external_services:
  redis:
    host: 127.0.0.1
    port: 6379

使用說明：
- 修改後需重新啟動程式或容器使設定生效。
- 若在 Docker 中，可將設定透過 volume 掛載或以環境變數注入容器中。

---

## 6. env 環境變數（含 Docker 內）說明

說明：環境變數常用於覆蓋 config.yaml 設定或儲存機密（例如 API 金鑰、密碼）。範例：

- APP_PORT=8000         # 覆蓋服務埠
- APP_HOST=0.0.0.0
- LOG_LEVEL=INFO
- DATABASE_URL=...      # 數據庫連線字串
- SECRET_KEY=...        # 應用的密鑰或 Token

Docker 中設定方式：
- 在 Dockerfile 或 docker-compose.yml 中使用 `environment:` 設定環境變數
- 或使用 `docker run -e "APP_PORT=8000" ...` 直接注入

安全建議：
- 不要將敏感資訊寫入版本控制（不要把密碼或金鑰寫在 repo 的檔案中），可使用 Docker secrets、環境變數管理工具或外部機密管理服務。

---

## 7. GPU 加速與 CUDA 函式庫依賴說明

若系統包含需要 GPU（例如深度學習或巨量計算）的功能，需注意以下：

必要條件：
- 主機的 NVIDIA 顯示卡與相應驅動（NVIDIA Driver）已正確安裝。
- 安裝相容的 CUDA Toolkit（版本應與專案相依套件相容）。
- 若使用 Docker，安裝 NVIDIA Container Toolkit，並使用 `--gpus` 參數或 `nvidia` runtime 來讓容器能存取 GPU。
- 可能還需安裝 cuDNN 或其他 CUDA 相關函式庫（視模型需求）。

檢查工具與指令：
- nvidia-smi        # 檢查驅動與 GPU 是否可見（在宿主機）
- 在容器內確認有 GPU 可見：docker run --gpus all --rm nvidia/cuda:11.0-base nvidia-smi

注意相容性：
- CUDA、驅動與深度學習套件（如 PyTorch、TensorFlow）之間需要版本相容，若發生錯誤，通常為版本不匹配所致。
- 本專案的 Windows GPU 安裝路徑已固定到「先安裝 `requirements.txt`、再以 `requirements.windows-cuda.txt` 覆寫 CUDA 版 torch (`torch==2.11.0+cu126`)」，避免 `pip install -r requirements.txt` 誤裝成 `torch ... +cpu`。

---

## 8. 維護說明

例行維護項目：
- 定期備份 data/ 與 models/ 資料夾。
- 監控服務日誌（logs/）與容器狀態（docker ps、docker logs）。
- 定期更新相依套件與安全性修補，但先在測試環境驗證再套用到生產環境。
- 若使用 GPU，監控 GPU 利用率與記憶體使用情況以避免資源耗盡。

升級流程建議：
1. 在測試環境拉最新程式碼並執行測試。
2. 更新相依套件並在測試環境跑完整工作流程。
3. 在維護時段將服務移到維護模式，備份資料後在生產環境部署更新。

---

## 9. 常見問題（FAQ）與排除步驟

Q1：服務啟動失敗或崩潰
- 檢查日誌檔（logs/ 或 docker logs <container>），確認錯誤訊息。
- 確認 config.yaml 與環境變數是否設定正確，是否有埠衝突。

Q2：Docker 容器啟動但服務不回應
- 檢查容器內的應用是否已啟動（docker exec -it <container> bash 並查看進程）。
- 檢查網路設定與映射的埠是否正確（docker ps 與 docker inspect）。

Q3：GPU 在容器中不可見
- 確認宿主機 `nvidia-smi` 可用，且安裝 NVIDIA Container Toolkit。
- 使用 `docker run --gpus all nvidia/cuda:... nvidia-smi` 驗證容器是否能看到 GPU。

Q4：套件相依性或版本不相容
- 使用 `requirements.txt` 建立隔離的虛擬環境並安裝依賴。
- 若使用 GPU，加倍注意 PyTorch/TF 與 CUDA 的版本相容表。
- Windows + NVIDIA GPU 若看到 `torch.cuda.is_available() == False`，請在專案根目錄執行：
  `python -m pip install --upgrade --force-reinstall -r requirements.windows-cuda.txt --prefer-binary`

Q5：資料遺失或權限問題
- 確認資料目錄（data/）權限，避免服務無法讀寫。
- 經常備份並測試備份還原程序。

---

## 10. 聯絡與回報流程

- 若為一般操作或使用問題，請先提供：錯誤日誌片段、config.yaml（不包含任何機密）、操作步驟與時間點。
- 若為緊急系統中斷，請先依排錯清單（檢查容器、日誌、網路埠）收集資訊，並通知開發/維運團隊進行深入調查。

---

附錄：
- 常用命令速查：
  - 建置：docker build -t project-name .
  - 啟動（compose）：docker-compose up -d
  - 停止（compose）：docker-compose down
  - 日誌：docker logs -f <container>
  - 檢查 GPU：nvidia-smi

- 重要檔案位置（以專案根目錄為基準）：
  - main.py
  - src/（程式碼）
  - config.yaml
  - requirements.txt
  - docker/（如存在）

結語：
本手冊提供日常操作與常見問題的快速指南，若需針對細節（例如 config.yaml 的確切欄位或 Dockerfile 設定）做深入說明，請提供該檔案內容或授權檢視後進一步產出實作步驟。
